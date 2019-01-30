import wx
from polygon_creation_mode import PolygonCreationMode
from constants import NORMAL_COLOR, HANDLE_SIZE

# TODO: listen to ESC key: if ESC is pressed then cancel construction of a new slice

class PolygonCreatorMixin:
    def __init__(self, model, canvas, selector):
        self._model = model
        self._canvas = canvas
        self._selector = selector  # the mixin responsible for handling slice selection

        # Coordinates of vertices in polygon that is being constructed
        self._vertices = []

        # FloatCanvas handles
        self._point_handles = []
        self._line_handles = []

    def start(self):
        self._vertices = []
        self._point_handles = []
        self._line_handles = []

        self._canvas.Bind(PolygonCreationMode.EVT_TOMO_POLY_CREATE_MOTION, self._on_mouse_move)
        self._canvas.Bind(PolygonCreationMode.EVT_TOMO_POLY_CREATE_LEFT_UP, self._on_left_mouse_button_up)
        self._canvas.Bind(wx.EVT_CHAR_HOOK, self._key_pressed)

    def stop(self):
        self._remove_temporary_polygon()
        self._canvas.redraw()

        self._canvas.Unbind(PolygonCreationMode.EVT_TOMO_POLY_CREATE_MOTION)
        self._canvas.Unbind(PolygonCreationMode.EVT_TOMO_POLY_CREATE_LEFT_UP)
        self._canvas.Unbind(wx.EVT_CHAR_HOOK)

    def _key_pressed(self, event):
        key = event.GetKeyCode()
        print('polygon creator: keydown key={}'.format(key))
        event.Skip()

    def _on_mouse_move(self, event):
        if len(self._vertices) == 0:
            event.Skip()
            return

        coords = event.GetCoords()

        # Update position of the handle on the last vertex
        self._point_handles[-1].SetPoint(coords)

        # Update position of the end point of the tentative lines
        if len(self._vertices) >= 2:
            self._line_handles[-2].Points[1] = coords
            self._line_handles[-1].Points[0] = coords
        else:
            self._line_handles[-1].Points[1] = coords

        self._canvas.redraw(True)

        event.Skip()  # CHECKME: can we just call event.Skip() as the very first line of the event handler, instead of at the end of every return path? I would think so.

    def _on_left_mouse_button_up(self, event):
        p = event.GetCoords()

        self._vertices.append(p)

        if len(self._vertices) == 4:
            # Add new polygon to the model
            new_polygon = [(v[0], -v[1]) for v in self._vertices]
            self._model.slice_polygons.append(new_polygon)

            # Update canvas
            self._remove_temporary_polygon()
            self._canvas.set_slice_polygons(self._model.slice_polygons)

            # Automatically select the new slice
            new_slice_index = len(self._model.slice_polygons) - 1
            self._selector.set_selected_slices([new_slice_index])

            self._canvas.redraw()
            return

        # De-select slices if they were selected
        if len(self._vertices) == 1:
            self._selector.set_selected_slices([])

        # Add vertex handles
        if len(self._vertices) == 1:
            h = self._canvas.Canvas.AddSquarePoint(p, Color=NORMAL_COLOR, Size=HANDLE_SIZE)
            self._point_handles.append(h)

        h = self._canvas.Canvas.AddSquarePoint(p, Color=NORMAL_COLOR, Size=HANDLE_SIZE)
        self._point_handles.append(h)

        # Add lines
        if len(self._vertices) == 3:
            h = self._line_handles.pop()
            self._canvas.remove_objects([h])

        h = self._canvas.Canvas.AddLine([(p[0], p[1]), (p[0], p[1])], LineColor=NORMAL_COLOR)
        self._line_handles.append(h)

        if len(self._vertices) >= 2:
            # Close the polygon to a tentative triangle or quadrilateral
            start = self._vertices[0]
            h = self._canvas.Canvas.AddLine([(p[0], p[1]), (start[0], start[1])], LineColor=NORMAL_COLOR)
            self._line_handles.append(h)

        self._canvas.redraw()

    def _remove_temporary_polygon(self):
        self._canvas.remove_objects(self._point_handles)
        self._canvas.remove_objects(self._line_handles)
        self._point_handles = []
        self._line_handles = []
        self._vertices = []

