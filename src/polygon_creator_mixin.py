
from polygon_creation_mode import PolygonCreationMode
from constants import NORMAL_COLOR, HANDLE_SIZE

class PolygonCreatorMixin():

    def __init__(self, model, canvas):
        self._model = model
        self._canvas = canvas

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
        self._canvas.Bind(PolygonCreationMode.EVT_TOMO_POLY_CREATE_RIGHT_UP, self._on_right_mouse_button_up)

    def stop(self):
        self._remove_temporary_polygon()
        self._canvas.redraw()

        self._canvas.Unbind(PolygonCreationMode.EVT_TOMO_POLY_CREATE_MOTION)
        self._canvas.Unbind(PolygonCreationMode.EVT_TOMO_POLY_CREATE_LEFT_UP)
        self._canvas.Unbind(PolygonCreationMode.EVT_TOMO_POLY_CREATE_RIGHT_UP)


    def _on_right_mouse_button_up(self, event):
        print('creator: right up')
        # if len(self._vertices) == 0:
        #     return
        #
        # point = self._point_handles.pop()
        # line = self._line_handles.pop()
        # self._vertices.pop()
        # self._canvas.Canvas.RemoveObject(point)
        # self._canvas.Canvas.RemoveObject(line)


    def _on_mouse_move(self, event):
        if len(self._vertices) == 0:
            return

        coords = event.GetCoords()

        # Update position of the handle on the last vertex
        point = self._point_handles[-1]
        point.SetPoint(coords)

        # Update position of the end point of the last line
        line = self._line_handles[-1]
        line.Points[1] = coords

        self._canvas.redraw(True)

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
            self._canvas.redraw()
            return

        if len(self._vertices) == 1:
            h = self._canvas.Canvas.AddSquarePoint(p, Color=NORMAL_COLOR, Size=HANDLE_SIZE)
            self._point_handles.append(h)

        h = self._canvas.Canvas.AddSquarePoint(p, Color=NORMAL_COLOR, Size=HANDLE_SIZE)
        self._point_handles.append(h)

        h = self._canvas.Canvas.AddLine([(p[0], p[1]), (p[0], p[1])], LineColor=NORMAL_COLOR)
        self._line_handles.append(h)

    def _remove_temporary_polygon(self):
        self._canvas.remove_objects(self._point_handles)
        self._canvas.remove_objects(self._line_handles)
        self._point_handles = []
        self._line_handles = []
        self._vertices = []

