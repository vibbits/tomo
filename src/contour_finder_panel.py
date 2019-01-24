import wx
import wx.grid
import tools
from contour_finder import ContourFinder
import numpy as np

import matplotlib
matplotlib.use('wxagg')
import matplotlib.pyplot as plt

class ContourFinderPanel(wx.Panel):
    _canvas = None
    _model = None

    done_button = None
    _step_button = None

    _contour_finder = None
    _preprocessed_image = None
    _current_contour = None
    _prev_polygon = None

    def __init__(self, parent, model, canvas):
        wx.Panel.__init__(self, parent, size = (350, -1))
        self._canvas = canvas
        self._model = model
        self._contour_finder = ContourFinder()

        title = wx.StaticText(self, wx.ID_ANY, "Slices finder")
        title.SetFont(wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.BOLD))
        separator = wx.StaticLine(self, wx.ID_ANY)

        label = wx.StaticText(self, wx.ID_ANY, "Just a little experiment for now.")
        label.Wrap(330)  # force line wrapping

        button_size = (125, -1)

        preprocess_button = wx.Button(self, wx.ID_ANY, "Preprocess", size = button_size)

        self._start_button = wx.Button(self, wx.ID_ANY, "Jitter Contour", size = button_size)
        self._start_button.Enable(False)

        self._step_button = wx.Button(self, wx.ID_ANY, "Optimize Contour", size = button_size)
        self._step_button.Enable(False)

        self._jitter_test_button = wx.Button(self, wx.ID_ANY, "Jitter test", size = button_size)
        self._jitter_test_button.Enable(False)

        self._duplication_test_button = wx.Button(self, wx.ID_ANY, "Duplication test", size = button_size)
        self._duplication_test_button.Enable(False)

        self.done_button = wx.Button(self, wx.ID_ANY, "Done",
                                     size=button_size)  # Not this panel but the ApplicationFame will listen to clicks on this button.

        self.Bind(wx.EVT_BUTTON, self._on_preprocess_button_click, preprocess_button)
        self.Bind(wx.EVT_BUTTON, self._on_start_button_click, self._start_button)
        self.Bind(wx.EVT_BUTTON, self._on_step_button_click, self._step_button)
        self.Bind(wx.EVT_BUTTON, self._on_jitter_test_button_click, self._jitter_test_button)
        self.Bind(wx.EVT_BUTTON, self._on_duplication_test_button_click, self._duplication_test_button)

        b = 5  # border size
        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(title, 0, wx.ALL | wx.EXPAND, border = b)
        contents.Add(separator, 0, wx.ALL | wx.EXPAND, border = b)
        contents.Add(label, 0, wx.ALL | wx.EXPAND, border = b)
        contents.Add(preprocess_button, 0, wx.ALL | wx.CENTER, border = b)
        contents.Add(self._start_button, 0, wx.ALL | wx.CENTER, border = b)
        contents.Add(self._step_button, 0, wx.ALL | wx.CENTER, border = b)
        contents.Add(self._jitter_test_button, 0, wx.ALL | wx.CENTER, border = b)
        contents.Add(self._duplication_test_button, 0, wx.ALL | wx.CENTER, border = b)
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

        self._start_button.Enable(True)
        self._jitter_test_button.Enable(True)
        self._duplication_test_button.Enable(True)

    def _on_duplication_test_button_click(self, event):
        slice_polygons = tools.json_load_polygons(self._model.slice_polygons_path)
        print('Loaded {} slice polygons from {}'.format(len(slice_polygons), self._model.slice_polygons_path))
        for contour in slice_polygons:
            self._draw_contour(contour, "BLUE", remove_previous=False)

        # Predict slices in the ribbon via simple translation + copy
        slice1 = slice_polygons[0]
        slice2 = slice_polygons[1]
        displacement_vector = slice2[0] - slice1[0]
        num_copies = 9
        new_slices = self._duplicate_polygons(slice1, displacement_vector, num_copies)
        for contour in new_slices:
            self._draw_contour(contour, "GREEN", remove_previous=False)

        # Optimize the approximate contours
        self._contour_finder.set_optimization_parameters(h_for_gradient_approximation=1.0, max_iterations=150,
                                                         gradient_step_size=5e-3, edge_sample_distance=40.0)

        for contour in new_slices:
            optimized_contour = self._contour_finder.optimize_contour(self._preprocessed_image, contour)
            self._draw_contour(optimized_contour, "RED", remove_previous=False)

        # Ribbon 2
        ribbon2_slice1 = np.array([[9679, 2199], [11280, 2039], [10949, 987], [9640, 1113]])
        ribbon2_slice1_bottom_left = ribbon2_slice1[0] # np.array([9679, 2199])
        ribbon2_slice2_bottom_left = np.array([9778, 3282])

        # Predict slices in ribbon 2 via copy and translate from the first (user defined) slice in ribbon 2 and an analogous (user defined) point on slice 2.
        displacement_vector = ribbon2_slice2_bottom_left - ribbon2_slice1_bottom_left
        num_copies = 9
        new_slices = self._duplicate_polygons(ribbon2_slice1, displacement_vector, num_copies)
        for contour in new_slices:
            self._draw_contour(contour, "GREEN", remove_previous=False)

        # Optimize the approximate contours
        for contour in new_slices:
            optimized_contour = self._contour_finder.optimize_contour(self._preprocessed_image, contour)
            self._draw_contour(optimized_contour, "RED", remove_previous=False)

    def _duplicate_polygons(self, polygon, displacement_vector, num_copies):
        # displacement_vector = np.array[dx,dy]
        assert num_copies >= 0
        return [polygon + (i + 1) * displacement_vector for i in range(num_copies)]

    def _on_start_button_click(self, event):
        # Load the user-defined ground truth slice outlines (not really needed, but we can use them for assessing our result)
        slice_polygons = tools.json_load_polygons(self._model.slice_polygons_path)
        print('Loaded {} slice polygons from {}'.format(len(slice_polygons), self._model.slice_polygons_path))
        true_slice1 = slice_polygons[0]
        print(true_slice1)
        # true_slice1 = [(1540, 1886),
        #                (3142, 1931),
        #                (2944,  848),
        #                (1630,  806)]

        score = self._contour_finder.calculate_contour_score(self._preprocessed_image, self._contour_finder.contour_to_vector(true_slice1))
        print('Score of ground truth slice outline={}'.format(score))

        jitter = 100
        self._current_contour = [(1540-jitter, 1886+jitter),
                                 (3142-jitter, 1931),
                                 (2944+jitter,  848+jitter),
                                 (1630,  836-jitter)]  # [(x,y)...]

        self._draw_contour(self._current_contour, "Blue", True)  # initial contour

        self._step_button.Enable(True)

    def _on_step_button_click(self, event):

        self._contour_finder.set_optimization_parameters(h_for_gradient_approximation=1.0, max_iterations=50,
                                                         gradient_step_size=5e-3, edge_sample_distance=50.0)

        optimized_contour = self._contour_finder.optimize_contour(self._preprocessed_image, self._current_contour)

        self._draw_contour(optimized_contour, "Red", remove_previous=True)

        self._current_contour = optimized_contour

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

