import wx
import wx.grid
import tools
from contour_finder import ContourFinder
import numpy as np
import random
import cv2
import os
from preprocess_dialog import PreprocessDialog

# FIXME: if we are in the contour editing tool, the currently selected contours will have handles; if we then jitter or optimize the contour,
#        the contour gets updated, but not the handles.
# IMPROVEME: The model should publish changes and the canvas and some tools should listen to changes to the model and update itself when needed

class ContourFinderPanel(wx.Panel):

    def __init__(self, parent, model, canvas, selector):
        wx.Panel.__init__(self, parent, size = (350, -1))
        self._canvas = canvas
        self._model = model
        self._selector = selector  # mixin for handling and tracking slice contour selection
        self._contour_finder = ContourFinder()
        self._prev_polygon = None
        self._preprocessed_image = None

        # Contour energy minimization parameters
        # TODO: combine into a structure, this class already has too many member variables
        self.h_for_gradient_approximation = 1.0
        self.max_iterations = 100
        self.vertex_distance_threshold = 0.5
        self.gradient_step_size = 5e-3
        self.edge_sample_distance = 100.0

        # Build UI
        title = wx.StaticText(self, wx.ID_ANY, "Slices finder")
        title.SetFont(wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.BOLD))
        separator = wx.StaticLine(self, wx.ID_ANY)

        # Contour energy minimization edit fields
        w = 40
        self._h_for_gradient_approximation_edit = wx.TextCtrl(self, wx.ID_ANY, str(self.h_for_gradient_approximation), size=(w, -1))
        self._max_iterations_edit = wx.TextCtrl(self, wx.ID_ANY, str(self.max_iterations), size=(w, -1))
        self._vertex_distance_threshold_edit = wx.TextCtrl(self, wx.ID_ANY, str(self.vertex_distance_threshold), size=(w, -1))
        self._gradient_step_size_edit = wx.TextCtrl(self, wx.ID_ANY, str(self.gradient_step_size), size=(w, -1))
        self._edge_sample_distance_edit = wx.TextCtrl(self, wx.ID_ANY, str(self.edge_sample_distance), size=(w, -1))

        self.Bind(wx.EVT_TEXT, self._on_h_for_gradient_approximation_change, self._h_for_gradient_approximation_edit)
        self.Bind(wx.EVT_TEXT, self._on_max_iterations_change, self._max_iterations_edit)
        self.Bind(wx.EVT_TEXT, self._on_gradient_step_size_change, self._gradient_step_size_edit)
        self.Bind(wx.EVT_TEXT, self._on_edge_sample_distance_change, self._edge_sample_distance_edit)
        self.Bind(wx.EVT_TEXT, self._on_vertex_distance_threshold_change, self._vertex_distance_threshold_edit)

        # Buttons
        button_size = (125, -1)

        preprocess_button = wx.Button(self, wx.ID_ANY, "Preprocess", size = button_size)
        load_button = wx.Button(self, wx.ID_ANY, "Load", size = button_size)

        self._show_button = wx.Button(self, wx.ID_ANY, "Show", size=button_size)
        self._show_button.Enable(False)

        self._improve_button = wx.Button(self, wx.ID_ANY, "Improve Contours", size = button_size)
        self._improve_button.Enable(False)

        self._jitter_button = wx.Button(self, wx.ID_ANY, "Jitter Contours", size = button_size)  # For testing only
        self._jitter_button.Enable(False)

        self.done_button = wx.Button(self, wx.ID_ANY, "Done", size=button_size)  # Not this panel but the ApplicationFame will listen to clicks on this button.

        self.Bind(wx.EVT_BUTTON, self._on_preprocess_button_click, preprocess_button)
        self.Bind(wx.EVT_BUTTON, self._on_jitter_button_click, self._jitter_button)
        self.Bind(wx.EVT_BUTTON, self._on_improve_button_click, self._improve_button)
        self.Bind(wx.EVT_BUTTON, self._on_load_button_click, load_button)
        self.Bind(wx.EVT_BUTTON, self._on_show_button_click, self._show_button)

        parameters_sizer = wx.FlexGridSizer(cols=2, vgap=4, hgap=14)
        parameters_sizer.Add(wx.StaticText(self, wx.ID_ANY, "Gradient estimation h:"), flag=wx.LEFT | wx.ALIGN_RIGHT)
        parameters_sizer.Add(self._h_for_gradient_approximation_edit, flag=wx.RIGHT)
        parameters_sizer.Add(wx.StaticText(self, wx.ID_ANY, "Max iterations:"), flag=wx.LEFT | wx.ALIGN_RIGHT)
        parameters_sizer.Add(self._max_iterations_edit, flag=wx.RIGHT)
        parameters_sizer.Add(wx.StaticText(self, wx.ID_ANY, "Gradient descent step size:"), flag=wx.LEFT | wx.ALIGN_RIGHT)
        parameters_sizer.Add(self._gradient_step_size_edit, flag=wx.RIGHT)
        parameters_sizer.Add(wx.StaticText(self, wx.ID_ANY, "Edge sample distance:"), flag=wx.LEFT | wx.ALIGN_RIGHT)
        parameters_sizer.Add(self._edge_sample_distance_edit, flag=wx.RIGHT)
        parameters_sizer.Add(wx.StaticText(self, wx.ID_ANY, "Vertex distance threshold:"), flag=wx.LEFT | wx.ALIGN_RIGHT)
        parameters_sizer.Add(self._vertex_distance_threshold_edit, flag=wx.RIGHT)

        contours_box = wx.StaticBox(self, -1, 'Contours')
        contours_sizer = wx.StaticBoxSizer(contours_box, wx.VERTICAL)
        contours_sizer.Add(parameters_sizer, 0, wx.ALL | wx.CENTER, 10)
        contours_sizer.Add(self._improve_button, 0, wx.ALL | wx.CENTER, 10)

        preprocessing_box = wx.StaticBox(self, -1, 'Preprocessing')
        preprocessing_sizer = wx.StaticBoxSizer(preprocessing_box, wx.VERTICAL)
        preprocessing_sizer.Add(preprocess_button, 0, wx.ALL | wx.CENTER, 10)
        preprocessing_sizer.Add(load_button, 0, wx.ALL | wx.CENTER, 10)
        preprocessing_sizer.Add(self._show_button, 0, wx.ALL | wx.CENTER, 10)

        debugging_box = wx.StaticBox(self, -1, 'Debugging')
        debugging_sizer = wx.StaticBoxSizer(debugging_box, wx.VERTICAL)
        debugging_sizer.Add(self._jitter_button, 0, wx.ALL | wx.CENTER, 10)

        b = 5  # border size
        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(title, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(separator, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(preprocessing_sizer, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(contours_sizer, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(debugging_sizer, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(self.done_button, 0, wx.ALL | wx.CENTER, border=b)

        self.SetSizer(contents)
        contents.Fit(self)

    def activate(self):
        pass

    def deactivate(self):
        pass

    def _on_h_for_gradient_approximation_change(self, event):
        self.h_for_gradient_approximation = float(self._h_for_gradient_approximation_edit.GetValue())
        print('h_for_gradient_approximation={}'.format(self.h_for_gradient_approximation))

    def _on_max_iterations_change(self, event):
        self.max_iterations = float(self._max_iterations_edit.GetValue())
        print('max_iterations={}'.format(self.max_iterations))

    def _on_gradient_step_size_change(self, event):
        self.gradient_step_size = float(self._gradient_step_size_edit.GetValue())
        print('gradient_step_size={}'.format(self.gradient_step_size))

    def _on_edge_sample_distance_change(self, event):
        self.edge_sample_distance = float(self._edge_sample_distance_edit.GetValue())
        print('edge_sample_distance={}'.format(self.edge_sample_distance))

    def _on_vertex_distance_threshold_change(self, event):
        self.vertex_distance_threshold = float(self._vertex_distance_threshold_edit.GetValue())
        print('vertex_distance_threshold={}'.format(self.vertex_distance_threshold))

    def _on_load_button_click(self, event):
        # Read preprocessed version of "20x_lens\bisstitched-0.tif" where contrast was enhanced, edges were amplified and then blurred to make gradient descent work better.
        # preprocessed_path = 'E:\\git\\bits\\bioimaging\\Secom\\tomo\\data\\20x_lens\\bisstitched-0-contrast-enhanced-mexicanhat_separable_radius40.tif'  # WORKS
        preprocessed_path = 'E:\\git\\bits\\bioimaging\\Secom\\tomo\\data\\20x_lens\\bisstitched-0-contrast-enhanced-mexicanhat_separable_radius20-gaussianblur20pix.tif'  # WORKS BETTER?

        path = preprocessed_path
        defaultDir = os.path.dirname(path)
        defaultFile = os.path.basename(path)
        with wx.FileDialog(None, "Select the preprocessed overview image",
                           defaultDir, defaultFile,
                           wildcard="TIFF files (*.tif;*.tiff)|*.tif;*.tiff|PNG files (*.png)|*.png|JPEG files (*.jpg;*.jpeg)|*.jpg;*.jpeg",
                           style=wx.FD_OPEN) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()

                print('Should preprocess {} but instead we will just read the result {}'.format(self._model.overview_image_path, path))
                image = tools.read_image_as_grayscale(path)

                # The images we preprocessed with Fiji had edges that were XXXcolorXXX
                # but our active contours algorithm needs them to be XXXcolorXXXX, so invert it.
                assert image.dtype == np.uint8
                self._preprocessed_image = 255 - image

                self._preprocessing_done()

    def _on_preprocess_button_click(self, event):

        img = tools.read_image_as_grayscale(self._model.overview_image_path,
                                            cv2.IMREAD_GRAYSCALE + cv2.IMREAD_ANYDEPTH)  # IMREAD_ANYDEPTH to preserve as 16 bit

        with PreprocessDialog(img, self._model, None, wx.ID_ANY, "Preprocess Overview Image") as dlg:
            dlg.CenterOnScreen()
            if dlg.ShowModal() == wx.OK:
                wait = wx.BusyInfo("Preprocessing {}x{} pixel overview image...".format(img.shape[1], img.shape[0]))
                dlg.preprocess(img)
                self._preprocessed_image = dlg.get_preprocessed_image()
                del wait

                self._preprocessing_done()

    def _preprocessing_done(self):
        # Display the loaded preprocessed image
        show_preprocessed_image(self._preprocessed_image)

        self._improve_button.Enable(True)
        self._jitter_button.Enable(True)
        self._show_button.Enable(True)

    def _on_show_button_click(self, event):
        show_preprocessed_image(self._preprocessed_image)

    def _duplicate_polygons(self, polygon, displacement_vector, num_copies):
        # displacement_vector = np.array[dx,dy]
        assert num_copies >= 0
        return [polygon + (i + 1) * displacement_vector for i in range(num_copies)]

    def _on_jitter_button_click(self, event):
        selected_slices = self._selector.get_selected_slices()
        for i in selected_slices:
            polygon = self._model.slice_polygons[i]
            jittered_polygon = self._add_jitter(polygon, 80)
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
        self._contour_finder.set_optimization_parameters(self.h_for_gradient_approximation,
                                                         self.max_iterations,
                                                         self.vertex_distance_threshold,
                                                         self.gradient_step_size,
                                                         self.edge_sample_distance)

        selected_slices = self._selector.get_selected_slices()
        for i in selected_slices:
            polygon = self._model.slice_polygons[i]
            optimized_polygon = self._contour_finder.optimize_contour(self._preprocessed_image, polygon)
            # self._draw_contour(optimized_polygon, "Red", remove_previous=False)
            self._model.slice_polygons[i] = optimized_polygon  # update model
            self._canvas.set_slice_outline(i, self._flipY(optimized_polygon))  # update canvas
            self._canvas.redraw(True)

    def _draw_contour(self, contour, color = "Green", remove_previous=False):
        pts = [(p[0], -p[1]) for p in contour]
        if remove_previous and (self._prev_polygon is not None):
            self._canvas.remove_objects([self._prev_polygon])
        self._prev_polygon = self._canvas.Canvas.AddPolygon(pts, LineColor=color)
        self._canvas.Canvas.Draw()


def show_preprocessed_image(image, window='Preprocessed Overview Image', max_height=1080-100, max_width=1920-100):
    height, width = image.shape
    scalew = float(max_width) / width
    scaleh = float(max_height) / height
    scale = min(1.0, min(scalew, scaleh))  # scale uniformly, and only scale down, never up
    image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    cv2.namedWindow(window)
    cv2.imshow(window, image)