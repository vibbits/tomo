import wx
from wx.lib.floatcanvas import GUIMode

import resources

class MarkMode(GUIMode.GUIBase):
    # Mode label, shown in the tool bar.
    LABEL = "Mark"

    # Event types
    EVT_TYPE_TOMO_MARK_LEFT_DOWN = wx.NewEventType()
    EVT_TYPE_TOMO_MARK_MOTION = wx.NewEventType()

    # Event binders
    EVT_TOMO_MARK_LEFT_DOWN = wx.PyEventBinder(EVT_TYPE_TOMO_MARK_LEFT_DOWN)
    EVT_TOMO_MARK_MOTION = wx.PyEventBinder(EVT_TYPE_TOMO_MARK_MOTION)

    def __init__(self, canvas):
        GUIMode.GUIBase.__init__(self, canvas)
        self.Cursor = self.MakeMarkCursor()

    def MakeMarkCursor(self):
        img = resources.crosshair.GetImage()
        img.SetOption(wx.IMAGE_OPTION_CUR_HOTSPOT_X, 12)
        img.SetOption(wx.IMAGE_OPTION_CUR_HOTSPOT_Y, 12)
        return wx.Cursor(img)

    def OnLeftDown(self, event):
        # print('Mark tool: left mouse button down {} {}'.format(event, event.GetPosition()))
        EventType = self.EVT_TYPE_TOMO_MARK_LEFT_DOWN
        self.Canvas._RaiseMouseEvent(event, EventType)

    def OnMove(self, event):
        # print('Mark tool: mouse move {} {}'.format(event, event.GetPosition()))
        EventType = self.EVT_TYPE_TOMO_MARK_MOTION
        self.Canvas._RaiseMouseEvent(event, EventType)