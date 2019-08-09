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
        ok = self._em_scale_dropdown.SetStringSelection(self._model.get_em_scale_string())
        assert ok

        em_magnification_label = wx.StaticText(self, wx.ID_ANY, "Magnification:")
        self._em_magnification_text = wx.TextCtrl(self, wx.ID_ANY, str(self._model.em_magnification), size=(70, -1))

        em_dwell_time_label = wx.StaticText(self, wx.ID_ANY, u"Dwell time [\u03bcs]:")  # \u03bc is the greek letter mu
        self._em_dwell_time_text = wx.TextCtrl(self, wx.ID_ANY, str(self._model.em_dwell_time_microseconds), size=(70, -1))

        em_acquisition_delay_label = wx.StaticText(self, wx.ID_ANY, "Acquisition Delay [s]:")
        self._em_acquisition_delay_text = wx.TextCtrl(self, wx.ID_ANY, str(self._model.delay_between_EM_image_acquisition_secs), size=(70, -1))

        # The image size is just information to the user, a reminder that we rely on the acquired images to be of a certain size.
        image_size_label = wx.StaticText(self, wx.ID_ANY, "Image size (width x height):")
        self._image_size_pixels = wx.StaticText(self, wx.ID_ANY, "{} x {} pixels".format(0, 0))

        #
        sift_output_folder_label = wx.StaticText(self, wx.ID_ANY, "Output Folder:")
        self._sift_output_folder_edit = wx.TextCtrl(self, wx.ID_ANY, self._model.lm_sift_output_folder, size=(w, -1))
        self._sift_output_folder_button = wx.Button(self, wx.ID_ANY, "Browse")

        sift_out_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sift_out_sizer.Add(self._sift_output_folder_edit, flag=wx.ALIGN_CENTER_VERTICAL)
        sift_out_sizer.AddSpacer(8)
        sift_out_sizer.Add(self._sift_output_folder_button, flag=wx.ALIGN_CENTER_VERTICAL)

        sift_pixel_size_label = wx.StaticText(self, wx.ID_ANY, u"Pixel size [pixels/\u03bcm]:")  # \u03bc is the greek letter mu
        self._sift_pixel_size_value = wx.StaticText(self, wx.ID_ANY, "0.0")

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

        acquisition_fgs.Add(image_size_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        acquisition_fgs.Add(self._image_size_pixels, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        #
        output_box = wx.StaticBox(self, -1, 'Output')
        output_sizer = wx.StaticBoxSizer(output_box, wx.VERTICAL)
        output_sizer.Add(output_fgs, 0, wx.ALL | wx.CENTER, 10)

        #
        acquisition_box = wx.StaticBox(self, -1, 'Acquisition Parameters')
        acquisition_sizer = wx.StaticBoxSizer(acquisition_box, wx.VERTICAL)
        acquisition_sizer.Add(acquisition_fgs, 0, wx.ALL, 10)

        # SIFT registration
        sift_fgs = wx.FlexGridSizer(cols=2, vgap=4, hgap=8)
        sift_fgs.Add(sift_output_folder_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sift_fgs.Add(sift_out_sizer, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sift_fgs.Add(sift_pixel_size_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sift_fgs.Add(self._sift_pixel_size_value, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        sift_box = wx.StaticBox(self, -1, 'SIFT Registration')
        sift_sizer = wx.StaticBoxSizer(sift_box, wx.VERTICAL)
        sift_sizer.Add(sift_fgs, 0, wx.ALL|wx.CENTER, 10)

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
        self.Bind(wx.EVT_TEXT, self._on_sift_output_folder_change, self._sift_output_folder_edit)
        self.Bind(wx.EVT_BUTTON, self._on_sift_output_folder_browse_button_click, self._sift_output_folder_button)
        self.Bind(wx.EVT_BUTTON, self._on_acquire_button_click, self._acquire_button)

        b = 5
        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(output_sizer, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(acquisition_sizer, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(sift_sizer, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(instructions_label, 0, wx.ALL | wx.CENTER, border=b)
        contents.Add(self._acquire_button, 0, wx.ALL | wx.CENTER, border=b)

        self.SetSizer(contents)
        contents.Fit(self)

        # Update dependent labels
        self._update_image_size_labels()

    def _on_em_output_folder_browse_button_click(self, event):
        defaultPath = self._model.em_images_output_folder
        with wx.DirDialog(self, "Select the output directory for EM images", defaultPath) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                self._model.em_images_output_folder = path
                self._em_images_output_folder_edit.SetValue(path)

    def _on_sift_output_folder_browse_button_click(self, event):
        defaultPath = self._model.em_sift_output_folder
        print('defaultPath=' + defaultPath)
        with wx.DirDialog(self, "Select the SIFT output directory", defaultPath) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                print('Set em_sift_output_folder = ' + path)
                self._model.em_sift_output_folder = path
                self._sift_output_folder_edit.SetValue(path)

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
        scale_string  = self._em_scale_dropdown.GetStringSelection()
        self._model.set_em_scale_string(scale_string)
        print('em_scale={}'.format(self._model.em_scale))
        self._update_image_size_labels()

    def _on_magnification_change(self, event):
        self._model.em_magnification = int(self._em_magnification_text.GetValue())
        print('em_magnification={}'.format(self._model.em_magnification))
        self._update_image_size_labels()

    def _on_dwell_time_change(self, event):
        self._model.em_dwell_time_microseconds = float(self._em_dwell_time_text.GetValue())
        print('em_dwell_time_microsecs={}'.format(self._model.em_dwell_time_microseconds))

    def _on_delay_change(self, event):
        self._model.delay_between_EM_image_acquisition_secs = float(self._em_acquisition_delay_text.GetValue())
        print('delay_between_EM_image_acquisition_secs={}'.format(self._model.delay_between_EM_image_acquisition_secs))

    def _on_sift_output_folder_change(self, event):
        self._model.em_sift_output_folder = self._sift_output_folder_edit.GetValue()
        print('em_sift_output_folder={}'.format(self._model.em_sift_output_folder))

    def _update_image_size_labels(self):  # IMPROVEME: again, using a listener on the model would probably be cleaner/safer
        w, h = self._model.get_em_image_size_in_pixels()
        self._image_size_pixels.SetLabelText('{} x {}'.format(w, h))
        pixels_per_micrometer = self._model.get_em_pixels_per_micrometer()
        self._sift_pixel_size_value.SetLabelText('{:f}'.format(pixels_per_micrometer))


