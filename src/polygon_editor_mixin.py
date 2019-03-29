import tools
from pubsub import pub
from wx.lib.floatcanvas import FloatCanvas
from polygon_editing_mode import PolygonEditingMode
from model import MSG_SLICE_POLYGON_CHANGED
from constants import NORMAL_COLOR, ACTIVE_COLOR, HANDLE_SIZE

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

        self._active_handle = None  # The (floatcanvas handle object, slice index, vertex index) of the vertex/handle that the mouse is currently over, or None if the mouse is not over a handle.
        self._dragging = None
        self._handles = []  # List of tuples (FloatCanvas object for the handle, slice index of the handle, vertex index of the handle)

    def start(self):
        self._dragging = None
        self._active_handle = None

        self._add_slice_handles(self._selector.get_selected_slices())
        self._canvas.redraw(True)

        self._canvas.Bind(PolygonEditingMode.EVT_TOMO_POLY_EDIT_MOTION, self._on_mouse_move)
        self._canvas.Bind(PolygonEditingMode.EVT_TOMO_POLY_EDIT_LEFT_DOWN, self._on_left_mouse_button_down)
        self._canvas.Bind(PolygonEditingMode.EVT_TOMO_POLY_EDIT_LEFT_UP, self._on_left_mouse_button_up)

        pub.subscribe(self._on_polygon_model_change, MSG_SLICE_POLYGON_CHANGED)

    def stop(self):
        pub.unsubscribe(self._on_polygon_model_change, MSG_SLICE_POLYGON_CHANGED)

        self._canvas.Unbind(PolygonEditingMode.EVT_TOMO_POLY_EDIT_MOTION)
        self._canvas.Unbind(PolygonEditingMode.EVT_TOMO_POLY_EDIT_LEFT_DOWN)
        self._canvas.Unbind(PolygonEditingMode.EVT_TOMO_POLY_EDIT_LEFT_UP)

        self._remove_slice_handles()
        self._canvas.redraw(True)

    def _on_polygon_model_change(self, index, polygon):
        self._remove_slice_handles()
        self._add_slice_handles(self._selector.get_selected_slices())
        self._canvas.redraw(True)

    def _on_left_mouse_button_down(self, event):
        # Check if user clicked on a handle to start dragging it.
        if self._active_handle:
            # The mouse is over a handle, and the user presses the mouse button down,
            # so we remember which handle is being dragged so we can update the slice contour shape
            # when we receive mouse move events later on.
            self._dragging = self._active_handle

    def _on_mouse_move(self, event):
        # If user was dragging a handle, then we need to update the slice polygon accordingly
        coords = event.GetCoords()
        pos = (coords[0], -coords[1])
        # print("Mouse move, position: %i, %i" % pos)

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

        event.Skip()

    def _on_left_mouse_button_up(self, event):
        # Check if user was dragging a handle and released it
        if self._dragging:
            self._dragging = None
            return

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
        # print("handle enter, object = {}".format(object.Name))
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
        # print("handle leave, object = {}".format(object.Name))
        if self._dragging:
            return
        object.SetColor(NORMAL_COLOR)
        self._active_handle = None
        self._canvas.redraw(True)

    def _parse_handle_name(self, handle):
        name = handle.Name  # name is for example 'PolygonHandle:2:3', encoding the slice and vertex indices
        chunks = name.split(':')
        slice_idx = int(chunks[1])
        vertex_idx = int(chunks[2])
        return handle, slice_idx, vertex_idx

