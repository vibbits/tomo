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
from constants import POINTER_MODE_NAME

import matplotlib
matplotlib.use('wxagg')
import matplotlib.pyplot as plt

class FocusPanel(wx.Panel):
    def __init__(self, parent, canvas, model):
        wx.Panel.__init__(self, parent, size=(350, -1))
        self._canvas = canvas
        self._model = model
        self._focus_map = None  # we need an overview image aligned with the stage before we can build a focus map (because we need to know the extent of the sample grid)
        self._table = self._make_table()  # table with user-defined focus (x, y, z)
        self._stage_position_object = None

        title = wx.StaticText(self, wx.ID_ANY, "Focus")
        title.SetFont(wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.BOLD))
        separator = wx.StaticLine(self, wx.ID_ANY)

        label = wx.StaticText(self, wx.ID_ANY, "Click on the overview image with the 'Move Stage' (V) tool to move the stage to a specific position. Then manually focus the microscope in Odemis and press 'Remember focus'. Repeat this for several points on the sample and finally press 'Done'.")
        label.Wrap(330)  # force line wrapping

        button_size = (125, -1)
        remember_focus_button = wx.Button(self, wx.ID_ANY, "Remember focus", size=button_size)
        self.done_button = wx.Button(self, wx.ID_ANY, "Done", size=button_size)  # Not this panel but the ApplicationFame will listen to clicks on this button.
        discard_all_button = wx.Button(self, wx.ID_ANY, "Discard all", size=button_size)
        self._save_button = wx.Button(self, wx.ID_ANY, "Save Focus Map", size=button_size)
        self._save_button.Enable(False)
        self._show_button = wx.Button(self, wx.ID_ANY, "Show Focus Map", size=button_size)
        self._show_button.Enable(False)

        self.Bind(wx.EVT_BUTTON, self._on_remember_focus_button_click, remember_focus_button)
        self.Bind(wx.EVT_BUTTON, self._on_discard_all_button_click, discard_all_button)
        self.Bind(wx.EVT_BUTTON, self._on_save_button_click, self._save_button)
        self.Bind(wx.EVT_BUTTON, self._on_show_button_click, self._show_button)

        table_title = wx.StaticText(self, wx.ID_ANY, "User defined focus positions:")

        b = 5  # border size
        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(title, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(separator, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(label, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(remember_focus_button, 0, wx.ALL | wx.CENTER, border=b)
        contents.Add(discard_all_button, 0, wx.ALL | wx.CENTER, border=b)
        contents.Add(self._save_button, 0, wx.ALL | wx.CENTER, border=b)
        contents.Add(self._show_button, 0, wx.ALL | wx.CENTER, border=b)
        contents.Add(self.done_button, 0, wx.ALL | wx.CENTER, border=b)
        contents.Add(table_title, 0, wx.ALL, border=b)
        contents.Add(self._table, 0, wx.ALL, border=b)

        self.SetSizer(contents)
        contents.Fit(self)

    def activate(self):
        if self._focus_map is None:
            self._focus_map = self._make_focus_map()

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
        table.SetColLabelValue(0, "stage x (m)")
        table.SetColLabelValue(1, "stage y (m)")
        table.SetColLabelValue(2, "focus z")
        table.EnableEditing(False)
        table.DisableDragRowSize()
        table.SetRowLabelSize(40)  # width of the column that displays the row number
        return table

    def reset(self):
        self._focus_map.reset()
        self._canvas.remove_focus_positions()
        self._canvas.redraw()
        self._clear_table()
        self._show_button.Enable(False)
        self._save_button.Enable(False)

    def _clear_table(self):
        num_rows = self._table.GetNumberRows()
        self._table.DeleteRows(0, num_rows)
        self._table.InsertRows(0, 1)  # add an empty row - it looks nicer than just a table with only a header
        self.GetTopLevelParent().Layout()

    def _add_to_table(self, x, y, z):
        row = len(self._focus_map.get_user_defined_focus_positions()) - 1
        self._table.InsertRows(row)
        self._table.SetCellValue(row, 0, '{:.9f}'.format(x))  # x and y are expressed in meters, display position with nanometer precision
        self._table.SetCellValue(row, 1, '{:.9f}'.format(y))
        self._table.SetCellValue(row, 2, '{:.9f}'.format(z))
        self._save_button.Enable(True)
        self._show_button.Enable(True)

    def get_focus_map(self):
        return self._focus_map

    def _make_focus_map(self):
        # Find the extent of rectangle in stage coordinates that covers the overview image.
        image = self._canvas.get_wximage()
        xmin, xmax, ymin, ymax = self._determine_focus_map_grid_extent(image, self._model.overview_image_to_stage_coord_trf)

        num_samples_x = 50
        step = (xmax - xmin) / num_samples_x
        return FocusMap(xmin, xmax, ymin, ymax, step)

    def _on_left_mouse_button_down(self, event):
        coords = event.GetCoords()

        image_coords = (coords[0], -coords[1])
        print("Left mouse button clicked: %i, %i" % image_coords)

        # Remove previous stage position mark from canvas (if any)
        if self._stage_position_object != None:
            self._canvas.remove_objects(self._stage_position_object)

        # Draw current stage position on canvas
        canvas_coords = (image_coords[0], -image_coords[1])  # Note: we need to pass canvas coordinates to add_cross (so y < 0 means over the image)
        self._stage_position_object = self._canvas.add_cross(canvas_coords, "Blue")  # TODO: define color in constants.py instead
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

        # When running Tomo on a development computer without the Odemis software,
        # we generate fake z-focus values for testing purposes.
        if secom_tools.odemis_stubbed:
            z = 10*stage_pos[0] + stage_pos[1]
            print('FAKE focus absolute position: z={}'.format(z))
        else:
            z = secom_tools.get_absolute_focus_z_position()

        # Remember focus
        self._focus_map.add_user_defined_focus_position(stage_pos, z)

        # Update table
        self._add_to_table(stage_pos[0], stage_pos[1], z)
        self.GetTopLevelParent().Layout()

        # Convert the stage position 'stage_pos' to overview image pixel coordinates to draw on the canvas!
        mat = np.linalg.inv(self._model.overview_image_to_stage_coord_trf)
        image_space_stage_pos = self._transform_coord(mat, stage_pos)

        # Draw the position where focus was acquired on the overview image
        self._canvas.add_focus_position(image_space_stage_pos)
        self._canvas.redraw()
        # IMPROVEME draw the _number_ of focus position on canvas too

    def _on_discard_all_button_click(self, event):
        dlg = wx.MessageDialog(self, "Discard all user defined focus positions?", "Discard all", style=wx.YES | wx.NO)
        if dlg.ShowModal() == wx.ID_YES:
            self.reset()

    def _on_show_button_click(self, event):
        self._draw_focus_map()

    def _on_save_button_click(self, event):
        """
        Sample the focus map and save it to a text file.
        """
        defaultDir = ''
        defaultFile = 'focus_map.txt'
        with wx.FileDialog(self, "Specify name of focus map file",
                           defaultDir, defaultFile,
                           wildcard="Text files (*.txt)|*.txt",
                           style=wx.FD_SAVE) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                focus_samples = self._focus_map.get_focus_grid()
                np.savetxt(path, focus_samples, delimiter = '\t')
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
        focus_samples = self._focus_map.get_focus_grid()
        xmin, xmax, ymin, ymax = self._focus_map.get_extent()

        fig, ax = plt.subplots()

        # Show an image grid with interpolated focus z-values
        im = ax.imshow(focus_samples, cmap=plt.cm.Reds, origin='lower', interpolation='none', extent=[xmin, xmax, ymin, ymax])

        # Add a color bar
        cbar = fig.colorbar(im)
        cbar.ax.set_ylabel('Focus z')

        # Indicate positions where user acquired focus z-value
        positions = np.array(self._focus_map.get_user_defined_focus_positions())
        for p in positions[:, 0:2]:
            plt.scatter(p[0], p[1], s=100, c='k', marker='+')

        # Show the plot (non-blocking)
        plt.xlabel('Stage x')
        plt.ylabel('Stage y')
        plt.title('Interpolated focus z-values')
        plt.show(block=False)

