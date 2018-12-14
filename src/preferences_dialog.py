# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx

class PreferencesDialog(wx.Dialog):
    _model = None

    _odemis_cli_path_edit = None
    _registration_script_file_edit = None
    _fiji_path_edit = None

    # Staging area for model, will be copied into _model if user presses OK, will be discarded on Cancel
    _odemis_cli = None
    _fiji_path = None
    _sift_registration_script = None

    def __init__(self, model, parent, ID, title, size=wx.DefaultSize, pos=wx.DefaultPosition, style=wx.DEFAULT_DIALOG_STYLE):
        wx.Dialog.__init__(self, parent, ID, title, pos, size, style)

        self._model = model
        self._odemis_cli = self._model.odemis_cli
        self._fiji_path = self._model.fiji_path
        self._sift_registration_script = self._model.sift_registration_script

        w = 450

        fiji_path_label = wx.StaticText(self, wx.ID_ANY, "Fiji Folder:")
        self._fiji_path_edit = wx.TextCtrl(self, wx.ID_ANY, model.fiji_path, size=(w, -1))

        odemis_cli_path_label = wx.StaticText(self, wx.ID_ANY, "Odemis CLI Tool:")
        self._odemis_cli_path_edit = wx.TextCtrl(self, wx.ID_ANY, model.odemis_cli, size=(w, -1))

        registration_script_file_label = wx.StaticText(self, wx.ID_ANY, "Registration Script for Fiji:")
        self._registration_script_file_edit = wx.TextCtrl(self, wx.ID_ANY, model.sift_registration_script, size = (w, -1))

        # Environment
        env_fgs = wx.FlexGridSizer(cols = 2, vgap = 4, hgap = 8)
        env_fgs.Add(fiji_path_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        env_fgs.Add(self._fiji_path_edit, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        env_fgs.Add(odemis_cli_path_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        env_fgs.Add(self._odemis_cli_path_edit, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        env_fgs.Add(registration_script_file_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        env_fgs.Add(self._registration_script_file_edit, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        env_box = wx.StaticBox(self, -1, 'Environment')
        env_sizer = wx.StaticBoxSizer(env_box, wx.VERTICAL)
        env_sizer.Add(env_fgs, 0, wx.ALL | wx.CENTER, 10)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        ok_button = wx.Button(self, label='OK')
        cancel_button = wx.Button(self, label='Cancel')
        hbox.Add(cancel_button)
        hbox.Add(ok_button, flag=wx.LEFT, border=5)

        self.Bind(wx.EVT_TEXT, self._on_odemis_cli_path_change, self._odemis_cli_path_edit)
        self.Bind(wx.EVT_TEXT, self._on_fiji_path_change, self._fiji_path_edit)
        self.Bind(wx.EVT_TEXT, self._on_registration_script_change, self._registration_script_file_edit)
        self.Bind(wx.EVT_BUTTON, self._on_ok, ok_button)
        self.Bind(wx.EVT_BUTTON, self._on_cancel, cancel_button)

        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(env_sizer, 0, wx.ALL | wx.EXPAND, border=5)
        contents.Add(hbox, flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, border=10)

        self.SetSizer(contents)
        contents.Fit(self)

    def _on_ok(self, event):
        self._model.odemis_cli = self._odemis_cli
        self._model.fiji_path = self._fiji_path
        self._model.sift_registration_script = self._sift_registration_script
        self._model.write_parameters()
        self.EndModal(wx.OK)

    def _on_cancel(self, event):
        # We want to discard the changes, so don't copy staging values into self._model
        self.EndModal(wx.CANCEL)

    def _on_odemis_cli_path_change(self, event):
        self._odemis_cli = self._odemis_cli_path_edit.GetValue()

    def _on_fiji_path_change(self, event):
        self._fiji_path = self._fiji_path_edit.GetValue()

    def _on_registration_script_change(self, event):
        self._sift_registration_script = self._registration_script_file_edit.GetValue()
