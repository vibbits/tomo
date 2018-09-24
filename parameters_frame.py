# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx
from wx.lib.pubsub import pub

from model import TomoModel
from preferences_dialog import PreferencesDialog
from overview_image_dialog import OverviewImageDialog
from acquisition_dialog import AcquisitionDialog
from image_panel import ImagePanel

import tools
import mapping
import sys

class ParametersFrame(wx.Frame):
    _model = None

    # UI elements
    _image_panel = None
    _lm_image_acquisition_item = None

    def __init__(self, parent, ID, title, size = (1024, 1024), pos = wx.DefaultPosition):
        wx.Frame.__init__(self, parent, ID, title, pos, size)
        self.SetBackgroundColour(wx.Colour(240, 240, 240))  # TODO: the same default background color as for wx.Dialog - can we set it automatically, or via some style?

        self._model = TomoModel()

        # Menu
        menu_bar = wx.MenuBar()

        file_menu = wx.Menu()
        import_overview_image_item = file_menu.Append(wx.NewId(), "Import Overview Image...")
        exit_menu_item = file_menu.Append(wx.NewId(), "Exit")

        edit_menu = wx.Menu()
        prefs_menu_item = edit_menu.Append(wx.NewId(), "Preferences...")

        microscope_menu = wx.Menu()
        self._lm_image_acquisition_item = microscope_menu.Append(wx.NewId(), "Acquire LM Images...")
        self._lm_image_acquisition_item.Enable(False)

        menu_bar.Append(file_menu, "&File")
        menu_bar.Append(edit_menu, "&Edit")
        menu_bar.Append(microscope_menu, "&Microscope")

        self.Bind(wx.EVT_MENU, self._on_exit, exit_menu_item)
        self.Bind(wx.EVT_MENU, self._on_edit_preferences, prefs_menu_item)
        self.Bind(wx.EVT_MENU, self._on_import_overview_image, import_overview_image_item)
        self.Bind(wx.EVT_MENU, self._on_lm_image_acquisition, self._lm_image_acquisition_item)
        self.SetMenuBar(menu_bar)

        # Image Panel
        self._image_panel = ImagePanel(self, "img panel")

        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(self._image_panel, 0, wx.ALL | wx.EXPAND, border = 5)

        self.SetSizer(contents)
        # contents.Fit(self)  # don't do it, because it undoes the fixed size we set

        # TODO: IMPORTANT improvement: especially for the numeric fields, deal with situation where the input field is temporarily empty (while entering a number), and also forbid leaving the edit field if the value is not acceptable (or replace it with the last acceptable value)

        pub.subscribe(self._do_import_overview_image, 'overviewimage.import')  # FIXME: do we want to use this mechanism? do the import in the import dialog? if so we still need to enable the lm acquisition menu entry here somehow

    def _on_exit(self, event):
        self.Close()

    def _do_import_overview_image(self):
        # Shorthands
        overview_image_path = self._model.overview_image_path
        slice_polygons_path = self._model.slice_polygons_path
        original_point_of_interest = self._model.original_point_of_interest
        overview_image_mm_per_pixel = self._model.overview_image_mm_per_pixel

        # # Read overview image
        # print('Loading ' + overview_image_path)
        # img = tools.read_image(overview_image_path)
        # if img is None:
        #     sys.exit('Failed to open {}'.format(overview_image_path))

        # Read slice polygon coordinates
        slice_polygons = tools.json_load_polygons(slice_polygons_path)
        print('Loaded {} slice polygons from {}'.format(len(slice_polygons), slice_polygons_path))

        # # Draw the slice polygons onto the overview image
        # tools.draw_slice_polygons(img, slice_polygons)

        # Transform point-of-interest from one slice to the next
        print('Original point-of-interest: x={} y={}'.format(*original_point_of_interest))
        transformed_points_of_interest = mapping.repeatedly_transform_point(slice_polygons, original_point_of_interest)
        self._model.all_points_of_interest = [original_point_of_interest] + transformed_points_of_interest

        # # Draw the points of interests (POIs) onto the overview image
        # tools.draw_points_of_interest(img, self._model.all_points_of_interest)
        #
        # tools.display(img, overview_image_path)

        # Display overview image pixel size information
        overview_image_pixelsize_in_microns = 1000.0 / overview_image_mm_per_pixel
        print('Overview image pixel size = {} micrometer = {} mm per pixel'.format(overview_image_pixelsize_in_microns,
                                                                                   overview_image_mm_per_pixel))

        # Draw the overview image, slice outlines and POIs.
        max_size = 1024
        self._image_panel.set_image(self._model.overview_image_path, max_size)
        self._image_panel.set_points_of_interest(self._model.all_points_of_interest)
        self._image_panel.set_slice_outlines(slice_polygons)
        self.Refresh()  # force a redraw of the image panel

        # Enable the menu item for acquiring LM images
        # (We can now use it because we've got POIs)
        self._lm_image_acquisition_item.Enable(True)

    def _on_import_overview_image(self, event):
        dlg = OverviewImageDialog(self._model, None, wx.ID_ANY, "Overview Image")
        dlg.CenterOnScreen()
        dlg.Show(True)

    def _on_edit_preferences(self, event):
        dlg = PreferencesDialog(self._model, None, wx.ID_ANY, "Preferences")
        dlg.CenterOnScreen()
        dlg.Show(True)

    def _on_lm_image_acquisition(self, event):
        dlg = AcquisitionDialog(self._model, None, wx.ID_ANY, "Acquire LM Images")
        dlg.CenterOnScreen()
        dlg.Show(True)

