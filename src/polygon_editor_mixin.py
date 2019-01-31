import wx
import tools
from wx.lib.floatcanvas import FloatCanvas
from polygon_editing_mode import PolygonEditingMode
from constants import NOTHING, NORMAL_COLOR, ACTIVE_COLOR, REGULAR_LINE_WIDTH, HIGHLIGHTED_LINE_WIDTH, HANDLE_SIZE

# FIXME: If we delete a slice, then some other parts of the model may have to be invalidated.
#        For example, the list with predicted points of interest will have to be recalculated.
#        (Not always, in case of POIs only if we remove a slice that is part of the range of slices for which we did predict POIs.
#         Maybe we should forbid editing the slices once we've set POIs?)
# FIXME: Key events are only received if the canvas has focus, for example by clicking it first.
#        This is undesirable, we _always_ want the key event.
#        For more info, and possible solution: https://forums.wxwidgets.org/viewtopic.php?t=42399
# IMPROVEME: it would be better if the "view" layer 'listens' to model changes.
#            For example, that if we change a slice outline or delete one,
#            that the view layer gets a callback and can update the canvas.
#            We can use the PyPubSub package for this. (But first check which version of this package that we need on the SECOM...)
# NOTE: See also https://github.com/wxWidgets/Phoenix/blob/master/samples/floatcanvas/PolyEditor.py

HANDLE_NAME_PREFIX = 'PolygonHandle'

