# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx
from wx.lib.floatcanvas import FloatCanvas

import numpy as np
import os
import json
import copy
import operator

import tools
import secom_tools
import resources
from json_numpy import JSONNumpyEncoder, json_numpy_array_decoder
from model import TomoModel
from mark_mode import MarkMode
from move_stage_mode import MoveStageMode
from preferences_dialog import PreferencesDialog
from overview_image_dialog import OverviewImageDialog
from lm_acquisition_dialog import LMAcquisitionDialog
from em_acquisition_dialog import EMAcquisitionDialog
from registration_import_dialog import RegistrationImportDialog
from overview_canvas import OverviewCanvas
from ribbon_outline_dialog import RibbonOutlineDialog
from focus_panel import FocusPanel
from contour_finder_panel import ContourFinderPanel
from stage_alignment_panel import StageAlignmentPanel
from point_of_interest_panel import PointOfInterestPanel
from segmentation_panel import SegmentationPanel
from about_dialog import AboutDialog

from polygon_selection_mode import PolygonSelectionMode
from polygon_editing_mode import PolygonEditingMode
from polygon_creation_mode import PolygonCreationMode
from polygon_selector_mixin import PolygonSelectorMixin
from polygon_editor_mixin import PolygonEditorMixin
from polygon_creator_mixin import PolygonCreatorMixin
from ribbon_builder_mixin import RibbonBuilderMixin
from ribbon_builder_mode import RibbonBuilderMode

