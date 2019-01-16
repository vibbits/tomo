import wx
from polygon_selection_mode import PolygonSelectionMode
from polygon_creation_mode import PolygonCreationMode
from polygon_editor_mixin import PolygonEditorMixin
from polygon_creator_mixin import PolygonCreatorMixin
from constants import POINTER_MODE_NAME

# TODO? add support for re-ordering slices? (e.g. by dragging the mouse cursor in one long sweep over each slice in the correct order)

# IMPROVEME: factor out all general "side panel" code (so for the title, separator line, optional instruction text, an optional panel with more widget and a done button)


class PolygonEditorPanel(wx.Panel):

    done_button = None

    def __init__(self, parent, model, canvas):
        wx.Panel.__init__(self, parent, size=(350, -1), style=wx.WANTS_CHARS)  # WANTS_CHARS is needed so we can detect when DEL is pressed for deleting a slice

        self._canvas = canvas
        self._editor = PolygonEditorMixin(model, canvas)
        self._creator = PolygonCreatorMixin(model, canvas)

        # Build the user interface
        title = wx.StaticText(self, wx.ID_ANY, "Polygon Editor")
        title.SetFont(wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.BOLD))
        separator = wx.StaticLine(self, wx.ID_ANY)

        instructions_label1 = wx.StaticText(self, wx.ID_ANY, ("Use the Polygon Selection tool to edit the position of the vertices of an existing polygon, or to delete a polygon altogether. "))
        instructions_label2 = wx.StaticText(self, wx.ID_ANY, ("Use the Polygon Creation tool to draw a completely new polygon. Start at the bottom left corner of the slice and add vertices counter-clockwise."))

        # Force line wrapping
        w = 330
        instructions_label1.Wrap(w)
        instructions_label2.Wrap(w)

        button_size = (125, -1)
        self.done_button = wx.Button(self, wx.ID_ANY, "Done", size=button_size)  # The ApplicationFame will listen to clicks on this button.

        b = 5  # border size
        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(title, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(separator, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(instructions_label1, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(instructions_label2, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(self.done_button, 0, wx.ALL | wx.CENTER, border=b)

        self.SetSizer(contents)
        contents.Fit(self)

    def activate(self):
        # print('Polygon editor panel: activate')
        self._canvas.Activate(PolygonSelectionMode.NAME)
        self._canvas.EnableTool(PolygonCreationMode.NAME, True)
        self._editor.start()
        self._creator.start()

    def deactivate(self):
        # print('Polygon editor panel: deactivate')
        self._canvas.Deactivate(PolygonSelectionMode.NAME)
        self._canvas.Deactivate(PolygonCreationMode.NAME)
        self._canvas.Activate(POINTER_MODE_NAME)
        self._editor.stop()
        self._creator.stop()
