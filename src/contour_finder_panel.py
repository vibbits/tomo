import wx
import tools
from contour_finder import ContourFinder
from contour_finder import contour_to_vector
import numpy as np
import random
import cv2
import os
from preprocess_dialog import PreprocessDialog
import matplotlib
matplotlib.use('wxagg')
from matplotlib import pyplot as plt

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
        self._preprocessed_overview_image = None

        # Ribbon building
        self._num_slices = 1  # number of new slices to detect by extending a seed slice contour and using the preprocessed overview image which highlights edges
        self._max_score_drop_ratio = 0.65

        # Contour energy minimization parameters
        # TODO: combine into a structure, this class already has too many member variables
        self.h_for_gradient_approximation = 1.0
        self.max_iterations = 100
        self.vertex_distance_threshold = 0.5
        self.gradient_step_size = 5e-3
        self.edge_sample_distance = 10.0
        self.verbose = False

        self._set_contour_finder_options()

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

        preprocess_button = wx.Button(self, wx.ID_ANY, "Preprocess", size=button_size)
        load_button = wx.Button(self, wx.ID_ANY, "Load", size=button_size)
        self._save_button = wx.Button(self, wx.ID_ANY, "Save", size=button_size)
        self._save_button.Enable(False)

        self._show_button = wx.Button(self, wx.ID_ANY, "Show", size=button_size)
        self._show_button.Enable(False)

        self._improve_button = wx.Button(self, wx.ID_ANY, "Improve Contours", size=button_size)
        self._improve_button.Enable(False)

        self._jitter_button = wx.Button(self, wx.ID_ANY, "Jitter Contours", size=button_size)
        self._jitter_button.Enable(False)

        self._add_slices_button = wx.Button(self, wx.ID_ANY, "Add Slices", size=button_size)
        self._add_slices_button.Enable(False)

        self._complete_ribbon_button = wx.Button(self, wx.ID_ANY, "Complete Ribbon", size=button_size)
        self._complete_ribbon_button.Enable(False)

        self._print_score_button = wx.Button(self, wx.ID_ANY, "Print Contour Score", size=button_size)
        self._print_score_button.Enable(False)

        self._plot_score_button = wx.Button(self, wx.ID_ANY, "Plot Contour Score", size=button_size)
        self._plot_score_button.Enable(False)

        verbose_checkbox = wx.CheckBox(self, wx.ID_ANY, label="Verbose")
        verbose_checkbox.SetValue(self.verbose)

        self.done_button = wx.Button(self, wx.ID_ANY, "Done", size=button_size)  # Not this panel but the ApplicationFame will listen to clicks on this button.

        self.Bind(wx.EVT_BUTTON, self._on_preprocess_button_click, preprocess_button)
        self.Bind(wx.EVT_BUTTON, self._on_jitter_button_click, self._jitter_button)
        self.Bind(wx.EVT_BUTTON, self._on_print_score_button_click, self._print_score_button)
        self.Bind(wx.EVT_BUTTON, self._on_plot_score_button_click, self._plot_score_button)
        self.Bind(wx.EVT_BUTTON, self._on_improve_button_click, self._improve_button)
        self.Bind(wx.EVT_BUTTON, self._on_load_button_click, load_button)
        self.Bind(wx.EVT_BUTTON, self._on_save_button_click, self._save_button)
        self.Bind(wx.EVT_BUTTON, self._on_show_button_click, self._show_button)
        self.Bind(wx.EVT_BUTTON, self._on_add_slices_button_click, self._add_slices_button)
        self.Bind(wx.EVT_BUTTON, self._on_complete_ribbon_button_click, self._complete_ribbon_button)
        self.Bind(wx.EVT_CHECKBOX, self._on_verbose_checkbox, verbose_checkbox)

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
        debugging_sizer.Add(verbose_checkbox, 0, wx.ALL | wx.CENTER, 5)
        debugging_sizer.Add(self._print_score_button, 0, wx.ALL | wx.CENTER, 5)
        debugging_sizer.Add(self._plot_score_button, 0, wx.ALL | wx.CENTER, 5)
        debugging_sizer.Add(self._jitter_button, 0, wx.ALL | wx.CENTER, 5)

        self._num_slices_edit = wx.TextCtrl(self, wx.ID_ANY, str(self._num_slices), size=(w, -1))
        self.Bind(wx.EVT_TEXT, self._on_num_slices_change, self._num_slices_edit)

        add_slices_params_sizer = wx.FlexGridSizer(cols=2, vgap=4, hgap=14)
        add_slices_params_sizer.Add(wx.StaticText(self, wx.ID_ANY, "Number of new slices:"), flag=wx.LEFT | wx.ALIGN_RIGHT)
        add_slices_params_sizer.Add(self._num_slices_edit, flag=wx.RIGHT)

        self._max_score_drop_edit = wx.TextCtrl(self, wx.ID_ANY, str(self._max_score_drop_ratio), size=(w, -1))
        self.Bind(wx.EVT_TEXT, self._on_max_score_drop_change, self._max_score_drop_edit)

        complete_ribbon_params_sizer = wx.FlexGridSizer(cols=2, vgap=4, hgap=14)
        complete_ribbon_params_sizer.Add(wx.StaticText(self, wx.ID_ANY, "Max score drop (ratio):"), flag=wx.LEFT | wx.ALIGN_RIGHT)
        complete_ribbon_params_sizer.Add(self._max_score_drop_edit, flag=wx.RIGHT)

        ribbon_box = wx.StaticBox(self, -1, 'Ribbon')
        ribbon_sizer = wx.StaticBoxSizer(ribbon_box, wx.VERTICAL)
        ribbon_sizer.Add(complete_ribbon_params_sizer, 0, wx.ALL | wx.CENTER, 5)
        ribbon_sizer.Add(self._complete_ribbon_button, 0, wx.ALL | wx.CENTER, 5)
        ribbon_sizer.Add(wx.StaticLine(self, wx.ID_ANY))
        ribbon_sizer.Add(add_slices_params_sizer, 0, wx.ALL | wx.CENTER, 5)
        ribbon_sizer.Add(self._add_slices_button, 0, wx.ALL | wx.CENTER, 5)

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

    def _set_contour_finder_options(self):
        self._contour_finder.set_optimization_parameters(self.h_for_gradient_approximation,
                                                         self.max_iterations,
                                                         self.vertex_distance_threshold,
                                                         self.gradient_step_size,
                                                         self.edge_sample_distance,
                                                         self.verbose)

    def _on_verbose_checkbox(self, event):
        self.verbose = event.GetEventObject().GetValue()
        print('verbose={}'.format(self.verbose))

    def _on_num_slices_change(self, event):
        self._num_slices = int(self._num_slices_edit.GetValue())
        print('_num_slices={}'.format(self._num_slices))

    def _on_max_score_drop_change(self, event):
        val = float(self._max_score_drop_edit.GetValue())
        self._max_score_drop_ratio = min(max(0.0, val), 1.0)  # the score drop is a ratio, clamp to 0,1 TODO: use a validator instead?
        print('_max_score_drop_ratio={}'.format(self._max_score_drop_ratio))

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

    def _on_print_score_button_click(self, event):
        # Print the contour score for all selected slices. The higher the score the better the contour is supposed to
        # match the actual slice outline.
        selected_slices = self._selector.get_selected_slices()
        for i in selected_slices:
            contour = self._model.slice_polygons[i]
            contour_vector = contour_to_vector(contour)
            score_samples = self._contour_finder.calculate_contour_score_samples(self._preprocessed_overview_image, contour_vector)
            edge_scores = [np.sum(edge_samples) for edge_samples in score_samples]
            assert len(edge_scores) == 4
            s1, s2, s3, s4 = edge_scores[0], edge_scores[1], edge_scores[2], edge_scores[3]
            print('Slice #{} score = {:.1f} = {:.1f} + {:.1f} + {:.1f} + {:.1f}'.format(i+1, s1 + s2 + s3 + s4, s1, s2, s3, s4))

    def _on_plot_score_button_click(self, event):
        selected_slices = self._selector.get_selected_slices()
        if len(selected_slices) == 1:  # IMPROVEME? enable/disable the plot score button depending on # contours selected
            idx = selected_slices[0]
            contour = self._model.slice_polygons[idx]
            contour_vector = contour_to_vector(contour)
            sample_scores = self._contour_finder.calculate_contour_score_samples(self._preprocessed_overview_image, contour_vector)
            plot_contour_sample_scores(idx + 1, sample_scores)
        else:
            print('Please select a single contour whose score samples need to be plotted.')

    def _on_load_button_click(self, event):
        # Read preprocessed version of "20x_lens\bisstitched-0.tif" where contrast was enhanced, edges were amplified and then blurred to make gradient descent work better.
        # preprocessed_path = 'E:\\git\\bits\\bioimaging\\Secom\\tomo\\data\\20x_lens\\bisstitched-0-contrast-enhanced-mexicanhat_separable_radius40-inverted.tif'  # works
        # preprocessed_path = 'E:\\git\\bits\\bioimaging\\Secom\\tomo\\data\\20x_lens\\bisstitched-0-contrast-enhanced-mexicanhat_separable_radius20-gaussianblur20pix-inverted.tif'  # also works (better?)

        path = self._model.preprocessed_overview_image_path
        defaultDir = os.path.dirname(path)
        defaultFile = os.path.basename(path)
        with wx.FileDialog(None, "Select the preprocessed overview image",
                           defaultDir, defaultFile,
                           wildcard="TIFF files (*.tif;*.tiff)|*.tif;*.tiff|PNG files (*.png)|*.png|JPEG files (*.jpg;*.jpeg)|*.jpg;*.jpeg",
                           style=wx.FD_OPEN) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self._model.preprocessed_overview_image_path = dlg.GetPath()
                self._model.write_parameters()  # remember path as default for later
                wait = wx.BusyInfo("Loading preprocessed overview image...".format(self._model.preprocessed_overview_image_path))
                self._preprocessed_overview_image = tools.read_image_as_grayscale(self._model.preprocessed_overview_image_path)
                del wait
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
                success = tools.save_image(self._preprocessed_overview_image, path)
                assert success  # IMPROVEME: pop up dialog informing the user about success or failure of saving
                print('Preprocessed overview image saved to {}'.format(path))

    def _on_preprocess_button_click(self, event):
        wait = wx.BusyInfo("Loading {}".format(self._model.overview_image_path))
        # Read the overview image at its full bit depth
        # (We already have it in memory, but only as 8-bit.)
        img = tools.read_image_as_grayscale(self._model.overview_image_path,
                                            cv2.IMREAD_GRAYSCALE + cv2.IMREAD_ANYDEPTH)  # IMREAD_ANYDEPTH to preserve as 16 bit
        del wait

        # IMPROVEME: while the preprocess() code at first sight ought to be able to work with 8-bit images,
        #            it does not seem to produce nice preprocessed edge images. With 16-bit image it does seem to work,
        #            so for now we convert 8-bit to 16-bit here, but we need to understand what's wrong with the 8-bit code path.
        if img.dtype == np.uint8:
            img = img.astype(np.uint16) * 257

        with PreprocessDialog(img, self._model, None, wx.ID_ANY, "Preprocess Overview Image") as dlg:
            dlg.CenterOnScreen()
            if dlg.ShowModal() == wx.OK:
                wait = wx.BusyInfo("Preprocessing {} x {} pixels overview image...".format(img.shape[1], img.shape[0]))
                dlg.preprocess(img)
                self._preprocessed_overview_image = dlg.get_preprocessed_image()
                del wait
                self._got_preprocessed_image()

    def _got_preprocessed_image(self):
        # Display the preprocessed image (either loaded or just calculated)
        display_image(self._preprocessed_overview_image)

        self._show_button.Enable(True)
        self._save_button.Enable(True)
        self._improve_button.Enable(True)
        self._add_slices_button.Enable(True)
        self._complete_ribbon_button.Enable(True)
        self._jitter_button.Enable(True)
        self._print_score_button.Enable(True)
        self._plot_score_button.Enable(True)

    def _on_show_button_click(self, event):
        display_image(self._preprocessed_overview_image)

    def _duplicate_polygons(self, polygon, displacement_vector, num_copies):
        # displacement_vector = np.array[dx,dy]
        assert num_copies >= 0
        return [polygon + (i + 1) * displacement_vector for i in range(num_copies)]

    def _on_jitter_button_click(self, event):
        MAX_JITTER_DISTANCE = 80  # in x and in y
        selected_slices = self._selector.get_selected_slices()
        for i in selected_slices:
            polygon = self._model.slice_polygons[i]
            jittered_polygon = self._add_jitter(polygon, MAX_JITTER_DISTANCE)
            self._model.set_slice_polygon(i, jittered_polygon)  # update model
            self._canvas.set_slice_outline(i, self._flipY(jittered_polygon))  # update canvas
            self._canvas.redraw(True)

    def _flipY(self, contour):
        """
        Transform the contour from canvas coordinates (y-axis pointing up) to image coordinates (y-axis pointing down).

        :param contour: a list of vertex coordinates [(x, y)] representing the contour in canvas coordinates
        :return: the contour in image coordinates: [(x, -y)]
        """
        return [(x, -y) for (x, y) in contour]

    def _add_jitter(self, contour, max_delta):
        """
        Randomly perturb a contour.

        :param contour: a list of coordinate pairs: [(x, y), ...] representing the slice contour vertices in ccw order
        :param max_delta: maximum vertical or horizontal random displacement of the contour vertices
        :return: the perturbed contour, as a list of vertex coordinates [(x,y)]
        """
        return [(x + random.randint(-max_delta, max_delta),
                 y + random.randint(-max_delta, max_delta))
                for (x, y) in contour]

    def _on_improve_button_click(self, event):
        self._set_contour_finder_options()

        selected_slices = self._selector.get_selected_slices()
        for i in selected_slices:
            polygon = self._model.slice_polygons[i]
            optimized_polygon = self._contour_finder.optimize_contour(self._preprocessed_overview_image, polygon)
            self._model.set_slice_polygon(i, optimized_polygon)  # update model
            self._canvas.set_slice_outline(i, self._flipY(optimized_polygon))  # update canvas  # TODO? listen to model changes instead?
            self._canvas.redraw(True)

    def _on_complete_ribbon_button_click(self, event):
        self._grow_ribbon(complete_ribbon=True)

    def _on_add_slices_button_click(self, event):
        self._grow_ribbon(complete_ribbon=False)

    def _grow_ribbon(self, complete_ribbon):
        """
        Grow one or two selected "seed" slices into a ribbon of slices.
        
        :param complete_ribbon: boolean, if True then we will keep on adding new slices until its scores becomes too low,
        if False then we will add at most self._num_slices (and also stop if the score of a new slice is too low)
        """

        self._set_contour_finder_options()

        selected_slice_indices = self._selector.get_selected_slices()
        selected_slice_indices = selected_slice_indices[
                                 -2:]  # normally only one or two slices should be selected, if more are selected, then we take the last two.

        # IMPROVEME: make sure to disable the 'build ribbon' button if there are more than 2 selected slices (for that we will need the pubsub mechanism to listen to selection changes)

        # Collect the actual slice contours of the slices with the given indices.
        slices = [self._model.slice_polygons[i] for i in selected_slice_indices]

        # convert from [(x,y)] to [np.array] for easier calculations on point vectors
        slices = [[np.array(vertex) for vertex in s] for s in slices]

        old_slice, mat = _ribbon_building_bootstrap(slices)
        i = 0
        while True:
            if not complete_ribbon:
                if i >= self._num_slices:
                    break

            # Predict an approximate next slice (approximate shape and approximate position)
            new_slice = _transform_slice(old_slice, mat)
            self._draw_contour(new_slice, "Blue")

            # Use gradient descent to find the true location and shape of the next slice,
            # in the neighborhood of our approximation.
            new_slice_for_model = self._contour_finder.optimize_contour(self._preprocessed_overview_image, new_slice)

            # Assess if tentative new slice stands a chance of being correct. If not, then terminate ribbon building.
            template_slice = old_slice  # use the previously slice (which turned out to be good) as the template to judge the quality of the new slice
            if self._terminate_ribbon_building(template_slice, new_slice_for_model, self._max_score_drop_ratio):
                print('Tentative new contour of low quality; terminating ribbon building')
                self._draw_contour(new_slice_for_model, "Red")
                # TODO: add debugging option to make ghost drawing optional, and, add ability to delete the ghosts.
                break

            # Add to model and update canvas.
            self._model.slice_polygons.extend([new_slice_for_model])
            self._canvas.set_slice_polygons(self._model.slice_polygons)
            self._canvas.redraw(True)

            # Prepare for estimating the next slice
            new_slice = [np.array(vertex) for vertex in
                         new_slice_for_model]  # convert from [(x,y)] to [np.array([x,y])] for easier calculations on point vectors
            mat = _estimate_transformation(old_slice, new_slice)
            old_slice = new_slice
            i = i + 1

    def _terminate_ribbon_building(self, template_contour, new_contour, max_score_drop_ratio):
        """
        Returns whether to terminate automatic ribbon building because. This may happen because we reached the end of a
        ribbon, or because we failed to track the ribbon correctly (typically because of a sudden break or kink in the ribbon)

        :param template_contour: xxx
        :param new_contour: xxx
        :param max_score_drop_ratio:
        :return: true if the tentative new contour is likely to be an incorrect or spurious slice contour;
                 false if there is a good chance that the new contour matches a real slice outline
        """
        template_scores = np.array(self._edge_scores(template_contour))
        new_scores = np.array(self._edge_scores(new_contour))
        poor_quality = np.any(new_scores < template_scores * max_score_drop_ratio)
        return poor_quality

    def _edge_scores(self, contour):
        sample_scores = self._contour_finder.calculate_contour_score_samples(self._preprocessed_overview_image, contour_to_vector(contour))
        return [np.sum(edge_samples) for edge_samples in sample_scores]

    def _draw_contour(self, contour, color="Green", remove_previous=False):
        pts = [(p[0], -p[1]) for p in contour]
        if remove_previous and (self._prev_polygon is not None):
            self._canvas.remove_objects([self._prev_polygon])
        self._prev_polygon = self._canvas.Canvas.AddPolygon(pts, LineColor=color)
        self._canvas.Canvas.Draw()


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

    # The rotation angle would be:
    # (a) the angle between the top and the bottom edge of the slice
    # plus
    # (b) the angle due to a possible wedge-shaped gap between slices.
    # For now we assume that the top and bottom edge of the slice are parallel (IMPROVE)
    # and the gap cannot be estimated from a single slice. So we assume the rotation angle to be zero for now.
    # rotation_angle = 0

    return _build_transformation_matrix(translation)


