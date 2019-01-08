import wx
import tools
from wx.lib.floatcanvas import FloatCanvas
from polygon_selection_mode import PolygonSelectionMode

NOTHING = -1  # an invalid index indicating no slice or no handle.
NORMAL_COLOR = 'Green'
ACTIVE_COLOR = 'Red'
HANDLE_NAME_PREFIX = 'PolygonHandle'
REGULAR_LINE_WIDTH = 1  # IMPROVEME: should be the same width as when the polygon was drawn outside this mode, we should probably move these constants to a separate file.
HIGHLIGHTED_LINE_WIDTH = 3


class PolygonEditorPanel(wx.Panel):
    _canvas = None
    _model = None

    _over = NOTHING  # slice number that cursor is over, or NOTHING otherwise; the slice that the cursor is over is drawn highlighted
    _selected = NOTHING  # currently selected slice, or NOTHING otherwise; the selected slice has handles drawn over its vertices
    _active_handle = NOTHING  # NOTHING if no handle is active; otherwise the index of the vertex in the '_selected' slice
    _dragging = NOTHING  # the index of the vertex (in the '_selected' slice contour) whose handle is being dragged; or NOTHING otherwise

    # FloatCanvas objects
    _handles = []  # FloatCanvas objects for the handles of the currently selected slice
    _slice_numbers = []  # FloatCanvas objects for the slice numbers (so the user can see in which order they are supposed to be)

    # user interface
    done_button = None

    def __init__(self, parent, model, canvas):
        wx.Panel.__init__(self, parent, size=(350, -1), style=wx.WANTS_CHARS)  # WANTS_CHARS is needed so we can detect when DEL is pressed for deleting a slice

        self._canvas = canvas
        self._model = model

        # Build the user interface
        title = wx.StaticText(self, wx.ID_ANY, "Polygon Editor")
        title.SetFont(wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.BOLD))
        separator = wx.StaticLine(self, wx.ID_ANY)

        instructions_label = wx.StaticText(self, wx.ID_ANY, ("Pick the Polygon Selection tool from the tool bar. "
                                                             "Then hover over the polygon that you want to edit and left-click to select it. "
                                                             "Click and drag the vertex handles to edit its shape. "
                                                             "(It is not possible to add or delete vertices, to create new polygons or to delete existing polygons.)"))
        w = 330
        instructions_label.Wrap(w)  # force line wrapping

        button_size = (125, -1)
        self.done_button = wx.Button(self, wx.ID_ANY, "Done", size=button_size)  # The ApplicationFame will listen to clicks on this button.

        b = 5  # border size
        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(title, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(separator, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(instructions_label, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(self.done_button, 0, wx.ALL | wx.CENTER, border=b)

        self.SetSizer(contents)
        contents.Fit(self)

    def activate(self):
        # print('Polygon editor panel: activate')
        self._over = NOTHING
        self._selected = NOTHING
        self._dragging = NOTHING
        self._active_handle = NOTHING
        self._handles = []
        self._slice_numbers = []
        self._add_slice_numbers()
        self._canvas.Bind(PolygonSelectionMode.EVT_TOMO_POLY_SELECT_MOTION, self._on_mouse_move)
        self._canvas.Bind(PolygonSelectionMode.EVT_TOMO_POLY_SELECT_LEFT_DOWN, self._on_left_mouse_button_down)
        self._canvas.Bind(PolygonSelectionMode.EVT_TOMO_POLY_SELECT_LEFT_UP, self._on_left_mouse_button_up)
        self._canvas.Bind(wx.EVT_CHAR_HOOK, self._key_pressed)  # CHECKME: EVT_CHAR or EVT_CHAR_HOOK ???

    def deactivate(self):
        # print('Polygon editor panel: deactivate')
        self._remove_slice_handles()
        self._remove_slice_numbers()
        self._canvas.Unbind(PolygonSelectionMode.EVT_TOMO_POLY_SELECT_MOTION)
        self._canvas.Unbind(PolygonSelectionMode.EVT_TOMO_POLY_SELECT_LEFT_DOWN)
        self._canvas.Unbind(PolygonSelectionMode.EVT_TOMO_POLY_SELECT_LEFT_UP)
        self._canvas.Unbind(wx.EVT_CHAR_HOOK)

    def _key_pressed(self, event):
        """
        Handle a key press. The purpose is to be able to delete the currently selected slice if the user
        presses the DEL key.
        :param event:
        """

        # FIXME: Key events are only received if the canvas has focus, for example by clicking it first.
        #        This is undersirable, we _always_ want the key event.

        key = event.GetKeyCode()
        print('polygon editor: keydown key={}'.format(key))
        if key == wx.WXK_DELETE or key == wx.WXK_NUMPAD_DELETE:
            if self._selected != NOTHING:
                # Remove slice handles from canvas
                self._remove_slice_handles()

                # Remove slice from canvas
                self._canvas.remove_slice_outline(self._selected)

                # Remove slice from model
                self._model.slice_polygons.pop(self._selected)

                # Update slice numbers
                self._remove_slice_numbers()
                self._add_slice_numbers()

                # Update state
                if self._over == self._selected:
                    self._over = NOTHING
                self._selected = NOTHING
                self._dragging = NOTHING
                self._active_handle = NOTHING

                # Redraw
                self._canvas.redraw(True)

        # FIXME: If we delete a slice, then some other parts of the model may have to be invalidated.
        #        For example, the list with predicted points of interest will have to be recalculated.
        #        (Not always, in case of POIs only if we remove a slice that is part of the range of slices for which we did predict POIs.
        #         Maybe we should forbid editing the slices once we've set POIs?)

    def _on_left_mouse_button_down(self, event):
        if self._active_handle != NOTHING:
            # The mouse is over a handle, and the user presses the mouse button down,
            # so we remember which handle is being dragged so we can update the slice contour
            # when we receive mouse move events lateron.
            self._dragging = self._active_handle

    def _on_mouse_move(self, event):
        coords = event.GetCoords()
        pos = (coords[0], -coords[1])
        # print("Mouse move, position: %i, %i" % pos)

        # Special situation: we're dragging a slice handle
        if self._dragging != NOTHING:
            # Update model
            self._model.slice_polygons[self._selected][self._dragging] = pos
            # Update slice handles
            self._handles[self._dragging].SetPoint(coords)
            # Update slice outline
            self._canvas.set_slice_outline_vertex_position(self._selected, self._dragging, coords)
            self._canvas.redraw(True)
            return

        slices_hit = tools.polygons_hit(self._model.slice_polygons, pos)

        old_over = self._over
        new_over = slices_hit[0] if slices_hit else -1

        if old_over == new_over:
            return

        if old_over != NOTHING:
            self._canvas.set_slice_outline_linewidth(old_over, REGULAR_LINE_WIDTH)

        if new_over != NOTHING:
            self._canvas.set_slice_outline_linewidth(new_over, HIGHLIGHTED_LINE_WIDTH)

        self._canvas.redraw(True)

        self._over = new_over

    def _on_left_mouse_button_up(self, event):
        if self._dragging != NOTHING:
            # The user released a slice handle that was being dragged.
            self._dragging = NOTHING
            return

        if self._over == self._selected:
            return

        if self._selected != NOTHING:
            self._remove_slice_handles()

        if self._over != NOTHING:
            self._add_slice_handles(self._over)

        self._canvas.redraw(True)

        self._selected = self._over

    def _add_slice_handles(self, slice_index):
        self._handles = self._make_slice_handles(self._model.slice_polygons[slice_index])
        self._bind_hover_events(self._handles)

    def _make_slice_handles(self, pts):
        """
        :param pts: a list of slice vertices coordinates
        :return: a list with floatcanvas objects representing handles (little squares) placed over the given vertex positions (pts)
        """
        handles = []
        pts = [(p[0], -p[1]) for p in pts]  # note: flip y to convert from image coordinates (with y >= 0) back to canvas coords
        for p in pts:
            h = self._canvas.Canvas.AddSquarePoint(p, Color=NORMAL_COLOR, Size=8)
            # h = self._canvas.Canvas.AddRectangle(p, (20,20), LineColor=NORMAL_COLOR) # rectangles are subject to zooming in/out (undesirable; can we suppress this?)
            handles.append(h)
        return handles

    def _bind_hover_events(self, handles):
        """
        Register callbacks for when the cursor moves onto or away from the slice handles.
        :param handles: list of floatcanvas objects (the slice handles), one per slice vertex.
        """
        for i, h in enumerate(handles):
            h.Name = '{}{}'.format(HANDLE_NAME_PREFIX, i) # the name string encodes the vertex index number, we'll need it if the user drags the handle to modify the slice contour
            h.Bind(FloatCanvas.EVT_FC_ENTER_OBJECT, self._handle_enter)
            h.Bind(FloatCanvas.EVT_FC_LEAVE_OBJECT, self._handle_leave)

    def _remove_slice_handles(self):
        """
        Remove the handles on the currently selected slice.
        Handles are little squares for modifying the slice contour.
        """
        self._canvas.remove_objects(self._handles)
        self._handles = []

    def _handle_enter(self, object):
        """
        Called when the cursor moves onto an object handle (little square on a slice vertex)
        :param object: the floatcanvas object that the mouse moved onto (little square in our case)
        """
        # print("handle enter, object = {}".format(object.Name))
        if self._dragging != NOTHING:
            return
        object.SetColor(ACTIVE_COLOR)
        self._active_handle = int(object.Name.split(HANDLE_NAME_PREFIX)[1])
        self._canvas.redraw(True)

    def _handle_leave(self, object):
        """
        Called when the cursor moves away from an object handle (little square on a slice vertex)
        :param object: the floatcanvas object that the mouse moved away from (little square in our case)
        """
        # print("handle leave, object = {}".format(object.Name))
        if self._dragging != NOTHING:
            return
        object.SetColor(NORMAL_COLOR)
        self._active_handle = NOTHING
        self._canvas.redraw(True)

    # IMPROVEME: the slice numbers should probably be handled in the OverviewCanvas, as they are interesting outside the polygon editor too.
    # And it should then be possible to show/hide them from the Tomo menu.

    def _add_slice_numbers(self):
        self._slice_numbers = []
        for i, polygon in enumerate(self._model.slice_polygons):
            pos = tools.polygon_center(polygon)
            pos = (pos[0], -pos[1])
            obj = self._canvas.Canvas.AddText(str(i+1), pos, Size=10, BackgroundColor=None, Color=NORMAL_COLOR, Position="cc")
            self._slice_numbers.append(obj)

    def _remove_slice_numbers(self):
        self._canvas.remove_objects(self._slice_numbers)

    # IMPROVEME: it would be better if the "view" layer 'listens' to model changes.
    # For example, that if we change a slice outline or delete one,
    # that the view layer gets a callback and can update the canvas.
    # We can use the PyPubSub package for this. (But first check which version of this package that we need on the SECOM...)
