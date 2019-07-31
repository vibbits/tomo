# Frank Vernaillen
# September 2018-2019
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx

class EMAcquisitionDialog(wx.Dialog):

    def __init__(self, model, parent, ID, title, size=wx.DefaultSize, pos=wx.DefaultPosition, style=wx.DEFAULT_DIALOG_STYLE):
        wx.Dialog.__init__(self, parent, ID, title, pos, size, style)

        self._model = model

        w = 450  # width for long input fields

        #
        em_images_output_folder_label = wx.StaticText(self, wx.ID_ANY, "Output Folder:")
        self._em_images_output_folder_edit = wx.TextCtrl(self, wx.ID_ANY, self._model.em_images_output_folder, size=(w, -1))
        self._em_images_output_folder_button = wx.Button(self, wx.ID_ANY, "Browse")

        output_folder_sizer = wx.BoxSizer(wx.HORIZONTAL)
        output_folder_sizer.Add(self._em_images_output_folder_edit, flag=wx.ALIGN_CENTER_VERTICAL)
        output_folder_sizer.AddSpacer(8)
        output_folder_sizer.Add(self._em_images_output_folder_button, flag=wx.ALIGN_CENTER_VERTICAL)

        prefix_label = wx.StaticText(self, wx.ID_ANY, "Filename Prefix:")
        self._em_prefix_edit = wx.TextCtrl(self, wx.ID_ANY, self._model.em_images_prefix, size=(w, -1))

        #
        scales = ['1,1', '2,2', '4,4', '8,8', '16,16']
        em_scale_label = wx.StaticText(self, wx.ID_ANY, "Scale:")
        self._em_scale_dropdown = wx.Choice(self, wx.ID_ANY, choices=scales)
        ok = self._em_scale_dropdown.SetStringSelection(self._model.em_scale)
        assert(ok)

        em_magnification_label = wx.StaticText(self, wx.ID_ANY, "Magnification:")
        self._em_magnification_text = wx.TextCtrl(self, wx.ID_ANY, str(self._model.em_magnification), size=(70, -1))

        em_dwell_time_label = wx.StaticText(self, wx.ID_ANY, u"Dwell time [\u03bcs]:")  # \u03bc is the greek letter mu
        self._em_dwell_time_text = wx.TextCtrl(self, wx.ID_ANY, str(self._model.em_dwell_time_microseconds), size=(70, -1))

        em_acquisition_delay_label = wx.StaticText(self, wx.ID_ANY, "Acquisition Delay [s]:")
        self._em_acquisition_delay_text = wx.TextCtrl(self, wx.ID_ANY, str(self._model.delay_between_EM_image_acquisition_secs), size=(70, -1))

        #
        output_fgs = wx.FlexGridSizer(cols=2, vgap=4, hgap=8)
        output_fgs.Add(em_images_output_folder_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        output_fgs.Add(output_folder_sizer, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        output_fgs.Add(prefix_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        output_fgs.Add(self._em_prefix_edit, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        #
        acquisition_fgs = wx.FlexGridSizer(cols=2, vgap=4, hgap=8)
        acquisition_fgs.Add(em_scale_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        acquisition_fgs.Add(self._em_scale_dropdown, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        acquisition_fgs.Add(em_magnification_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        acquisition_fgs.Add(self._em_magnification_text, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        acquisition_fgs.Add(em_dwell_time_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        acquisition_fgs.Add(self._em_dwell_time_text, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        acquisition_fgs.Add(em_acquisition_delay_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        acquisition_fgs.Add(self._em_acquisition_delay_text, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        #
        output_box = wx.StaticBox(self, -1, 'Output')
        output_sizer = wx.StaticBoxSizer(output_box, wx.VERTICAL)
        output_sizer.Add(output_fgs, 0, wx.ALL | wx.CENTER, 10)

        #
        acquisition_box = wx.StaticBox(self, -1, 'Acquisition Parameters')
        acquisition_sizer = wx.StaticBoxSizer(acquisition_box, wx.VERTICAL)
        acquisition_sizer.Add(acquisition_fgs, 0, wx.ALL, 10)

        #
        instructions_label = wx.StaticText(self, wx.ID_ANY, ("Prepare the EM microscope. The stage must be positioned at the point of interest. "
                                                             "Then press the button below to start image acquisition."))
        instructions_label.Wrap(650)  # Force line wrapping of the instructions text (max 650 pixels per line).

        self._acquire_button = wx.Button(self, wx.ID_ANY, "Acquire EM Images")

        self.Bind(wx.EVT_TEXT, self._on_em_images_output_folder_change, self._em_images_output_folder_edit)
        self.Bind(wx.EVT_TEXT, self._on_prefix_change, self._em_prefix_edit)
        self.Bind(wx.EVT_TEXT, self._on_delay_change, self._em_acquisition_delay_text)
        self.Bind(wx.EVT_TEXT, self._on_dwell_time_change, self._em_dwell_time_text)
        self.Bind(wx.EVT_TEXT, self._on_magnification_change, self._em_magnification_text)
        self.Bind(wx.EVT_CHOICE, self._on_scale_change, self._em_scale_dropdown)
        self.Bind(wx.EVT_BUTTON, self._on_em_output_folder_browse_button_click, self._em_images_output_folder_button)
        self.Bind(wx.EVT_BUTTON, self._on_acquire_button_click, self._acquire_button)

        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(output_sizer, 0, wx.ALL | wx.EXPAND, border=5)
        contents.Add(acquisition_sizer, 0, wx.ALL | wx.EXPAND, border=5)
        contents.Add(instructions_label, 0, wx.ALL | wx.CENTER, border=5)
        contents.Add(self._acquire_button, 0, wx.ALL | wx.CENTER, border=5)

        self.SetSizer(contents)
        contents.Fit(self)

    def _on_em_output_folder_browse_button_click(self, event):
        defaultPath = self._model.em_images_output_folder
        with wx.DirDialog(self, "Select the output directory for EM images", defaultPath) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                self._model.em_images_output_folder = path
                self._em_images_output_folder_edit.SetValue(path)

    def _on_acquire_button_click(self, event):
        self._model.write_parameters()
        self.EndModal(wx.ID_OK)

    def _on_em_images_output_folder_change(self, event):
        self._model.em_images_output_folder = self._em_images_output_folder_edit.GetValue()
        print('em_images_output_folder={}'.format(self._model.em_images_output_folder))

    def _on_prefix_change(self, event):
        self._model.em_images_prefix = self._em_prefix_edit.GetValue()
        print('em_images_prefix={}'.format(self._model.em_images_prefix))

    def _on_scale_change(self, event):
        self._model.em_scale = self._em_scale_dropdown.GetStringSelection()
        print('em_scale={}'.format(self._model.em_scale))

    def _on_magnification_change(self, event):
        self._model.em_magnification = int(self._em_magnification_text.GetValue())
        print('em_magnification={}'.format(self._model.em_magnification))

    def _on_dwell_time_change(self, event):
        self._model.em_dwell_time_microseconds = float(self._em_dwell_time_text.GetValue())
        print('em_dwell_time_microsecs={}'.format(self._model.em_dwell_time_microseconds))

    def _on_delay_change(self, event):
        self._model.delay_between_EM_image_acquisition_secs = float(self._em_acquisition_delay_text.GetValue())
        print('delay_between_EM_image_acquisition_secs={}'.format(self._model.delay_between_EM_image_acquisition_secs))