def _estimate_transformation(slice1, slice2):
    """
    Estimate a rigid coordinate transformation that approximately maps one slice onto another.

    :param slice1: the source slice, as a list of np.array([x,y]) vertex coordinates
    :param slice2: the target slice (cfr slice1)
    :return: a 3x3 numpy transformation matrix that transforms the coordinates of slice1 into the coordinates of the
             approximate position of slice2, assuming that slice2 is attached at the bottom edge of slice1,
             forming a ribbon. For now the transformation is always a simple translation.
    """

    # Estimate translation
    mid_top1 = (slice1[2] + slice1[3]) / 2.0
    mid_top2 = (slice2[2] + slice2[3]) / 2.0
    translation = mid_top2 - mid_top1

    # Estimate rotation from angle between top1 en top2, in degrees
    # Not yet implemented!
    # rotation_angle = 0

    return _build_transformation_matrix(translation)


def _build_transformation_matrix(translation):
    # Note: if rotation ever needs to be implemented, then we will need both the rotation angle and the rotation
    # center as additional arguments. The full transformation then consists of (1) translating the rotation center to
    # the origin, (2) rotating, (3) translating back, and (4) the translation from one slice to the next.

    tx, ty = translation

    mat = np.array([[1, 0, tx],
                    [0, 1, ty],
                    [0, 0,  1]])
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


