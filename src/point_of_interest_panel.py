import wx
import mapping
from mark_mode import MarkMode
import tools

class PointOfInterestPanel(wx.Panel):
    _canvas = None
    _model = None

    # user interface
    done_button = None
    _poi_x_edit = None
    _poi_y_edit = None

    def __init__(self, parent, model, canvas):
        wx.Panel.__init__(self, parent, size=(350, -1))

        self._canvas = canvas
        self._model = model

        # Build the user interface
        title = wx.StaticText(self, wx.ID_ANY, "Point of interest")
        title.SetFont(wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.BOLD))
        separator = wx.StaticLine(self, wx.ID_ANY)

        self._poi_x_edit = wx.TextCtrl(self, wx.ID_ANY, "", size=(50, -1))
        self._poi_y_edit = wx.TextCtrl(self, wx.ID_ANY, "", size=(50, -1))
        self._poi_x_edit.SetEditable(False)
        self._poi_y_edit.SetEditable(False)

        poi_sizer = wx.BoxSizer(wx.HORIZONTAL)
        poi_sizer.Add(wx.StaticText(self, wx.ID_ANY, "Point of interest (image coordinates):"), flag = wx.ALIGN_CENTER_VERTICAL)
        poi_sizer.AddSpacer(5)
        poi_sizer.Add(self._poi_x_edit, flag=wx.ALIGN_CENTER_VERTICAL)
        poi_sizer.AddSpacer(5)
        poi_sizer.Add(self._poi_y_edit, flag=wx.ALIGN_CENTER_VERTICAL)
        poi_sizer.AddSpacer(5)

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
        contents.Add(poi_sizer, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, border=b)
        contents.Add(self.done_button, 0, wx.ALL | wx.CENTER, border=b)

        self.SetSizer(contents)
        contents.Fit(self)

    def activate(self):
        # Listen to mark tool mouse clicks so we can place the mark
        self._canvas.Canvas.Bind(MarkMode.EVT_TOMO_MARK_LEFT_DOWN, self._on_left_mouse_button_down)

    def deactivate(self):
        self._canvas.Canvas.Unbind(MarkMode.EVT_TOMO_MARK_LEFT_DOWN)

    def _update_poi(self, image_coords):
        # IMPROVEME: if image_coords is None, then show a label "No point of interest selected yet." instead of showing empty POI x/y coordinate boxes.
        x_val = "{:d}".format(image_coords[0]) if image_coords else ""
        y_val = "{:d}".format(image_coords[1]) if image_coords else ""
        self._poi_x_edit.SetValue(x_val)
        self._poi_y_edit.SetValue(y_val)

    def _on_left_mouse_button_down(self, event):
        canvas_coords = event.GetCoords()
        poi_coords = (int(round(canvas_coords[0])), -int(round(canvas_coords[1])))

        slices_hit = tools.polygons_hit(self._model.slice_polygons, poi_coords)
        if not slices_hit:
            print("No point of interest was selected. Please click inside a slice.") # IMPROVEME: show message in GUI - a message box? or a warning in the side panel?
            self._model.original_point_of_interest = None
            self._model.all_points_of_interest = []
        else:
            reference_slice_index = slices_hit[0]
            self._model.original_point_of_interest = poi_coords
            self._model.all_points_of_interest = self._predict_points_of_interest(poi_coords, reference_slice_index)

        # Show poi position numerically in ui
        self._update_poi(self._model.original_point_of_interest)

        # Draw the points of interest
        self._canvas.set_points_of_interest(self._model.all_points_of_interest)
        self._canvas.redraw()

    def _predict_points_of_interest(self, poi_coords, reference_slice_index):
        # Transform point-of-interest from one slice to the next
        # The reference_slice_index is the index of the slice in which the user specified the point-of-interest.
        # We will only predict points-of-interest in subsequent slices.

        original_point_of_interest = poi_coords
        slice_polygons = self._model.slice_polygons[reference_slice_index:]

        transformed_points_of_interest = mapping.repeatedly_transform_point(slice_polygons, original_point_of_interest)
        if not transformed_points_of_interest:
            print("An error occurred while calculating predicted points-of-interest.")  # IMPROVEME: display a warning message (e.g. in red) in the panel instead.

        return [original_point_of_interest] + transformed_points_of_interest

