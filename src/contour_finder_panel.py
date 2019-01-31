import wx
import wx.grid
import tools
from contour_finder import ContourFinder
import numpy as np
import random

import matplotlib
matplotlib.use('wxagg')
import matplotlib.pyplot as plt

# IMPROVEME: add a Settings panel with the ContourFinder optimization parameters
# IMPROVEME: add settings for preprocessing the overview image (edge enhancement) ?
# FIXME: if we are in the contour editing tool, the currently selected contours will have handles; if we then jitter or optimize the contour, the contour gets updated, but not the handles
# The model should publish changes and the canvas and some tools should listen to changes to the model and update itself when needed

class ContourFinderPanel(wx.Panel):
    _canvas = None
    _model = None

    done_button = None
    _improve_button = None

    _contour_finder = None
    _preprocessed_image = None
    _prev_polygon = None

    def __init__(self, parent, model, canvas, selector):
        wx.Panel.__init__(self, parent, size = (350, -1))
        self._canvas = canvas
        self._model = model
        self._selector = selector  # mixin for handling and tracking slice contour selection
        self._contour_finder = ContourFinder()

        title = wx.StaticText(self, wx.ID_ANY, "Slices finder")
        title.SetFont(wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.BOLD))
        separator = wx.StaticLine(self, wx.ID_ANY)

        label = wx.StaticText(self, wx.ID_ANY, "Just a little experiment for now.")
        label.Wrap(330)  # force line wrapping

        button_size = (125, -1)

        preprocess_button = wx.Button(self, wx.ID_ANY, "Preprocess", size = button_size)

        self._improve_button = wx.Button(self, wx.ID_ANY, "Improve Contours", size = button_size)
        self._improve_button.Enable(False)

        self._jitter_button = wx.Button(self, wx.ID_ANY, "Jitter Contours", size = button_size)  # For testing only
        self._jitter_button.Enable(False)

        self._jitter_test_button = wx.Button(self, wx.ID_ANY, "Jitter Test", size = button_size)  # For testing only
        self._jitter_test_button.Enable(False)

        self.done_button = wx.Button(self, wx.ID_ANY, "Done",
                                     size=button_size)  # Not this panel but the ApplicationFame will listen to clicks on this button.

        self.Bind(wx.EVT_BUTTON, self._on_preprocess_button_click, preprocess_button)
        self.Bind(wx.EVT_BUTTON, self._on_jitter_button_click, self._jitter_button)
        self.Bind(wx.EVT_BUTTON, self._on_improve_button_click, self._improve_button)
        self.Bind(wx.EVT_BUTTON, self._on_jitter_test_button_click, self._jitter_test_button)

        b = 5  # border size
        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(title, 0, wx.ALL | wx.EXPAND, border = b)
        contents.Add(separator, 0, wx.ALL | wx.EXPAND, border = b)
        contents.Add(label, 0, wx.ALL | wx.EXPAND, border = b)
        contents.Add(preprocess_button, 0, wx.ALL | wx.CENTER, border = b)
        contents.Add(self._improve_button, 0, wx.ALL | wx.CENTER, border = b)
        contents.Add(self._jitter_button, 0, wx.ALL | wx.CENTER, border = b)
        contents.Add(self._jitter_test_button, 0, wx.ALL | wx.CENTER, border = b)
        contents.Add(self.done_button, 0, wx.ALL | wx.CENTER, border = b)

        self.SetSizer(contents)
        contents.Fit(self)

    def activate(self):
        pass

    def deactivate(self):
        pass

    def _on_preprocess_button_click(self, event):
        self._preprocessed_image = self._contour_finder.preprocess_image(self._model.overview_image_path)

        # invert so we can then maximize the amount of black pixels "collected" by the edges
        # (after inversion, white will be close to 0, and black pixels >> 0)
        self._preprocessed_image = 255 - self._preprocessed_image

        self._improve_button.Enable(True)
        self._jitter_button.Enable(True)
        self._jitter_test_button.Enable(True)

    def _duplicate_polygons(self, polygon, displacement_vector, num_copies):
        # displacement_vector = np.array[dx,dy]
        assert num_copies >= 0
        return [polygon + (i + 1) * displacement_vector for i in range(num_copies)]

    def _on_jitter_button_click(self, event):
        selected_slices = self._selector.get_selected_slices()
        for i in selected_slices:
            polygon = self._model.slice_polygons[i]
            jittered_polygon = self._add_jitter(polygon, 100)
            self._model.slice_polygons[i] = jittered_polygon  # update model
            self._canvas.set_slice_outline(i, self._flipY(jittered_polygon))  # update canvas
            # self._draw_contour(polygon, "Blue", False)  # Draw original polygon
            self._canvas.redraw(True)

    def _flipY(self, contour):  # contour is a list of coordinate pairs: [(x, y), ...]; return a new list with the y coordinated inverted (to transform between canvas and image coordinates)
        return [(x, -y) for (x, y) in contour]

    def _add_jitter(self, contour, max_delta):   # contour is a list of coordinate pairs: [(x, y), ...]
        return [(x + random.randint(-max_delta, max_delta),
                 y + random.randint(-max_delta, max_delta))
                for (x, y) in contour]

    def _on_improve_button_click(self, event):

        self._contour_finder.set_optimization_parameters(h_for_gradient_approximation=1.0, max_iterations=50,
                                                         gradient_step_size=5e-3, edge_sample_distance=50.0)

        selected_slices = self._selector.get_selected_slices()
        for i in selected_slices:
            polygon = self._model.slice_polygons[i]
            optimized_polygon = self._contour_finder.optimize_contour(self._preprocessed_image, polygon)
            # self._draw_contour(optimized_polygon, "Red", remove_previous=False)
            self._model.slice_polygons[i] = optimized_polygon  # update model
            self._canvas.set_slice_outline(i, self._flipY(optimized_polygon))  # update canvas
            self._canvas.redraw(True)

    def _on_jitter_test_button_click(self, event):
        slice_polygons = tools.json_load_polygons(self._model.slice_polygons_path)
        print('Loaded {} slice polygons from {}'.format(len(slice_polygons), self._model.slice_polygons_path))
        polygon = slice_polygons[0]

        self._contour_finder = ContourFinder()
        self._preprocessed_image = tools.read_image_as_grayscale('E:\\git\\bits\\bioimaging\\Secom\\tomo\\data\\20x_lens\\bisstitched-0-contrast-enhanced-mexicanhat_separable_radius40.tif')
        self._sample_score_for_contour_with_displaced_vertex(polygon)

    def _draw_contour(self, contour, color = "Green", remove_previous=False):
        pts = [(p[0], -p[1]) for p in contour]
        if remove_previous and (self._prev_polygon is not None):
            self._canvas.remove_objects([self._prev_polygon])
        self._prev_polygon = self._canvas.Canvas.AddPolygon(pts, LineColor=color)
        self._canvas.Canvas.Draw()

    def _draw(self):
        img = self._preprocessed_image
        y = 1147
        values = [img[y,x] for x in range(1300, 3300)]
        plt.plot(values)
        plt.title('Image samples')
        plt.show(block=False)

    def _sample_score_for_contour_with_displaced_vertex(self, contour, max_delta=50):
        print('Calculating the score of a contour that gets deformed by displacing one of its vertices. This takes a little while...')

        xrange = range(-max_delta, max_delta)
        yrange = range(-max_delta, max_delta)
        nx = len(xrange)
        ny = len(yrange)
        scores = np.zeros((ny, nx))
        for i, dx in enumerate(xrange):
            for j, dy in enumerate(yrange):
                # displace the first vertex of the contour
                contour_vec = self._contour_finder.contour_to_vector(contour)
                contour_vec[0] += dx
                contour_vec[1] += dy

                # for debugging, plot the tweaked contour
                # cnt = self._cf.vector_to_contour(contour_vec)
                # self._draw_contour(cnt, "Red", True)

                # calculate the modified contour's score
                scores[j, i] = self._contour_finder.calculate_contour_score(self._preprocessed_image, contour_vec)

        # Plot the scores of the contours for each displacement.
        # The scores are shown as a colored image where the x and y axis
        # represent the displacement of the vertex, and the color the resulting contour score.
        # On top of this image lines of identical scores are drawn.
        extent = [-max_delta, max_delta, -max_delta, max_delta]
        fig, ax = plt.subplots()
        cs = ax.contour(xrange, yrange, scores, colors='k', extent=extent, origin='lower')
        im = ax.imshow(scores, cmap=plt.cm.Reds, interpolation='none', extent=extent, origin='lower')
        ax.clabel(cs, inline=1, fontsize=10)
        fig.colorbar(im)
        plt.title('Deformed contour score')
        plt.show(block=False)

