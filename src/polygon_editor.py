from wx.lib.floatcanvas import NavCanvas, FloatCanvas

class PolygonEditor:
    _canvas = None
    _vertices = []
    _edges = []

    def __init__(self, canvas):
        self._canvas = canvas
        self._canvas.Bind(FloatCanvas.EVT_MOTION, self._on_mouse_move)
        self._canvas.Bind(FloatCanvas.EVT_LEFT_UP, self._on_left_mouse_button_up)

    def _print_coords(self, text, event):
        print(f'{text} coords={event.Coords}')

    # TODO: while editing a polygon, if we already have a point or an edge,
    #       listen to backspace and delete the most recently added point/edge

    # TODO: ability to close a polygon (and stop editing it / start creating a new one) - snap to first point in polygon

    # TODO: maybe draw the lines so far as a transparent polygon with one missing edge

    def _on_mouse_move(self, event):
        # TODO:
        # if mouse cursor close to first vertex of the polygon, then highlight it (and set a flag to remember this)
        # (if not close anymore, stop highlighting)

        if self._edges:
            _, old_edge = self._pop_halfopen_line_segment()
            self._push_halfopen_line_segment(startpos=old_edge.Points[0], endpos=event.Coords)
            self._canvas.Draw()

    def _on_left_mouse_button_up(self, event):
        # if flag set that we are close to the first vertex of the polygon
        #    add line between endpoint of previous edge and this first vertex, thus closing the polygon nicely
        #    then start a new polygon
        # endif

        pos = event.Coords
        if not self._vertices:
            self._push_vertex(pos)
        self._push_halfopen_line_segment(pos, pos)
        self._canvas.Draw()

    def _push_halfopen_line_segment(self, startpos, endpos):
        self._push_vertex(endpos)
        self._push_edge(startpos, endpos)

    def _push_vertex(self, pos):
        vertex = self._canvas.AddPoint(pos, Color='red', Diameter=4)
        self._vertices.append(vertex)

    def _push_edge(self, startpos, endpos):
        edge = self._canvas.AddLine([startpos, endpos], LineColor='red')
        self._edges.append(edge)

    def _pop_vertex(self):
        # TODO: check for self._vertices list empty
        vertex = self._vertices.pop()
        self._canvas.RemoveObject(vertex)
        return vertex

    def _pop_edge(self):
        # TODO: check for self._edges list empty
        edge = self._edges.pop()
        self._canvas.RemoveObject(edge)
        return edge

    def _pop_halfopen_line_segment(self):
        vertex = self._pop_vertex()
        edge = self._pop_edge()
        return vertex, edge
