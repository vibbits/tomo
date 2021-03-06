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
#   - draws the focus position on the overview image (also the number of the focus position is shown)
#
# Tomo can use these focus samples to interpolate the z-focus position across the slices.

import wx
import wx.grid
import numpy as np
import secom_tools
from focus_map import FocusMap
from move_stage_mode import MoveStageMode
from constants import POINTER_MODE_NAME, PRELIMINARY_FOCUS_POSITION_COLOR, FOCUS_POSITION_COLOR, MARKER_SIZE

import matplotlib
matplotlib.use('wxagg')
import matplotlib.pyplot as plt

class FocusPanel(wx.Panel):
    def __init__(self, parent, canvas, model):
        wx.Panel.__init__(self, parent, size=(350, -1))
        self._canvas = canvas
        self._model = model
        self._stage_position_object = None  # FloatCanvas object for drawing the requested focus position
        self._table = self._make_table()  # table with user-defined focus (x, y, z)
        self._table.Bind(wx.EVT_KEY_DOWN, self._on_grid_keypress)
        self._table.Bind(wx.grid.EVT_GRID_LABEL_RIGHT_CLICK, self._on_grid_label_right_click)  # to delete a row
        self._table.Bind(wx.grid.EVT_GRID_LABEL_LEFT_CLICK, self._on_grid_label_left_click)  # to grab focus for copy-paste

        title = wx.StaticText(self, wx.ID_ANY, "Focus Map")
        title.SetFont(wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.BOLD))
        separator = wx.StaticLine(self, wx.ID_ANY)

        label = wx.StaticText(self, wx.ID_ANY, "Click on the overview image with the 'Move Stage' (V) tool to move the stage to a specific position. Then manually focus the microscope in Odemis and press 'Remember focus'. Repeat this for several points on the sample and finally press 'Done'.")
        label.Wrap(330)  # force line wrapping

        button_size = (150, -1)
        remember_focus_button = wx.Button(self, wx.ID_ANY, "Remember Focus", size=button_size)
        self.done_button = wx.Button(self, wx.ID_ANY, "Done", size=button_size)  # Not this panel but the ApplicationFame will listen to clicks on this button.
        discard_all_button = wx.Button(self, wx.ID_ANY, "Discard All", size=button_size)
        self._load_button = wx.Button(self, wx.ID_ANY, "Load", size=button_size)
        self._save_button = wx.Button(self, wx.ID_ANY, "Save", size=button_size)
        self._save_button.Enable(False)
        self._save_samples_button = wx.Button(self, wx.ID_ANY, "Save Sampled Map", size=button_size)
        self._save_samples_button.Enable(False)
        self._show_button = wx.Button(self, wx.ID_ANY, "Display Focus Map", size=button_size)
        self._show_button.Enable(False)

        self.Bind(wx.EVT_BUTTON, self._on_remember_focus_button_click, remember_focus_button)
        self.Bind(wx.EVT_BUTTON, self._on_discard_all_button_click, discard_all_button)
        self.Bind(wx.EVT_BUTTON, self._on_load_button_click, self._load_button)
        self.Bind(wx.EVT_BUTTON, self._on_save_button_click, self._save_button)
        self.Bind(wx.EVT_BUTTON, self._on_save_samples_button_click, self._save_samples_button)
        self.Bind(wx.EVT_BUTTON, self._on_show_button_click, self._show_button)

        table_title = wx.StaticText(self, wx.ID_ANY, "User defined focus positions:")

        b = 5  # border size

        #
        focus_points_box = wx.StaticBox(self, -1, 'Focus map')
        focus_points_sizer = wx.StaticBoxSizer(focus_points_box, wx.VERTICAL)
        focus_points_sizer.Add(remember_focus_button, 0, wx.ALL | wx.CENTER, border=b)
        focus_points_sizer.Add(discard_all_button, 0, wx.ALL | wx.CENTER, border=b)
        focus_points_sizer.Add(self._load_button, 0, wx.ALL | wx.CENTER, border=b)
        focus_points_sizer.Add(self._save_button, 0, wx.ALL | wx.CENTER, border=b)

        #
        quality_box = wx.StaticBox(self, -1, 'Quality Control')
        quality_sizer = wx.StaticBoxSizer(quality_box, wx.VERTICAL)
        quality_sizer.Add(self._save_samples_button, 0, wx.ALL | wx.CENTER, border=b)
        quality_sizer.Add(self._show_button, 0, wx.ALL | wx.CENTER, border=b)

        #
        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(title, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(separator, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(label, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(focus_points_sizer, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(quality_sizer, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(table_title, 0, wx.ALL, border=b)
        contents.Add(self._table, 0, wx.ALL, border=b)
        contents.Add(self.done_button, 0, wx.ALL | wx.CENTER, border=b)

        self.SetSizer(contents)
        contents.Fit(self)

    def _on_grid_label_left_click(self, event):
        # User clicked on a table row or column label. It then becomes highlighted in gray.
        # However, being highlighted in gray does not mean that the table has focus,
        # so pressing ctrl-C to copy the contents will not work. Only if the selection is in orange
        # does the table have focus and does ctrl-C work. To avoid this confusing situation we
        # grab focus programmatically whenever the user click on a row on column label.
        # IMPROVEME: this is still not ideal, the grid also has the concept of current cell (gridcursor)
        # which does not automatically change when we select a row/column, but it does get used to determine
        # which rows/columns to select if the user modifies the selection with a shift-click on a row or column
        # label. E.g. click on a cell, then click on the label of another row (the grid cursor remains on the original cell,
        # but the new row is selected. The shift-click on another row. A block of cells is now selected, starting from
        # the unselected cell with the grid cursor, instead of starting with the selected row. This is strange.
        # To fix this, I think we should move the grid cursor to the first cell in the row/column if the
        # user click on a column/row label *and* shift is not pressed; if shift is pressed, do not move the grid cursor.
        self._table.SetFocus()
        event.Skip()

    def activate(self):
        if self._model.focus_map is None:
            self._model.focus_map = self._make_focus_map()

        self._canvas.Activate(MoveStageMode.NAME)

        # Listen to the move stage tool mouse clicks so we can place the mark
        self._canvas.Canvas.Bind(MoveStageMode.EVT_TOMO_MOVESTAGE_LEFT_DOWN, self._on_left_mouse_button_down)

    def deactivate(self):
        self._canvas.Deactivate(MoveStageMode.NAME)
        self._canvas.Activate(POINTER_MODE_NAME)

        self._canvas.Canvas.Unbind(MoveStageMode.EVT_TOMO_MOVESTAGE_LEFT_DOWN)

    def _make_table(self):
        # Make a spreadsheet like table.
        # See https://groups.google.com/forum/#!msg/wxpython-users/CsII2JsSEOI/DkectFCHAewJ
        # and https://wxpython.org/Phoenix/docs/html/wx.grid.Grid.html
        num_rows = 1  # empty initial row, for cosmetic reason
        num_cols = 3
        table = wx.grid.Grid(self, wx.ID_ANY)
        table.SetDefaultCellAlignment(wx. ALIGN_CENTRE, wx. ALIGN_CENTRE)
        table.CreateGrid(num_rows, num_cols)
        table.SetColLabelValue(0, "stage x [m]")
        table.SetColLabelValue(1, "stage y [m]")
        table.SetColLabelValue(2, "focus z")

        # Focus panel width = 350 pixels = 5 (border) + 40 (label column width) + 3 x 100 (x, y, and z columns width) + 5 (border)
        col_size = 100
        table.SetColSize(0, col_size)
        table.SetColSize(1, col_size)
        table.SetColSize(2, col_size)
        table.SetRowLabelSize(40)  # width of the column that displays the row number
        table.SetMaxClientSize((-1, 300))  # maximum vertical size is limited because if the table grows to high, the Done button underneath it disappears (IMPROVEME: is there no way to ensure that the Done button is always shown and the table only gets the remaining space above the button?)

        table.EnableEditing(False)
        table.DisableDragRowSize()
        return table

    def reset(self):
        self._model.focus_map.reset()
        self._canvas.remove_focus_positions()
        self._canvas.redraw()
        self._clear_table()
        self._save_button.Enable(False)
        self._show_button.Enable(False)
        self._save_samples_button.Enable(False)

    def _on_grid_keypress(self, event):
        # print('Focus table keypress key={} shiftDown={} ctrldown={} cmdDown={} altdown={}'.format(event.GetKeyCode(), event.shiftDown, event.controlDown, event.cmdDown, event.altDown))
        if event.controlDown and (not event.shiftDown) and (not event.altDown) and event.GetKeyCode() == ord('C'):
            # CTRL-C pressed (for copy-paste)
            num_selections = self._get_number_of_selections_in_table()
            if num_selections == 0:
                return

            if num_selections == 1:
                text = self._get_selected_text_in_table()
                data = wx.TextDataObject()
                data.SetText(text)
                if wx.TheClipboard.Open():
                    wx.TheClipboard.SetData(data)
                    wx.TheClipboard.Close()
            else:
                print('Focus table has multiple selections. Cannot copy this to the clipboard (it would be confusing).')
        else:
            event.Skip()

    def _get_number_of_selections_in_table(self):
        # Cells can be selected in different ways (complete row, complete column, individual cells, block of cells).
        # This function returns how many of these different selection ways are currently active on the table.
        return (len(self._table.GetSelectedRows()) > 0) + \
               (len(self._table.GetSelectedCols()) > 0) + \
                len(self._table.GetSelectedCells()) + \
                len(self._table.GetSelectionBlockTopLeft())

    def _get_selected_text_in_table(self):
        # Cells can be selected in different ways:
        # 1. by selecting a block (click one corner, then shift-click the other corner)
        # 2. by selecting individual cells (combining them via ctrl click)
        # 3. by selecting a complete row/column (by clicking on the row/column header)
        # Each of these possible selections needs to be checked for with different function calls:
        # via GetSelectedCells (for 2), GetSelectionBlockTopLeft/BottomRight (for 1), GetSelectedRows/Cols (for 3).
        # Note for example that GetSelectedCells() does not return any cells if we did a block selection.
        if self._table.GetSelectedRows():
            rows = sorted(self._table.GetSelectedRows())
            cols = range(self._table.GetNumberCols())
        elif self._table.GetSelectedCols():
            cols = sorted(self._table.GetSelectedCols())
            rows = range(self._table.GetNumberRows() - 1)  # -1 because we always have a last empty row in the table
        elif self._table.GetSelectedCells():
            cells = self._table.GetSelectedCells()
            assert len(cells) == 1
            cell = cells[0]
            cols = [cell.Col]
            rows = [cell.Row]
        elif self._table.GetSelectionBlockTopLeft():
            topleft = self._table.GetSelectionBlockTopLeft()
            bottomright = self._table.GetSelectionBlockBottomRight()
            assert len(topleft) == 1
            assert len(topleft) == len(bottomright)
            cols = range(topleft[0].Col, bottomright[0].Col + 1)
            rows = range(topleft[0].Row, bottomright[0].Row + 1)
        else:
            rows = []
            cols = []

        return self._get_cells_as_text(rows, cols)

    def _get_cells_as_text(self, rows, cols):
        text = ""
        for r in rows:
            vals = [str(self._table.GetCellValue(r, c)) for c in cols]
            text += ' '.join(vals)
            text += "\n"
        print(text)
        return text

    def _clear_table(self):
        num_rows = self._table.GetNumberRows()
        self._table.DeleteRows(0, num_rows)
        self._table.InsertRows(0, 1)  # add an empty row - it looks nicer than just a table with only a header
        self.GetTopLevelParent().Layout()

    def _add_to_table(self, row, x, y, z):
        self._table.InsertRows(row)
        self._table.SetCellValue(row, 0, '{:.9f}'.format(x))  # x and y are expressed in meters, display position with nanometer precision
        self._table.SetCellValue(row, 1, '{:.9f}'.format(y))
        self._table.SetCellValue(row, 2, '{:.9f}'.format(z))
        self._table.GoToCell(row + 1, 0)  # in case the table is too large to show all rows, make sure that the new row is visible
        self._save_samples_button.Enable(True)
        self._save_button.Enable(True)
        self._show_button.Enable(True)

    def _make_focus_map(self):
        # Find the extent of rectangle in stage coordinates that covers the overview image.
        image = self._canvas.get_wximage()
        xmin, xmax, ymin, ymax = self._determine_focus_map_grid_extent(image, self._model.overview_image_to_stage_coord_trf)

        num_samples_x = 50
        step = (xmax - xmin) / num_samples_x
        return FocusMap(xmin, xmax, ymin, ymax, step)

    def _on_grid_label_right_click(self, event):
        # IMPROVEME: using right click to directly trigger a delete is surprising for the user
        #            we expect a right click to pop up a context menu (e.g. with a 'Delete Row' menu entry)
        row = event.GetRow()
        if (row >= 0) and (row < self._table.GetNumberRows() - 1):
            with wx.MessageDialog(self, 'Discard focus position %s?' % (row+1), 'Discard?', wx.OK | wx.CANCEL | wx.ICON_QUESTION) as dlg:
                dlg.CenterOnScreen()
                result = dlg.ShowModal()
                if result == wx.ID_OK:
                    self._delete_table_row(row)
                    event.Skip()

    def _delete_table_row(self, row):
        # Update table
        self._table.DeleteRows(row, 1, True)
        self.GetTopLevelParent().Layout()

        # Update focus map
        positions = self._model.focus_map.get_user_defined_focus_positions()
        del positions[row]
        self._model.focus_map.set_user_defined_focus_positions(positions)

        # Update overview image
        self._canvas.remove_focus_positions()
        for i, (x, y, z) in enumerate(positions):
            label = str(i + 1)
            self._add_focus_position_to_canvas((x, y), label)

        # CHECKME? if table now empty, probably need to disable saves and show focus map buttons

    def _add_user_requested_stage_position_mark(self, image_coords):
        canvas_coords = (image_coords[0], -image_coords[1])  # Note: we need to pass canvas coordinates to add_cross (so y < 0 means over the image)
        self._stage_position_object = self._canvas.add_cross(canvas_coords, PRELIMINARY_FOCUS_POSITION_COLOR)  # mark position where user asked to move the stage to, before he/she will set the focus in Odemis
        self._canvas.redraw()

    def _remove_user_requested_stage_position_mark(self):
        if self._stage_position_object is not None:
            self._canvas.remove_objects(self._stage_position_object)
            self._stage_position_object = None

    def _on_left_mouse_button_down(self, event):
        coords = event.GetCoords()
        image_coords = (coords[0], -coords[1])

        # Remove previous stage position mark from canvas (if any)
        self._remove_user_requested_stage_position_mark()

        # Draw user requested target stage position on canvas
        self._add_user_requested_stage_position_mark(image_coords)

        # Convert image coords to stage coords
        mat = self._model.overview_image_to_stage_coord_trf
        homog_pos = np.array([image_coords[0], image_coords[1], 1])
        homog_trf_pos = np.dot(mat, homog_pos)
        stage_pos = homog_trf_pos[0:2]

        # Move stage to target position
        secom_tools.set_absolute_stage_position(stage_pos)

    def _on_remember_focus_button_click(self, event):
        # Query stage position and focus height
        # (The user may have changed the stage position in Odemis,
        # so we cannot trust the position he/she moved to in Tomo before.)
        x, y = secom_tools.get_absolute_stage_position()

        # When running Tomo on a development computer without the Odemis software,
        # we generate fake z-focus values for testing purposes.
        if secom_tools.odemis_stubbed:
            z = x + y
            print('FAKE focus absolute position: z={}'.format(z))
        else:
            z = secom_tools.get_absolute_focus_z_position()

        # Remember focus
        self._model.focus_map.add_user_defined_focus_position(x, y, z)

        # Update table
        row = len(self._model.focus_map.get_user_defined_focus_positions()) - 1
        self._add_to_table(row, x, y, z)
        self.GetTopLevelParent().Layout()

        # Remove preliminary (= where user clicked) stage position mark from canvas
        self._remove_user_requested_stage_position_mark()

        # Draw the position where focus was actually acquired on the overview image
        label = str(len(self._model.focus_map.get_user_defined_focus_positions()))
        self._add_focus_position_to_canvas((x, y), label)

    def _add_focus_position_to_canvas(self, stage_pos, label):
        # Convert the stage position 'stage_pos' to overview image pixel coordinates to draw on the canvas!
        mat = np.linalg.inv(self._model.overview_image_to_stage_coord_trf)
        image_space_stage_pos = self._transform_coord(mat, stage_pos)

        # Draw the position where focus was acquired on the overview image
        self._canvas.add_focus_position(image_space_stage_pos, label, FOCUS_POSITION_COLOR, MARKER_SIZE)
        self._canvas.redraw()

    def _on_discard_all_button_click(self, event):
        dlg = wx.MessageDialog(self, "Discard all user defined focus positions?", "Discard all", style=wx.YES | wx.NO)
        if dlg.ShowModal() == wx.ID_YES:
            self.reset()

    def _on_show_button_click(self, event):
        self._draw_focus_map()

    def _on_save_button_click(self, event):
        defaultDir = ''
        defaultFile = 'focus_map.txt'
        with wx.FileDialog(self, "Specify name of focus map file",
                           defaultDir, defaultFile,
                           wildcard="Text files (*.txt)|*.txt",
                           style=wx.FD_SAVE) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                self._model.focus_map.save_to_file(path)
                print('Saved user defined focus positions to {}'.format(path))

    def _on_load_button_click(self, event):
        defaultDir = ''
        defaultFile = 'focus_map.txt'
        with wx.FileDialog(self, "Specify name of focus map file to load",
                           defaultDir, defaultFile,
                           wildcard="Text files (*.txt)|*.txt",
                           style=wx.FD_OPEN) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                if len(self._model.focus_map.get_user_defined_focus_positions()) > 0:
                    with wx.MessageDialog(self, "You have user-defined focus positions already. They will be lost when loading new positions from file.", 'Load new focus positions?',
                                          wx.OK | wx.CANCEL | wx.ICON_QUESTION) as dlg:
                        if dlg.ShowModal() == wx.ID_CANCEL:
                            return
                self._do_load(path)

    def _do_load(self, path):
        print('Loading user defined focus positions from {}'.format(path))
        self._model.focus_map.reset()
        self._model.focus_map.load_from_file(path)
        self._canvas.remove_focus_positions()
        self._clear_table()
        positions = self._model.focus_map.get_user_defined_focus_positions()
        for i, (x, y, z) in enumerate(positions):
            self._add_to_table(i, x, y, z)
            self._add_focus_position_to_canvas((x, y), str(i + 1))
        self.GetTopLevelParent().Layout()
        self._canvas.redraw()

    def _on_save_samples_button_click(self, event):
        # Perhaps useful for offline plotting and inspection of the focus map
        defaultDir = ''
        defaultFile = 'sampled_focus_map.txt'
        with wx.FileDialog(self, "Specify name of sampled focus map file",
                           defaultDir, defaultFile,
                           wildcard="Text files (*.txt)|*.txt",
                           style=wx.FD_SAVE) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                focus_samples = self._model.focus_map.get_focus_grid()
                np.savetxt(path, focus_samples, delimiter='\t')
                print('Sampled focus map saved to {}'.format(path))

    def _transform_coord(self, mat, pos):
        homog_pos = np.array([pos[0], pos[1], 1])
        homog_trf_pos = np.dot(mat, homog_pos)
        result_pos = homog_trf_pos[0:2]
        return result_pos

    def _determine_focus_map_grid_extent(self, image, image_to_stage_coord_trf):
        #
        # image origin is in the top left corner, y axis pointing down
        # image size = w pixels wide, h pixels high
        # stage y-axis is pointing up
        # stage origin can be anywhere, even outside the overview image
        # image_to_stage_coord_trf can be used to transform between image and stage coordinates
        #
        # image
        # origin             ^
        # (0,0)              |                                 (w-1, 0)
        #   +----->----------|-------------------------------------+
        #   | p1             |                                  p2 |
        #   |                |                                     |
        #   v                |                                     |
        #   |                |                                     |
        #   |                +-------------------------------------------------->
        #   |             stage                                    |
        #   |             origin                                   |
        #   |                                                      |
        #   |                                                      |
        #   |                                                      |
        #   |                                                      |
        #   |                                                      |
        #   |                                                      |
        #   | p3                                                p4 |
        #   +------------------------------------------------------+
        # (0, h-1)                                             (w-1, h-1)
        #

        w = image.GetWidth()
        h = image.GetHeight()

        # CHECKME: should we sample up to (w,h) instead of (w-1,h-1) ?
        p1 = self._transform_coord(image_to_stage_coord_trf, np.array([0, 0, 1]))
        p2 = self._transform_coord(image_to_stage_coord_trf, np.array([w - 1, 0, 1]))
        p3 = self._transform_coord(image_to_stage_coord_trf, np.array([0, h - 1, 1]))
        p4 = self._transform_coord(image_to_stage_coord_trf, np.array([w - 1, h - 1, 1]))

        # The transformation between image and stage coordinates does not involve a rotation.
        # The image rectangle gets mapped onto a rectangle in stage coordinates space.

        # Check that the image rectangle is still a rectangle in stage coordinates.
        # assert p1[0] ~== p3[0]
        # assert p2[0] ~== p4[0]
        # assert p1[1] ~== p2[1]
        # assert p3[1] ~== p4[1]

        # Find the extent in stage coordinates that covers the image.
        # We will interpolate the focus z-values over that rectangular region in stage coordinates space.
        xmin = min(p1[0], p4[0])
        xmax = max(p1[0], p4[0])
        ymin = min(p1[1], p4[1])
        ymax = max(p1[1], p4[1])

        assert xmin <= xmax
        assert ymin <= ymax

        # Determine stage position step size such that we have 'num_samples_x' samples along x
        # step = (xmax - xmin) / num_samples_x

        return xmin, xmax, ymin, ymax

    def _draw_focus_map(self):
        focus_map = self._model.focus_map

        focus_samples = focus_map.get_focus_grid()
        xmin, xmax, ymin, ymax = focus_map.get_extent()

        fig, ax = plt.subplots()

        # Show an image grid with interpolated focus z-values
        im = ax.imshow(focus_samples, cmap=plt.cm.Reds, origin='lower', interpolation='none', extent=[xmin, xmax, ymin, ymax])

        # Add a color bar
        cbar = fig.colorbar(im)
        cbar.ax.set_ylabel('Focus z')

        # Indicate positions where user acquired focus z-value
        positions = np.array(focus_map.get_user_defined_focus_positions())
        for p in positions[:, 0:2]:
            plt.scatter(p[0], p[1], s=100, c='k', marker='+')

        # Show the plot (non-blocking)
        plt.xlabel('Stage x')
        plt.ylabel('Stage y')
        plt.title('Interpolated focus z-values')
        plt.show(block=False)

