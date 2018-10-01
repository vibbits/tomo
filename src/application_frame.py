# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx
from wx.lib.pubsub import pub
from wx.lib.floatcanvas import FloatCanvas

import numpy as np
import cv2

import polygon_simplification
import tools
import mapping
from model import TomoModel
from preferences_dialog import PreferencesDialog
from overview_image_dialog import OverviewImageDialog
from lm_acquisition_dialog import LMAcquisitionDialog
from em_acquisition_dialog import EMAcquisitionDialog
from overview_panel import OverviewPanel
from ribbon_outline_dialog import RibbonOutlineDialog
from ribbons_mask_dialog import RibbonsMaskDialog
from point_of_interest_dialog import PointOfInterestDialog
from segmentation_panel import SegmentationPanel
from ribbon_splitter import segment_contours_into_slices, draw_contour_numbers

class ApplicationFrame(wx.Frame):
    _model = None

    _image_panel = None
    _status_label = None

    # Menu
    _import_overview_image_item = None
    _load_slice_polygons_item = None
    _lm_image_acquisition_item = None
    _em_image_acquisition_item = None
    _load_ribbons_mask_item = None

    def __init__(self, parent, ID, title, size = (1024, 1024), pos = wx.DefaultPosition):
        wx.Frame.__init__(self, parent, ID, title, pos, size)
        self.SetBackgroundColour(wx.Colour(240, 240, 240))  # TODO: the same default background color as for wx.Dialog - can we set it automatically, or via some style?

        self._model = TomoModel()

        # Menu
        menu_bar = wx.MenuBar()

        file_menu = wx.Menu()
        self._import_overview_image_item = file_menu.Append(wx.NewId(), "Import Overview Image...")
        self._load_slice_polygons_item = file_menu.Append(wx.NewId(), "Load Slice Polygons...")
        self._load_slice_polygons_item.Enable(False)
        self._load_ribbons_mask_item = file_menu.Append(wx.NewId(), "Load Ribbons Mask...")
        self._load_slice_polygons_item.Enable(True)
        exit_menu_item = file_menu.Append(wx.NewId(), "Exit")

        edit_menu = wx.Menu()
        prefs_menu_item = edit_menu.Append(wx.NewId(), "Preferences...")

        microscope_menu = wx.Menu()
        self._set_point_of_interest_item = microscope_menu.Append(wx.NewId(), "Set point of interest...")
        self._set_point_of_interest_item.Enable(False)
        self._lm_image_acquisition_item = microscope_menu.Append(wx.NewId(), "Acquire LM Images...")
        self._lm_image_acquisition_item.Enable(False)
        self._em_image_acquisition_item = microscope_menu.Append(wx.NewId(), "Acquire EM Images...")
        self._em_image_acquisition_item.Enable(False)

        menu_bar.Append(file_menu, "&File")
        menu_bar.Append(edit_menu, "&Edit")
        menu_bar.Append(microscope_menu, "&Microscope")

        self.Bind(wx.EVT_MENU, self._on_exit, exit_menu_item)
        self.Bind(wx.EVT_MENU, self._on_edit_preferences, prefs_menu_item)
        self.Bind(wx.EVT_MENU, self._on_import_overview_image, self._import_overview_image_item)
        self.Bind(wx.EVT_MENU, self._on_load_slice_polygons, self._load_slice_polygons_item)
        self.Bind(wx.EVT_MENU, self._on_set_point_of_interest, self._set_point_of_interest_item)
        self.Bind(wx.EVT_MENU, self._on_lm_image_acquisition, self._lm_image_acquisition_item)
        self.Bind(wx.EVT_MENU, self._on_em_image_acquisition, self._em_image_acquisition_item)
        self.Bind(wx.EVT_MENU, self._on_load_ribbons_mask, self._load_ribbons_mask_item)

        self.SetMenuBar(menu_bar)

        self._status_label = wx.StaticText(self, wx.ID_ANY, "")

        # Image Panel
        self._image_panel = OverviewPanel(self)
        self._image_panel.Bind(FloatCanvas.EVT_MOTION, self._on_mouse_move_over_image)

        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(self._image_panel, 1, wx.ALL | wx.EXPAND, border = 5) # note: proportion=1 here is crucial, 0 will not work
        contents.Add(self._status_label, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT, border = 5)
        self.SetSizer(contents)

        # TODO: IMPORTANT improvement: especially for the numeric fields, deal with situation where the input field is
        # temporarily empty (while entering a number), and also forbid leaving the edit field if the value is not acceptable (or replace it with the last acceptable value)

        pub.subscribe(self._do_import_overview_image, 'overviewimage.import')
        pub.subscribe(self._do_load_slice_polygons, 'slicepolygons.load')
        pub.subscribe(self._do_load_ribbons_mask, 'ribbonsmask.load')
        pub.subscribe(self._do_set_point_of_interest, 'pointofinterest.set')
        pub.subscribe(self._do_lm_acquire, 'lm.acquire')
        pub.subscribe(self._do_em_acquire, 'em.acquire')

    def _on_mouse_move_over_image(self, event):
        self._status_label.SetLabelText("Pos: %i, %i" % (event.Coords[0], -event.Coords[1]))  # flip y so we have the y-axis pointing down and (0,0)= top left corner of the image

    def _on_import_overview_image(self, event):
        dlg = OverviewImageDialog(self._model, None, wx.ID_ANY, "Overview Image")
        dlg.CenterOnScreen()
        dlg.Show(True)

    def _on_load_slice_polygons(self, event):
        dlg = RibbonOutlineDialog(self._model, None, wx.ID_ANY, "Slice Polygons")
        dlg.CenterOnScreen()
        dlg.Show(True)

    def _on_load_ribbons_mask(self, event):
        dlg = RibbonsMaskDialog(self._model, None, wx.ID_ANY, "Ribbons Mask")
        dlg.CenterOnScreen()
        dlg.Show(True)

    def _on_edit_preferences(self, event):
        dlg = PreferencesDialog(self._model, None, wx.ID_ANY, "Preferences")
        dlg.CenterOnScreen()
        dlg.Show(True)

    def _on_set_point_of_interest(self, event):
        dlg = PointOfInterestDialog(self._model, None, wx.ID_ANY, "Point of Interest in First Slice")
        dlg.CenterOnScreen()
        dlg.Show(True)

    def _on_lm_image_acquisition(self, event):
        dlg = LMAcquisitionDialog(self._model, None, wx.ID_ANY, "Acquire LM Images")
        dlg.CenterOnScreen()
        dlg.Show(True)

    def _on_em_image_acquisition(self, event):
        dlg = EMAcquisitionDialog(self._model, None, wx.ID_ANY, "Acquire EM Images")
        dlg.CenterOnScreen()
        dlg.Show(True)

    def _on_exit(self, event):
        self.Close()

    def _do_import_overview_image(self):
        # Display overview image pixel size information
        overview_image_pixelsize_in_microns = 1000.0 / self._model.overview_image_mm_per_pixel
        print('Overview image pixel size = {} micrometer = {} mm per pixel'.format(overview_image_pixelsize_in_microns,
                                                                                   self._model.overview_image_mm_per_pixel))

        # Add and draw the overview image
        self._image_panel.remove_image()
        self._image_panel.add_image(self._model.overview_image_path)
        self._image_panel.zoom_to_fit()

        # Enable the menu item for loading the slice outlines
        # (We can now use it because we've got the pixel size of the overview image (really needed????))
        self._load_slice_polygons_item.Enable(True)

    def _do_load_slice_polygons(self):
        # Read slice polygon coordinates
        self._model.slice_polygons = tools.json_load_polygons(self._model.slice_polygons_path)
        print('Loaded {} slice polygons from {}'.format(len(self._model.slice_polygons), self._model.slice_polygons_path))

        # Add and draw the slice outlines
        self._image_panel.add_slice_outlines(self._model.slice_polygons)
        self._image_panel.redraw()

        # Enable the menu item for acquiring LM images
        # (We can now use it because we've got POIs)
        self._load_slice_polygons_item.Enable(False)  # We cannot import a polygons file multiple times right now
        self._set_point_of_interest_item.Enable(True)

    @staticmethod
    def _find_ribbons(ribbons_mask_path):
        img = tools.read_image(ribbons_mask_path)
        print(f'Ribbons mask image: shape={img.shape} type={img.dtype}')

        # e.g. our test image E:\git\bits\bioimaging\Secom\tomo\data\10x_lens\SET_6stitched-0_10xlens_ribbons_mask.tif
        #      has background pixels with value 0, and foreground pixels (=the ribbons) with value 255

        # CHECKME Convert to grayscale, needed for findContours???
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Invert the image. CHECKME findContours expect foreground to be 0? 255? and background to be value 0? 255?
        img_gray = (255-img_gray)

        # Find the contours
        if (cv2.__version__[0] == '2'):
            ribbons, _ = cv2.findContours(img_gray, cv2.RETR_LIST, method = cv2.CHAIN_APPROX_SIMPLE)
        else:
            _, ribbons, _ = cv2.findContours(img_gray, cv2.RETR_LIST, method = cv2.CHAIN_APPROX_SIMPLE)

        # Note: findContours(..., cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE) returns a list of numpy arrays of shape (numvertices, 1, 2)
        print(f'Found {len(ribbons)} ribbons')

        return (img, ribbons)

    @staticmethod
    def _load_template_slice(filename):
        # Returns a list of (x,y) coordinates of the slice vertices
        # template_slice_contour = [( 760, 1404), (1572, 1435), (1474,  880), ( 808,  857)]
        polygons = tools.json_load_polygons(filename)
        assert(len(polygons) == 1)
        return polygons[0]

    def _do_load_ribbons_mask(self):
        print('_do_load_ribbons_mask')

        frame = wx.Frame(self, wx.ID_ANY, "Ribbon Segmentation", size = (1024, 1024))
        segm_panel = SegmentationPanel(frame)
        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(segm_panel, 1, wx.EXPAND)
        frame.SetSizer(contents)
        frame.CenterOnScreen()
        frame.Show(True)

        # TODO: maybe draw the ribbons mask transparently over the overview image?
        segm_panel.add_image(self._model.ribbons_mask_path)
        segm_panel.redraw()

        template_slice_contour = ApplicationFrame._load_template_slice(self._model.template_slice_path)
        segm_panel.add_polygon(template_slice_contour, "Green", line_width = 4)
        segm_panel.add_text("template", tools.polygon_center(template_slice_contour), "Green", font_size = 100)
        segm_panel.redraw()

        wx.Yield()  # give wxPython opportunity to redraw the frame

        # ribbon splitting code: "F:\Manual Backups\Ubuntu_26sep2018\development\DetectSlices\SplitRibbon\SplitRibbon.py"
        # OpenCV watershed: https://docs.opencv.org/3.1.0/d3/db4/tutorial_py_watershed.html (maybe it can be used to imitate Fiji > Process > Binary > Watershed ?)

        (img, ribbons) = ApplicationFrame._find_ribbons(self._model.ribbons_mask_path)
        ribbons = [tools.opencv_contour_to_list(ribbon) for ribbon in ribbons]

        # TODO - we should probably do the segmentation ribbon by ribbon, and only afterwards combine the different slices.
        # TODO: try to implement Fiji-style watershed segmentation of binary images
        #
        print('Simplifying ribbon contours. May be slow, please be patient.')
        wait = wx.BusyInfo("Simplifying contours. Please wait...")
        green = (0, 255, 0)
        simplified_ribbons = []
        for ribbon in ribbons:
            estimated_num_slices_in_ribbon = round(tools.polygon_area(ribbon) / tools.polygon_area(template_slice_contour))
            print(f'Estimated number of slices in ribbon: {estimated_num_slices_in_ribbon}')
            desired_num_vertices_in_ribbon = estimated_num_slices_in_ribbon * 6  # we want at least 4 points per slice, plus some extra to handle accidental dents in the slice shape
            simplified_ribbon = polygon_simplification.reduce_polygon(ribbon, desired_num_vertices_in_ribbon)
            simplified_ribbons.append(simplified_ribbon)
        del wait

        # Perform greedy/optimal split of ribbon
        wait = wx.BusyInfo("Segmenting ribbons into slices. Please wait...")
        simplified_ribbons_opencv = [tools.list_to_opencv_contour(rib) for rib in simplified_ribbons]
        rbns = segment_contours_into_slices(simplified_ribbons_opencv, template_slice_contour, junk_contours = [], greedy = False)
        del wait

        # Merge slices of each ribbon in one single list of slices
        slices = [tools.opencv_contour_to_list(slc) for rbn in rbns for slc in rbn]  # Flatten the list with ribbons with slices, into a list of slices.

        # Reorder slices in probable order
        # TODO

        # Simplify each slice
        # TODO: check if it is possible to end up with a slice that has fewer than 4 vertices...
        simplify_slices = True
        if simplify_slices:
            slices = [polygon_simplification.reduce_polygon(slice, 4) for slice in slices]

        # Save slices to JSON
        filename = r'E:\git\bits\bioimaging\Secom\tomo\data\10x_lens\auto_slices.json'
        print(f'Saving segmented slices to {filename}')
        tools.json_save_polygons(filename, slices)

        # Show each slice, with slice numbers
        for i, slice in enumerate(slices):
            segm_panel.add_polygon(slice, "Red", line_width = 2)
            segm_panel.add_text(str(i), tools.polygon_center(slice), "Red", font_size = 100)
        segm_panel.redraw()

        print('...Done...')

        # TODOs
        # 1: load template slice quad coords (later: let the user define one interactively) (TODO: add path to dialog)
        # 2: extract ribbons outlines
        # 3: simplify ribbons outlines to ~#slices x 4or5 points   (we can estimate the #slices from the ribbon area / template area)
        # 4: apply greedy or best splitting of simplified ribbon outline   (TODO: add best/greedy/watershed choice to dialog)
        # 5: simplify each split slice to exactly 4 points (some may have a few more)
        # 6: save slice outlines to JSON for later use

    def _do_set_point_of_interest(self):
        # Transform point-of-interest from one slice to the next
        original_point_of_interest = self._model.original_point_of_interest
        print('Original point-of-interest: x={} y={}'.format(*original_point_of_interest))
        transformed_points_of_interest = mapping.repeatedly_transform_point(self._model.slice_polygons, original_point_of_interest)
        self._model.all_points_of_interest = [original_point_of_interest] + transformed_points_of_interest

        # Draw the points of interest
        self._image_panel.remove_points_of_interest()
        self._image_panel.add_points_of_interest(self._model.all_points_of_interest)
        self._image_panel.redraw()

        # Enable/disable menu entries
        self._lm_image_acquisition_item.Enable(True)   # we've got points of interest now, so we can acquire LM images

    def _do_lm_acquire(self):
        # Calculate the physical displacements on the sample required for moving between the points of interest.
        overview_image_pixelsize_in_microns = 1000.0 / self._model.overview_image_mm_per_pixel
        self._model.slice_offsets_microns = tools.physical_point_of_interest_offsets_in_microns(self._model.all_points_of_interest,
                                                                                                overview_image_pixelsize_in_microns)
        print('Rough offset from slice polygons (in microns): ' + repr(self._model.slice_offsets_microns))

        # Now acquire an LM image at the point of interest location in each slice.
        tools.acquire_microscope_images('LM',
                                        self._model.slice_offsets_microns, self._model.delay_between_LM_image_acquisition_secs,
                                        self._model.odemis_cli, self._model.lm_images_output_folder, self._model.lm_images_prefix)

        # Have Fiji execute a macro for aligning the LM images
        # using Fiji's Plugins > Registration > Linear Stack Alignment with SIFT
        # https://imagej.net/Headless#Running_macros_in_headless_mode
        print('Aligning LM images')
        print('Starting a headless Fiji and calling the SIFT image registration plugin. Please be patient...')
        retcode, out, err = tools.commandline_exec(
            [self._model.fiji_path, "-Dpython.console.encoding=UTF-8", "--ij2", "--headless", "--console", "--run",
             self._model.sift_registration_script,
             "srcdir='{}',dstdir='{}',prefix='{}'".format(self._model.sift_input_folder, self._model.sift_output_folder, self._model.lm_images_prefix)])
        print('retcode={}\nstdout=\n{}\nstderr={}\n'.format(retcode, out, err))

        # Parse the output of the SIFT registration plugin and extract
        # the transformation matrices to register each slice onto the next.
        print('Extracting SIFT transformation for fine slice transformation')
        sift_matrices = tools.extract_sift_alignment_matrices(out)
        print(sift_matrices)

        # In sift_registration.py we asked for translation only transformations.
        # So our matrices should be pure translations. Extract the last column (=the offset) and convert from pixel
        # coordinates to physical distances on the sample.
        # (We also add a (0,0) offset for the first slice.)
        sift_images_pixelsize_in_microns = 1000.0 / self._model.sift_images_mm_per_pixel
        sift_offsets_microns = [np.array([0, 0])] + [mat[:, 2] * sift_images_pixelsize_in_microns for mat in
                                                     sift_matrices]
        print('Fine SIFT offset (in microns): ' + repr(sift_offsets_microns))

        # Invert y of the SIFT offsets
        sift_offsets_microns = [np.array([offset[0], -offset[1]]) for offset in sift_offsets_microns]
        print('Fine SIFT offset y-inverted (in microns): ' + repr(sift_offsets_microns))

        # Combine (=sum) the rough translations obtained by mapping the slice polygons (of a x10 or x20 overview image)
        # onto one another with the fine corrections obtained by SIFT registration of (x100) light microscopy images.
        self._model.combined_offsets_microns = [trf_pair[0] + trf_pair[1] for i, trf_pair in
                                                enumerate(zip(self._model.slice_offsets_microns, sift_offsets_microns))]
        print('Rough offset from slice polygons + fine SIFT offset (in microns): ' + repr(self._model.combined_offsets_microns))

        # Show overview of the offsets
        tools.show_offsets_table(self._model.slice_offsets_microns, sift_offsets_microns, self._model.combined_offsets_microns)

        # Enable/disable menu entries
        self._em_image_acquisition_item.Enable(True)
        self._lm_image_acquisition_item.Enable(False)

    def _do_em_acquire(self):
        # Calculate the cumulative movement of the stage from the point of interest on the first slice
        # to the point of interest on the last slice. (This movement occurred while acquiring LM images).
        total_movement = sum(self._model.combined_offsets_microns)

        # Move the stage back to the point of interest on the first slice.
        # so can then acquire EM images on those same points of interest in the different slices
        # but using the more accurate offsets.
        print('Move stage back to point of interest in first slice')
        tools.move_stage(self._model.odemis_cli, -total_movement)

        # Now acquire an EM image at the samen point of interest location in each slice,
        # but use the more accurate stage offsets (obtained from slice mapping + SIFT registration).
        tools.acquire_microscope_images('EM',
                                        self._model.combined_offsets_microns, self._model.delay_between_EM_image_acquisition_secs,
                                        self._model.odemis_cli, self._model.em_images_output_folder, self._model.em_images_prefix)

        # Enable/disable menu entries
        self._em_image_acquisition_item.Enable(False)