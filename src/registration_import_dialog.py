# Frank Vernaillen
# August 2019
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx


class RegistrationImportDialog(wx.Dialog):
    def __init__(self, registration_output_dir, parent, ID, title, size=wx.DefaultSize, pos=wx.DefaultPosition, style=wx.DEFAULT_DIALOG_STYLE):
        wx.Dialog.__init__(self, parent, ID, title, pos, size, style)

        self._registration_output_dir = registration_output_dir
        self._registration_output = None  # the actual contents (=text) of the registration output file

        w = 450  # width for long input fields

        registration_output_file_label = wx.StaticText(self, wx.ID_ANY, "Registration Output File:")
        self._registration_output_file_edit = wx.TextCtrl(self, wx.ID_ANY, '', size=(w, -1))
        self._browse_button = wx.Button(self, wx.ID_ANY, "Browse")

        path_sizer = wx.BoxSizer(wx.HORIZONTAL)
        path_sizer.Add(self._registration_output_file_edit, flag=wx.ALIGN_CENTER_VERTICAL)
        path_sizer.AddSpacer(8)
        path_sizer.Add(self._browse_button, flag=wx.ALIGN_CENTER_VERTICAL)

        fgs = wx.FlexGridSizer(cols=2, vgap=4, hgap=8)
        fgs.Add(registration_output_file_label, flag=wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        fgs.Add(path_sizer, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        instructions_label = wx.StaticText(self, wx.ID_ANY, (
            "Please select the file with the manually saved text output from the 'Linear Stack Alignment with SIFT' plugin."
            "The transformation matrices for aligning the images will be extracted and used as offset corrections for the point-of-interest positions."))
        instructions_label.Wrap(650)  # Force line wrapping of the instructions text

        # IMPROVEME: we can cancel the dialog by pressing the x button in the title bar, but perhaps an actual Cancel button would be nice here.
        self._import_button = wx.Button(self, wx.ID_ANY, "Import")
        self._import_button.SetFocus()

        box = wx.StaticBox(self, wx.ID_ANY)
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        sizer.Add(fgs, 0, wx.ALL | wx.CENTER, 10)

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
        defaultDir = self._registration_output_dir
        defaultFile = ''
        with wx.FileDialog(self, "Select the registration output file",
                           defaultDir, defaultFile,
                           wildcard="Text files (*.txt)|*.txt") as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                self._registration_output_file_edit.SetValue(path)

    def _on_import_button_click(self, event):
        path = self._registration_output_file_edit.GetValue()
        print('Reading {}'.format(path))
        with open(path) as f:
            self._registration_output = f.read()
        self.EndModal(wx.ID_OK)

    def get_registration_output(self):
        """
        :return: the contents of the registration output text file, as a single string with multiple lines
        """
        return self._registration_output

