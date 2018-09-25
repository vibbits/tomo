# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx
import tools
import numpy as np

class AcquisitionDialog(wx.Dialog):
    _model = None

    # UI elements
    _lm_images_output_folder_edit = None
    _prefix_edit = None
    _lm_acquisition_delay_text = None
    _sift_input_folder_edit = None
    _sift_output_folder_edit = None
    _sift_pixel_size_edit = None
    _acquire_button = None

    def __init__(self, model, parent, ID, title, size = wx.DefaultSize, pos = wx.DefaultPosition, style = wx.DEFAULT_DIALOG_STYLE):
        wx.Dialog.__init__(self, parent, ID, title, pos, size, style)

        self._model = model

        w = 450  # width for long input fields

        #
        lm_images_output_folder_label = wx.StaticText(self, wx.ID_ANY, "Output Folder:")
        self._lm_images_output_folder_edit = wx.TextCtrl(self, wx.ID_ANY, self._model.lm_images_output_folder, size = (w, -1))

        prefix_label = wx.StaticText(self, wx.ID_ANY, "Filename Prefix:")
        self._prefix_edit = wx.TextCtrl(self, wx.ID_ANY, self._model.lm_images_prefix, size = (w, -1))

        lm_acquisition_delay_label = wx.StaticText(self, wx.ID_ANY, "Acquisition Delay (sec):")
        self._lm_acquisition_delay_text = wx.TextCtrl(self, wx.ID_ANY, str(self._model.delay_between_LM_image_acquisition_secs), size = (50, -1))

        #
        sift_input_folder_label = wx.StaticText(self, wx.ID_ANY, "Input Folder:")
        self._sift_input_folder_edit = wx.TextCtrl(self, wx.ID_ANY, self._model.sift_input_folder, size = (w, -1))

        sift_output_folder_label = wx.StaticText(self, wx.ID_ANY, "Output Folder:")
        self._sift_output_folder_edit = wx.TextCtrl(self, wx.ID_ANY, self._model.sift_output_folder, size = (w, -1))

        sift_pixel_size_label = wx.StaticText(self, wx.ID_ANY, "Pixel size (mm/pixel):")
        self._sift_pixel_size_edit = wx.TextCtrl(self, wx.ID_ANY, str(self._model.sift_images_mm_per_pixel), size = (100, -1))

        # LM Image Acquisition
        lm_fgs = wx.FlexGridSizer(cols = 2, vgap = 4, hgap = 8)
        lm_fgs.Add(lm_images_output_folder_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(self._lm_images_output_folder_edit, flag =wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(prefix_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(self._prefix_edit, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(lm_acquisition_delay_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lm_fgs.Add(self._lm_acquisition_delay_text, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        lm_box = wx.StaticBox(self, -1, 'LM Image Acquisition')
        lm_sizer = wx.StaticBoxSizer(lm_box, wx.VERTICAL)
        lm_sizer.Add(lm_fgs, 0, wx.ALL|wx.CENTER, 10)

        # SIFT registration
        sift_fgs = wx.FlexGridSizer(cols = 2, vgap = 4, hgap = 8)
        sift_fgs.Add(sift_input_folder_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sift_fgs.Add(self._sift_input_folder_edit, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sift_fgs.Add(sift_output_folder_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sift_fgs.Add(self._sift_output_folder_edit, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sift_fgs.Add(sift_pixel_size_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        sift_fgs.Add(self._sift_pixel_size_edit, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        sift_box = wx.StaticBox(self, -1, 'SIFT Registration')
        sift_sizer = wx.StaticBoxSizer(sift_box, wx.VERTICAL)
        sift_sizer.Add(sift_fgs, 0, wx.ALL|wx.CENTER, 10)

        self._acquire_button = wx.Button(self, wx.ID_ANY, "Acquire LM Images!")

        self.Bind(wx.EVT_TEXT, self._on_lm_images_output_folder_change, self._lm_images_output_folder_edit)
        self.Bind(wx.EVT_TEXT, self._on_prefix_change, self._prefix_edit)
        self.Bind(wx.EVT_TEXT, self._on_delay_change, self._lm_acquisition_delay_text)
        self.Bind(wx.EVT_TEXT, self._on_sift_input_folder_change, self._sift_input_folder_edit)
        self.Bind(wx.EVT_TEXT, self._on_sift_output_folder_change, self._sift_output_folder_edit)
        self.Bind(wx.EVT_TEXT, self._on_sift_pixel_size_change, self._sift_pixel_size_edit)
        self.Bind(wx.EVT_BUTTON, self._on_acquire_button_click, self._acquire_button)

        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(lm_sizer, 0, wx.ALL | wx.EXPAND, border = 5)
        contents.Add(sift_sizer, 0, wx.ALL | wx.EXPAND, border = 5)
        contents.Add(self._acquire_button, 0, wx.ALL | wx.CENTER, border = 5)

        self.SetSizer(contents)
        contents.Fit(self)

    def _on_acquire_button_click(self, event):
        self.Show(False)
        self._model.write_parameters()
        self._do_acquire()
        self.Destroy()

    def _do_acquire(self):
        # Calculate the physical displacements on the sample required for moving between the points of interest.
        overview_image_pixelsize_in_microns = 1000.0 / self._model.overview_image_mm_per_pixel
        slice_offsets_microns = tools.physical_point_of_interest_offsets_in_microns(self._model.all_points_of_interest,
                                                                                    overview_image_pixelsize_in_microns)
        print('Rough offset from slice polygons (in microns): ' + repr(slice_offsets_microns))

        # Now acquire an LM image at the point of interest location in each slice.
        tools.acquire_light_microscope_images(slice_offsets_microns, self._model.delay_between_LM_image_acquisition_secs,
                                              self._model.odemis_cli, self._model.lm_images_output_folder, self._model.lm_images_prefix)

        # Have Fiji execute a macro for aligning the LM images
        # using Fiji's Plugins > Registration > Linear Stack Alignment with SIFT
        # https://imagej.net/Headless#Running_macros_in_headless_mode
        print('Aligning LM images')
        print('Starting a headless Fiji and calling the SIFT image registration plugin. Please be patient...')
        retcode, out, err = tools.commandline_exec(
            [self._model.fiji_path, "-Dpython.console.encoding=UTF-8", "--ij2", "--headless", "--console", "--run",
             self._model.sift_registration_script,
             "srcdir='{}',dstdir='{}',prefix='{}'".format(self._model.sift_input_folder, self._model.sift_output_folder, self._model.lm_images_prefix)])
        print('retcode={}\nstdout=\n{}\nstderr={}\n'.format(retcode, out, err))

        # Parse the output of the SIFT registration plugin and extract
        # the transformation matrices to register each slice onto the next.
        print('Extracting SIFT transformation for fine slice transformation')
        sift_matrices = tools.extract_sift_alignment_matrices(out)
        print(sift_matrices)

        # In sift_registration.py we asked for translation only transformations.
        # So our matrices should be pure translations. Extract the last column (=the offset) and convert from pixel
        # coordinates to physical distances on the sample.
        # (We also add a (0,0) offset for the first slice.)
        sift_images_pixelsize_in_microns = 1000.0 / self._model.sift_images_mm_per_pixel
        sift_offsets_microns = [np.array([0, 0])] + [mat[:, 2] * sift_images_pixelsize_in_microns for mat in
                                                     sift_matrices]
        print('Fine SIFT offset (in microns): ' + repr(sift_offsets_microns))

        # Invert y of the SIFT offsets
        sift_offsets_microns = [np.array([offset[0], -offset[1]]) for offset in sift_offsets_microns]
        print('Fine SIFT offset y-inverted (in microns): ' + repr(sift_offsets_microns))

        # Combine (=sum) the rough translations obtained by mapping the slice polygons (of an x20 overview image) onto one another
        # with the fine corrections obtained by SIFT registration of (x100) light microscopy images.
        combined_offsets_microns = [trf_pair[0] + trf_pair[1] for i, trf_pair in
                                    enumerate(zip(slice_offsets_microns, sift_offsets_microns))]
        print('Rough offset from slice polygons + fine SIFT offset (in microns): ' + repr(combined_offsets_microns))

        # Show overview of the offsets
        tools.show_offsets_table(slice_offsets_microns, sift_offsets_microns, combined_offsets_microns)

        # TODO? Also acquire EM images? Using combined_offsets_microns?
        # odemis-cli --se-detector --output filename.ome.tiff

    def _on_lm_images_output_folder_change(self, event):
        self._model.lm_images_output_folder = self._lm_images_output_folder_edit.GetValue()
        print('lm_images_output_folder={}'.format(self._model.lm_images_output_folder))

    def _on_prefix_change(self, event):
        self._model.lm_images_prefix = self._prefix_edit.GetValue()
        print('lm_images_prefix={}'.format(self._model.lm_images_prefix))

    def _on_delay_change(self, event):
        self._model.delay_between_LM_image_acquisition_secs = float(self._lm_acquisition_delay_text.GetValue())
        print('delay_between_LM_image_acquisition_secs={}'.format(self._model.delay_between_LM_image_acquisition_secs))

    def _on_sift_input_folder_change(self, event):
        self._model.sift_input_folder = self._sift_input_folder_edit.GetValue()
        print('sift_input_folder={}'.format(self._model.sift_input_folder))

    def _on_sift_output_folder_change(self, event):
        self._model.sift_output_folder = self._sift_output_folder_edit.GetValue()
        print('sift_output_folder={}'.format(self._model.sift_output_folder))

    def _on_sift_pixel_size_change(self, event):
        self._model.sift_images_mm_per_pixel = float(self._sift_pixel_size_edit.GetValue())
        print('sift_images_mm_per_pixel={}'.format(self._model.sift_images_mm_per_pixel))
