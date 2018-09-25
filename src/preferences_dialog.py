# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx

class PreferencesDialog(wx.Dialog):
    _model = None

    _odemis_cli_path_edit = None
    _registration_script_file_edit = None
    _fiji_path_edit = None

    def __init__(self, model, parent, ID, title, size = wx.DefaultSize, pos = wx.DefaultPosition, style = wx.DEFAULT_DIALOG_STYLE):
        wx.Dialog.__init__(self, parent, ID, title, pos, size, style)

        self._model = model

        w = 450

        fiji_path_label = wx.StaticText(self, wx.ID_ANY, "Fiji Folder:")
        self._fiji_path_edit = wx.TextCtrl(self, wx.ID_ANY, model.fiji_path, size = (w, -1))

        odemis_cli_path_label = wx.StaticText(self, wx.ID_ANY, "Odemis CLI Tool:")
        self._odemis_cli_path_edit = wx.TextCtrl(self, wx.ID_ANY, model.odemis_cli, size = (w, -1))

        registration_script_file_label = wx.StaticText(self, wx.ID_ANY, "Registration Script for Fiji:")
        self._registration_script_file_edit = wx.TextCtrl(self, wx.ID_ANY, model.sift_registration_script, size = (w, -1))

        # Environment
        env_fgs = wx.FlexGridSizer(cols = 2, vgap = 4, hgap = 8)
        env_fgs.Add(fiji_path_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        env_fgs.Add(self._fiji_path_edit, flag =wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        env_fgs.Add(odemis_cli_path_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        env_fgs.Add(self._odemis_cli_path_edit, flag =wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        env_fgs.Add(registration_script_file_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        env_fgs.Add(self._registration_script_file_edit, flag =wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        env_box = wx.StaticBox(self, -1, 'Environment')
        env_sizer = wx.StaticBoxSizer(env_box, wx.VERTICAL)
        env_sizer.Add(env_fgs, 0, wx.ALL|wx.CENTER, 10)

        self.Bind(wx.EVT_TEXT, self._on_odemis_cli_path_change, self._odemis_cli_path_edit)
        self.Bind(wx.EVT_TEXT, self._on_fiji_path_change, self._fiji_path_edit)
        self.Bind(wx.EVT_TEXT, self._on_registration_script_change, self._registration_script_file_edit)

        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(env_sizer, 0, wx.ALL | wx.EXPAND, border = 5)

        self.SetSizer(contents)
        contents.Fit(self)

        # TODO: OK/Cancel buttons? Disable x button in window?

    def _on_odemis_cli_path_change(self, event):
        self._model.odemis_cli = self._odemis_cli_path_edit.GetValue()
        print('odemis_cli={}'.format(self._model.odemis_cli))

    def _on_fiji_path_change(self, event):
        self._model.fiji_path = self._fiji_path_edit.GetValue()
        print('fiji={}'.format(self._model.fiji_path))

    def _on_registration_script_change(self, event):
        self._model.sift_registration_script = self._registration_script_file_edit.GetValue()
        print('sift_registration_script={}'.format(self._model.sift_registration_script))