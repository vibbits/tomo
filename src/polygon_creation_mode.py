import wx
from wx.lib.floatcanvas import GUIMode

class PolygonCreationMode(GUIMode.GUIBase):
    # Mode label, shown in the tool bar.
    NAME = "Polygon Creation"

    # Event types
    EVT_TYPE_TOMO_POLY_CREATE_LEFT_UP = wx.NewEventType()
    EVT_TYPE_TOMO_POLY_CREATE_RIGHT_UP = wx.NewEventType()
    EVT_TYPE_TOMO_POLY_CREATE_MOTION = wx.NewEventType()

    # Event binders
    EVT_TOMO_POLY_CREATE_LEFT_UP = wx.PyEventBinder(EVT_TYPE_TOMO_POLY_CREATE_LEFT_UP)
    EVT_TOMO_POLY_CREATE_RIGHT_UP = wx.PyEventBinder(EVT_TYPE_TOMO_POLY_CREATE_RIGHT_UP)
    EVT_TOMO_POLY_CREATE_MOTION = wx.PyEventBinder(EVT_TYPE_TOMO_POLY_CREATE_MOTION)

    def __init__(self, canvas=None):
        GUIMode.GUIBase.__init__(self, canvas)
        self.Cursor = self.MakePolygonCreationCursor()

    def MakePolygonCreationCursor(self):
        return wx.NullCursor  # FIXME This must be a different cursor!

    def OnLeftUp(self, event):
        # print('Polygon creation tool: left mouse button up {} {}'.format(event, event.GetPosition()))
        EventType = self.EVT_TYPE_TOMO_POLY_CREATE_LEFT_UP
        self.Canvas._RaiseMouseEvent(event, EventType)

    def OnRightUp(self, event):
        # print('Polygon creation tool: right mouse button up {} {}'.format(event, event.GetPosition()))
        EventType = self.EVT_TYPE_TOMO_POLY_CREATE_RIGHT_UP
        self.Canvas._RaiseMouseEvent(event, EventType)

    def OnMove(self, event):
        # print('Polygon creation tool: mouse move {} {}'.format(event, event.GetPosition()))

        # Process enter and leave events
        # (see wx.lib.floatcanvas.GUIMode source code)
        self.Canvas.MouseOverTest(event)

        EventType = self.EVT_TYPE_TOMO_POLY_CREATE_MOTION
        self.Canvas._RaiseMouseEvent(event, EventType)