class ApplicationFrame(wx.Frame):

    def __init__(self, parent, ID, title, size=(1280, 1024), pos=wx.DefaultPosition):
        wx.Frame.__init__(self, parent, ID, title, pos, size)
        self.SetBackgroundColour(wx.Colour(240, 240, 240))  # TODO: the same default background color as for wx.Dialog - can we set it automatically, or via some style?

        self._model = TomoModel()

        # Set application icon
        icon = resources.tomo.GetIcon()
        self.SetIcon(icon)

        # Menu
        self._menu_state = None  # a tuple with enabled/disabled flags for various menu items; used when a side panel is visible and we want to behave in a modal fashion
        menu_bar = self._build_menu_bar()
        self.SetMenuBar(menu_bar)

        # Custom tool modes definition. They will be associated with tools in the toolbar.
        # We can listen to mouse events when such a mode is active.
        # (The third element in each tuple is a bitmap for showing in the toolbar. The mode itself typically also
        # set a custom cursor; often the same bitmap.)
        self._mark_mode = MarkMode()
        self._polygon_selection_mode = PolygonSelectionMode()
        self._polygon_editing_mode = PolygonEditingMode()
        self._polygon_creation_mode = PolygonCreationMode()
        self._move_stage_mode = MoveStageMode()
        self._ribbon_builder_mode = RibbonBuilderMode()
        custom_modes = [(MarkMode.NAME, self._mark_mode, resources.crosshair.GetBitmap()),
                        (MoveStageMode.NAME, self._move_stage_mode, resources.movestage.GetBitmap()),
                        (PolygonSelectionMode.NAME, self._polygon_selection_mode, resources.selectpolygon.GetBitmap()),
                        (PolygonCreationMode.NAME, self._polygon_creation_mode, resources.createpolygon.GetBitmap()),
                        (PolygonEditingMode.NAME, self._polygon_editing_mode, resources.editpolygon.GetBitmap()),
                        (RibbonBuilderMode.NAME, self._ribbon_builder_mode, resources.buildribbon.GetBitmap())]

        # Canvas
        self._overview_canvas = OverviewCanvas(self, custom_modes)

        # Slice contour manipulation mixins
        self._selector = PolygonSelectorMixin(self._model, self._overview_canvas)
        self._editor = PolygonEditorMixin(self._model, self._overview_canvas, self._selector)
        self._creator = PolygonCreatorMixin(self._model, self._overview_canvas, self._selector)
        self._ribbon_builder = RibbonBuilderMixin(self._model, self._overview_canvas, self._selector)

        # By default disable the custom modes, they are only active when their corresponding side panel is visible
        for mode in custom_modes:
            tool = self._overview_canvas.FindToolByName(mode[0])
            self._overview_canvas.ToolBar.EnableTool(tool.GetId(), False)

        self._overview_canvas.RegisterTool(PolygonSelectionMode.NAME, self._selector.start, self._selector.stop)
        self._overview_canvas.RegisterTool(PolygonCreationMode.NAME, self._creator.start, self._creator.stop)
        self._overview_canvas.RegisterTool(PolygonEditingMode.NAME, self._editor.start, self._editor.stop)
        self._overview_canvas.RegisterTool(RibbonBuilderMode.NAME, self._ribbon_builder.start, self._ribbon_builder.stop)

        # Slice contour handling is possible.
        self._overview_canvas.EnableTool(PolygonSelectionMode.NAME, True)
        self._overview_canvas.EnableTool(PolygonEditingMode.NAME, True)
        self._overview_canvas.EnableTool(PolygonCreationMode.NAME, True)
        self._overview_canvas.EnableTool(RibbonBuilderMode.NAME, True)

        # Listen to mouse movements so we can show the mouse position in the status bar.
        # We also need to listen to mouse movements when some custom modes are active (since regular FloatCanvas events do not happen then).
        self._overview_canvas.Bind(FloatCanvas.EVT_MOTION, self._on_mouse_move_over_canvas)
        self._overview_canvas.Bind(MarkMode.EVT_TOMO_MARK_MOTION, self._on_mouse_move_over_canvas)
        self._overview_canvas.Bind(MoveStageMode.EVT_TOMO_MOVESTAGE_MOTION, self._on_mouse_move_over_canvas)
        self._overview_canvas.Bind(PolygonSelectionMode.EVT_TOMO_POLY_SELECT_MOTION, self._on_mouse_move_over_canvas)
        self._overview_canvas.Bind(PolygonEditingMode.EVT_TOMO_POLY_EDIT_MOTION, self._on_mouse_move_over_canvas)
        self._overview_canvas.Bind(PolygonCreationMode.EVT_TOMO_POLY_CREATE_MOTION, self._on_mouse_move_over_canvas)
        self._overview_canvas.Bind(RibbonBuilderMode.EVT_TOMO_RIBBON_BUILDER_MOTION, self._on_mouse_move_over_canvas)
        self._overview_canvas.Canvas.Bind(wx.EVT_LEAVE_WINDOW, self._on_mouse_leave_canvas)

        # Status bar at the bottom of the window
        self._status_label = wx.StaticText(self, wx.ID_ANY, "")

        # Focus side panel
        self._focus_panel = FocusPanel(self, self._overview_canvas, self._model)
        self._focus_panel.Show(False)
        self.Bind(wx.EVT_BUTTON, self._on_build_focus_map_done_button_click, self._focus_panel.done_button)

        # Contour finder side panel
        self._contour_finder_panel = ContourFinderPanel(self, self._model, self._overview_canvas, self._selector)
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
        self.Bind(wx.EVT_BUTTON, self._on_segmentation_done_button_click, self._segmentation_panel.done_button)

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
        file_menu.AppendSeparator()
        self._load_slice_polygons_item = file_menu.Append(wx.NewId(), "Load Slice Polygons...")
        self._save_slice_polygons_item = file_menu.Append(wx.NewId(), "Save Slice Polygons...")
        file_menu.AppendSeparator()
        self._load_poi_item = file_menu.Append(wx.NewId(), "Load Point of Interest...")
        self._load_poi_item.Enable(False)  # we need slice outlines and an aligned stage before we can use a saved POI file
        file_menu.AppendSeparator()
        exit_menu_item = file_menu.Append(wx.NewId(), "Exit")

        # IMPROVEME: enable/disable saving the polygons (via the menu, _save_slice_polygons_item) if we have slice polygons (either loaded or drawn manually)

        edit_menu = wx.Menu()
        prefs_menu_item = edit_menu.Append(wx.NewId(), "Preferences...")

        microscope_menu = wx.Menu()
        self._align_stage_item = microscope_menu.Append(wx.NewId(), "Align stage and overview image...")
        self._align_stage_item.Enable(False)
        self._set_point_of_interest_item = microscope_menu.Append(wx.NewId(), "Set point of interest...")
        self._set_point_of_interest_item.Enable(False) # the point of interest is specified in overview image coordinates (so we need an overview image) and will predict analogous points of interest in the other slices (so we need to have slice outlines)
        self._build_focus_map_item = microscope_menu.Append(wx.NewId(), "Build Focus Map...")
        self._build_focus_map_item.Enable(False)  # focus setup is only possible after we've aligned stage with overview image (because in the focus mode we can click on the overview image to move the stage to our target point where we want to manually set the focus)
        microscope_menu.AppendSeparator()
        self._lm_image_acquisition_item = microscope_menu.Append(wx.NewId(), "Acquire LM Images...")
        self._lm_image_acquisition_item.Enable(False)
        self._em_image_acquisition_item = microscope_menu.Append(wx.NewId(), "Acquire EM Images...")
        self._em_image_acquisition_item.Enable(False)
        microscope_menu.AppendSeparator()
        self._show_offsets_table_item = microscope_menu.Append(wx.NewId(), "Show Offsets Table")
        self._show_offsets_table_item.Enable(False)

        segmentation_menu = wx.Menu()
        self._contour_finder_item = segmentation_menu.Append(wx.NewId(), "Find slice contours...")  # an active contours (style) contour fitting prototype
        self._contour_finder_item.Enable(False)

        # Enable/disable unfinished/unstable experiments. Disabled by default.
        experimenting = False

        experimental_menu = wx.Menu()
        self._segment_ribbons_item = experimental_menu.Append(wx.NewId(), "Segment Ribbons...")
        self._segment_ribbons_item.Enable(experimenting)
        self._save_screenshot_item = experimental_menu.Append(wx.NewId(), "Save Screenshot...")
        self._save_screenshot_item.Enable(experimenting)

        view_menu = wx.Menu()
        self._show_slice_numbers_item = view_menu.Append(wx.NewId(), "Show slice numbers", kind=wx.ITEM_CHECK)
        self._show_slice_numbers_item.Check(True)

        help_menu = wx.Menu()
        self._about_item = help_menu.Append(wx.NewId(), "About")

        menu_bar.Append(file_menu, "&File")
        menu_bar.Append(edit_menu, "&Edit")
        menu_bar.Append(microscope_menu, "&Microscope")
        menu_bar.Append(segmentation_menu, "&Segmentation")
        menu_bar.Append(experimental_menu, "&Experimental")
        menu_bar.Append(view_menu, "&View")
        menu_bar.Append(help_menu, "&Help")

        self.Bind(wx.EVT_MENU, self._on_exit, exit_menu_item)
        self.Bind(wx.EVT_MENU, self._on_edit_preferences, prefs_menu_item)
        self.Bind(wx.EVT_MENU, self._on_import_overview_image, self._import_overview_image_item)
        self.Bind(wx.EVT_MENU, self._on_load_slice_polygons, self._load_slice_polygons_item)
        self.Bind(wx.EVT_MENU, self._on_save_slice_polygons, self._save_slice_polygons_item)
        self.Bind(wx.EVT_MENU, self._on_load_poi, self._load_poi_item)
        self.Bind(wx.EVT_MENU, self._on_set_point_of_interest, self._set_point_of_interest_item)
        self.Bind(wx.EVT_MENU, self._on_align_stage, self._align_stage_item)
        self.Bind(wx.EVT_MENU, self._on_show_offsets_table, self._show_offsets_table_item)
        self.Bind(wx.EVT_MENU, self._on_lm_image_acquisition, self._lm_image_acquisition_item)
        self.Bind(wx.EVT_MENU, self._on_em_image_acquisition, self._em_image_acquisition_item)
        self.Bind(wx.EVT_MENU, self._on_segment_ribbons, self._segment_ribbons_item)
        self.Bind(wx.EVT_MENU, self._on_find_contours, self._contour_finder_item)
        self.Bind(wx.EVT_MENU, self._on_save_screenshot, self._save_screenshot_item)
        self.Bind(wx.EVT_MENU, self._on_build_focus_map, self._build_focus_map_item)
        self.Bind(wx.EVT_MENU, self._on_show_slice_numbers, self._show_slice_numbers_item)
        self.Bind(wx.EVT_MENU, self._on_about, self._about_item)

        return menu_bar

    def _on_show_slice_numbers(self, event):
        show_numbers = self._show_slice_numbers_item.IsChecked()
        self._overview_canvas.set_show_slice_numbers(show_numbers)
        self._overview_canvas.redraw(True)

    def _on_mouse_move_over_canvas(self, event):
        x =  int(round(event.Coords[0]))
        y = -int(round(event.Coords[1]))  # flip y so we have the y-axis pointing down and (0,0)= top left corner of the image
        self._status_label.SetLabelText("x: {:d} y: {:d}".format(x, y))
        event.Skip()  # we're just observing the mouse moves, so pass on the event

    def _on_mouse_leave_canvas(self, event):
        # If the mouse moves off the canvas, then clear the mouse coordinates,
        # otherwise the last position inside the canvas would shown, which is useless and confusing.
        self._status_label.SetLabelText("")
        event.Skip()

    def _on_import_overview_image(self, event):
        with OverviewImageDialog(self._model, None, wx.ID_ANY, "Overview Image") as dlg:
            dlg.CenterOnScreen()
            if dlg.ShowModal() == wx.ID_OK:
                self._do_import_overview_image()

    def _on_load_poi(self, event):
        with wx.FileDialog(self, "Specify name of point of interest file to load",
                           defaultDir='',
                           defaultFile='poi_info.json',
                           wildcard="JSON files (*.json)|*.json",
                           style=wx.FD_OPEN) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                self._do_load_poi_info(path)

    def _on_load_slice_polygons(self, event):
        with RibbonOutlineDialog(self._model, None, wx.ID_ANY, "Slice Polygons") as dlg:
            dlg.CenterOnScreen()
            if dlg.ShowModal() == wx.ID_OK:
                self._do_load_slice_polygons()

    def _on_save_slice_polygons(self, event):
        path = self._model.slice_polygons_path  # by default suggest saving to the same location where the slices were last loaded from
        defaultDir = os.path.dirname(path)
        defaultFile = os.path.basename(path)
        with wx.FileDialog(self, "Select the slice outlines file",
                           defaultDir, defaultFile,
                           wildcard="JSON files (*.json)|*.json",
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                tools.json_save_polygons(path, self._model.slice_polygons)
                print('Saved {} slice polygons to {}'.format(len(self._model.slice_polygons), path))

    def _on_save_screenshot(self, event):
        defaultDir = ""
        defaultFile = ""
        with wx.FileDialog(self, "Specify filename for screenshot",
                           defaultDir, defaultFile,
                           wildcard="PNG files (*.png)|*.png",
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                #self._overview_canvas.get_wximage().SaveFile(path, wx.BITMAP_TYPE_PNG)
                self._overview_canvas.Canvas.SaveAsImage(path, wx.BITMAP_TYPE_PNG)
                print('Saved screenshot to {}'.format(path))

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
            dlg.set_default_poi_list()
            dlg.CenterOnScreen()
            if dlg.ShowModal() == wx.ID_OK:
                self._do_em_acquire()

    def _on_find_contours(self, event):
        self._show_side_panel(self._contour_finder_panel, True)

    def _on_find_contours_done_button_click(self, event):
        self._show_side_panel(self._contour_finder_panel, False)

    def _on_segment_ribbons(self, event):
        self._show_side_panel(self._segmentation_panel, True)

    def _on_segmentation_done_button_click(self, event):
        self._show_side_panel(self._segmentation_panel, False)

    def _on_build_focus_map(self, event):
        self._show_side_panel(self._focus_panel, True)

    def _on_build_focus_map_done_button_click(self, event):
        self._show_side_panel(self._focus_panel, False)

    def _on_show_offsets_table(self, event):
        tools.show_offsets_table(self._model.all_offsets_microns, self._model.combined_offsets_microns)

    def _on_align_stage(self, event):
        self._show_side_panel(self._stage_alignment_panel, True)

    def _on_stage_alignment_done_button_click(self, event):
        self._show_side_panel(self._stage_alignment_panel, False)

        # Enable/disable menu entries
        stage_is_aligned = (self._model.overview_image_to_stage_coord_trf is not None)
        self._build_focus_map_item.Enable(stage_is_aligned)  # during focus acquisition we will move the stage, so it needs to be aligned
        self._lm_image_acquisition_item.Enable(self._can_acquire_lm_images())
        self._em_image_acquisition_item.Enable(self._can_acquire_em_images())

        have_slices = bool(self._model.slice_polygons)
        self._load_poi_item.Enable(have_slices)

        # FIXME/CHECKME: do we need to recalculate or redo certain operations if the stage was aligned already, and the user now changes it?

    def _on_set_point_of_interest(self, event):
        self._show_side_panel(self._point_of_interest_panel, True)

    def _on_point_of_interest_done_button_click(self, event):
        self._show_side_panel(self._point_of_interest_panel, False)

        # Enable/disable menu entries
        self._lm_image_acquisition_item.Enable(self._can_acquire_lm_images())
        self._em_image_acquisition_item.Enable(False)  # After changing the POI we need to acquire LM images first to obtain registration-corrected stage movements.

    def _can_acquire_lm_images(self):
        stage_is_aligned = self._stage_is_aligned()
        have_point_of_interest = bool(self._model.all_points_of_interest)
        return stage_is_aligned and have_point_of_interest

    def _can_acquire_em_images(self):
        stage_is_aligned = self._stage_is_aligned()
        have_accurate_poi_positions = self._model.combined_offsets_microns is not None
        return stage_is_aligned and have_accurate_poi_positions

    def _stage_is_aligned(self):
        return self._model.overview_image_to_stage_coord_trf is not None

    def _show_side_panel(self, side_panel, show):
        # Note: while the side panel is shown, the application behaves more or less like modal
        # and most of the menus will be disabled.

        if not show:
            side_panel.deactivate()
            self._enable_menu(self._menu_state)

        side_panel.Show(show)
        self.GetTopLevelParent().Layout()
        self._overview_canvas.redraw()

        if show:
            self._menu_state = self._disable_menu()
            side_panel.activate()

    def _on_about(self, event):
        dlg = AboutDialog()
        dlg.ShowModal()
        dlg.Destroy()

    def _on_exit(self, event):
        answer = wx.MessageBox('Exit Tomo?', '', wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION, self)
        if answer == wx.YES:
            self.Close()

    def _disable_menu(self):
        e1 = self._import_overview_image_item.IsEnabled(); self._import_overview_image_item.Enable(False)
        e2 = self._lm_image_acquisition_item.IsEnabled(); self._lm_image_acquisition_item.Enable(False)
        e3 = self._em_image_acquisition_item.IsEnabled(); self._em_image_acquisition_item.Enable(False)
        e4 = self._segment_ribbons_item.IsEnabled(); self._segment_ribbons_item.Enable(False)
        e5 = self._load_slice_polygons_item.IsEnabled(); self._load_slice_polygons_item.Enable(False)
        e6 = self._build_focus_map_item.IsEnabled(); self._build_focus_map_item.Enable(False)
        e7 = self._set_point_of_interest_item.IsEnabled(); self._set_point_of_interest_item.Enable(False)
        e8 = self._align_stage_item.IsEnabled(); self._align_stage_item.Enable(False)
        e9 = self._load_poi_item.IsEnabled(); self._load_poi_item.Enable(False)
        e10 = self._show_offsets_table_item.IsEnabled(); self._show_offsets_table_item.Enable(False)
        return e1, e2, e3, e4, e5, e6, e7, e8, e9, e10

    def _enable_menu(self, state):
        e1, e2, e3, e4, e5, e6, e7, e8, e9, e10 = state
        self._import_overview_image_item.Enable(e1)
        self._lm_image_acquisition_item.Enable(e2)
        self._em_image_acquisition_item.Enable(e3)
        self._segment_ribbons_item.Enable(e4)
        self._load_slice_polygons_item.Enable(e5)
        self._build_focus_map_item.Enable(e6)
        self._set_point_of_interest_item.Enable(e7)
        self._align_stage_item.Enable(e8)
        self._load_poi_item.Enable(e9)
        self._show_offsets_table_item.Enable(e10)

    def _do_import_overview_image(self):
        # Display overview image pixel size information
        overview_image_pixelsize_in_microns = 1000.0 / self._model.overview_image_pixels_per_mm
        print('Overview image pixel size = {} micrometer = {} pixel per mm'.format(overview_image_pixelsize_in_microns,
                                                                                   self._model.overview_image_pixels_per_mm))

        # Load and display the overview image
        self._overview_canvas.load_image(self._model.overview_image_path)
        self._overview_canvas.zoom_to_fit()

        # Once we have an overview image the user can use it to identify a landmark on that image
        # and the same one in Odemis. This constitutes stage - overview image alignment.
        self._align_stage_item.Enable(True)

        # Experimental: gradient descent slice contour finding (needs an overview image)
        self._contour_finder_item.Enable(True)

    def _do_load_slice_polygons(self):
        # Read slice polygon coordinates
        self._model.slice_polygons = tools.json_load_polygons(self._model.slice_polygons_path)
        print('Loaded {} slice polygons from {}'.format(len(self._model.slice_polygons), self._model.slice_polygons_path))

        # Add and draw the slice outlines
        self._overview_canvas.set_slice_polygons(self._model.slice_polygons)
        self._overview_canvas.zoom_to_fit()
        self._overview_canvas.redraw()

        # Enable the menu item for setting or loading a point of interest
        # (We can now because we have reference slice contours - though typically we will also want to load the overview image)
        self._set_point_of_interest_item.Enable(True)
        self._load_poi_item.Enable(self._stage_is_aligned())

    def _transform_image_coords_to_stage_coords(self, image_coords):   # IMPROVEME: this is also coded somewhere else, use this function instead
        # Convert image coords to stage coords
        mat = self._model.overview_image_to_stage_coord_trf
        homog_pos = np.array([image_coords[0], image_coords[1], 1])
        homog_trf_pos = np.dot(mat, homog_pos)
        stage_pos = homog_trf_pos[0:2]
        return stage_pos

    def _move_stage_to_first_point_of_interest(self):
        print('Moving stage to the first point-of-interest.')
        poi_image_coords = self._model.all_points_of_interest[0]
        poi_stage_coords = self._transform_image_coords_to_stage_coords(poi_image_coords)
        secom_tools.set_absolute_stage_position(poi_stage_coords)

    def _do_lm_acquire(self):
        ###
        if self._model.slice_offsets_microns is None:
            print('There were no earlier LM acquisitions. POI position prediction is based on slice contours only.')

            # Calculate the physical displacements on the sample required for moving between the points of interest.
            overview_image_pixelsize_in_microns = 1000.0 / self._model.overview_image_pixels_per_mm
            self._model.slice_offsets_microns = tools.physical_point_of_interest_offsets_in_microns(self._model.all_points_of_interest, 
                                                                                                    overview_image_pixelsize_in_microns)
            print('Rough offset from slice polygons (in microns): ' + repr(self._model.slice_offsets_microns))

            # Obsolete comment:
            #    For each LM image acquisition we start *new* offset corrections.
            #    This ensures that if we change the POI we also start with a blank slate for offset corrections,
            #    otherwise we would incorrectly combine offset corrections for one POI with those for another
            #    (with possibly a different number of slices)
            # FIXME: clean up this code + PointOfInterestPanel. When changing the POI, or the number of POIs, the position corrections
            # should be discarded, but the user needs to be made aware of this in that panel.
            self._model.all_offsets_microns = [{'name': 'Slice mapping',
                                            'parameters': {},
                                            'offsets': self._model.slice_offsets_microns}]

            self._model.combined_offsets_microns = copy.deepcopy(self._model.slice_offsets_microns)
        else:
            print('There were earlier LM acquisitions. Their position corrections will be taken into account for the current acquisition.')
        ###

        # Move the stage to the first point of interest.
        # The stage may not currently be positioned there because,
        # for example, we may have moved the stage while building the focus map.
        self._move_stage_to_first_point_of_interest()

        # Remember current stage position so we can return to it after imaging.
        orig_stage_pos = secom_tools.get_absolute_stage_position()

        # Print an overview of the position corrections.
        print('The following position corrections will be taken into account during LM image acquisition:')
        tools.show_offsets_table(self._model.all_offsets_microns, self._model.combined_offsets_microns)

        # Now acquire an LM image at the point of interest location in each slice.
        wait = wx.BusyInfo("Acquiring LM images...")
        secom_tools.acquire_lm_microscope_images(self._model.combined_offsets_microns, self._model.lm_stabilization_time_secs, self._model.delay_between_LM_image_acquisition_secs,
                                                 self._model.odemis_cli, self._model.lm_images_output_folder, self._model.lm_images_prefix,
                                                 self._model.focus_map if self._model.lm_use_focus_map else None)
        del wait

        # Perform image registration on the acquired stack of LM images
        info_description = 'LM {} Registration'.format(self._model.lm_registration_params['method'])
        self._do_registration('LM', self._model.fiji_path, self._model.registration_script,
                              self._model.lm_registration_params,
                              self._model.lm_images_output_folder, self._model.lm_images_prefix, self._model.lm_registration_output_folder,
                              len(self._model.all_points_of_interest),
                              self._model.lm_image_size, self._model.lm_registration_images_pixels_per_mm,
                              info_description,
                              {})  # IMPROVEME? perhaps a nice touch would be to store the LM lens that was used. Can we query that via odemis-cli perhaps?

        # Move stage back to initial position
        print('Moving stage back to position at start of LM image acquisition')
        secom_tools.set_absolute_stage_position(orig_stage_pos)

        # Enable/disable menu entries
        self._em_image_acquisition_item.Enable(True)
        self._show_offsets_table_item.Enable(True)

    def _do_em_acquire(self):
        # At this point the user should have vented the EM chamber and positioned the EM microscope
        # precisely on the (sub-cellular) feature of interest, close to the original point-of-interest
        # on the first slice.

        # Remember current stage position so we can return to it after imaging.
        orig_stage_pos = secom_tools.get_absolute_stage_position()

        # Print an overview of the position corrections.
        print('The following position corrections will be taken into account during EM image acquisition:')
        tools.show_offsets_table(self._model.all_offsets_microns, self._model.combined_offsets_microns)

        # Now acquire an EM image at the same point of interest location in each slice,
        # but use the more accurate stage offsets (obtained from slice mapping + image registration).
        wait = wx.BusyInfo("Acquiring EM images...")
        secom_tools.acquire_em_microscope_images(self._model.combined_offsets_microns, self._model.delay_between_EM_image_acquisition_secs,
                                                 self._model.odemis_cli, self._model.em_images_output_folder, self._model.em_images_prefix,
                                                 self._model.get_em_scale_string(), self._model.em_magnification, self._model.em_dwell_time_microseconds,
                                                 self._model.em_pois_to_image)
        del wait

        # Perform image registration on the acquired stack of EM images
        image_size = self._model.get_em_image_size_in_pixels()  # (width, height) in pixels
        pixels_per_micrometer = self._model.get_em_pixels_per_micrometer()
        image_pixels_per_mm = 1000.0 * pixels_per_micrometer

        info_description = 'EM {} Registration'.format(self._model.em_registration_params['method'])

        self._do_registration('EM', self._model.fiji_path, self._model.registration_script,
                              self._model.em_registration_params,
                              self._model.em_images_output_folder, self._model.em_images_prefix, self._model.em_registration_output_folder,
                              len(self._model.all_points_of_interest),
                              image_size, image_pixels_per_mm,
                              info_description,
                              {'em_scale': self._model.get_em_scale_string(),
                               'em_magnification' : self._model.em_magnification,
                               'em_dwell_time_microseconds' : self._model.em_dwell_time_microseconds})

        # Move stage back to initial position
        print('Moving stage back to position at start of EM image acquisition')
        secom_tools.set_absolute_stage_position(orig_stage_pos)

    def _do_registration(self, modality, fiji_path, registration_script, registration_params,
                         input_folder, input_filenames_prefix, output_folder,
                         num_images,
                         orig_image_size, pixels_per_mm,
                         info_description,
                         info_parameters):
        # modality is 'EM' or 'LM'

        # Ensure that folder exists, if not create it and its parent folders.
        tools.make_dir(output_folder)

        # Tell Fiji to execute a macro that (i) reads the LM/EM images, (ii) merges them into a stack,
        # (iii) saves the stack to TIFF, (iv) aligns the slices in this stack
        # and (v) saves the aligned stack to TIFF.
        # Registration happens either with Fiji's Plugins > Registration > Linear Stack Alignment with SIFT, or with Plugins > StackReg.

        busy_string = "Registering {} images...".format(modality)

        print(busy_string)
        print('Starting a headless Fiji and calling the image registration plugin. Please be patient...')
        script_args = "srcdir='{}',dstdir='{}',prefix='{}',method='{}',numimages='{}',do_invert='{}',do_enhance_contrast='{}',do_crop='{}',roi_x='{}',roi_y='{}',roi_width='{}',roi_height='{}'".format(
            input_folder, output_folder, input_filenames_prefix, registration_params['method'],
            num_images,
            registration_params["invert"],
            registration_params["enhance_contrast"],
            registration_params["crop"],
            registration_params["roi"][0], registration_params["roi"][1],
            registration_params["roi"][2], registration_params["roi"][3])

        # Note: info about headless ImageJ: https://imagej.net/Headless#Running_macros_in_headless_mode
        wait = wx.BusyInfo(busy_string)
        retcode, out, err = tools.commandline_exec(
            [fiji_path, "-Dpython.console.encoding=UTF-8", "--ij2", "--headless", "--console", "--run",
             registration_script, script_args])

        print('Headless Fiji retcode={}\nstdout=\n{}\nstderr={}\n'.format(retcode, out, err))
        del wait

        # # # # # # # # # # BEGIN EXPERIMENTAL CODE

        update_offsets = True

        output_filename = '{}_aligned_stack.tif'.format(registration_params['method'])
        registration_correct = wx.MessageBox('Please check the registration result {}.\n'
                                             'Are all images aligned correctly?'.format(os.path.join(output_folder, output_filename)), 'Registration successful?',
                                             wx.YES_NO | wx.ICON_QUESTION, self)       # "Yes" is selected by default
        if registration_correct == wx.NO:
            print('User feedback: registration is not correct.')
            with RegistrationImportDialog(output_folder, None, wx.ID_ANY, "Import Registration Output") as dlg:
                if dlg.ShowModal() == wx.ID_OK:
                    print('Using manual registration output')
                    out = dlg.get_registration_output()
                    info_description = info_description + ' (Manual)'
                else:
                    print('User feedback: do not use manual registration')
                    update_offsets = False
        else:
            print('User feedback: registration is correct.')

        # # # # # # # # # # END EXPERIMENTAL CODE

        if update_offsets:
            # Parse the output of the registration plugin and extract
            # the transformation matrices to register each slice onto the next.
            print('Extracting transformation matrices from registration plugin output')
            registration_matrices = tools.extract_registration_matrices(registration_params['method'], out)
            print(registration_matrices)

            registration_offsets_microns = self.calculate_registration_offsets(registration_matrices, orig_image_size, pixels_per_mm, registration_params)
            print('Registration corrected point-of-interest offsets [micrometer]: ' + repr(registration_offsets_microns))

            # Combine (=sum) existing offsets with this new one
            assert self._model.combined_offsets_microns is not None
            assert len(self._model.combined_offsets_microns) == len(registration_offsets_microns)
            self._model.combined_offsets_microns = map(operator.add, self._model.combined_offsets_microns, registration_offsets_microns)
            print('Combined offsets [micrometer]: ' + repr(self._model.combined_offsets_microns))

            # Append offset correction to "history" of existing offsets.
            self._model.all_offsets_microns.append({'name': info_description,
                                                    'parameters': info_parameters,
                                                    'offsets': registration_offsets_microns})
        else:
            print('Registration plugin output NOT used.')
            print('Slice offsets NOT updated with corrections.')

        #
        self._do_save_poi_info(output_folder)

        # For debugging / validation: display the offsets table.
        tools.show_offsets_table(self._model.all_offsets_microns, self._model.combined_offsets_microns)

    def calculate_registration_offsets(self, registration_matrices, orig_image_size, pixels_per_mm, registration_params):
        # Calculate a fine stage position correction (in pixels) from the transformation
        # that is needed to register successive images of the same ROI in successive sample sections.
        image_size = registration_params["roi"][2:] if registration_params["crop"] else orig_image_size
        center = np.array([image_size[0] / 2.0, image_size[1] / 2.0])  # image center, in pixels

        registration_offsets = [np.array([0, 0])]  # stage position corrections (in pixels); one correction per sample section
        for mat in registration_matrices:  # there is one transformation matrix per sample section
            # mat is a 2x3 numpy array; 3rd column is the translation vector

            new_center = np.dot(mat, np.array([center[0], center[1], 1.0]))
            offset = new_center - center  # displacement in pixels
            registration_offsets.append(offset)
            center = new_center

        # Scale the offsets from dimensionless pixels to microns (for stage movements)
        pixelsize_in_microns = 1000.0 / pixels_per_mm
        registration_offsets_microns = [offset * pixelsize_in_microns for offset in registration_offsets]

        # Invert y component of the registration offsets.
        # Our images have their origin at the top left corner, with y-axis pointing down;
        # the stage has its y-axis pointing up (?).
        registration_offsets_microns = [np.array([offset[0], -offset[1]]) for offset in registration_offsets_microns]

        return registration_offsets_microns

    def _do_save_poi_info(self, output_folder):

        # Make the point of interest (POI) position data persistent.
        # This will allow us to first perform LM image acquisitions for multiple initial ROIs,
        # then prepare the microscope for EM image acquisition (this is time consuming since microscope needs to be pumped vacuum),
        # and finally use the stored data from the LM acquisition to image all corresponding sections for each POI in EM mode.
        # Note: we store more data than is strictly necessary, partially for debugging purposes, and partially in case we later
        # need the additional information after all for some reason.
        poi_info = {'version': '2',  # version of this POI info file
                    'all_points_of_interest': self._model.all_points_of_interest,
                    'combined_offsets_microns': self._model.combined_offsets_microns,
                    'all_offsets_microns': self._model.all_offsets_microns,  # info only, not used
                    'overview_image_to_stage_coord_trf': self._model.overview_image_to_stage_coord_trf,  # info only, not used
                    'overview_image_pixels_per_mm': self._model.overview_image_pixels_per_mm}  # info only, not used
        poi_json = json.dumps(poi_info, cls=JSONNumpyEncoder)
        print(poi_json)

        filename = os.path.join(output_folder, 'poi_info.json')
        print('Saving POI info to {}'.format(filename))
        with open(filename, 'w') as f:   # IMPROVEME: check for IO errors e.g. file is locked or already exists etc.
            f.write(poi_json)

    def _do_load_poi_info(self, filename):
        print('Loading POI info from {}'.format(filename))
        with open(filename) as f:  # IMPROVEME: check for IO errors
            poi_info = json.load(f, object_hook=json_numpy_array_decoder)
        print(poi_info)

        # Update model with loaded point of interest
        self._model.combined_offsets_microns = poi_info['combined_offsets_microns']
        self._model.all_points_of_interest = poi_info['all_points_of_interest']
        self._model.original_point_of_interest = self._model.all_points_of_interest[0]
        self._model.all_offsets_microns = poi_info['all_offsets_microns']

        # Update POI panel
        self._point_of_interest_panel.on_poi_loaded_from_file()

        # Print offsets table for verification
        tools.show_offsets_table(self._model.all_offsets_microns, self._model.combined_offsets_microns)

        # Move stage to the first point of interest. This is where the stage needs to be if the user
        # wants to start EM image acquisition.
        # (I'm not sure if answering "No" here is ever useful for the user. Perhaps a simple info message would suffice?)
        answer = wx.MessageBox('Move the stage to the point of interest in the first section?', 'Move stage?',
                               wx.YES_NO | wx.ICON_QUESTION, self)       # "Yes" is selected by default
        if answer == wx.YES:
            self._move_stage_to_first_point_of_interest()

        # Enable/disable menu items
        self._lm_image_acquisition_item.Enable(self._stage_is_aligned())
        self._em_image_acquisition_item.Enable(self._stage_is_aligned())
        self._show_offsets_table_item.Enable(True)
