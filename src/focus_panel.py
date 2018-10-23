# Workflow:
#
# As long as the user want to acquire focus positions, this is repeated:
#
# 1 In Odemis the user positions the stage to a desired location and manually sets the correct focus.
# 2 In Tomo the user indicates that a new focus position needs to be remembered
# 3 Tomo then
#   - queries Odemis for the current focus z
#   - queries Odemis for the stage x and y position
#   - stores this information
#   - draws the focus position on the overview image (also a the how-many-th focus position number is shown)
#
# Tomo can use these focus samples to interpolate the z-focus position across the slices.
# Acquiring focus at a couple of positions up-front is optional.

import wx
import secom_tools
from focus_map import FocusMap

class FocusPanel(wx.Panel):
    _canvas = None
    _focus_map = None  # CHECKME: should the focus_map be part of _model?

    done_button = None

    def __init__(self, parent, canvas):
        wx.Panel.__init__(self, parent, size = (200, -1))
        self._canvas = canvas
        self._focus_map = FocusMap()

        button_size = (125, -1)
        label = wx.StaticText(self, wx.ID_ANY, "In Odemis, move the stage and manually focus the microscope. Then press 'Remember focus'. Repeat this for several points on the sample and then press 'Done'.")
        label.Wrap(180)  # force line wrapping
        set_focus_button = wx.Button(self, wx.ID_ANY, "Remember focus", size = button_size)
        self.done_button = wx.Button(self, wx.ID_ANY, "Done", size = button_size)  # Not this panel but the ApplicationFame will listen to clicks on this button.
        discard_all_button = wx.Button(self, wx.ID_ANY, "Discard all", size = button_size)

        self.Bind(wx.EVT_BUTTON, self._on_set_focus_button_click, set_focus_button)
        self.Bind(wx.EVT_BUTTON, self._on_discard_all_button_click, discard_all_button)

        b = 5  # border size
        contents = wx.BoxSizer(wx.VERTICAL)
        # TODO: add a sidebar title with perhaps a line underneath
        contents.Add(label, 0, wx.ALL | wx.EXPAND, border = b)
        contents.Add(set_focus_button, 0, wx.ALL | wx.CENTER, border = b)
        contents.Add(discard_all_button, 0, wx.ALL | wx.CENTER, border = b)
        contents.Add(self.done_button, 0, wx.ALL | wx.CENTER, border = b)

        # TODO: add a spreadsheet like table; see https://groups.google.com/forum/#!msg/wxpython-users/CsII2JsSEOI/DkectFCHAewJ

        self.SetSizer(contents)
        contents.Fit(self)

    def reset(self):
        self._focus_map.reset()
        self._canvas.remove_focus_positions()
        self._canvas.redraw()

    def get_focus_map(self):
        return self._focus_map

    def _on_set_focus_button_click(self, event):
        # Query stage position and focus height
        pos = secom_tools.get_stage_position()
        z = secom_tools.get_focus_z_position()

        # Remember focus
        self._focus_map.add_user_defined_focus_position(pos, z)

        # Draw the position where focus was acquired on the overview image
        self._canvas.add_focus_position(pos)
        self._canvas.redraw()

    def _on_discard_all_button_click(self, event):
        dlg = wx.MessageDialog(self, "Discard all user defined focus positions?", "Discard all", style = wx.YES | wx.NO)
        if dlg.ShowModal() == wx.ID_YES:
            self.reset()
