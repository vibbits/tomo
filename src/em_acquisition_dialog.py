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

        em_poi_filter_label = wx.StaticText(self, wx.ID_ANY, "Positions to image (first is 1):")
        self._em_poi_filter_text = wx.TextCtrl(self, wx.ID_ANY, "None", size=(70, -1))

        #
        registration_output_folder_label = wx.StaticText(self, wx.ID_ANY, "Output Folder:")
        self._registration_output_folder_edit = wx.TextCtrl(self, wx.ID_ANY, self._model.em_registration_output_folder, size=(w, -1))
        self._registration_output_folder_button = wx.Button(self, wx.ID_ANY, "Browse")

        regist_out_sizer = wx.BoxSizer(wx.HORIZONTAL)
        regist_out_sizer.Add(self._registration_output_folder_edit, flag=wx.ALIGN_CENTER_VERTICAL)
        regist_out_sizer.AddSpacer(8)
        regist_out_sizer.Add(self._registration_output_folder_button, flag=wx.ALIGN_CENTER_VERTICAL)

        registration_pixel_size_label = wx.StaticText(self, wx.ID_ANY, u"Pixel size [nm]:")
        self._registration_pixel_size_nm_value = wx.StaticText(self, wx.ID_ANY, "0.0")

        em_registration_method_label = wx.StaticText(self, wx.ID_ANY, "Registration method:")
        self._em_registration_dropdown = wx.Choice(self, wx.ID_ANY, choices=self._model.registration_methods)
        ok = self._em_registration_dropdown.SetStringSelection(self._model.em_registration_params['method'])
        assert ok

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

        acquisition_fgs.Add(em_poi_filter_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        acquisition_fgs.Add(self._em_poi_filter_text, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        #
        output_box = wx.StaticBox(self, -1, 'Output')
        output_sizer = wx.StaticBoxSizer(output_box, wx.VERTICAL)
        output_sizer.Add(output_fgs, 0, wx.ALL | wx.CENTER, 10)

        #
        acquisition_box = wx.StaticBox(self, -1, 'Acquisition Parameters')
        acquisition_sizer = wx.StaticBoxSizer(acquisition_box, wx.VERTICAL)
        acquisition_sizer.Add(acquisition_fgs, 0, wx.ALL, 10)

        # Registration
        regist_fgs = wx.FlexGridSizer(cols=2, vgap=4, hgap=8)
        regist_fgs.Add(em_registration_method_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        regist_fgs.Add(self._em_registration_dropdown, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        regist_fgs.Add(registration_output_folder_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        regist_fgs.Add(regist_out_sizer, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        regist_fgs.Add(registration_pixel_size_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        regist_fgs.Add(self._registration_pixel_size_nm_value, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        regist_box = wx.StaticBox(self, -1, 'Image Registration')
        regist_sizer = wx.StaticBoxSizer(regist_box, wx.VERTICAL)
        regist_sizer.Add(regist_fgs, 0, wx.ALL|wx.CENTER, 10)

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
        self.Bind(wx.EVT_TEXT, self._on_poi_filter_change, self._em_poi_filter_text)
        self.Bind(wx.EVT_CHOICE, self._on_scale_change, self._em_scale_dropdown)
        self.Bind(wx.EVT_BUTTON, self._on_em_output_folder_browse_button_click, self._em_images_output_folder_button)
        self.Bind(wx.EVT_TEXT, self._on_registration_output_folder_change, self._registration_output_folder_edit)
        self.Bind(wx.EVT_BUTTON, self._on_registration_output_folder_browse_button_click, self._registration_output_folder_button)
        self.Bind(wx.EVT_CHOICE, self._on_registration_method_change, self._em_registration_dropdown)
        self.Bind(wx.EVT_BUTTON, self._on_acquire_button_click, self._acquire_button)

        b = 5
        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(output_sizer, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(acquisition_sizer, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(regist_sizer, 0, wx.ALL | wx.EXPAND, border=b)
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

    def _on_registration_output_folder_browse_button_click(self, event):
        defaultPath = self._model.em_registration_output_folder
        print('defaultPath=' + defaultPath)
        with wx.DirDialog(self, "Select the registration output directory", defaultPath) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                print('Set em_registration_output_folder = ' + path)
                self._model.em_registration_output_folder = path
                self._registration_output_folder_edit.SetValue(path)

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
        scale_string = self._em_scale_dropdown.GetStringSelection()
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

        # FIXME: it seems that setting a dwell time < 800 ns gets silently ignored by Odemis
        # (which then continues to use the typically larger current dwell time)
        # Check in Odemis source code if we can confirm that. And then forbid the user from setting a smaller value here in Tomo.

    def set_default_poi_list(self):
        first_poi, last_poi = 1, len(self._model.all_points_of_interest)
        self._model.em_pois_to_image = range(1, last_poi + 1)
        self._em_poi_filter_text.SetValue('{}-{}'.format(first_poi, last_poi))

    def _on_poi_filter_change(self, event):
        num_pois = len(self._model.all_points_of_interest)
        text = self._em_poi_filter_text.GetValue()
        print('em_poi_filter_text="{}" num_pois={}'.format(text, num_pois))
        pois_range = _parse_filter_text(text, num_pois)
        if pois_range is not None:
            first_poi, last_poi = pois_range
            print('Valid POIs filter: acquire pois {} to {}'.format(first_poi, last_poi))
            self._model.em_pois_to_image = range(first_poi, last_poi + 1)
        else:
            print('Invalid POIs filter text -> acquire all POIs')
            self._model.em_pois_to_image = range(1, num_pois + 1)

    def _on_delay_change(self, event):
        self._model.delay_between_EM_image_acquisition_secs = float(self._em_acquisition_delay_text.GetValue())
        print('delay_between_EM_image_acquisition_secs={}'.format(self._model.delay_between_EM_image_acquisition_secs))

    def _on_registration_output_folder_change(self, event):
        self._model.em_registration_output_folder = self._registration_output_folder_edit.GetValue()
        print('em_registration_output_folder={}'.format(self._model.em_registration_output_folder))

    def _on_registration_method_change(self, event):
        self._model.em_registration_params['method'] = self._em_registration_dropdown.GetStringSelection()
        print('em registration method={}'.format(self._model.em_registration_params['method']))

    def _update_image_size_labels(self):  # IMPROVEME: again, using a listener on the model would probably be cleaner/safer
        w, h = self._model.get_em_image_size_in_pixels()
        self._image_size_pixels.SetLabelText('{} x {}'.format(w, h))
        pixelsize_in_nanometer = self._model.get_em_pixelsize_in_nanometer()
        self._registration_pixel_size_nm_value.SetLabelText('{:f}'.format(pixelsize_in_nanometer))


def _parse_filter_text(text, upper_limit):  
    # Parse a string such as "n-m" with 1 <= n <= m <= upper_limit into (n, m).
    # Returns None if text does not satisfy this requirements.
    print('filter text={}'.format(text))
    chunks = text.split('-')
    if len(chunks) != 2:
        return None
    s1, s2 = chunks
    if not(s1.isdigit() and s2.isdigit()):
        return None
    lo, hi = int(s1), int(s2)
    if lo < 1 or hi > upper_limit or lo > hi:
        return None
    return lo, hi