def display_image(image, window='Preprocessed Overview Image', max_height=1080 - 100, max_width=1920 - 100):
    """
    Show an image in a window with a given maximum size on screen. The image will be scaled uniformly to fit the
    desired maximum window dimensions.

    :param image: the image to display
    :param window: the window name, can be used to refer to it later, or to update its contents
    :param max_height: maximum height of the image window, in pixels
    :param max_width: maximum width of the image window, in pixels
    """
    height, width = image.shape
    scalew = float(max_width) / width
    scaleh = float(max_height) / height
    scale = min(1.0, min(scalew, scaleh))  # scale uniformly, and only scale down, never up
    image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    cv2.namedWindow(window)
    cv2.imshow(window, image)


def plot_contour_sample_scores(contour_nr, sample_scores):
    # Edge boundaries
    edge_boundaries = np.cumsum([len(edge_samples) for edge_samples in sample_scores]) + 0.5   # 0.5 to draw the boundaries between, not on sample points

    # Collect all samples
    samples = np.sum(sample_scores)  # IMPROVEME: this really only has the effect of just flattening the list of score lists, but sounds as if it does some summation

    # Score per countour edge (information, for title)
    edge_scores = [np.sum(edge_samples) for edge_samples in sample_scores]
    assert len(edge_scores) == 4
    s1, s2, s3, s4 = edge_scores[0], edge_scores[1], edge_scores[2], edge_scores[3]
    title = 'Slice #{} score = {:.1f} = {:.1f} + {:.1f} + {:.1f} + {:.1f}'.format(contour_nr, s1 + s2 + s3 + s4, s1, s2, s3, s4)

    # Plot it all
    plt.figure()
    plt.plot(samples, '+')
    for b in edge_boundaries:
        plt.axvline(b, color='k', linestyle=':')
    plt.title(title)
    plt.show()

