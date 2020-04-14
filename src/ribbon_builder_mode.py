import wx
from base_mode import BaseMode

class RibbonBuilderMode(BaseMode):
    # Mode label, shown in the tool bar.
    NAME = "Ribbon Builder"

    # Event types
    EVT_TYPE_TOMO_RIBBON_BUILDER_LEFT_DOWN = wx.NewEventType()
    EVT_TYPE_TOMO_RIBBON_BUILDER_LEFT_UP = wx.NewEventType()
    EVT_TYPE_TOMO_RIBBON_BUILDER_RIGHT_UP = wx.NewEventType()
    EVT_TYPE_TOMO_RIBBON_BUILDER_MOTION = wx.NewEventType()

    # Event binders
    EVT_TOMO_RIBBON_BUILDER_LEFT_DOWN = wx.PyEventBinder(EVT_TYPE_TOMO_RIBBON_BUILDER_LEFT_DOWN)
    EVT_TOMO_RIBBON_BUILDER_LEFT_UP = wx.PyEventBinder(EVT_TYPE_TOMO_RIBBON_BUILDER_LEFT_UP)
    EVT_TOMO_RIBBON_BUILDER_RIGHT_UP = wx.PyEventBinder(EVT_TYPE_TOMO_RIBBON_BUILDER_RIGHT_UP)
    EVT_TOMO_RIBBON_BUILDER_MOTION = wx.PyEventBinder(EVT_TYPE_TOMO_RIBBON_BUILDER_MOTION)

    def __init__(self, canvas=None):
        BaseMode.__init__(self, canvas)
        self.Cursor = wx.NullCursor  # use regular arrow cursor

    def OnLeftDown(self, event):
        # print('Ribbon builder tool: left mouse button down {} {}'.format(event, event.GetPosition()))
        EventType = self.EVT_TYPE_TOMO_RIBBON_BUILDER_LEFT_DOWN
        self.Canvas._RaiseMouseEvent(event, EventType)

    def OnLeftUp(self, event):
        # print('Ribbon builder tool: left mouse button up {} {}'.format(event, event.GetPosition()))
        EventType = self.EVT_TYPE_TOMO_RIBBON_BUILDER_LEFT_UP
        self.Canvas._RaiseMouseEvent(event, EventType)

    def OnRightUp(self, event):
        # print('Ribbon builder tool: right mouse button up {} {}'.format(event, event.GetPosition()))
        EventType = self.EVT_TYPE_TOMO_RIBBON_BUILDER_RIGHT_UP
        self.Canvas._RaiseMouseEvent(event, EventType)

    def OnMove(self, event):
        # print('Ribbon builder tool: mouse move {} {}'.format(event, event.GetPosition()))

        # Process enter and leave events
        # (see wx.lib.floatcanvas.GUIMode source code)
        self.Canvas.MouseOverTest(event)

        EventType = self.EVT_TYPE_TOMO_RIBBON_BUILDER_MOTION
        self.Canvas._RaiseMouseEvent(event, EventType)
