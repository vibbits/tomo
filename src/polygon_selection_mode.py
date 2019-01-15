import wx
from wx.lib.floatcanvas import GUIMode

class PolygonSelectionMode(GUIMode.GUIBase):
    # Mode label, shown in the tool bar.
    NAME = "Polygon Selection"

    # Event types
    EVT_TYPE_TOMO_POLY_SELECT_LEFT_UP = wx.NewEventType()
    EVT_TYPE_TOMO_POLY_SELECT_LEFT_DOWN = wx.NewEventType()
    EVT_TYPE_TOMO_POLY_SELECT_MOTION = wx.NewEventType()

    # Event binders
    EVT_TOMO_POLY_SELECT_LEFT_UP = wx.PyEventBinder(EVT_TYPE_TOMO_POLY_SELECT_LEFT_UP)
    EVT_TOMO_POLY_SELECT_LEFT_DOWN = wx.PyEventBinder(EVT_TYPE_TOMO_POLY_SELECT_LEFT_DOWN)
    EVT_TOMO_POLY_SELECT_MOTION = wx.PyEventBinder(EVT_TYPE_TOMO_POLY_SELECT_MOTION)

    def __init__(self, canvas=None):
        GUIMode.GUIBase.__init__(self, canvas)
        self.Cursor = self.MakePolygonSelectionCursor()

    def MakePolygonSelectionCursor(self):
        return wx.NullCursor  # TODO: design a custom cursor for this operation.

    def OnLeftUp(self, event):
        # print('Polygon selection tool: left mouse button up {} {}; canvas={}'.format(event, event.GetPosition(), self.Canvas))
        EventType = self.EVT_TYPE_TOMO_POLY_SELECT_LEFT_UP
        self.Canvas._RaiseMouseEvent(event, EventType)

    def OnLeftDown(self, event):
        # print('Polygon selection tool: left mouse button down {} {}'.format(event, event.GetPosition()))
        EventType = self.EVT_TYPE_TOMO_POLY_SELECT_LEFT_DOWN
        self.Canvas._RaiseMouseEvent(event, EventType)

    def OnMove(self, event):
        # print('Polygon selection tool: mouse move {} {}'.format(event, event.GetPosition()))

        # Process enter and leave events
        # (see wx.lib.floatcanvas.GUIMode source code)
        self.Canvas.MouseOverTest(event)

        EventType = self.EVT_TYPE_TOMO_POLY_SELECT_MOTION
        self.Canvas._RaiseMouseEvent(event, EventType)
