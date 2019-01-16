import wx
from base_mode import BaseMode

import resources

class PolygonCreationMode(BaseMode):
    # Mode label, shown in the tool bar.
    NAME = "Polygon Creation"

    # Event types
    EVT_TYPE_TOMO_POLY_CREATE_LEFT_UP = wx.NewEventType()
    EVT_TYPE_TOMO_POLY_CREATE_LEFT_DOWN = wx.NewEventType()
    EVT_TYPE_TOMO_POLY_CREATE_MOTION = wx.NewEventType()

    # Event binders
    EVT_TOMO_POLY_CREATE_LEFT_UP = wx.PyEventBinder(EVT_TYPE_TOMO_POLY_CREATE_LEFT_UP)
    EVT_TOMO_POLY_CREATE_LEFT_DOWN = wx.PyEventBinder(EVT_TYPE_TOMO_POLY_CREATE_LEFT_DOWN)
    EVT_TOMO_POLY_CREATE_MOTION = wx.PyEventBinder(EVT_TYPE_TOMO_POLY_CREATE_MOTION)

    def __init__(self, canvas=None):
        BaseMode.__init__(self, canvas)
        self.Cursor = self.MakeCursor(resources.crosshair.GetImage(), 12, 12)  # TODO: use dedicated tool cursor instead

    def OnLeftUp(self, event):
        print('Polygon creation tool: left mouse button up {} {}; canvas={}'.format(event, event.GetPosition(), self.Canvas))
        EventType = self.EVT_TYPE_TOMO_POLY_CREATE_LEFT_UP
        self.Canvas._RaiseMouseEvent(event, EventType)

    def OnLeftDown(self, event):
        # print('Polygon creation tool: left mouse button down {} {}'.format(event, event.GetPosition()))
        EventType = self.EVT_TYPE_TOMO_POLY_CREATE_LEFT_DOWN
        self.Canvas._RaiseMouseEvent(event, EventType)

    def OnMove(self, event):
        # print('Polygon creation tool: mouse move {} {}'.format(event, event.GetPosition()))

        # Process enter and leave events
        # (see wx.lib.floatcanvas.GUIMode source code)
        self.Canvas.MouseOverTest(event)

        EventType = self.EVT_TYPE_TOMO_POLY_CREATE_MOTION
        self.Canvas._RaiseMouseEvent(event, EventType)
