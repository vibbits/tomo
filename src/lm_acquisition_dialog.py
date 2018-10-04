# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx
from wx.lib.pubsub import pub

class LMAcquisitionDialog(wx.Dialog):
    _model = None

    # UI elements
    _lm_images_output_folder_edit = None
    _prefix_edit = None
    _lm_acquisition_delay_edit = None
    _sift_input_folder_edit = None
    _sift_output_folder_edit = None
    _sift_pixel_size_edit = None
    _sift_input_folder_button = None
    _sift_output_folder_button = None
    _lm_images_output_folder_button = None
    _acquire_button = None
    _lm_max_autofocus_change_label = None
    _lm_max_autofocus_change_edit = None
    _lm_do_autofocus_checkbox = None

    def __init__(self, model, parent, ID, title, size = wx.DefaultSize, pos = wx.DefaultPosition, style = wx.DEFAULT_DIALOG_STYLE):
        wx.Dialog.__init__(self, parent, ID, title, pos, size, style)

        self._model = model

        w = 450  # width for long input fields

        #
        lm_images_output_folder_label = wx.StaticText(self, wx.ID_ANY, "Output Folder:")
        self._lm_images_output_folder_edit = wx.TextCtrl(self, wx.ID_ANY, self._model.lm_images_output_folder, size = (w, -1))
        self._lm_images_output_folder_button = wx.Button(self, wx.ID_ANY, "Browse")

        prefix_label = wx.StaticText(self, wx.ID_ANY, "Filename Prefix:")
        self._prefix_edit = wx.TextCtrl(self, wx.ID_ANY, self._model.lm_images_prefix, size = (w, -1))

        lm_acquisition_delay_label = wx.StaticText(self, wx.ID_ANY, "Acquisition Delay (sec):")
        self._lm_acquisition_delay_edit = wx.TextCtrl(self, wx.ID_ANY, str(self._model.delay_between_LM_image_acquisition_secs), size = (50, -1))

        lm_sizer = wx.BoxSizer(wx.HORIZONTAL)
        lm_sizer.Add(self._lm_images_output_folder_edit, flag = wx.ALIGN_CENTER_VERTICAL)
        lm_sizer.AddSpacer(8)
        lm_sizer.Add(self._lm_images_output_folder_button, flag = wx.ALIGN_CENTER_VERTICAL)

        empty_label = wx.StaticText(self, wx.ID_ANY, "")

        self._lm_do_autofocus_checkbox = wx.CheckBox(self, wx.ID_ANY, "Perform Autofocus")
        self._lm_do_autofocus_checkbox.SetValue(self._model.lm_do_autofocus)

        self._lm_max_autofocus_change_label = wx.StaticText(self, wx.ID_ANY, "Max. Autofocus Change (nanometer):")
        self._lm_max_autofocus_change_edit = wx.TextCtrl(self, wx.ID_ANY, str(self._model.lm_max_autofocus_change_nanometers), size = (50, -1))

        self._enable_autofocus_edit_field(self._model.lm_do_autofocus)

        #
        sift_input_folder_label = wx.StaticText(self, wx.ID_ANY, "Input Folder:")
        self._sift_input_folder_edit = wx.TextCtrl(self, wx.ID_ANY, self._model.sift_input_folder, size = (w, -1))
        self._sift_input_folder_button = wx.Button(self, wx.ID_ANY, "Browse")

        sift_in_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sift_in_sizer.Add(self._sift_input_folder_edit, flag = wx.ALIGN_CENTER_VERTICAL)
        sift_in_sizer.AddSpacer(8)
        sift_in_sizer.Add(self._sift_input_folder_button, flag = wx.ALIGN_CENTER_VERTICAL)

        sift_output_folder_label = wx.StaticText(self, wx.ID_ANY, "Output Folder:")
        self._sift_output_folder_edit = wx.TextCtrl(self, wx.ID_ANY, self._model.sift_output_folder, size = (w, -1))
        self._sift_output_folder_button = wx.Button(self, wx.ID_ANY, "Browse")

        sift_out_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sift_out_sizer.Add(self._sift_output_folder_edit, flag = wx.ALIGN_CENTER_VERTICAL)
        sift_out_sizer.AddSpacer(8)
        sift_out_sizer.Add(self._sift_output_folder_button, flag = wx.ALIGN_CENTER_VERTICAL)

        sift_pixel_size_label = wx.StaticText(self, wx.ID_ANY, "Pixel size (mm/pixel):")
        self._sift_pixel_size_edit = wx.TextCtrl(self, wx.ID_ANY, str(self._model.sift_images_mm_per_pixel), size = (100, -1))

        # LM Image Acquisition
        lm_fgs = wx.FlexGridSizer(cols = 2, vgap = 4, hgap = 8)
        lm_fgs.Add(lm_images_output_folder_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(lm_sizer, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(prefix_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(self._prefix_edit, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(lm_acquisition_delay_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(self._lm_acquisition_delay_edit, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(empty_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(self._lm_do_autofocus_checkbox, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(self._lm_max_autofocus_change_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(self._lm_max_autofocus_change_edit, flag =wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        lm_box = wx.StaticBox(self, -1, 'LM Image Acquisition')
        lm_sizer = wx.StaticBoxSizer(lm_box, wx.VERTICAL)
        lm_sizer.Add(lm_fgs, 0, wx.ALL|wx.CENTER, 10)

        # SIFT registration
        sift_fgs = wx.FlexGridSizer(cols = 2, vgap = 4, hgap = 8)
        sift_fgs.Add(sift_input_folder_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sift_fgs.Add(sift_in_sizer, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sift_fgs.Add(sift_output_folder_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sift_fgs.Add(sift_out_sizer, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sift_fgs.Add(sift_pixel_size_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sift_fgs.Add(self._sift_pixel_size_edit, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        sift_box = wx.StaticBox(self, -1, 'SIFT Registration')
        sift_sizer = wx.StaticBoxSizer(sift_box, wx.VERTICAL)
        sift_sizer.Add(sift_fgs, 0, wx.ALL|wx.CENTER, 10)

        instructions_label = wx.StaticText(self, wx.ID_ANY, ("Prepare the LM microscope and position it over the point-of-interest in the first slice. "
                                                             "Afterwards, press the button below to start image acquisition. " 
                                                             "The microscope will successively acquire LM images at the point-of-interest on each slice "
                                                             "and align them with SIFT image registration. Furthermore, the image offsets calculated during "
                                                             "registration are used to improve the predicted point-of-interest positions in the different slices."))
        instructions_label.Wrap(650)  # Force line wrapping of the instructions text (max 650 pixels per line).

        self._acquire_button = wx.Button(self, wx.ID_ANY, "Acquire LM Images")

        self.Bind(wx.EVT_TEXT, self._on_lm_images_output_folder_change, self._lm_images_output_folder_edit)
        self.Bind(wx.EVT_TEXT, self._on_prefix_change, self._prefix_edit)
        self.Bind(wx.EVT_TEXT, self._on_delay_change, self._lm_acquisition_delay_edit)
        self.Bind(wx.EVT_TEXT, self._on_sift_input_folder_change, self._sift_input_folder_edit)
        self.Bind(wx.EVT_TEXT, self._on_sift_output_folder_change, self._sift_output_folder_edit)
        self.Bind(wx.EVT_TEXT, self._on_sift_pixel_size_change, self._sift_pixel_size_edit)
        self.Bind(wx.EVT_CHECKBOX, self._on_lm_do_autofocus_change, self._lm_do_autofocus_checkbox)
        self.Bind(wx.EVT_TEXT, self._on_lm_max_autofocus_change, self._lm_max_autofocus_change_edit)
        self.Bind(wx.EVT_BUTTON, self._on_lm_output_folder_browse_button_click, self._lm_images_output_folder_button)
        self.Bind(wx.EVT_BUTTON, self._on_sift_input_folder_browse_button_click, self._sift_input_folder_button)
        self.Bind(wx.EVT_BUTTON, self._on_sift_output_folder_browse_button_click, self._sift_output_folder_button)
        self.Bind(wx.EVT_BUTTON, self._on_acquire_button_click, self._acquire_button)

        b = 5 # border size
        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(lm_sizer, 0, wx.ALL | wx.EXPAND, border = b)
        contents.Add(sift_sizer, 0, wx.ALL | wx.EXPAND, border = b)
        contents.Add(instructions_label, 0, wx.ALL | wx.CENTER, border = b)
        contents.Add(self._acquire_button, 0, wx.ALL | wx.CENTER, border = b)

        self.SetSizer(contents)
        contents.Fit(self)

    def _enable_autofocus_edit_field(self, enable):
        self._lm_max_autofocus_change_label.Enable(enable)
        self._lm_max_autofocus_change_edit.Enable(enable)

    # TODO: try to generalize/unify the 3 functions below (and similar ones in other ui source files)

    def _on_lm_output_folder_browse_button_click(self, event):
        defaultPath = self._model.lm_images_output_folder
        dlg = wx.DirDialog(self, "Select the output directory for LM images", defaultPath)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self._model.lm_images_output_folder = path
            self._lm_images_output_folder_edit.SetLabelText(path)
        dlg.Destroy()

    def _on_sift_input_folder_browse_button_click(self, event):
        defaultPath = self._model.sift_input_folder
        dlg = wx.DirDialog(self, "Select the SIFT input directory", defaultPath)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self._model.sift_input_folder = path
            self._sift_input_folder_edit.SetLabelText(path)
        dlg.Destroy()

    def _on_sift_output_folder_browse_button_click(self, event):
        defaultPath = self._model.sift_output_folder
        dlg = wx.DirDialog(self, "Select the SIFT output directory", defaultPath)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self._model.sift_output_folder = path
            self._sift_output_folder_edit.SetLabelText(path)
        dlg.Destroy()

    def _on_acquire_button_click(self, event):
        self.Show(False)
        self._model.write_parameters()
        pub.sendMessage('lm.acquire')
        self.Destroy()

    def _on_lm_images_output_folder_change(self, event):
        self._model.lm_images_output_folder = self._lm_images_output_folder_edit.GetValue()
        print('lm_images_output_folder={}'.format(self._model.lm_images_output_folder))

    def _on_prefix_change(self, event):
        self._model.lm_images_prefix = self._prefix_edit.GetValue()
        print('lm_images_prefix={}'.format(self._model.lm_images_prefix))

    def _on_delay_change(self, event):
        self._model.delay_between_LM_image_acquisition_secs = float(self._lm_acquisition_delay_edit.GetValue())
        print('delay_between_LM_image_acquisition_secs={}'.format(self._model.delay_between_LM_image_acquisition_secs))

    def _on_lm_do_autofocus_change(self, event):
        self._model.lm_do_autofocus = self._lm_do_autofocus_checkbox.IsChecked()
        print('lm_do_autofocus={}'.format(self._model.lm_do_autofocus))
        self._enable_autofocus_edit_field(self._model.lm_do_autofocus)

    def _on_lm_max_autofocus_change(self, event):
        self._model.lm_max_autofocus_change_nanometers = float(self._lm_max_autofocus_change_edit.GetValue())
        print('lm_max_autofocus_change_nanometers={}'.format(self._model.lm_max_autofocus_change_nanometers))

    def _on_sift_input_folder_change(self, event):
        self._model.sift_input_folder = self._sift_input_folder_edit.GetValue()
        print('sift_input_folder={}'.format(self._model.sift_input_folder))

    def _on_sift_output_folder_change(self, event):
        self._model.sift_output_folder = self._sift_output_folder_edit.GetValue()
        print('sift_output_folder={}'.format(self._model.sift_output_folder))

    def _on_sift_pixel_size_change(self, event):
        self._model.sift_images_mm_per_pixel = float(self._sift_pixel_size_edit.GetValue())
        print('sift_images_mm_per_pixel={}'.format(self._model.sift_images_mm_per_pixel))
