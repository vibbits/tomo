# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx
import wx.lib.intctrl


class LMAcquisitionDialog(wx.Dialog):
    def __init__(self, model, parent, ID, title, size=wx.DefaultSize, pos=wx.DefaultPosition, style=wx.DEFAULT_DIALOG_STYLE):
        wx.Dialog.__init__(self, parent, ID, title, pos, size, style)

        self._model = model

        w = 450  # width for long input fields

        #
        lm_images_output_folder_label = wx.StaticText(self, wx.ID_ANY, "Output Folder:")
        self._lm_images_output_folder_edit = wx.TextCtrl(self, wx.ID_ANY, self._model.lm_images_output_folder, size=(w, -1))
        self._lm_images_output_folder_button = wx.Button(self, wx.ID_ANY, "Browse")

        prefix_label = wx.StaticText(self, wx.ID_ANY, "Filename Prefix:")
        self._prefix_edit = wx.TextCtrl(self, wx.ID_ANY, self._model.lm_images_prefix, size=(w, -1))

        lm_stabilization_time_label = wx.StaticText(self, wx.ID_ANY, "Stabilization time (sec):")
        self._lm_stabilization_time_edit = wx.TextCtrl(self, wx.ID_ANY, str(self._model.lm_stabilization_time_secs), size=(50, -1))

        lm_acquisition_delay_label = wx.StaticText(self, wx.ID_ANY, "Delay after imaging (sec):")
        self._lm_acquisition_delay_edit = wx.TextCtrl(self, wx.ID_ANY, str(self._model.delay_between_LM_image_acquisition_secs), size=(50, -1))

        if not self._can_use_focus_map():
            self._model.lm_use_focus_map = False

        self._lm_use_focusmap_checkbox = wx.CheckBox(self, wx.ID_ANY, "Use Focus Map")
        self._lm_use_focusmap_checkbox.Enable(self._can_use_focus_map())
        self._lm_use_focusmap_checkbox.SetValue(self._model.lm_use_focus_map)

        lm_sizer = wx.BoxSizer(wx.HORIZONTAL)
        lm_sizer.Add(self._lm_images_output_folder_edit, flag=wx.ALIGN_CENTER_VERTICAL)
        lm_sizer.AddSpacer(8)
        lm_sizer.Add(self._lm_images_output_folder_button, flag=wx.ALIGN_CENTER_VERTICAL)

        empty_label1 = wx.StaticText(self, wx.ID_ANY, "")  # IMPROVEME: using an empty label as placeholder is probably not the
        empty_label2 = wx.StaticText(self, wx.ID_ANY, "")
        empty_label3 = wx.StaticText(self, wx.ID_ANY, "")

        sift_output_folder_label = wx.StaticText(self, wx.ID_ANY, "Output Folder:")
        self._sift_output_folder_edit = wx.TextCtrl(self, wx.ID_ANY, self._model.lm_sift_output_folder, size=(w, -1))
        self._sift_output_folder_button = wx.Button(self, wx.ID_ANY, "Browse")

        sift_out_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sift_out_sizer.Add(self._sift_output_folder_edit, flag=wx.ALIGN_CENTER_VERTICAL)
        sift_out_sizer.AddSpacer(8)
        sift_out_sizer.Add(self._sift_output_folder_button, flag=wx.ALIGN_CENTER_VERTICAL)

        sift_pixel_size_label = wx.StaticText(self, wx.ID_ANY, "Pixel size (pixels/mm):")
        self._sift_pixel_size_edit = wx.TextCtrl(self, wx.ID_ANY, str(self._model.lm_sift_images_pixels_per_mm), size=(100, -1))

        # The image size is just information to the user, a reminder that we rely on the acquired images to be of a certain size.
        image_size_label = wx.StaticText(self, wx.ID_ANY, "Image size (width x height):")
        image_size_pixels = wx.StaticText(self, wx.ID_ANY, "{} x {} pixels".format(self._model.lm_image_size[0], self._model.lm_image_size[1]))

        self._enhance_contrast_checkbox = wx.CheckBox(self, wx.ID_ANY, "Enhance contrast before registration")
        self._enhance_contrast_checkbox.SetValue(self._model.lm_registration_params["enhance_contrast"])

        self._crop_checkbox = wx.CheckBox(self, wx.ID_ANY, "Crop before registration")
        self._crop_checkbox.SetValue(self._model.lm_registration_params["crop"])

        self._roi_label = wx.StaticText(self, wx.ID_ANY, "Crop ROI (x, y, width, height):")  # in pixels
        self._roi_x_edit = wx.lib.intctrl.IntCtrl(self, wx.ID_ANY, 0, min=0, limited=True, allow_none=False, size=(50, -1))
        self._roi_y_edit = wx.lib.intctrl.IntCtrl(self, wx.ID_ANY, 0, min=0, limited=True, allow_none=False, size=(50, -1))
        self._roi_width_edit = wx.lib.intctrl.IntCtrl(self, wx.ID_ANY, 0, min=0, limited=True, allow_none=False, size=(50, -1))
        self._roi_height_edit = wx.lib.intctrl.IntCtrl(self, wx.ID_ANY, 0, min=0, limited=True, allow_none=False, size=(50, -1))
        self._update_roi()

        roi_values_sizer = wx.BoxSizer(wx.HORIZONTAL)
        roi_values_sizer.Add(self._roi_x_edit, flag=wx.ALIGN_CENTER_VERTICAL)
        roi_values_sizer.Add(self._roi_y_edit, flag=wx.ALIGN_CENTER_VERTICAL)
        roi_values_sizer.Add(self._roi_width_edit, flag=wx.ALIGN_CENTER_VERTICAL)
        roi_values_sizer.Add(self._roi_height_edit, flag=wx.ALIGN_CENTER_VERTICAL)

        # LM Image Acquisition
        lm_fgs = wx.FlexGridSizer(cols=2, vgap=4, hgap=8)
        lm_fgs.Add(lm_images_output_folder_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(lm_sizer, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(prefix_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(self._prefix_edit, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(lm_stabilization_time_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(self._lm_stabilization_time_edit, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(lm_acquisition_delay_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(self._lm_acquisition_delay_edit, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(empty_label1, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(self._lm_use_focusmap_checkbox, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        lm_fgs.Add(image_size_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(image_size_pixels, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        lm_box = wx.StaticBox(self, -1, 'LM Image Acquisition')
        lm_sizer = wx.StaticBoxSizer(lm_box, wx.VERTICAL)
        lm_sizer.Add(lm_fgs, 0, wx.ALL|wx.CENTER, 10)

        # SIFT registration
        sift_fgs = wx.FlexGridSizer(cols=2, vgap=4, hgap=8)
        sift_fgs.Add(sift_output_folder_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sift_fgs.Add(sift_out_sizer, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sift_fgs.Add(sift_pixel_size_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sift_fgs.Add(self._sift_pixel_size_edit, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        sift_fgs.Add(empty_label2, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sift_fgs.Add(self._enhance_contrast_checkbox, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sift_fgs.Add(empty_label3, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sift_fgs.Add(self._crop_checkbox, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        sift_fgs.Add(self._roi_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sift_fgs.Add(roi_values_sizer, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        sift_box = wx.StaticBox(self, -1, 'SIFT Registration')
        sift_sizer = wx.StaticBoxSizer(sift_box, wx.VERTICAL)
        sift_sizer.Add(sift_fgs, 0, wx.ALL|wx.CENTER, 10)

        instructions_label = wx.StaticText(self, wx.ID_ANY, ("If the LM microscope is ready and positioned over the point-of-interest in the first slice "
                                                             "press the button below to start image acquisition. " 
                                                             "The microscope will successively acquire LM images at the point-of-interest on each slice "
                                                             "and align them with SIFT image registration. Furthermore, the image offsets calculated during "
                                                             "registration are used to improve the predicted point-of-interest positions in the different slices. "
                                                             "After imaging the last slice, the stage will be moved back to the point-of-interest on the first slice."))
        instructions_label.Wrap(650)  # Force line wrapping of the instructions text (max 650 pixels per line).

        self._acquire_button = wx.Button(self, wx.ID_ANY, "Acquire LM Images")

        self.Bind(wx.EVT_TEXT, self._on_lm_images_output_folder_change, self._lm_images_output_folder_edit)
        self.Bind(wx.EVT_TEXT, self._on_prefix_change, self._prefix_edit)
        self.Bind(wx.EVT_TEXT, self._on_stabilization_time_change, self._lm_stabilization_time_edit)
        self.Bind(wx.EVT_TEXT, self._on_delay_change, self._lm_acquisition_delay_edit)
        self.Bind(wx.EVT_TEXT, self._on_sift_output_folder_change, self._sift_output_folder_edit)
        self.Bind(wx.EVT_TEXT, self._on_sift_pixel_size_change, self._sift_pixel_size_edit)
        self.Bind(wx.EVT_CHECKBOX, self._on_enhance_contrast_change, self._enhance_contrast_checkbox)
        self.Bind(wx.EVT_CHECKBOX, self._on_use_focusmap_change, self._lm_use_focusmap_checkbox)
        self.Bind(wx.EVT_CHECKBOX, self._on_crop_change, self._crop_checkbox)
        self.Bind(wx.lib.intctrl.EVT_INT, self._on_roi_int_change, self._roi_x_edit)
        self.Bind(wx.lib.intctrl.EVT_INT, self._on_roi_int_change, self._roi_y_edit)
        self.Bind(wx.lib.intctrl.EVT_INT, self._on_roi_int_change, self._roi_width_edit)
        self.Bind(wx.lib.intctrl.EVT_INT, self._on_roi_int_change, self._roi_height_edit)
        self.Bind(wx.EVT_BUTTON, self._on_lm_output_folder_browse_button_click, self._lm_images_output_folder_button)
        self.Bind(wx.EVT_BUTTON, self._on_sift_output_folder_browse_button_click, self._sift_output_folder_button)
        self.Bind(wx.EVT_BUTTON, self._on_acquire_button_click, self._acquire_button)

        b = 5 # border size
        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(lm_sizer, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(sift_sizer, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(instructions_label, 0, wx.ALL | wx.CENTER, border=b)
        contents.Add(self._acquire_button, 0, wx.ALL | wx.CENTER, border=b)

        self.SetSizer(contents)
        contents.Fit(self)

    def _can_use_focus_map(self):
        focus_map = self._model.focus_map
        return (focus_map is not None) and (len(focus_map.get_user_defined_focus_positions()) > 0)

    # TODO: try to generalize/unify the 2 functions below (and similar ones in other ui source files)

    def _on_lm_output_folder_browse_button_click(self, event):
        defaultPath = self._model.lm_images_output_folder
        print('defaultPath='+defaultPath)
        with wx.DirDialog(self, "Select the output directory for LM images", defaultPath) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                print('Set lm_images_output_folder = ' + path)
                self._model.lm_images_output_folder = path
                self._lm_images_output_folder_edit.SetValue(path)

    def _on_sift_output_folder_browse_button_click(self, event):
        defaultPath = self._model.lm_sift_output_folder
        print('defaultPath='+defaultPath)
        with wx.DirDialog(self, "Select the SIFT output directory", defaultPath) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                print('Set lm_sift_output_folder = ' + path)
                self._model.lm_sift_output_folder = path
                self._sift_output_folder_edit.SetValue(path)

    def _on_acquire_button_click(self, event):
        self._model.write_parameters()
        self.EndModal(wx.ID_OK)

    def _on_lm_images_output_folder_change(self, event):
        self._model.lm_images_output_folder = self._lm_images_output_folder_edit.GetValue()
        print('lm_images_output_folder={}'.format(self._model.lm_images_output_folder))

    def _on_prefix_change(self, event):
        self._model.lm_images_prefix = self._prefix_edit.GetValue()
        print('lm_images_prefix={}'.format(self._model.lm_images_prefix))

    def _on_delay_change(self, event):
        self._model.delay_between_LM_image_acquisition_secs = float(self._lm_acquisition_delay_edit.GetValue())
        print('delay_between_LM_image_acquisition_secs={}'.format(self._model.delay_between_LM_image_acquisition_secs))

    def _on_stabilization_time_change(self, event):
        self._model.lm_stabilization_time_secs = float(self._lm_stabilization_time_edit.GetValue())
        print('lm_stabilization_time_secs={}'.format(self._model.lm_stabilization_time_secs))

    def _on_use_focusmap_change(self, event):
        self._model.lm_use_focus_map = self._lm_use_focusmap_checkbox.IsChecked()
        print('lm_use_focus_map={}'.format(self._model.lm_use_focus_map))

    def _on_crop_change(self, event):
        self._model.lm_registration_params['crop'] = self._crop_checkbox.IsChecked()
        print('crop={}'.format(self._model.lm_registration_params['crop']))
        self._update_roi()

    def _update_roi(self):
        if self._model.lm_registration_params['crop']:
            self._roi_label.Enable(True)
            self._roi_x_edit.Enable(True)
            self._roi_y_edit.Enable(True)
            self._roi_width_edit.Enable(True)
            self._roi_height_edit.Enable(True)
            self._roi_x_edit.SetValue(self._model.lm_registration_params['roi'][0])
            self._roi_y_edit.SetValue(self._model.lm_registration_params['roi'][1])
            self._roi_width_edit.SetValue(self._model.lm_registration_params['roi'][2])
            self._roi_height_edit.SetValue(self._model.lm_registration_params['roi'][3])
        else:
            self._roi_label.Enable(False)
            self._roi_x_edit.Enable(False)
            self._roi_y_edit.Enable(False)
            self._roi_width_edit.Enable(False)
            self._roi_height_edit.Enable(False)
            self._roi_x_edit.ChangeValue(0)  # ChangeValue() does NOT send a change event
            self._roi_y_edit.ChangeValue(0)
            self._roi_width_edit.ChangeValue(0)
            self._roi_height_edit.ChangeValue(0)


    def _on_roi_int_change(self, event):
        if self._model.lm_registration_params['crop'] == False:
            return
        obj = event.EventObject
        roi = self._model.lm_registration_params['roi']
        if obj == self._roi_x_edit:
            roi[0] = self._roi_x_edit.GetValue()
        elif obj == self._roi_y_edit:
            roi[1] = self._roi_y_edit.GetValue()
        elif obj == self._roi_width_edit:
            roi[2] = self._roi_width_edit.GetValue()
        elif obj == self._roi_height_edit:
            roi[3] = self._roi_height_edit.GetValue()
        # print('roi=[{} {} {} {}]'.format(self._model.lm_registration_params['roi'][0],
        #                                  self._model.lm_registration_params['roi'][1],
        #                                  self._model.lm_registration_params['roi'][2],
        #                                  self._model.lm_registration_params['roi'][3]))

    def _on_enhance_contrast_change(self, event):
        self._model.lm_registration_params['enhance_contrast'] = self._enhance_contrast_checkbox.IsChecked()
        print('enhance_contrast={}'.format(self._model.lm_registration_params['enhance_contrast']))

    def _on_sift_output_folder_change(self, event):
        self._model.lm_sift_output_folder = self._sift_output_folder_edit.GetValue()
        print('lm_sift_output_folder={}'.format(self._model.lm_sift_output_folder))

    def _on_sift_pixel_size_change(self, event):
        self._model.lm_sift_images_pixels_per_mm = float(self._sift_pixel_size_edit.GetValue())
        print('lm_sift_images_pixels_per_mm={}'.format(self._model.lm_sift_images_pixels_per_mm))
