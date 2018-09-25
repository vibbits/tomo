# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx
from wx.lib.pubsub import pub

class OverviewImageDialog(wx.Dialog):
    _model = None

    _overview_image_path_edit = None
    _overview_pixel_size_edit = None
    _slice_polygons_path_edit = None
    _point_of_interest_x_edit = None
    _point_of_interest_y_edit = None

    def __init__(self, model, parent, ID, title, size = wx.DefaultSize, pos = wx.DefaultPosition, style = wx.DEFAULT_DIALOG_STYLE):
        wx.Dialog.__init__(self, parent, ID, title, pos, size, style)

        self._model = model

        w = 450  # width for long input fields

        overview_image_path_label = wx.StaticText(self, wx.ID_ANY, "Image File:")
        self._overview_image_path_edit = wx.TextCtrl(self, wx.ID_ANY, self._model.overview_image_path, size = (w, -1))

        overview_pixel_size_label = wx.StaticText(self, wx.ID_ANY, "Pixel size (mm/pixel):")
        self._overview_pixel_size_edit = wx.TextCtrl(self, wx.ID_ANY, str(self._model.overview_image_mm_per_pixel), size = (100, -1))

        slice_polygons_path_label = wx.StaticText(self, wx.ID_ANY, "Slice Polygons File:")
        self._slice_polygons_path_edit = wx.TextCtrl(self, wx.ID_ANY, self._model.slice_polygons_path, size = (w, -1))

        point_of_interest_label = wx.StaticText(self, wx.ID_ANY, "Point of Interest (X, Y):")
        self._point_of_interest_x_edit = wx.TextCtrl(self, wx.ID_ANY, str(self._model.original_point_of_interest[0]), size = (50, -1))
        self._point_of_interest_y_edit = wx.TextCtrl(self, wx.ID_ANY, str(self._model.original_point_of_interest[1]), size = (50, -1))

        poiSizer = wx.BoxSizer(wx.HORIZONTAL)
        poiSizer.Add(self._point_of_interest_x_edit, flag = wx.ALIGN_CENTER_VERTICAL)
        poiSizer.AddSpacer(8)
        poiSizer.Add(self._point_of_interest_y_edit, flag = wx.ALIGN_CENTER_VERTICAL)

        fgs = wx.FlexGridSizer(cols = 2, vgap = 4, hgap = 8)
        fgs.Add(overview_image_path_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        fgs.Add(self._overview_image_path_edit, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        fgs.Add(overview_pixel_size_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        fgs.Add(self._overview_pixel_size_edit, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        fgs.Add(slice_polygons_path_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        fgs.Add(self._slice_polygons_path_edit, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        fgs.Add(point_of_interest_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        fgs.Add(poiSizer, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        self._import_button = wx.Button(self, wx.ID_ANY, "Import!")

        box = wx.StaticBox(self, wx.ID_ANY)
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        sizer.Add(fgs, 0, wx.ALL|wx.CENTER, 10)

        self.Bind(wx.EVT_TEXT, self._on_overview_image_path_change, self._overview_image_path_edit)
        self.Bind(wx.EVT_TEXT, self._on_overview_pixel_size_change, self._overview_pixel_size_edit)
        self.Bind(wx.EVT_TEXT, self._on_slice_polygons_path_change, self._slice_polygons_path_edit)
        self.Bind(wx.EVT_TEXT, self._on_poi_x_change, self._point_of_interest_x_edit)
        self.Bind(wx.EVT_TEXT, self._on_poi_y_change, self._point_of_interest_y_edit)
        self.Bind(wx.EVT_BUTTON, self._on_import_button_click, self._import_button)

        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(sizer, 0, wx.ALL | wx.EXPAND, border = 5)
        contents.Add(self._import_button, 0, wx.ALL | wx.CENTER, border = 5)

        self.SetSizer(contents)
        contents.Fit(self)

    def _on_import_button_click(self, event):
        self.Show(False)
        self._model.write_parameters()
        pub.sendMessage('overviewimage.import')
        self.Destroy()

    def _on_poi_x_change(self, event):
        self._model.original_point_of_interest[0] = float(self._point_of_interest_x_edit.GetValue())
        print('original_point_of_interest[0]={}'.format(self._model.original_point_of_interest[0]))

    def _on_poi_y_change(self, event):
        self._model.original_point_of_interest[1] = float(self._point_of_interest_y_edit.GetValue())
        print('original_point_of_interest[1]={}'.format(self._model.original_point_of_interest[1]))

    def _on_overview_pixel_size_change(self, event):
        self._model.overview_image_mm_per_pixel = float(self._overview_pixel_size_edit.GetValue())
        print('overview_image_mm_per_pixel={}'.format(self._model.overview_image_mm_per_pixel))

    def _on_overview_image_path_change(self, event):
        self._model.overview_image_path = self._overview_image_path_edit.GetValue()
        print('overview_image_path={}'.format(self._model.overview_image_path))

    def _on_slice_polygons_path_change(self, event):
        self._model.slice_polygons_path = self._slice_polygons_path_edit.GetValue()
        print('slice_polygons_path={}'.format(self._model.slice_polygons_path))
