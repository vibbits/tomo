# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx
import os

class RibbonsMaskDialog(wx.Dialog):
    _model = None

    _ribbons_mask_path_edit = None
    _template_slice_path_edit = None
    _browse_button = None
    _browse_button2 = None
    _load_button = None

    def __init__(self, model, parent, ID, title, size = wx.DefaultSize, pos = wx.DefaultPosition, style = wx.DEFAULT_DIALOG_STYLE):
        wx.Dialog.__init__(self, parent, ID, title, pos, size, style)

        self._model = model

        w = 450  # width for long input fields

        ribbons_mask_path_label = wx.StaticText(self, wx.ID_ANY, "Ribbons Mask File:")
        self._ribbons_mask_path_edit = wx.TextCtrl(self, wx.ID_ANY, self._model.ribbons_mask_path, size = (w, -1))
        self._browse_button = wx.Button(self, wx.ID_ANY, "Browse")

        template_slice_label = wx.StaticText(self, wx.ID_ANY, "Template Slice File:")
        self._template_slice_path_edit = wx.TextCtrl(self, wx.ID_ANY, self._model.template_slice_path, size = (w, -1))
        self._browse2_button = wx.Button(self, wx.ID_ANY, "Browse")

        path_sizer = wx.BoxSizer(wx.HORIZONTAL)
        path_sizer.Add(self._ribbons_mask_path_edit, flag = wx.ALIGN_CENTER_VERTICAL)
        path_sizer.AddSpacer(8)
        path_sizer.Add(self._browse_button, flag = wx.ALIGN_CENTER_VERTICAL)

        path_sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        path_sizer2.Add(self._template_slice_path_edit, flag = wx.ALIGN_CENTER_VERTICAL)
        path_sizer2.AddSpacer(8)
        path_sizer2.Add(self._browse2_button, flag = wx.ALIGN_CENTER_VERTICAL)

        fgs = wx.FlexGridSizer(cols = 2, vgap = 4, hgap = 8)
        fgs.Add(ribbons_mask_path_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        fgs.Add(path_sizer, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        fgs.Add(template_slice_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        fgs.Add(path_sizer2, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        self._load_button = wx.Button(self, wx.ID_ANY, "Load Ribbons Mask")

        box = wx.StaticBox(self, wx.ID_ANY)
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        sizer.Add(fgs, 0, wx.ALL | wx.CENTER, 10)

        self.Bind(wx.EVT_TEXT, self._on_ribbons_mask_path_change, self._ribbons_mask_path_edit)
        self.Bind(wx.EVT_TEXT, self._on_template_slice_path_change, self._template_slice_path_edit)
        self.Bind(wx.EVT_BUTTON, self._on_load_button_click, self._load_button)
        self.Bind(wx.EVT_BUTTON, self._on_browse_button_click, self._browse_button)
        self.Bind(wx.EVT_BUTTON, self._on_browse2_button_click, self._browse2_button)

        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(sizer, 0, wx.ALL | wx.EXPAND, border = 5)
        contents.Add(self._load_button, 0, wx.ALL | wx.CENTER, border = 5)

        self.SetSizer(contents)
        contents.Fit(self)

    def _on_browse_button_click(self, event):
        path = self._model.slice_polygons_path
        defaultDir = os.path.dirname(path)
        defaultFile = os.path.basename(path)
        dlg = wx.FileDialog(self, "Select the ribbons mask file",
                            defaultDir, defaultFile,
                            wildcard = "TIFF files (*.tif;*.tiff)|*.tif;*.tiff|PNG files (*.png)|*.png|JPEG files (*.jpg;*.jpeg)|*.jpg;*.jpeg")
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self._model.ribbons_mask_path = path
            self._ribbons_mask_path_edit.SetValue(path)
        dlg.Destroy()

    def _on_browse2_button_click(self, event):
        path = self._model.template_slice_path
        defaultDir = os.path.dirname(path)
        defaultFile = os.path.basename(path)
        with wx.FileDialog(self, "Select the template slice contour file",
                            defaultDir, defaultFile,
                            wildcard = "JSON files (*.json)|*.json") as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                self._model.template_slice_path = path
                self._template_slice_path_edit.SetValue(path)

    def _on_load_button_click(self, event):
        self._model.write_parameters()
        self.EndModal(wx.ID_OK)

    def _on_ribbons_mask_path_change(self, event):
        self._model.ribbons_mask_path = self._ribbons_mask_path_edit.GetValue()
        print('ribbons_mask_path={}'.format(self._model.ribbons_mask_path))

    def _on_template_slice_path_change(self, event):
        self._model.template_slice_path = self._template_slice_path_edit.GetValue()
        print('template_slice_path={}'.format(self._model.template_slice_path))
