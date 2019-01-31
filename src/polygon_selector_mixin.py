import wx
import tools
from polygon_selection_mode import PolygonSelectionMode
from constants import REGULAR_LINE_WIDTH, HIGHLIGHTED_LINE_WIDTH
import numpy as np

# IMPROVEME: add ability to interactively extend the selection with additional slices
# IMPROVEME: add ability to interactively de-select specific slices
# IMPROVEME: do a select all slices if ctrl-a is pressed

class PolygonSelectorMixin:
    def __init__(self, model, canvas):
        self._model = model
        self._canvas = canvas

        self._selection_rect = None  # FloatCanvas handle of the selection rectangle that is being dragged
        self._selected_slices = []  # indices (in self._model.slice_polygons) of the slices that are completely inside self._selection_rect

    def get_selected_slices(self):  # returns a list with the indices of the selected slices (indices in model.slice_polygons[])
        return self._selected_slices

    def set_selected_slices(self, selected_slices):  # a list with indices of the (only) slices that need to be set in the selected state
        self._remove_selection_rectangle()
        self._update_selected_slices(selected_slices)

    def start(self):
        self._canvas.Bind(PolygonSelectionMode.EVT_TOMO_POLY_SELECT_MOTION, self._on_mouse_move)
        self._canvas.Bind(PolygonSelectionMode.EVT_TOMO_POLY_SELECT_LEFT_DOWN, self._on_left_mouse_button_down)
        self._canvas.Bind(PolygonSelectionMode.EVT_TOMO_POLY_SELECT_LEFT_UP, self._on_left_mouse_button_up)
        self._canvas.Bind(wx.EVT_CHAR_HOOK, self._key_pressed)
        self._canvas.Canvas.Bind(wx.EVT_LEAVE_WINDOW, self._on_leave_canvas)

    def stop(self):
        self._canvas.Unbind(PolygonSelectionMode.EVT_TOMO_POLY_SELECT_MOTION)
        self._canvas.Unbind(PolygonSelectionMode.EVT_TOMO_POLY_SELECT_LEFT_DOWN)
        self._canvas.Unbind(PolygonSelectionMode.EVT_TOMO_POLY_SELECT_LEFT_UP)
        self._canvas.Unbind(wx.EVT_CHAR_HOOK)
        self._canvas.Canvas.Unbind(wx.EVT_LEAVE_WINDOW)

        self._remove_selection_rectangle()

    def _key_pressed(self, event):
        key = event.GetKeyCode()
        print('polygon selector: keydown key={} shiftDown={} ctrldown={} cmdDown={} altdown={}'.format(key, event.shiftDown, event.controlDown,
                                                                                                       event.cmdDown, event.altDown))
        if key == wx.WXK_DELETE or key == wx.WXK_NUMPAD_DELETE:
            # Delete the selected slices

            assert self._selection_rect is None  # FIXME: what happens if we press DEL while we are still dragging the selection rectangle...?

            if self._selected_slices is None:
                return

            # Keep only those slices in the model that are not selected for deletion
            num_polygons = len(self._model.slice_polygons)
            slices_to_keep = [i for i in range(num_polygons) if i not in self._selected_slices]
            self._model.slice_polygons = [self._model.slice_polygons[i] for i in slices_to_keep]

            # Remove slices from canvas
            self._canvas.set_slice_polygons(self._model.slice_polygons)

            # Update state
            self._selected_slices = []

            # Redraw
            self._canvas.redraw(True)

        elif key == wx.WXK_ESCAPE:
            # Deselect all
            self.set_selected_slices([])
            self._canvas.redraw(True)

        elif key == 65 and event.controlDown and not event.shiftDown:  # IMPROVEME: can this be written down cleaner? Using wx.KeyboardState or so? And get rid of the hard-coded 'A' value
            # CTRL-A pressed, select all
            total_num_slices = len(self._model.slice_polygons)
            self.set_selected_slices([i for i in range(total_num_slices)])
            self._canvas.redraw(True)

    def _on_leave_canvas(self, event):
        if self._selection_rect is None:
            event.Skip()
            return

        # Cancel the selection. This is necessary because if the mouse is outside the canvas, we also
        # do not receive mouse events anymore. So the mouse button may become up without us knowing. This then breaks
        # our mouse handling logic.

        # Remove selection rectangle
        self._remove_selection_rectangle()

        self._canvas.redraw(True)
        event.Skip()

    def _on_left_mouse_button_down(self, event):
        start_pos = event.GetCoords()
        wh = (1, 1)
        self._selection_rect = self._canvas.Canvas.AddRectangle(start_pos, wh, LineColor='BLACK', LineStyle='Dot')

    def _on_left_mouse_button_up(self, event):
        # Check for special case where mouse travelled outside the canvas and we cancelled the selection before
        # the mouse button came up.
        if self._selection_rect is None:
            return

        # Normally the selected polygons are updated during move events,
        # but we also need to update them if the user simply clicked somewhere (without mouse movement),
        # because then we need to deselect any selected slices.
        self._update_selection(event)

        # Remove selection rectangle
        self._remove_selection_rectangle()

        self._canvas.redraw(True)

    def _on_mouse_move(self, event):
        if self._selection_rect:
            self._update_selection(event)
            self._canvas.redraw(True)
        event.Skip()

    def _remove_selection_rectangle(self):
        if self._selection_rect:
            self._canvas.remove_objects([self._selection_rect])
            self._selection_rect = None

    def _update_selection(self, event):
        # Update the dotted selection rectangle on the canvas
        pos = event.GetCoords()
        start_pos = self._selection_rect.XY
        wh = (pos[0] - start_pos[0], pos[1] - start_pos[1])
        self._selection_rect.WH = wh

        # Check which slices are inside the selection rectangle, and draw them in a special line style
        # to indicate that they are selected.

        end_pos = (start_pos[0] + wh[0], start_pos[1] + wh[1])

        # Flip y coordinate: the slice polygons in model are in image coordinates, whereas our rect was in canvas coordinates
        start_pos = (start_pos[0], -start_pos[1])
        end_pos = (end_pos[0], -end_pos[1])

        rect = (np.array(start_pos), np.array(end_pos))
        new_selected_slices = self._find_slices_inside_rect(rect)

        self._update_selected_slices(new_selected_slices)

    def _update_selected_slices(self, new_selected_slices):
        for i in self._selected_slices:
            self._canvas.set_slice_outline_linewidth(i, REGULAR_LINE_WIDTH)

        for i in new_selected_slices:
            self._canvas.set_slice_outline_linewidth(i, HIGHLIGHTED_LINE_WIDTH)

        self._selected_slices = new_selected_slices

    def _find_slices_inside_rect(self, rect):
        slices = self._model.slice_polygons
        return [i for i in range(len(slices)) if tools.is_polygon_inside_rect(slices[i], rect)]

