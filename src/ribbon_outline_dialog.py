# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx
import os

class RibbonOutlineDialog(wx.Dialog):
    _model = None

    _slice_polygons_path_edit = None
    _browse_button = None
    _load_button = None

    def __init__(self, model, parent, ID, title, size = wx.DefaultSize, pos = wx.DefaultPosition, style = wx.DEFAULT_DIALOG_STYLE):
        wx.Dialog.__init__(self, parent, ID, title, pos, size, style)

        self._model = model

        w = 450  # width for long input fields

        slice_polygons_path_label = wx.StaticText(self, wx.ID_ANY, "Slice Polygons File:")
        self._slice_polygons_path_edit = wx.TextCtrl(self, wx.ID_ANY, self._model.slice_polygons_path, size = (w, -1))
        self._browse_button = wx.Button(self, wx.ID_ANY, "Browse")

        path_sizer = wx.BoxSizer(wx.HORIZONTAL)
        path_sizer.Add(self._slice_polygons_path_edit, flag = wx.ALIGN_CENTER_VERTICAL)
        path_sizer.AddSpacer(8)
        path_sizer.Add(self._browse_button, flag = wx.ALIGN_CENTER_VERTICAL)

        fgs = wx.FlexGridSizer(cols = 2, vgap = 4, hgap = 8)
        fgs.Add(slice_polygons_path_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        fgs.Add(path_sizer, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        instructions_label = wx.StaticText(self, wx.ID_ANY, (
            "Please select the JSON file that contains the coordinates of the slice outlines. "
            "This file may describe multiple ribbons with slices. The outline of each slice must be a quadrilateral. "
            "The slices must be specified in the order that they were cut from the sample."))
        instructions_label.Wrap(650)  # Force line wrapping of the instructions text

        self._load_button = wx.Button(self, wx.ID_ANY, "Load Slice Polygons")
        self._load_button.SetFocus()


        box = wx.StaticBox(self, wx.ID_ANY)
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        sizer.Add(fgs, 0, wx.ALL | wx.CENTER, 10)

        self.Bind(wx.EVT_TEXT, self._on_slice_polygons_path_change, self._slice_polygons_path_edit)
        self.Bind(wx.EVT_BUTTON, self._on_load_button_click, self._load_button)
        self.Bind(wx.EVT_BUTTON, self._on_browse_button_click, self._browse_button)

        b = 5  # border size
        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(sizer, 0, wx.ALL | wx.EXPAND, border = b)
        contents.Add(instructions_label, 0, wx.ALL | wx.CENTER, border = b)
        contents.Add(self._load_button, 0, wx.ALL | wx.CENTER, border = b)

        self.SetSizer(contents)
        contents.Fit(self)

    def _on_browse_button_click(self, event):
        path = self._model.slice_polygons_path
        defaultDir = os.path.dirname(path)
        defaultFile = os.path.basename(path)
        with wx.FileDialog(self, "Select the slice outlines file",
                            defaultDir, defaultFile,
                            wildcard = "JSON files (*.json)|*.json") as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                self._model.slice_polygons_path = path
                self._slice_polygons_path_edit.SetLabelText(path)

    def _on_load_button_click(self, event):
        self._model.write_parameters()
        self.EndModal(wx.ID_OK)

    def _on_slice_polygons_path_change(self, event):
        self._model.slice_polygons_path = self._slice_polygons_path_edit.GetValue()
        print('slice_polygons_path={}'.format(self._model.slice_polygons_path))
