# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx
import os

class OverviewImageDialog(wx.Dialog):
    _model = None

    _overview_image_path_edit = None
    _browse_button = None

    def __init__(self, model, parent, ID, title, size = wx.DefaultSize, pos = wx.DefaultPosition, style = wx.DEFAULT_DIALOG_STYLE):
        wx.Dialog.__init__(self, parent, ID, title, pos, size, style)

        self._model = model

        w = 450  # width for long input fields

        overview_image_path_label = wx.StaticText(self, wx.ID_ANY, "Image File:")
        self._overview_image_path_edit = wx.TextCtrl(self, wx.ID_ANY, self._model.overview_image_path, size=(w, -1))
        self._browse_button = wx.Button(self, wx.ID_ANY, "Browse")

        path_sizer = wx.BoxSizer(wx.HORIZONTAL)
        path_sizer.Add(self._overview_image_path_edit, flag=wx.ALIGN_CENTER_VERTICAL)
        path_sizer.AddSpacer(8)
        path_sizer.Add(self._browse_button, flag=wx.ALIGN_CENTER_VERTICAL)

        fgs = wx.FlexGridSizer(cols=2, vgap=4, hgap=8)  # IMPROVEME: FlexGridSizer is now overkill
        fgs.Add(overview_image_path_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        fgs.Add(path_sizer, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        instructions_label = wx.StaticText(self, wx.ID_ANY, (
            "Please select an overview LM image of the sample. It will be used for coarse microscope navigation. "
            "It should show the ribbons with the sample slices."))
        instructions_label.Wrap(620)  # Force line wrapping of the instructions text

        self._import_button = wx.Button(self, wx.ID_ANY, "Import")
        self._import_button.SetFocus()

        box = wx.StaticBox(self, wx.ID_ANY)
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        sizer.Add(fgs, 0, wx.ALL|wx.CENTER, 10)

        self.Bind(wx.EVT_TEXT, self._on_overview_image_path_change, self._overview_image_path_edit)
        self.Bind(wx.EVT_BUTTON, self._on_import_button_click, self._import_button)
        self.Bind(wx.EVT_BUTTON, self._on_browse_button_click, self._browse_button)

        b = 5  # border size
        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(sizer, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(instructions_label, 0, wx.ALL | wx.CENTER, border=b)
        contents.Add(self._import_button, 0, wx.ALL | wx.CENTER, border=b)

        self.SetSizer(contents)
        contents.Fit(self)

    def _on_browse_button_click(self, event):
        path = self._model.overview_image_path
        defaultDir = os.path.dirname(path)
        defaultFile = os.path.basename(path)
        with wx.FileDialog(self, "Select the overview image",
                           defaultDir, defaultFile,
                           wildcard="TIFF files (*.tif;*.tiff)|*.tif;*.tiff|PNG files (*.png)|*.png|JPEG files (*.jpg;*.jpeg)|*.jpg;*.jpeg") as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                self._model.overview_image_path = path
                self._overview_image_path_edit.SetLabelText(path)

    def _on_import_button_click(self, event):
        self._model.write_parameters()
        self.EndModal(wx.ID_OK)

    def _on_overview_image_path_change(self, event):
        self._model.overview_image_path = self._overview_image_path_edit.GetValue()
        print('overview_image_path={}'.format(self._model.overview_image_path))
