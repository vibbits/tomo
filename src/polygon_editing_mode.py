import wx
from base_mode import BaseMode

class PolygonEditingMode(BaseMode):
    # Mode label, shown in the tool bar.
    NAME = "Polygon Editing"

    # Event types
    EVT_TYPE_TOMO_POLY_EDIT_LEFT_UP = wx.NewEventType()
    EVT_TYPE_TOMO_POLY_EDIT_LEFT_DOWN = wx.NewEventType()
    EVT_TYPE_TOMO_POLY_EDIT_MOTION = wx.NewEventType()

    # Event binders
    EVT_TOMO_POLY_EDIT_LEFT_UP = wx.PyEventBinder(EVT_TYPE_TOMO_POLY_EDIT_LEFT_UP)
    EVT_TOMO_POLY_EDIT_LEFT_DOWN = wx.PyEventBinder(EVT_TYPE_TOMO_POLY_EDIT_LEFT_DOWN)
    EVT_TOMO_POLY_EDIT_MOTION = wx.PyEventBinder(EVT_TYPE_TOMO_POLY_EDIT_MOTION)

    def __init__(self, canvas=None):
        BaseMode.__init__(self, canvas)
        self.Cursor = wx.NullCursor  # use regular arrow cursor

    def OnLeftUp(self, event):
        # print('Polygon editing tool: left mouse button up {} {}; canvas={}'.format(event, event.GetPosition(), self.Canvas))
        EventType = self.EVT_TYPE_TOMO_POLY_EDIT_LEFT_UP
        self.Canvas._RaiseMouseEvent(event, EventType)

    def OnLeftDown(self, event):
        # print('Polygon editing tool: left mouse button down {} {}'.format(event, event.GetPosition()))
        EventType = self.EVT_TYPE_TOMO_POLY_EDIT_LEFT_DOWN
        self.Canvas._RaiseMouseEvent(event, EventType)

    def OnMove(self, event):
        # print('Polygon editing tool: mouse move {} {}'.format(event, event.GetPosition()))

        # Process enter and leave events
        # (see wx.lib.floatcanvas.GUIMode source code)
        self.Canvas.MouseOverTest(event)

        EventType = self.EVT_TYPE_TOMO_POLY_EDIT_MOTION
        self.Canvas._RaiseMouseEvent(event, EventType)
