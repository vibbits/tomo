# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx
from wx.lib.floatcanvas import FloatCanvas, GUIMode

import numpy as np
import cv2
import platform

import polygon_simplification
import tools
import secom_tools
import resources
from model import TomoModel
from mark_mode import MarkMode
from move_stage_mode import MoveStageMode
from preferences_dialog import PreferencesDialog
from overview_image_dialog import OverviewImageDialog
from lm_acquisition_dialog import LMAcquisitionDialog
from em_acquisition_dialog import EMAcquisitionDialog
from overview_canvas import OverviewCanvas
from ribbon_outline_dialog import RibbonOutlineDialog
from ribbons_mask_dialog import RibbonsMaskDialog
from segmentation_canvas import SegmentationCanvas
from focus_panel import FocusPanel
from contour_finder_panel import ContourFinderPanel
from ribbon_splitter import segment_contours_into_slices, draw_contour_numbers
from stage_alignment_panel import StageAlignmentPanel
from point_of_interest_panel import PointOfInterestPanel
from segmentation_panel import SegmentationPanel
from contour_finder import ContourFinder

class ApplicationFrame(wx.Frame):
    _model = None

    _overview_canvas = None
    _status_label = None
    _focus_panel = None
    _contour_finder_panel = None
    _stage_alignment_panel = None
    _point_of_interest_panel = None
    _segmentation_panel = None

    # Menu
    _import_overview_image_item = None
    _load_slice_polygons_item = None
    _lm_image_acquisition_item = None
    _em_image_acquisition_item = None
    _segment_ribbons_item = None
    _set_point_of_interest_item = None
    _set_focus_item = None
    _about_item = None

    _menu_state = None  # a tuple with enabled/disabled flags for various menu items; used when a side panel is visible and we want to behave in a modal fashion

    def __init__(self, parent, ID, title, size=(1280, 1024), pos = wx.DefaultPosition):
        wx.Frame.__init__(self, parent, ID, title, pos, size)
        self.SetBackgroundColour(wx.Colour(240, 240, 240))  # TODO: the same default background color as for wx.Dialog - can we set it automatically, or via some style?

        self._model = TomoModel()

        # Set application icon
        icon = resources.tomo.GetIcon()
        self.SetIcon(icon)

        # Menu
        menu_bar = self._build_menu_bar()
        self.SetMenuBar(menu_bar)

        # Custom tool modes definition. They will be associated with tools in the toolbar.
        # We can listen to mouse events when such a mode is active.
        custom_modes = [(MarkMode.NAME, MarkMode(self), resources.crosshair.GetBitmap()),
                        (MoveStageMode.NAME, MoveStageMode(self), resources.movestage.GetBitmap())]

        # Image Panel
        self._overview_canvas = OverviewCanvas(self, custom_modes)

        # By default disable the custom modes, they are only active when their corresponding side panel is visible
        for mode in custom_modes:
            tool = self._overview_canvas.FindToolByName(mode[0])
            self._overview_canvas.ToolBar.EnableTool(tool.GetId(), False)

        # Listen to mouse movements so we can show the mouse position in the status bar.
        # We also need to listen to mouse movements when some custom modes are active (since regular FloatCanvas events do not happen then).
        self._overview_canvas.Bind(FloatCanvas.EVT_MOTION, self._on_mouse_move_over_image)
        self._overview_canvas.Bind(MarkMode.EVT_TOMO_MARK_MOTION, self._on_mouse_move_over_image)
        self._overview_canvas.Bind(MoveStageMode.EVT_TOMO_MOVESTAGE_MOTION, self._on_mouse_move_over_image)

        # Status bar at the bottom of the window
        self._status_label = wx.StaticText(self, wx.ID_ANY, "")

        # Focus side panel
        self._focus_panel = FocusPanel(self, self._overview_canvas, self._model)
        self._focus_panel.Show(False)
        self.Bind(wx.EVT_BUTTON, self._on_focus_done_button_click, self._focus_panel.done_button)

        # Contour finder side panel
        self._contour_finder_panel = ContourFinderPanel(self, self._model, self._overview_canvas)
        self._contour_finder_panel.Show(False)
        self.Bind(wx.EVT_BUTTON, self._on_find_contours_done_button_click, self._contour_finder_panel.done_button)

        # Stage alignment side panel
        self._stage_alignment_panel = StageAlignmentPanel(self, self._model, self._overview_canvas)
        self._stage_alignment_panel.Show(False)
        self.Bind(wx.EVT_BUTTON, self._on_stage_alignment_done_button_click, self._stage_alignment_panel.done_button)

        # Point of interest panel
        self._point_of_interest_panel = PointOfInterestPanel(self, self._model, self._overview_canvas)
        self._point_of_interest_panel.Show(False)
        self.Bind(wx.EVT_BUTTON, self._on_point_of_interest_done_button_click, self._point_of_interest_panel.done_button)

        # Segmentation panel
        self._segmentation_panel = SegmentationPanel(self, self._model, self._overview_canvas)
        self._segmentation_panel.Show(False)
        self.Bind(wx.EVT_BUTTON, self._on_segmentation_done_button_click,
                  self._segmentation_panel.done_button)

        # IMPROVEME: rather than adding each side panel separately we probably should add just a single side panel
        #            with a "deck" of side panel cards? Does wxPython have this concept?

        hori = wx.BoxSizer(wx.HORIZONTAL)
        hori.Add(self._overview_canvas, 1, wx.ALL | wx.EXPAND, border=5)
        hori.Add(self._focus_panel, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT, border=5)
        hori.Add(self._contour_finder_panel, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT, border=5)
        hori.Add(self._stage_alignment_panel, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT, border=5)
        hori.Add(self._point_of_interest_panel, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT, border=5)
        hori.Add(self._segmentation_panel, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT, border=5)

        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(hori, 1, wx.EXPAND)  # note: proportion=1 here is crucial, 0 will not work
        contents.Add(self._status_label, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT, border=5)
        self.SetSizer(contents)

        # TODO: IMPORTANT improvement: especially for the numeric fields, deal with situation where the input field is
        # temporarily empty (while entering a number), and also forbid leaving the edit field if the value is not acceptable (or replace it with the last acceptable value)

    def _build_menu_bar(self):
        menu_bar = wx.MenuBar()

        file_menu = wx.Menu()
        self._import_overview_image_item = file_menu.Append(wx.NewId(), "Import Overview Image...")
        self._load_slice_polygons_item = file_menu.Append(wx.NewId(), "Load Slice Polygons...")
        self._load_slice_polygons_item.Enable(False)
        exit_menu_item = file_menu.Append(wx.NewId(), "Exit")

        edit_menu = wx.Menu()
        prefs_menu_item = edit_menu.Append(wx.NewId(), "Preferences...")

        microscope_menu = wx.Menu()
        self._align_stage_item = microscope_menu.Append(wx.NewId(), "Align stage and overview image...")
        self._align_stage_item.Enable(False)
        self._set_point_of_interest_item = microscope_menu.Append(wx.NewId(), "Set point of interest...")
        self._set_point_of_interest_item.Enable(False) # the point of interest is specified in overview image coordinates (so we need an overview image) and will predict analogous points of interest in the other slices (so we need to have slice outlines)
        self._set_focus_item = microscope_menu.Append(wx.NewId(), "Set focus...")
        self._set_focus_item.Enable(False)  # focus setup is only possible after we've aligned stage with overview image (because in the focus mode we can click on the overview image to move the stage to our target point where we want to manually set the focus)
        self._lm_image_acquisition_item = microscope_menu.Append(wx.NewId(), "Acquire LM Images...")
        self._lm_image_acquisition_item.Enable(False)
        self._em_image_acquisition_item = microscope_menu.Append(wx.NewId(), "Acquire EM Images...")
        self._em_image_acquisition_item.Enable(False)

        help_menu = wx.Menu()
        self._about_item = help_menu.Append(wx.NewId(), "About")

        experimental_menu = wx.Menu()
        self._segment_ribbons_item = experimental_menu.Append(wx.NewId(), "Segment Ribbons...")
        self._contour_finder_item = experimental_menu.Append(wx.NewId(), "Find slice contours...")  # gradient descent based slice contour fitting - does not work (yet?)
        self._contour_finder_item.Enable(False)

        menu_bar.Append(file_menu, "&File")
        menu_bar.Append(edit_menu, "&Edit")
        menu_bar.Append(microscope_menu, "&Microscope")
        menu_bar.Append(experimental_menu, "&Experimental")
        menu_bar.Append(help_menu, "&Help")

        self.Bind(wx.EVT_MENU, self._on_exit, exit_menu_item)
        self.Bind(wx.EVT_MENU, self._on_edit_preferences, prefs_menu_item)
        self.Bind(wx.EVT_MENU, self._on_import_overview_image, self._import_overview_image_item)
        self.Bind(wx.EVT_MENU, self._on_load_slice_polygons, self._load_slice_polygons_item)
        self.Bind(wx.EVT_MENU, self._on_set_point_of_interest, self._set_point_of_interest_item)
        self.Bind(wx.EVT_MENU, self._on_align_stage, self._align_stage_item)
        self.Bind(wx.EVT_MENU, self._on_lm_image_acquisition, self._lm_image_acquisition_item)
        self.Bind(wx.EVT_MENU, self._on_em_image_acquisition, self._em_image_acquisition_item)
        self.Bind(wx.EVT_MENU, self._on_segment_ribbons, self._segment_ribbons_item)
        self.Bind(wx.EVT_MENU, self._on_find_contours, self._contour_finder_item)
        self.Bind(wx.EVT_MENU, self._on_set_focus, self._set_focus_item)
        self.Bind(wx.EVT_MENU, self._on_about, self._about_item)

        return menu_bar

    def _on_mouse_move_over_image(self, event):
        x =  int(round(event.Coords[0]))
        y = -int(round(event.Coords[1]))  # flip y so we have the y-axis pointing down and (0,0)= top left corner of the image
        self._status_label.SetLabelText("x: {:d} y: {:d}".format(x, y))
        event.Skip()  # we're just observing the mouse moves, so pass on the event
        # IMPROVEME: when the mouse moves outside the image area, then clear the status label text, otherwise it displays some confusing irrelevant coordinate

    def _on_import_overview_image(self, event):
        with OverviewImageDialog(self._model, None, wx.ID_ANY, "Overview Image") as dlg:
            dlg.CenterOnScreen()
            if dlg.ShowModal() == wx.ID_OK:
                self._do_import_overview_image()

    def _on_load_slice_polygons(self, event):
        with RibbonOutlineDialog(self._model, None, wx.ID_ANY, "Slice Polygons") as dlg:
            dlg.CenterOnScreen()
            if dlg.ShowModal() == wx.ID_OK:
                self._do_load_slice_polygons()

    def _on_segment_ribbons(self, event):
        self._show_side_panel(self._segmentation_panel, True)

    def _on_segmentation_done_button_click(self, event):
        self._show_side_panel(self._segmentation_panel, False)

    def _on_edit_preferences(self, event):
        with PreferencesDialog(self._model, None, wx.ID_ANY, "Preferences") as dlg:
            dlg.CenterOnScreen()
            dlg.ShowModal()

    def _on_lm_image_acquisition(self, event):
        with LMAcquisitionDialog(self._model, None, wx.ID_ANY, "Acquire LM Images") as dlg:
            dlg.CenterOnScreen()
            if dlg.ShowModal() == wx.ID_OK:
                self._do_lm_acquire()

    def _on_em_image_acquisition(self, event):
        with EMAcquisitionDialog(self._model, None, wx.ID_ANY, "Acquire EM Images") as dlg:
            dlg.CenterOnScreen()
            if dlg.ShowModal() == wx.ID_OK:
                self._do_em_acquire()

    def _on_find_contours(self, event):
        self._show_side_panel(self._contour_finder_panel, True)

    def _on_find_contours_done_button_click(self, event):
        self._show_side_panel(self._contour_finder_panel, False)

    def _on_set_focus(self, event):
        self._overview_canvas.EnableToolByName(MoveStageMode.NAME, True)
        self._overview_canvas.EnableToolByName(MarkMode.NAME, False)
        self._show_side_panel(self._focus_panel, True)
        self._focus_panel.activate()

    def _on_focus_done_button_click(self, event):
        self._focus_panel.deactivate()
        self._show_side_panel(self._focus_panel, False)
        self._overview_canvas.EnableToolByName(MoveStageMode.NAME, False)
        # self._canvas_panel.SetMode(self._canvas_panel.FindToolByName("Pointer"))

    def _on_align_stage(self, event):
        self._overview_canvas.EnableToolByName(MarkMode.NAME, True)
        self._overview_canvas.EnableToolByName(MoveStageMode.NAME, False)
        self._show_side_panel(self._stage_alignment_panel, True)
        self._stage_alignment_panel.activate()

    def _on_stage_alignment_done_button_click(self, event):
        self._stage_alignment_panel.deactivate()
        self._show_side_panel(self._stage_alignment_panel, False)
        self._overview_canvas.EnableToolByName(MarkMode.NAME, False)
        # self._canvas_panel.SetMode(self._canvas_panel.FindToolByName("Pointer"))

        # Enable/disable menu entries
        stage_is_aligned = (self._model.overview_image_to_stage_coord_trf is not None)
        self._set_focus_item.Enable(stage_is_aligned)  # during focus acquisition we will move the stage, so it needs to be aligned
        self._lm_image_acquisition_item.Enable(self._can_acquire_lm_images())

    def _on_set_point_of_interest(self, event):
        self._overview_canvas.EnableToolByName(MarkMode.NAME, True)
        self._overview_canvas.EnableToolByName(MoveStageMode.NAME, False)
        self._show_side_panel(self._point_of_interest_panel, True)
        self._point_of_interest_panel.activate()

    def _on_point_of_interest_done_button_click(self, event):
        self._point_of_interest_panel.deactivate()
        self._show_side_panel(self._point_of_interest_panel, False)
        self._overview_canvas.EnableToolByName(MarkMode.NAME, False)
        # self._canvas_panel.Canvas.SetMode(self._canvas_panel.FindToolByName("Pointer"))  # CHECKME: does this work? is the pointer tool selected visually? otherwise try with e.g. the pan tool to confirm

        # Enable/disable menu entries
        self._lm_image_acquisition_item.Enable(self._can_acquire_lm_images())
        self._em_image_acquisition_item.Enable(False)  # After changing the POI we need to acquire LM images first to obtain SIFT-corrected stage movements.

    def _can_acquire_lm_images(self):
        stage_is_aligned = (self._model.overview_image_to_stage_coord_trf is not None)
        have_point_of_interest = bool(self._model.all_points_of_interest)
        return stage_is_aligned and have_point_of_interest

    def _show_side_panel(self, side_panel, show):
        side_panel.Show(show)
        self.GetTopLevelParent().Layout()
        self._overview_canvas.redraw()

        # Disable/Re-enable the menu depending on whether the side panel is active or not.
        # While the side panel is shown, the application behaves more or less like modal.
        if show:
            self._menu_state = self._disable_menu()
        else:
            self._enable_menu(self._menu_state)

    def _on_about(self, event):
        print('About...')
        # TODO: write a custom implementation. We don't have wx.adv (=Phoenix) on the SECOM computer. Or does it exist somewhere else?
        # info = wx.adv.AboutDialogInfo()
        # info.SetName('Tomo')
        # info.SetVersion('1.0')
        # info.SetDescription("Prototype application for tomography on SECOM")
        # info.SetCopyright('(c) 2018 VIB - Vlaams Instituut voor Biotechnologie')  # Not shown in the dialog on Windows?
        # info.SetWebSite('http://www.vib.be')
        # info.SetLicence("Proprietary. Copyright VIB, 2018.")
        # # info.SetIcon(wx.Icon('tomo.png', wx.BITMAP_TYPE_PNG))
        # # info.AddDeveloper('Frank Vernaillen')
        # wx.adv.AboutBox(info)

    def _on_exit(self, event):
        self.Close()

    def _disable_menu(self):
        e1 = self._import_overview_image_item.IsEnabled(); self._import_overview_image_item.Enable(False)
        e2 = self._lm_image_acquisition_item.IsEnabled(); self._lm_image_acquisition_item.Enable(False)
        e3 = self._em_image_acquisition_item.IsEnabled(); self._em_image_acquisition_item.Enable(False)
        e4 = self._segment_ribbons_item.IsEnabled(); self._segment_ribbons_item.Enable(False)
        e5 = self._load_slice_polygons_item.IsEnabled(); self._load_slice_polygons_item.Enable(False)
        e6 = self._set_focus_item.IsEnabled(); self._set_focus_item.Enable(False)
        e7 = self._set_point_of_interest_item.IsEnabled(); self._set_point_of_interest_item.Enable(False)
        e8 = self._align_stage_item.IsEnabled(); self._align_stage_item.Enable(False)
        return (e1, e2, e3, e4, e5, e6, e7, e8)

    def _enable_menu(self, state):
        e1, e2, e3, e4, e5, e6, e7, e8 = state
        self._import_overview_image_item.Enable(e1)
        self._lm_image_acquisition_item.Enable(e2)
        self._em_image_acquisition_item.Enable(e3)
        self._segment_ribbons_item.Enable(e4)
        self._load_slice_polygons_item.Enable(e5)
        self._set_focus_item.Enable(e6)
        self._set_point_of_interest_item.Enable(e7)
        self._align_stage_item.Enable(e8)

    def _do_import_overview_image(self):
        # Display overview image pixel size information
        overview_image_pixelsize_in_microns = 1000.0 / self._model.overview_image_pixels_per_mm
        print('Overview image pixel size = {} micrometer = {} pixel per mm'.format(overview_image_pixelsize_in_microns,
                                                                                   self._model.overview_image_pixels_per_mm))

        # Add and draw the overview image
        self._overview_canvas.set_image(self._model.overview_image_path)
        self._overview_canvas.zoom_to_fit()

        # Enable the menu item for loading the slice outlines
        # (We can now use it because we've got the pixel size of the overview image (really needed????))
        self._load_slice_polygons_item.Enable(True)

        # Once we have an overview image the user can use it to identify a landmark on that image
        # and the same one in Odemis. This constitutes stage - overview image alignment.
        self._align_stage_item.Enable(True)

        # Experimental: gradient descent slice contour finding (needs an overview image and, for now, ground truth slice outlines for comparison)
        self._contour_finder_item.Enable(True)

    def _do_load_slice_polygons(self):
        # Read slice polygon coordinates
        self._model.slice_polygons = tools.json_load_polygons(self._model.slice_polygons_path)
        print('Loaded {} slice polygons from {}'.format(len(self._model.slice_polygons), self._model.slice_polygons_path))

        # Add and draw the slice outlines
        self._overview_canvas.set_slice_outlines(self._model.slice_polygons)
        self._overview_canvas.redraw()

        # Enable the menu item for acquiring LM images
        # (We can now use it because we've got POIs)
        self._set_point_of_interest_item.Enable(True)

    def _image_coords_to_stage_coords(self, image_coords):   # IMPROVEME: this is also coded somewhere else, use this function instead
        # Convert image coords to stage coords
        mat = self._model.overview_image_to_stage_coord_trf
        homog_pos = np.array([image_coords[0], image_coords[1], 1])
        homog_trf_pos = np.dot(mat, homog_pos)
        stage_pos = homog_trf_pos[0:2]
        return stage_pos

    def _do_lm_acquire(self):
        # Move the stage to the first point of interest.
        # The stage may not currently be positioned there because,
        # for example, we may have moved the stage while building the focus map.
        print('Moving stage to the first point-of-interest.')
        poi_image_coords = self._model.all_points_of_interest[0]
        poi_stage_coords = self._image_coords_to_stage_coords(poi_image_coords)
        secom_tools.set_absolute_stage_position(poi_stage_coords)

        # Calculate the physical displacements on the sample required for moving between the points of interest.
        overview_image_pixelsize_in_microns = 1000.0 / self._model.overview_image_pixels_per_mm
        self._model.slice_offsets_microns = tools.physical_point_of_interest_offsets_in_microns(self._model.all_points_of_interest,
                                                                                                overview_image_pixelsize_in_microns)
        print('Rough offset from slice polygons (in microns): ' + repr(self._model.slice_offsets_microns))

        # Now acquire an LM image at the point of interest location in each slice.
        wait = wx.BusyInfo("Acquiring LM images...")
        secom_tools.acquire_microscope_images('LM',
                                              self._model.slice_offsets_microns, self._model.delay_between_LM_image_acquisition_secs,
                                              self._model.odemis_cli, self._model.lm_images_output_folder, self._model.lm_images_prefix,
                                              self._focus_panel.get_focus_map())
        del wait

        # Now tell Fiji to execute a macro that (i) reads the LM images, (ii) merges them into a stack,
        # (iii) saves the stack to TIFF, (iv) aligns the slices in this stack
        # using Fiji's Plugins > Registration > Linear Stack Alignment with SIFT
        # and (v) saves the aligned stack to TIFF.

        print('Aligning LM images')
        print('Starting a headless Fiji and calling the SIFT image registration plugin. Please be patient...')
        script_args = "srcdir='{}',dstdir='{}',prefix='{}',numimages='{}'".format(self._model.sift_input_folder, self._model.sift_output_folder, self._model.lm_images_prefix, len(self._model.all_points_of_interest))

        # Info about headless ImageJ: https://imagej.net/Headless#Running_macros_in_headless_mode
        wait = wx.BusyInfo("Aligning LM images...")
        retcode, out, err = tools.commandline_exec(
            [self._model.fiji_path, "-Dpython.console.encoding=UTF-8", "--ij2", "--headless", "--console", "--run",
             self._model.sift_registration_script, script_args])

        print('retcode={}\nstdout=\n{}\nstderr={}\n'.format(retcode, out, err))
        del wait

        # Parse the output of the SIFT registration plugin and extract
        # the transformation matrices to register each slice onto the next.
        print('Extracting SIFT transformation for fine slice transformation')
        sift_matrices = tools.extract_sift_alignment_matrices(out)
        print(sift_matrices)

        # In sift_registration.py we asked for translation only transformations.
        # So our matrices should be pure translations. Extract the last column (=the offset) and convert from pixel
        # coordinates to physical distances on the sample.
        # (We also add a (0,0) offset for the first slice.)
        sift_images_pixelsize_in_microns = 1000.0 / self._model.sift_images_pixels_per_mm
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

        # Move stage back to the first slice (using the inverse coarse movements)
        print('Moving stage back to the first point-of-interest.')
        total_stage_movement_microns = sum(self._model.slice_offsets_microns)
        secom_tools.move_stage_relative(self._model.odemis_cli, -total_stage_movement_microns)

        # Enable/disable menu entries
        self._em_image_acquisition_item.Enable(True)

    def _do_em_acquire(self):
        # At this point the user should have vented the EM chamber and positioned the EM microscope
        # precisely on the (sub-cellular) feature of interest, close to the original point-of-interest
        # on the first slice.

        # Now acquire an EM image at the same point of interest location in each slice,
        # but use the more accurate stage offsets (obtained from slice mapping + SIFT registration).
        wait = wx.BusyInfo("Acquiring EM images...")
        secom_tools.acquire_microscope_images('EM',
                                              self._model.combined_offsets_microns, self._model.delay_between_EM_image_acquisition_secs,
                                              self._model.odemis_cli, self._model.em_images_output_folder, self._model.em_images_prefix)
        del wait

        # Note: since the user needs to manually position the EM microscope over the POI in the first slice,
        # multiple series of EM image acquisition using _do_em_acquire() are perfectly fine.
        # (As long as the user did at least one LM image acquisition so we could calculate SIFT-corrected stage movements.)