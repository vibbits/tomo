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
import wx.grid
import numpy as np
import secom_tools
from focus_map import FocusMap
from move_stage_mode import MoveStageMode

class FocusPanel(wx.Panel):
    _canvas = None
    _model = None
    _focus_map = None  # CHECKME: should the focus_map be part of _model?
    _table = None  # table with user-defined focus (x, y, z)

    done_button = None
    _stage_position_object = None

    def __init__(self, parent, canvas, model):
        wx.Panel.__init__(self, parent, size = (350, -1))
        self._canvas = canvas
        self._model = model
        self._focus_map = FocusMap()
        self._table = self._make_table()

        title = wx.StaticText(self, wx.ID_ANY, "Focus")
        title.SetFont(wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.BOLD))
        separator = wx.StaticLine(self, wx.ID_ANY)

        label = wx.StaticText(self, wx.ID_ANY, "Click on the overview image with the 'Move Stage' tool to move the stage to a specific position. Then manually focus the microscope in Odemis and press 'Remember focus'. Repeat this for several points on the sample and finally press 'Done'.")
        label.Wrap(330)  # force line wrapping

        button_size = (125, -1)
        remember_focus_button = wx.Button(self, wx.ID_ANY, "Remember focus", size=button_size)
        self.done_button = wx.Button(self, wx.ID_ANY, "Done", size = button_size)  # Not this panel but the ApplicationFame will listen to clicks on this button.
        discard_all_button = wx.Button(self, wx.ID_ANY, "Discard all", size=button_size)

        self.Bind(wx.EVT_BUTTON, self._on_remember_focus_button_click, remember_focus_button)
        self.Bind(wx.EVT_BUTTON, self._on_discard_all_button_click, discard_all_button)

        table_title = wx.StaticText(self, wx.ID_ANY, "User defined focus positions:")

        b = 5  # border size
        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(title, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(separator, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(label, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(remember_focus_button, 0, wx.ALL | wx.CENTER, border=b)
        contents.Add(discard_all_button, 0, wx.ALL | wx.CENTER, border=b)
        contents.Add(self.done_button, 0, wx.ALL | wx.CENTER, border=b)
        contents.Add(table_title, 0, wx.ALL, border=b)
        contents.Add(self._table, 0, wx.ALL, border=b)

        self.SetSizer(contents)
        contents.Fit(self)

    def activate(self):
        # Listen to movestage tool mouse clicks so we can place the mark
        self._canvas.Canvas.Bind(MoveStageMode.EVT_TOMO_MOVESTAGE_LEFT_DOWN, self._on_left_mouse_button_down)

    def deactivate(self):
        self._canvas.Canvas.Unbind(MoveStageMode.EVT_TOMO_MOVESTAGE_LEFT_DOWN)

    def _make_table(self):
        # Make a spreadsheet like table.
        # See https://groups.google.com/forum/#!msg/wxpython-users/CsII2JsSEOI/DkectFCHAewJ
        # and https://wxpython.org/Phoenix/docs/html/wx.grid.Grid.html
        num_rows = 1  # empty initial roww, for cosmetic reason
        num_cols = 3
        table = wx.grid.Grid(self, wx.ID_ANY)
        table.SetDefaultCellAlignment(wx. ALIGN_CENTRE, wx. ALIGN_CENTRE)
        table.CreateGrid(num_rows, num_cols)
        table.SetColLabelValue(0, "stage x (m)")
        table.SetColLabelValue(1, "stage y (m)")
        table.SetColLabelValue(2, "focus z")
        table.EnableEditing(False)
        table.DisableDragRowSize()
        table.SetRowLabelSize(40)  # width of the column that displays the row number
        # IMPROVEME? Support deleting rows?
        return table

    def reset(self):
        self._focus_map.reset()
        self._canvas.remove_focus_positions()
        self._canvas.redraw()
        self._clear_table()

    def _clear_table(self):
        num_rows = self._table.GetNumberRows()
        self._table.DeleteRows(0, num_rows)
        self._table.InsertRows(0, 1)  # add an empty row - it looks nicer than just a table with only a header
        self.GetTopLevelParent().Layout()

    def _add_to_table(self, x, y, z):
        row = len(self._focus_map.get_user_defined_focus_positions()) - 1
        self._table.InsertRows(row)
        self._table.SetCellValue(row, 0, str(x))
        self._table.SetCellValue(row, 1, str(y))
        self._table.SetCellValue(row, 2, str(z))

    def get_focus_map(self):
        return self._focus_map

    def _on_left_mouse_button_down(self, event):
        print("Event = {}".format(event))
        coords = event.GetCoords()

        image_coords = (coords[0], -coords[1])
        print("Left mouse button clicked: %i, %i" % image_coords)

        # Remove previous stage position mark from canvas (if any)
        if self._stage_position_object != None:
            self._canvas.remove_objects(self._stage_position_object)

        # Draw current stage position on canvas
        canvas_coords = (image_coords[0], -image_coords[1])
        self._stage_position_object = self._canvas.add_cross(canvas_coords, "Red")  # Note: we need to pass canvas coordinates here (so y < 0 means over the image)
        self._canvas.redraw()

        # Convert image coords to stage coords
        mat = self._model.overview_image_to_stage_coord_trf
        homog_pos = np.array([image_coords[0], image_coords[1], 1])
        homog_trf_pos = np.dot(mat, homog_pos)
        stage_pos = homog_trf_pos[0:2]

        # Move stage to target position
        secom_tools.set_absolute_stage_position(stage_pos)

    def _on_remember_focus_button_click(self, event):
        # Query stage position and focus height
        stage_pos = secom_tools.get_absolute_stage_position()
        z = secom_tools.get_absolute_focus_z_position()

        # Remember focus
        self._focus_map.add_user_defined_focus_position(stage_pos, z)

        # Update table
        self._add_to_table(stage_pos[0], stage_pos[1], z)
        self.GetTopLevelParent().Layout()

        # Convert the stage position 'stage_pos' to overview image pixel coordinates to draw on the canvas!
        mat = self._model.overview_image_to_stage_coord_trf
        inv_mat = np.linalg.inv(mat)
        homog_pos = np.array([stage_pos[0], stage_pos[1], 1])
        homog_trf_pos = np.dot(inv_mat, homog_pos)
        image_space_stage_pos = homog_trf_pos[0:2]

        # Draw the position where focus was acquired on the overview image
        self._canvas.add_focus_position(image_space_stage_pos)
        self._canvas.redraw()
        # IMPROVEME draw the _number_ of focus position on canvas too

    def _on_discard_all_button_click(self, event):
        dlg = wx.MessageDialog(self, "Discard all user defined focus positions?", "Discard all", style = wx.YES | wx.NO)
        if dlg.ShowModal() == wx.ID_YES:
            self.reset()
