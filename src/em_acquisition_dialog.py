# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx
from wx.lib.pubsub import pub

class EMAcquisitionDialog(wx.Dialog):
    _model = None

    # UI elements
    _em_images_output_folder_edit = None
    _em_images_output_folder_button = None
    _em_prefix_edit = None
    _em_acquisition_delay_text = None
    _acquire_button = None

    def __init__(self, model, parent, ID, title, size = wx.DefaultSize, pos = wx.DefaultPosition, style = wx.DEFAULT_DIALOG_STYLE):
        wx.Dialog.__init__(self, parent, ID, title, pos, size, style)

        self._model = model

        w = 450  # width for long input fields

        #
        em_images_output_folder_label = wx.StaticText(self, wx.ID_ANY, "Output Folder:")
        self._em_images_output_folder_edit = wx.TextCtrl(self, wx.ID_ANY, self._model.em_images_output_folder, size = (w, -1))
        self._em_images_output_folder_button = wx.Button(self, wx.ID_ANY, "Browse")

        prefix_label = wx.StaticText(self, wx.ID_ANY, "Filename Prefix:")
        self._em_prefix_edit = wx.TextCtrl(self, wx.ID_ANY, self._model.em_images_prefix, size = (w, -1))

        em_acquisition_delay_label = wx.StaticText(self, wx.ID_ANY, "Acquisition Delay (sec):")
        self._em_acquisition_delay_text = wx.TextCtrl(self, wx.ID_ANY, str(self._model.delay_between_EM_image_acquisition_secs), size = (50, -1))

        em_sizer = wx.BoxSizer(wx.HORIZONTAL)
        em_sizer.Add(self._em_images_output_folder_edit, flag = wx.ALIGN_CENTER_VERTICAL)
        em_sizer.AddSpacer(8)
        em_sizer.Add(self._em_images_output_folder_button, flag = wx.ALIGN_CENTER_VERTICAL)

         # EM Image Acquisition
        em_fgs = wx.FlexGridSizer(cols = 2, vgap = 4, hgap = 8)
        em_fgs.Add(em_images_output_folder_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        em_fgs.Add(em_sizer, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        em_fgs.Add(prefix_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        em_fgs.Add(self._em_prefix_edit, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        em_fgs.Add(em_acquisition_delay_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        em_fgs.Add(self._em_acquisition_delay_text, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        em_box = wx.StaticBox(self, -1, 'EM Image Acquisition')
        em_sizer = wx.StaticBoxSizer(em_box, wx.VERTICAL)
        em_sizer.Add(em_fgs, 0, wx.ALL | wx.CENTER, 10)

        self._acquire_button = wx.Button(self, wx.ID_ANY, "Acquire EM Images!")

        self.Bind(wx.EVT_TEXT, self._on_em_images_output_folder_change, self._em_images_output_folder_edit)
        self.Bind(wx.EVT_TEXT, self._on_prefix_change, self._em_prefix_edit)
        self.Bind(wx.EVT_TEXT, self._on_delay_change, self._em_acquisition_delay_text)
        self.Bind(wx.EVT_BUTTON, self._on_em_output_folder_browse_button_click, self._em_images_output_folder_button)
        self.Bind(wx.EVT_BUTTON, self._on_acquire_button_click, self._acquire_button)

        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(em_sizer, 0, wx.ALL | wx.EXPAND, border = 5)
        contents.Add(self._acquire_button, 0, wx.ALL | wx.CENTER, border = 5)

        self.SetSizer(contents)
        contents.Fit(self)

    def _on_em_output_folder_browse_button_click(self, event):
        defaultPath = self._model.em_images_output_folder
        dlg = wx.DirDialog(self, "Select the output directory for EM images", defaultPath)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self._model.em_images_output_folder = path
            self._em_images_output_folder_edit.SetLabelText(path)
        dlg.Destroy()

    def _on_acquire_button_click(self, event):
        self.Show(False)
        self._model.write_parameters()
        pub.sendMessage('em.acquire')
        self.Destroy()

    def _on_em_images_output_folder_change(self, event):
        self._model.em_images_output_folder = self._em_images_output_folder_edit.GetValue()
        print('em_images_output_folder={}'.format(self._model.em_images_output_folder))

    def _on_prefix_change(self, event):
        self._model.em_images_prefix = self._em_prefix_edit.GetValue()
        print('em_images_prefix={}'.format(self._model.em_images_prefix))

    def _on_delay_change(self, event):
        self._model.delay_between_EM_image_acquisition_secs = float(self._em_acquisition_delay_text.GetValue())
        print('delay_between_EM_image_acquisition_secs={}'.format(self._model.delay_between_EM_image_acquisition_secs))
