# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx
from wx.lib.pubsub import pub

class PointOfInterestDialog(wx.Dialog):
    _model = None

    _point_of_interest_x_edit = None
    _point_of_interest_y_edit = None
    _set_button = None

    def __init__(self, model, parent, ID, title, size = wx.DefaultSize, pos = wx.DefaultPosition, style = wx.DEFAULT_DIALOG_STYLE):
        wx.Dialog.__init__(self, parent, ID, title, pos, size, style)

        self._model = model

        point_of_interest_label = wx.StaticText(self, wx.ID_ANY, "Point of Interest (X, Y):")
        self._point_of_interest_x_edit = wx.TextCtrl(self, wx.ID_ANY, str(self._model.original_point_of_interest[0]), size = (50, -1))
        self._point_of_interest_y_edit = wx.TextCtrl(self, wx.ID_ANY, str(self._model.original_point_of_interest[1]), size = (50, -1))

        poiSizer = wx.BoxSizer(wx.HORIZONTAL)
        poiSizer.Add(self._point_of_interest_x_edit, flag = wx.ALIGN_CENTER_VERTICAL)
        poiSizer.AddSpacer(8)
        poiSizer.Add(self._point_of_interest_y_edit, flag = wx.ALIGN_CENTER_VERTICAL)

        fgs = wx.FlexGridSizer(cols = 2, vgap = 4, hgap = 8)
        fgs.Add(point_of_interest_label, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        fgs.Add(poiSizer, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        instructions_label = wx.StaticText(self, wx.ID_ANY, (
            "Specify the coordinates of the point-of-interest in the first slice of the first ribbon. "
            "Afterwards, press the Set button. The selected point of interest will be marked with a green cross, "
            "and predicted analogous points in the other slices with a red cross."))
        instructions_label.Wrap(450)  # Force line wrapping of the instructions text

        self._set_button = wx.Button(self, wx.ID_ANY, "Set")

        box = wx.StaticBox(self, wx.ID_ANY)
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        sizer.Add(fgs, 0, wx.ALL|wx.CENTER, 10)

        self.Bind(wx.EVT_BUTTON, self._on_set_button_click, self._set_button)

        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(instructions_label, 0, wx.ALL | wx.CENTER, border = 5)
        contents.Add(sizer, 0, wx.ALL | wx.EXPAND, border = 5)
        contents.Add(self._set_button, 0, wx.ALL | wx.CENTER, border = 5)

        self.SetSizer(contents)
        contents.Fit(self)

    def _on_set_button_click(self, event):
        self.Show(False)
        self._model.original_point_of_interest[0] = float(self._point_of_interest_x_edit.GetValue())
        self._model.original_point_of_interest[1] = float(self._point_of_interest_y_edit.GetValue())
        self._model.write_parameters()
        print('original_point_of_interest={},{}'.format(self._model.original_point_of_interest[0], self._model.original_point_of_interest[1]))
        pub.sendMessage('pointofinterest.set')
        self.Destroy()
