import wx
import mapping
from mark_mode import MarkMode
from constants import POINTER_MODE_NAME
import tools

class PointOfInterestPanel(wx.Panel):
    _canvas = None
    _model = None
    _num_pois = 0
    _predicted_pois = []

    # user interface
    done_button = None
    _poi_label = None
    _num_pois_edit = None

    def __init__(self, parent, model, canvas):
        wx.Panel.__init__(self, parent, size=(350, -1))

        self._canvas = canvas
        self._model = model

        # Build the user interface
        title = wx.StaticText(self, wx.ID_ANY, "Point of interest")
        title.SetFont(wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.BOLD))
        separator = wx.StaticLine(self, wx.ID_ANY)

        self._poi_label = wx.StaticText(self, wx.ID_ANY, "")
        self._update_poi(self._model.original_point_of_interest)

        num_pois_label = wx.StaticText(self, wx.ID_ANY, "Number of slices:")  # CHECKME: should we use 'section' or 'slice' as terminology?
        self._num_pois_edit = wx.TextCtrl(self, wx.ID_ANY, str(self._num_pois), size=(50, -1), style=wx.TE_PROCESS_ENTER)
        self._num_pois_edit.Bind(wx.EVT_KEY_DOWN, self._on_num_pois_key_down)
        self._num_pois_edit.Bind(wx.EVT_KILL_FOCUS, self._on_num_pois_focus_lost)

        poi_sizer = wx.BoxSizer(wx.HORIZONTAL)
        poi_sizer.Add(wx.StaticText(self, wx.ID_ANY, "POI (image coordinates):"), flag=wx.ALIGN_CENTER_VERTICAL)
        poi_sizer.AddSpacer(5)
        poi_sizer.Add(self._poi_label)

        num_pois_sizer = wx.BoxSizer(wx.HORIZONTAL)
        num_pois_sizer.Add(num_pois_label, flag=wx.ALIGN_CENTER_VERTICAL)
        num_pois_sizer.AddSpacer(5)
        num_pois_sizer.Add(self._num_pois_edit, flag=wx.ALIGN_CENTER_VERTICAL)

        instructions_label = wx.StaticText(self, wx.ID_ANY, ("Use the Mark tool (+) to specify the point of interest inside any slice. "
                                                             "This point and predicted analogous points in the other slices will be marked with a red cross."))
        w = 330
        instructions_label.Wrap(w)  # force line wrapping

        button_size = (125, -1)
        self.done_button = wx.Button(self, wx.ID_ANY, "Done", size=button_size)  # The ApplicationFame will listen to clicks on this button.

        b = 5  # border size
        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(title, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(separator, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(instructions_label, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(poi_sizer, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND, border=b)
        contents.Add(num_pois_sizer, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND, border=b)
        contents.Add(self.done_button, 0, wx.ALL | wx.CENTER, border=b)

        self.SetSizer(contents)
        contents.Fit(self)

    def activate(self):
        self._canvas.Activate(MarkMode.NAME)

        # Listen to mark tool mouse clicks so we can place the mark
        self._canvas.Canvas.Bind(MarkMode.EVT_TOMO_MARK_LEFT_DOWN, self._on_left_mouse_button_down)

    def deactivate(self):
        self._canvas.Deactivate(MarkMode.NAME)
        self._canvas.Activate(POINTER_MODE_NAME)

        self._canvas.Canvas.Unbind(MarkMode.EVT_TOMO_MARK_LEFT_DOWN)

    def _on_num_pois_key_down(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_RETURN or keycode == wx.WXK_NUMPAD_ENTER or keycode == wx.WXK_TAB:
            self._handle_num_pois_change()
            event.EventObject.Navigate()
        event.Skip()

    def _on_num_pois_focus_lost(self, event):
        self._handle_num_pois_change()
        event.Skip()

    def _handle_num_pois_change(self):
        val = self._num_pois_edit.GetValue()
        if val.isdigit():
            new_num_pois = int(val)
            valid_change = (new_num_pois != self._num_pois) and (new_num_pois > 0) and (new_num_pois <= len(self._predicted_pois))
            if valid_change:
                self._num_pois = new_num_pois
                self._model.all_points_of_interest = self._predicted_pois[:new_num_pois]
                self._update_ui()
                return

        # The number of pois edit field either contains a string that is not an integer,
        # or it contains an integer that is not in the allowed range,
        # so we reset the edit field back to the last correct value.
        self._update_num_pois()

    def _update_ui(self):
        self._update_num_pois()

        # Show poi position numerically in ui
        self._update_poi(self._model.original_point_of_interest)

        # Draw the points of interest
        self._canvas.set_points_of_interest(self._model.all_points_of_interest)
        self._canvas.redraw()

    def _update_poi(self, image_coords):
        txt = 'x={:d} y={:d}'.format(image_coords[0], image_coords[1]) if image_coords else 'not yet specified'
        self._poi_label.SetLabelText(txt)

    def _update_num_pois(self):
        self._num_pois_edit.SetValue(str(self._num_pois))

    def _on_left_mouse_button_down(self, event):
        canvas_coords = event.GetCoords()
        poi_coords = (int(round(canvas_coords[0])), -int(round(canvas_coords[1])))

        slices_hit = tools.polygons_hit(self._model.slice_polygons, poi_coords)
        if not slices_hit:
            print("No point of interest was selected. Please click inside a slice.") # IMPROVEME: show message in GUI - a message box? or a warning in the side panel?
            self._model.original_point_of_interest = None
            self._predicted_pois = []
            self._num_pois = 0
        else:
            reference_slice_index = slices_hit[0]
            self._model.original_point_of_interest = poi_coords
            self._predicted_pois = self._predict_points_of_interest(poi_coords, reference_slice_index)
            if self._num_pois == 0:
                self._num_pois = len(self._predicted_pois)
            else:
                self._num_pois = min(self._num_pois, len(self._predicted_pois))

        self._model.all_points_of_interest = self._predicted_pois[:self._num_pois]

        # Update UI
        self._update_ui()

    def _predict_points_of_interest(self, poi_coords, reference_slice_index):
        # Transform point-of-interest from one slice to the next
        # The reference_slice_index is the index of the slice in which the user specified the point-of-interest.
        # We will only predict points-of-interest in subsequent slices.

        original_point_of_interest = poi_coords
        slice_polygons = self._model.slice_polygons[reference_slice_index:]

        transformed_points_of_interest = mapping.repeatedly_transform_point(slice_polygons, original_point_of_interest)
        if transformed_points_of_interest is None:
            print("An error occurred while calculating predicted points-of-interest.")  # IMPROVEME: display a warning message (e.g. in red) in the panel instead.

        return [original_point_of_interest] + transformed_points_of_interest

