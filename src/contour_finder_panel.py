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
# TODO: a very interesting feature that is missing is the ability to switch between showing the true overview image and showing the preprocessed image, with contours on top.
#       This may let us better understand the behavior of the gradient descent contourizer. What keeps us from adding this feature is that it seems to be hard to add an object
#       to our NavCanvas (always on top) but then move it to underneath the already added slice contours. The NavCanvas API does not seem to support this.

class ContourFinderPanel(wx.Panel):

    def __init__(self, parent, model, canvas, selector):
        wx.Panel.__init__(self, parent, size=(350, -1))
        self._canvas = canvas
        self._model = model
        self._selector = selector  # mixin for handling and tracking slice contour selection
        self._contour_finder = ContourFinder()
        self._prev_polygon = None
        self._preprocessed_image = None

        self._num_slices = 1  # number of new slices to detect by extending a seed slice contour and using the preprocessed overview image which highlights edges

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
        self._save_button = wx.Button(self, wx.ID_ANY, "Save", size = button_size)
        self._save_button.Enable(False)

        self._show_button = wx.Button(self, wx.ID_ANY, "Show", size=button_size)
        self._show_button.Enable(False)

        self._improve_button = wx.Button(self, wx.ID_ANY, "Improve Contours", size = button_size)
        self._improve_button.Enable(False)

        self._jitter_button = wx.Button(self, wx.ID_ANY, "Jitter Contours", size = button_size)  # For testing only
        self._jitter_button.Enable(False)

        self._build_ribbon_button = wx.Button(self, wx.ID_ANY, "Add Slices", size = button_size)  # For testing only
        self._build_ribbon_button.Enable(False)

        self._score_button = wx.Button(self, wx.ID_ANY, "Contour Score", size = button_size)  # For testing only
        self._score_button.Enable(False)

        self.done_button = wx.Button(self, wx.ID_ANY, "Done", size=button_size)  # Not this panel but the ApplicationFame will listen to clicks on this button.

        self.Bind(wx.EVT_BUTTON, self._on_preprocess_button_click, preprocess_button)
        self.Bind(wx.EVT_BUTTON, self._on_jitter_button_click, self._jitter_button)
        self.Bind(wx.EVT_BUTTON, self._on_score_button_click, self._score_button)
        self.Bind(wx.EVT_BUTTON, self._on_improve_button_click, self._improve_button)
        self.Bind(wx.EVT_BUTTON, self._on_load_button_click, load_button)
        self.Bind(wx.EVT_BUTTON, self._on_save_button_click, self._save_button)
        self.Bind(wx.EVT_BUTTON, self._on_show_button_click, self._show_button)
        self.Bind(wx.EVT_BUTTON, self._on_build_ribbon_button_click, self._build_ribbon_button)

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
        contours_sizer.Add(parameters_sizer, 0, wx.ALL | wx.CENTER, 5)
        contours_sizer.Add(self._improve_button, 0, wx.ALL | wx.CENTER, 5)

        preprocessing_box = wx.StaticBox(self, -1, 'Preprocessing')
        preprocessing_sizer = wx.StaticBoxSizer(preprocessing_box, wx.VERTICAL)
        preprocessing_sizer.Add(preprocess_button, 0, wx.BOTTOM | wx.CENTER, 5)
        preprocessing_sizer.Add(load_button, 0, wx.BOTTOM | wx.CENTER, 5)
        preprocessing_sizer.Add(self._save_button, 0, wx.BOTTOM | wx.CENTER, 5)
        preprocessing_sizer.Add(self._show_button, 0, wx.BOTTOM | wx.CENTER, 5)

        debugging_box = wx.StaticBox(self, -1, 'Debugging')
        debugging_sizer = wx.StaticBoxSizer(debugging_box, wx.VERTICAL)
        debugging_sizer.Add(self._jitter_button, 0, wx.ALL | wx.CENTER, 5)
        debugging_sizer.Add(self._score_button, 0, wx.ALL | wx.CENTER, 5)

        self._num_slices_edit = wx.TextCtrl(self, wx.ID_ANY, str(self._num_slices), size=(w, -1))
        self.Bind(wx.EVT_TEXT, self._on_num_slices_change, self._num_slices_edit)

        ribbon_params_sizer = wx.FlexGridSizer(cols=2, vgap=4, hgap=14)
        ribbon_params_sizer.Add(wx.StaticText(self, wx.ID_ANY, "Number of new slices:"), flag=wx.LEFT | wx.ALIGN_RIGHT)
        ribbon_params_sizer.Add(self._num_slices_edit, flag=wx.RIGHT)

        ribbon_box = wx.StaticBox(self, -1, 'Ribbon')
        ribbon_sizer = wx.StaticBoxSizer(ribbon_box, wx.VERTICAL)
        ribbon_sizer.Add(ribbon_params_sizer, 0, wx.ALL | wx.CENTER, 5)
        ribbon_sizer.Add(self._build_ribbon_button, 0, wx.ALL | wx.CENTER, 5)

        b = 2  # border size
        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(title, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(separator, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(preprocessing_sizer, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(contours_sizer, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(ribbon_sizer, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(debugging_sizer, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(self.done_button, 0, wx.ALL | wx.CENTER, border=b)

        self.SetSizer(contents)
        contents.Fit(self)

    def activate(self):
        pass

    def deactivate(self):
        pass

    def _on_num_slices_change(self, event):
        self._num_slices = int(self._num_slices_edit.GetValue())
        print('_num_slices={}'.format(self._num_slices))

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

    def _on_score_button_click(self, event):
        print('Contour score: {} = {} + {} + {} + {}'.format(0, 0, 0, 0, 0))

    def _on_load_button_click(self, event):
        # Read preprocessed version of "20x_lens\bisstitched-0.tif" where contrast was enhanced, edges were amplified and then blurred to make gradient descent work better.
        # preprocessed_path = 'E:\\git\\bits\\bioimaging\\Secom\\tomo\\data\\20x_lens\\bisstitched-0-contrast-enhanced-mexicanhat_separable_radius40.tif'  # works
        preprocessed_path = 'E:\\git\\bits\\bioimaging\\Secom\\tomo\\data\\20x_lens\\bisstitched-0-contrast-enhanced-mexicanhat_separable_radius20-gaussianblur20pix.tif'  # also works (better?)
        # IMPROVEME: remember the most recently used preprocessed image path

        path = preprocessed_path
        defaultDir = os.path.dirname(path)
        defaultFile = os.path.basename(path)
        with wx.FileDialog(None, "Select the preprocessed overview image",
                           defaultDir, defaultFile,
                           wildcard="TIFF files (*.tif;*.tiff)|*.tif;*.tiff|PNG files (*.png)|*.png|JPEG files (*.jpg;*.jpeg)|*.jpg;*.jpeg",
                           style=wx.FD_OPEN) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()

                print('Loading preprocessed overview image {}'.format(path))
                image = tools.read_image_as_grayscale(path)

                # The images we preprocessed with Fiji had edges that were XXXcolorXXX
                # but our active contours algorithm needs them to be XXXcolorXXXX, so invert it.
                # FIXME - instead invert those few preprocessed images from Fiji!
                assert image.dtype == np.uint8
                self._preprocessed_image = 255 - image

                self._got_preprocessed_image()

    def _on_save_button_click(self, event):
        defaultDir = ''
        defaultFile = 'preprocessed.tif'
        with wx.FileDialog(self, "Specify name of preprocessed overview image",
                           defaultDir, defaultFile,
                           wildcard="TIFF files (*.tif;*.tiff)|*.tif;*.tiff",
                           style=wx.FD_SAVE) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                success = tools.save_image(self._preprocessed_image, path)
                assert success  # IMPROVEME: pop up dialog on failure
                print('Preprocessed overview image saved to {}'.format(path))

    def _on_preprocess_button_click(self, event):

        img = tools.read_image_as_grayscale(self._model.overview_image_path,
                                            cv2.IMREAD_GRAYSCALE + cv2.IMREAD_ANYDEPTH)  # IMREAD_ANYDEPTH to preserve as 16 bit

        # IMPROVEME: while the preprocess() code at first sight ought to be able to work with 8-bit images,
        #            it does not seem to produce nice preprocessed edge images. With 16-bit image it does seem to work,
        #            so for now we convert 8-bit to 16-bit here, but we need to understand what's wrong with the 8-bit code path.
        if img.dtype == np.uint8:
            img = img.astype(np.uint16) * 257

        with PreprocessDialog(img, self._model, None, wx.ID_ANY, "Preprocess Overview Image") as dlg:
            dlg.CenterOnScreen()
            if dlg.ShowModal() == wx.OK:
                wait = wx.BusyInfo("Preprocessing {}x{} pixel overview image...".format(img.shape[1], img.shape[0]))
                dlg.preprocess(img)
                self._preprocessed_image = dlg.get_preprocessed_image()
                del wait

                self._got_preprocessed_image()

    def _got_preprocessed_image(self):
        # Display the preprocessed image (either loaded or just calculated)
        show_preprocessed_image(self._preprocessed_image)

        self._show_button.Enable(True)
        self._save_button.Enable(True)
        self._improve_button.Enable(True)
        self._build_ribbon_button.Enable(True)
        self._jitter_button.Enable(True)
        self._score_button.Enable(True)

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

    def _flipY(self, contour):
        """
        :param contour: a list of coordinate pairs: [(x, y), ...]
        :return: a new list with the y coordinated inverted (to transform between canvas and image coordinates)
        """
        return [(x, -y) for (x, y) in contour]

    def _add_jitter(self, contour, max_delta):
        """
        :param contour: a list of coordinate pairs: [(x, y), ...] representing the slice contour vertices in ccw order
        :param max_delta:
        :return:
        """
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

    def _on_build_ribbon_button_click(self, event):

        self._contour_finder.set_optimization_parameters(self.h_for_gradient_approximation,
                                                         self.max_iterations,
                                                         self.vertex_distance_threshold,
                                                         self.gradient_step_size,
                                                         self.edge_sample_distance)

        selected_slice_indices = self._selector.get_selected_slices()
        selected_slice_indices = selected_slice_indices[-2:]   # normally only one or two slices should be selected, if more are selected, then we take the last two.

        # IMPROVEME: make sure to disable the 'build ribbon' button if there are more than 2 selected slices (for that we will need the pubsub mechanism to listen to selection changes)

        # Collect the actual slice contours of the slices with the given indices.
        slices = [self._model.slice_polygons[i] for i in selected_slice_indices]

        # convert from [(x,y)] to [np.array] for easier calculations on point vectors
        slices = [[np.array(vertex) for vertex in slic] for slic in slices]

        slic, mat = _ribbon_building_bootstrap(slices)
        for i in range(self._num_slices):
            # Predict an approximate next slice (approximate shape and approximate position)
            new_slice = _transform_slice(slic, mat)
            self._draw_contour(new_slice, "Blue")

            # Use gradient descent to find the true location and shape of the next slice,
            # in the neighborhood of our approximation.
            new_slice_tup = [(x, y) for (x, y) in
                             new_slice]  # convert from numpy arrays to (x,y) pairs   # FIXME: avoid this by letting optimize_contour accept numpy arrays as vertices
            new_slice = self._contour_finder.optimize_contour(self._preprocessed_image, new_slice_tup)
            slice_for_model = new_slice
            new_slice = [np.array(vertex) for vertex in new_slice]  # convert from [(x,y)] to [np.array] for easier calculations on point vectors

            # Add to model and update canvas.
            self._model.slice_polygons.extend([slice_for_model])
            self._canvas.set_slice_polygons(self._model.slice_polygons)
            self._canvas.redraw(True)

            # XXX
            mat = _estimate_transformation(slic, new_slice)
            slic = new_slice


def _ribbon_building_bootstrap(slices):
    assert len(slices) == 1 or len(slices) == 2
    if len(slices) == 1:
        mat = _estimate_initial_transformation(slices[0])
        slic = slices[0]
    else:
        mat = _estimate_transformation(slices[0], slices[1])
        slic = slices[1]

    return slic, mat


def _estimate_initial_transformation(slice):
    mid_bottom = (slice[0] + slice[1]) / 2.0
    mid_top = (slice[2] + slice[3]) / 2.0

    translation = mid_bottom - mid_top
    rotation = 0  # TODO? Or is just a translation actually good enough because of the active contours step afterwards?

    return _build_transformation_matrix(translation, rotation)


def _estimate_transformation(slice1, slice2):
    """
    XXX
    :param slice1: num
    :param slice2:
    :return: a tuple (translation, rotation), where translation is the translation from slice1 to slice 2,
             and rotation the rotation in degrees clockwise to transform slice1 into slice2.
             Note that the transformation is only approximate, since slice2 will not be a rigid transformation of slice1
    """

    # estime translation
    mid_top1 = (slice1[2] + slice1[3]) / 2.0
    mid_top2 = (slice2[2] + slice2[3]) / 2.0
    translation = mid_top2 - mid_top1

    # estimation rotation from angle between top1 en top2, in degrees
    rotation = 0  # TODO? Or is just a translation actually good enough because of the active contours step afterwards?

    return _build_transformation_matrix(translation, rotation)


def _build_transformation_matrix(translation, angle_degrees):  # CHECKME: degrees cw or ccw?
    tx, ty = translation
    # FIXME: handle rotation
    mat = np.array([[1.0, 0, tx],
                    [0, 1.0, ty],
                    [0, 0, 1]])

    return mat


def _transform_slice(slice, mat):
    """
    :param slice: a list of four 2x1 numpy arrays, one for each vertex in the slice outline
    :param mat: the transformation matrix
    :return: the transformed slice outline (as list of numpy arrays)
    """

    # Make homogeneous coordinates
    slice = [np.array([x, y, 1.0]) for (x, y) in slice]

    # Transform each vertex in the slice outline
    slice = [np.dot(mat, vertex) for vertex in slice]

    # From homogeneous coordinates back to *whataretheycalled?*, so drop the final 1
    # (Also, but not obvious here: convert from numpy array to (x, y) pair as vertex representation)
    return [vertex[0:2] for vertex in slice]


def show_preprocessed_image(image, window='Preprocessed Overview Image', max_height=1080-100, max_width=1920-100):
    height, width = image.shape
    scalew = float(max_width) / width
    scaleh = float(max_height) / height
    scale = min(1.0, min(scalew, scaleh))  # scale uniformly, and only scale down, never up
    image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    cv2.namedWindow(window)
    cv2.imshow(window, image)