class PolygonEditorMixin:
    def __init__(self, model, canvas, selector):
        self._model = model
        self._canvas = canvas
        self._selector = selector  # the mixin that handles the current slice selection

        # self._over = NOTHING  # slice number that cursor is over, or NOTHING otherwise; the slice that the cursor is over is drawn highlighted
        # self._slice_being_edited = NOTHING  # currently selected slice, or NOTHING otherwise; the selected slice has handles drawn over its vertices

        # self._active_handle = NOTHING  # NOTHING if no handle is active; otherwise the index of the vertex in the '_slice_being_edited' slice
        # self._dragging = NOTHING  # the index of the vertex (in the '_slice_being_edited' slice contour) whose handle is being dragged; or NOTHING otherwise
        self._active_handle = None  # The (floatcanvas handle object, slice index, vertex index) of the vertex/handle that the mouse is currently over, or None if the mouse is not over a handle.
        self._dragging = None  # xxxx
        self._handles = []  # List of tuples (FloatCanvas object for the handle, slice index of the handle, vertex index of the handle)
        # self._slice_numbers = []  # FloatCanvas objects for the slice numbers (so the user can see in which order they are supposed to be)

    def start(self):
        # self._over = NOTHING
        # self._slice_being_edited = NOTHING
        self._dragging = None
        self._active_handle = None
        # self._slice_numbers = []

        self._add_slice_handles(self._selector.get_selected_slices())
        self._canvas.redraw(True)

        self._canvas.Bind(PolygonEditingMode.EVT_TOMO_POLY_EDIT_MOTION, self._on_mouse_move)
        self._canvas.Bind(PolygonEditingMode.EVT_TOMO_POLY_EDIT_LEFT_DOWN, self._on_left_mouse_button_down)
        self._canvas.Bind(PolygonEditingMode.EVT_TOMO_POLY_EDIT_LEFT_UP, self._on_left_mouse_button_up)

    def stop(self):
        self._canvas.Unbind(PolygonEditingMode.EVT_TOMO_POLY_EDIT_MOTION)
        self._canvas.Unbind(PolygonEditingMode.EVT_TOMO_POLY_EDIT_LEFT_DOWN)
        self._canvas.Unbind(PolygonEditingMode.EVT_TOMO_POLY_EDIT_LEFT_UP)
        self._remove_slice_handles()
        self._canvas.redraw(True)

    def _on_left_mouse_button_down(self, event):
        # Check if user clicked on a handle to start dragging it.
        # -------------------------------------------------------
        if self._active_handle:
            # The mouse is over a handle, and the user presses the mouse button down,
            # so we remember which handle is being dragged so we can update the slice contour shape
            # when we receive mouse move events later on.
            self._dragging = self._active_handle

    def _on_mouse_move(self, event):
        """
        We need to deal with two possible user actions here:
        1. The user was dragging a slice handle and we need to update the slice polygon accordingly.
        2. The user hover over a slice and we need to change it visual appearance to indicate that it can be selected.
        """

        coords = event.GetCoords()
        pos = (coords[0], -coords[1])
        # print("Mouse move, position: %i, %i" % pos)

        # Check if user was dragging a handle.
        # ------------------------------------

        if self._dragging:
            handle, slice_idx, vertex_idx = self._dragging

            # Update model
            self._model.slice_polygons[slice_idx][vertex_idx] = pos

            # Update the polygon vertex position on the canvas
            self._canvas.set_slice_outline_vertex_position(slice_idx, vertex_idx, coords)

            # Update position of slice number on the canvas
            new_center = tools.polygon_center(self._model.slice_polygons[slice_idx])
            new_center = (new_center[0], -new_center[1])
            self._canvas.set_slice_number_position(slice_idx, new_center)

            # Update slice handle
            handle.SetPoint(coords)

            # Redraw
            self._canvas.redraw(True)

            event.Skip()  # Pass on the event (e.g. so that we can update the mouse position in the status bar)
            return

        # # Check if user hovers over a slice.
        # # ----------------------------------
        #
        # slices_hit = tools.polygons_hit(self._model.slice_polygons, pos)
        #
        # old_over = self._over
        # new_over = slices_hit[0] if slices_hit else -1
        #
        # if old_over == new_over:
        #     event.Skip()
        #     return
        #
        # if old_over != NOTHING:
        #     self._canvas.set_slice_outline_linewidth(old_over, REGULAR_LINE_WIDTH)
        #
        # if new_over != NOTHING:
        #     self._canvas.set_slice_outline_linewidth(new_over, HIGHLIGHTED_LINE_WIDTH)
        #
        # self._canvas.redraw(True)
        #
        # self._over = new_over

        event.Skip()

    def _on_left_mouse_button_up(self, event):
        """
        We need to deal with two possible user actions here:
        1. The user was dragging a slice handle and released that handle.
        2. The user clicked inside a slice in order to select it.
        """

        # Check if user released a handle.
        # --------------------------------

        if self._dragging:
            # The user released a slice handle that was being dragged.
            self._dragging = None
            return

        # # Check if user selected a slice.
        # # -------------------------------
        #
        # if self._over == self._slice_being_edited:
        #     return
        #
        # if self._slice_being_edited != NOTHING:
        #     self._remove_slice_handles()
        #
        # if self._over != NOTHING:
        #     self._add_slice_handles(self._over)
        #
        # self._canvas.redraw(True)
        #
        # self._slice_being_edited = self._over

    def _add_slice_handles(self, slices):
        self._handles = self._make_slice_handles(slices)
        self._bind_hover_events(self._handles)

    def _make_slice_handles(self, slices):
        handles = []
        for slice_idx in slices:
            polygon = self._model.slice_polygons[slice_idx]
            for vertex_idx, p in enumerate(polygon):
                p = (p[0], -p[1]) # note: flip y to convert from image coordinates (with y >= 0) back to canvas coords
                h = self._canvas.Canvas.AddSquarePoint(p, Color=NORMAL_COLOR, Size=HANDLE_SIZE)
                # h = self._canvas.Canvas.AddRectangle(p, (20,20), LineColor=NORMAL_COLOR) # rectangles are subject to zooming in/out (undesirable; can we suppress this?)
                handle = (h, slice_idx, vertex_idx)
                handles.append(handle)
        return handles

    def _bind_hover_events(self, handles):
        """
        Register callbacks for when the cursor moves onto or away from the slice handles.
        :param handles: list of tuples (floatcanvas object, slice index, vertex index).
        """
        for handle in handles:
            h, slice_idx, vertex_idx = handle
            # Encode the slice and vertex index numbers in the handle's name,
            # we'll need them if the user drags the handle to modify the right slice contour
            h.Name = '{}:{}:{}'.format(HANDLE_NAME_PREFIX, slice_idx, vertex_idx)
            h.Bind(FloatCanvas.EVT_FC_ENTER_OBJECT, self._handle_enter)
            h.Bind(FloatCanvas.EVT_FC_LEAVE_OBJECT, self._handle_leave)

    def _remove_slice_handles(self):
        """
        Remove the handles on the currently selected slices.
        Handles are little squares for modifying the slice contour.
        """
        objs = [h for (h, _, _) in self._handles]
        self._canvas.remove_objects(objs)
        self._handles = []

    def _handle_enter(self, object):
        """
        Called when the cursor moves onto an object handle (little square on a slice vertex)
        :param object: the floatcanvas object that the mouse moved onto (little square in our case)
        """
        print("handle enter, object = {}".format(object.Name))
        if self._dragging:
            return
        object.SetColor(ACTIVE_COLOR)
        self._active_handle = self._parse_handle_name(object)
        self._canvas.redraw(True)

    def _handle_leave(self, object):
        """
        Called when the cursor moves away from an object handle (little square on a slice vertex)
        :param object: the floatcanvas object that the mouse moved away from (little square in our case)
        """
        print("handle leave, object = {}".format(object.Name))
        if self._dragging:
            return
        object.SetColor(NORMAL_COLOR)
        self._active_handle = None
        self._canvas.redraw(True)

    def _parse_handle_name(self, handle):
        name = handle.Name  # name is for example 'PolygonHandle:2:3'
        chunks = name.split(':')
        slice_idx = int(chunks[1])
        vertex_idx = int(chunks[2])
        return handle, slice_idx, vertex_idx

