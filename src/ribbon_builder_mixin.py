import numpy as np
from wx.lib.floatcanvas import FloatCanvas
from ribbon_builder_mode import RibbonBuilderMode
from constants import NORMAL_COLOR, ACTIVE_COLOR, REGULAR_LINE_WIDTH, HANDLE_SIZE

HANDLE_NAME_PREFIX = 'PolygonHandle'

# IMPROVEME: the RibbonBuilderMixin and the PolygonEditorMixin share quite some code related to adding handles on slice vertices and responding to the mouse hovering over them etc. Try to factor out the common code.

class RibbonBuilderMixin:
    def __init__(self, model, canvas, selector):
        self._model = model
        self._canvas = canvas
        self._selector = selector  # the mixin that handles the current slice selection

        self._dragging = None
        self._active_handle = None

        self._ghost_slices = []  # (temporary) replicates of the original slice polygon

        # FloatCanvas objects
        self._ghost_objs = []  # the FloatCanvas polygons for the "ghost" slices (i.e. the temporary duplicates of the slice that is being replicated)
        self._handles = []  # handles on the bottom-left corner of all slices in the model; dragging such a handle will replicate the slice whose handle is being dragged

    def start(self):
        # De-select all slices
        self._selector.set_selected_slices([])

        self._dragging = None
        self._active_handle = None

        self._ghost_slices = []
        self._ghost_objs = []

        num_slices = len(self._model.slice_polygons)
        self._add_slice_handles([i for i in range(num_slices)])

        self._canvas.redraw(True)

        self._canvas.Bind(RibbonBuilderMode.EVT_TOMO_RIBBON_BUILDER_MOTION, self._on_mouse_move)
        self._canvas.Bind(RibbonBuilderMode.EVT_TOMO_RIBBON_BUILDER_LEFT_DOWN, self._on_left_mouse_button_down)
        self._canvas.Bind(RibbonBuilderMode.EVT_TOMO_RIBBON_BUILDER_LEFT_UP, self._on_left_mouse_button_up)

    def stop(self):
        self._canvas.Unbind(RibbonBuilderMode.EVT_TOMO_RIBBON_BUILDER_MOTION)
        self._canvas.Unbind(RibbonBuilderMode.EVT_TOMO_RIBBON_BUILDER_LEFT_DOWN)
        self._canvas.Unbind(RibbonBuilderMode.EVT_TOMO_RIBBON_BUILDER_LEFT_UP)
        self._remove_slice_handles()
        self._canvas.redraw(True)

    def _on_left_mouse_button_down(self, event):
        # Check if user clicked on a handle to start dragging it.
        if self._active_handle:
            # The mouse is over a handle, and the user presses the mouse button down,
            # so we remember which handle is being dragged so we can replicate the correct slice
            # when we receive mouse move events later on.
            self._dragging = self._active_handle

    def _estimated_polygon_height_vector(self, polygon):  # return a numpy vector from the middle of the bottom quad edge to the middle of the top edge
        assert len(polygon) == 4
        # We also assume that the first point in the quadrilateral is the bottom left vertex
        bottom_middle = (np.array(polygon[0]) + np.array(polygon[1])) / 2.0  # middle of bottom base of the quadrilateral
        top_middle = (np.array(polygon[2]) + np.array(polygon[3])) / 2.0  # middle of the top base of the quadrilateral
        return top_middle - bottom_middle

    def _guess_desired_number_of_copies(self, template_polygon, displacement):  # CHECKME: I'm not sure this is a good estimate in all cases
        vec_h = self._estimated_polygon_height_vector(template_polygon)
        vec_d_unit = displacement / np.linalg.norm(displacement)
        proj_len = np.dot(vec_h, vec_d_unit)
        height_along_displacement = np.linalg.norm(proj_len * vec_d_unit)
        total_displacement_length = np.linalg.norm(displacement)
        desired_num_copies = int(max(1, round(total_displacement_length / height_along_displacement)))
        # print('{} {} {} => polydist={} totaldist={} => copies={}'.format(vec_h, vec_d_unit, proj_len, height_along_displacement, total_displacement_length, desired_num_copies))
        return desired_num_copies

    def _on_mouse_move(self, event):
        coords = event.GetCoords()
        pos = (coords[0], -coords[1])
        # print("RibbonBuildMixin mouse move, position: %i, %i" % pos)

        if self._dragging is None:
            event.Skip()
            return

        handle, slice_idx, vertex_idx = self._dragging

        # Calculate desired number of replicates and the displacement vector between the replicates
        template_polygon = self._model.slice_polygons[slice_idx]
        orig_pos = template_polygon[vertex_idx]
        total_displacement = np.array(pos) - np.array(orig_pos)
        print('pos now={} origpos={} total_displacement={}'.format(np.array(pos), np.array(orig_pos), total_displacement))
        desired_num_copies = self._guess_desired_number_of_copies(template_polygon, total_displacement)
        assert desired_num_copies > 0
        slice_displacement = total_displacement / desired_num_copies

        # Remove old ghosts
        self._remove_ghosts()

        # Add new ghosts
        self._ghost_slices = self._replicate_polygon(self._model.slice_polygons[slice_idx], slice_displacement, desired_num_copies)
        self._ghost_objs = self._make_ghosts(self._ghost_slices)

        # Redraw
        self._canvas.redraw(True)

        # Pass on the event (e.g. so that we can update the mouse position in the status bar)
        event.Skip()

    def _on_left_mouse_button_up(self, event):
        # Check if user released a handle.
        if self._dragging:
            # The user released a slice handle that was being dragged.
            self._dragging = None

            # Remove ghosts
            self._remove_ghosts()

            # Remove handles on the template polygon. We're done replicating it anyway.
            self._remove_slice_handles()

            # Add temporary polygons to the model
            self._model.slice_polygons.extend(self._ghost_slices)

            # Update canvas
            self._canvas.set_slice_polygons(self._model.slice_polygons)

            # Redraw
            self._canvas.redraw(True)
            return

    def _remove_ghosts(self):
        self._canvas.remove_objects(self._ghost_objs)
        self._ghost_objs = []

    def _replicate_polygon(self, polygon, displacement, num_copies):
        return [[vertex + (i + 1) * displacement for vertex in polygon] for i in range(num_copies)]

    def _make_ghosts(self, ghost_polygons):
        ghost_slices = []  # TODO: should we assert that list is empty instead?
        for polygon in ghost_polygons:
            pts = [self._flipY(p) for p in polygon]
            h = self._canvas.Canvas.AddPolygon(pts, LineColor=NORMAL_COLOR, LineWidth=REGULAR_LINE_WIDTH, LineStyle='Dot')  # CHECKME: is there a constant for 'Dot' ?
            ghost_slices.append(h)
        return ghost_slices

    def _add_slice_handles(self, slices):
        self._handles = self._make_slice_handles(slices)
        self._bind_hover_events(self._handles)

    def _make_slice_handles(self, slices):
        handles = []
        for slice_idx in slices:
            polygon = self._model.slice_polygons[slice_idx]
            for vertex_idx, p in enumerate(polygon):
                p = self._flipY(p)
                h = self._canvas.Canvas.AddSquarePoint(p, Color=NORMAL_COLOR, Size=HANDLE_SIZE)
                handle = (h, slice_idx, vertex_idx)
                handles.append(handle)
        return handles

    def _flipY(self, p):  # flip y to convert from image coordinates (with y >= 0) back to canvas coords
        return p[0], -p[1]

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
        print('handle enter: set active handle to {}'.format(self._active_handle))
        self._canvas.redraw(True)

    def _handle_leave(self, object):
        """
        Called when the cursor moves away from an object handle (little square on a slice vertex)
        :param object: the floatcanvas object that the mouse moved away from (little square in our case)
        """
        # print("handle leave, object = {}".format(object.Name))
        object.SetColor(NORMAL_COLOR)
        self._active_handle = None
        self._canvas.redraw(True)

    def _parse_handle_name(self, handle):
        name = handle.Name  # name is for example 'PolygonHandle:2:3'
        chunks = name.split(':')
        slice_idx = int(chunks[1])
        vertex_idx = int(chunks[2])
        return handle, slice_idx, vertex_idx

