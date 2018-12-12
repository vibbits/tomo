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
from overview_panel import OverviewPanel
from ribbon_outline_dialog import RibbonOutlineDialog
from ribbons_mask_dialog import RibbonsMaskDialog
from segmentation_panel import SegmentationPanel
from focus_panel import FocusPanel
from contour_finder_panel import ContourFinderPanel
from ribbon_splitter import segment_contours_into_slices, draw_contour_numbers
from stage_alignment_panel import StageAlignmentPanel
from point_of_interest_panel import PointOfInterestPanel
from contour_finder import ContourFinder

class ApplicationFrame(wx.Frame):
    _model = None

    _canvas_panel = None
    _status_label = None
    _focus_panel = None
    _contour_finder_panel = None
    _stage_alignment_panel = None
    _point_of_interest_panel = None

    # Menu
    _import_overview_image_item = None
    _load_slice_polygons_item = None
    _lm_image_acquisition_item = None
    _em_image_acquisition_item = None
    _load_ribbons_mask_item = None
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
        self._canvas_panel = OverviewPanel(self, custom_modes)

        # By default disable the custom modes, they are only active when their corresponding side panel is visible
        for mode in custom_modes:
            tool = self._canvas_panel.FindToolByName(mode[0])
            self._canvas_panel.ToolBar.EnableTool(tool.GetId(), False)

        # Listen to mouse movements so we can show the mouse position in the status bar.
        # We also need to listen to mouse movements when some custom modes are active (since regular FloatCanvas events do not happen then).
        self._canvas_panel.Bind(FloatCanvas.EVT_MOTION, self._on_mouse_move_over_image)
        self._canvas_panel.Bind(MarkMode.EVT_TOMO_MARK_MOTION, self._on_mouse_move_over_image)
        self._canvas_panel.Bind(MoveStageMode.EVT_TOMO_MOVESTAGE_MOTION, self._on_mouse_move_over_image)

        # Status bar at the bottom of the window
        self._status_label = wx.StaticText(self, wx.ID_ANY, "")

        # Focus side panel
        self._focus_panel = FocusPanel(self, self._canvas_panel, self._model)
        self._focus_panel.Show(False)
        self.Bind(wx.EVT_BUTTON, self._on_focus_done_button_click, self._focus_panel.done_button)

        # Contour finder side panel
        self._contour_finder_panel = ContourFinderPanel(self, self._model, self._canvas_panel)
        self._contour_finder_panel.Show(False)
        self.Bind(wx.EVT_BUTTON, self._on_find_contours_done_button_click, self._contour_finder_panel.done_button)

        # Stage alignment side panel
        self._stage_alignment_panel = StageAlignmentPanel(self, self._model, self._canvas_panel)
        self._stage_alignment_panel.Show(False)
        self.Bind(wx.EVT_BUTTON, self._on_stage_alignment_done_button_click, self._stage_alignment_panel.done_button)

        # Point of interest panel
        self._point_of_interest_panel = PointOfInterestPanel(self, self._model, self._canvas_panel)
        self._point_of_interest_panel.Show(False)
        self.Bind(wx.EVT_BUTTON, self._on_point_of_interest_done_button_click, self._point_of_interest_panel.done_button)

        # IMPROVEME: rather than adding each side panel separately we probably should add just a single side panel
        #            with a "deck" of side panel cards? Does wxPython have this concept?

        hori = wx.BoxSizer(wx.HORIZONTAL)
        hori.Add(self._canvas_panel, 1, wx.ALL | wx.EXPAND, border=5)
        hori.Add(self._focus_panel, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT, border=5)
        hori.Add(self._contour_finder_panel, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT, border=5)
        hori.Add(self._stage_alignment_panel, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT, border=5)
        hori.Add(self._point_of_interest_panel, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT, border=5)

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
        self._load_ribbons_mask_item = experimental_menu.Append(wx.NewId(), "Load Ribbons Mask...")
        self._contour_finder_item = experimental_menu.Append(wx.NewId(), "Find slice contours...")
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
        self.Bind(wx.EVT_MENU, self._on_load_ribbons_mask, self._load_ribbons_mask_item)
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

    def _on_load_ribbons_mask(self, event):
        with RibbonsMaskDialog(self._model, None, wx.ID_ANY, "Ribbons Mask") as dlg:
            dlg.CenterOnScreen()
            if dlg.ShowModal() == wx.ID_OK:
                self._do_load_ribbons_mask()

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
        self._canvas_panel.EnableToolByName(MoveStageMode.NAME, True)
        self._canvas_panel.EnableToolByName(MarkMode.NAME, False)
        self._show_side_panel(self._focus_panel, True)
        self._focus_panel.activate()

    def _on_focus_done_button_click(self, event):
        self._focus_panel.deactivate()
        self._show_side_panel(self._focus_panel, False)
        self._canvas_panel.EnableToolByName(MoveStageMode.NAME, False)
        # self._canvas_panel.SetMode(self._canvas_panel.FindToolByName("Pointer"))

    def _on_align_stage(self, event):
        self._canvas_panel.EnableToolByName(MarkMode.NAME, True)
        self._canvas_panel.EnableToolByName(MoveStageMode.NAME, False)
        self._show_side_panel(self._stage_alignment_panel, True)
        self._stage_alignment_panel.activate()

    def _on_stage_alignment_done_button_click(self, event):
        self._stage_alignment_panel.deactivate()
        self._show_side_panel(self._stage_alignment_panel, False)
        self._canvas_panel.EnableToolByName(MarkMode.NAME, False)
        # self._canvas_panel.SetMode(self._canvas_panel.FindToolByName("Pointer"))

        # Enable/disable menu entries
        stage_is_aligned = (self._model.overview_image_to_stage_coord_trf is not None)
        self._set_focus_item.Enable(stage_is_aligned)  # during focus acquisition we will move the stage, so it needs to be aligned
        self._lm_image_acquisition_item.Enable(self._can_acquire_lm_images())

    def _on_set_point_of_interest(self, event):
        self._canvas_panel.EnableToolByName(MarkMode.NAME, True)
        self._canvas_panel.EnableToolByName(MoveStageMode.NAME, False)
        self._show_side_panel(self._point_of_interest_panel, True)
        self._point_of_interest_panel.activate()

    def _on_point_of_interest_done_button_click(self, event):
        self._point_of_interest_panel.deactivate()
        self._show_side_panel(self._point_of_interest_panel, False)
        self._canvas_panel.EnableToolByName(MarkMode.NAME, False)
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
        self._canvas_panel.redraw()

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
        e4 = self._load_ribbons_mask_item.IsEnabled(); self._load_ribbons_mask_item.Enable(False)
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
        self._load_ribbons_mask_item.Enable(e4)
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
        self._canvas_panel.set_image(self._model.overview_image_path)
        self._canvas_panel.zoom_to_fit()

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
        self._canvas_panel.set_slice_outlines(self._model.slice_polygons)
        self._canvas_panel.redraw()

        # Enable the menu item for acquiring LM images
        # (We can now use it because we've got POIs)
        self._set_point_of_interest_item.Enable(True)


    @staticmethod
    def _find_ribbons(ribbons_mask_path):
        img = tools.read_image_as_color_image(ribbons_mask_path)
        print('Ribbons mask image: shape={} type={}'.format(img.shape, img.dtype))

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
        print('Found {} ribbons'.format(len(ribbons)))

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

        #######################################

        # cf = ContourFinder()
        # gray_image = read_grayscale_image('xxxx')
        # initial_contour = template_slice_contour
        # # TODO: randomly disturb initial_contour a bit for testing, and see if the optimization manages to find the template_slice_contour again.
        # cf.optimize_contour(self, gray_image, initial_contour)

        #######################################

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
            print('Estimated number of slices in ribbon: {}'.format(estimated_num_slices_in_ribbon))
            desired_num_vertices_in_ribbon = estimated_num_slices_in_ribbon * 5  # we want at least 4 points per slice, plus some extra to handle accidental dents in the slice shape
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
        acute_threshold_radians = 0 # 30 * math.pi / 180.0
        simplify_slices = True
        if simplify_slices:
            slices = [polygon_simplification.reduce_polygon(slice, 4, acute_threshold_radians) for slice in slices]

        # Save slices to JSON
        filename = r'E:\git\bits\bioimaging\Secom\tomo\data\10x_lens\auto_slices.json'
        print('Saving segmented slices to {}'.format(filename))
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
        print('Moving stage to the point-of-interest on the first slice.')
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
        if True:   # platform.system() == "Windows":
            # IMPROVEME: It seems that the True case is needed on Ubuntu.
            # We will need to double check that it also works on Windows. If so, remove the confusing else part.
            script_args = "srcdir='{}',dstdir='{}',prefix='{}'".format(self._model.sift_input_folder, self._model.sift_output_folder, self._model.lm_images_prefix)
        else:
            # Note: this does NOT seem to work on Ubuntu (on the SECOM computer) with Python 2.7 and Fiji.
            script_args = '"srcdir=\'{}\',dstdir=\'{}\',prefix=\'{}\'"'.format(self._model.sift_input_folder, self._model.sift_output_folder, self._model.lm_images_prefix)

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
        print('Moving stage back to the point-of-interest on the first slice.')
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