import wx
from wx.lib.floatcanvas import GUIMode

import resources

class MoveStageMode(GUIMode.GUIBase):
    # Mode label, shown in the tool bar.
    LABEL = "Move Stage"

    # Event types
    EVT_TYPE_TOMO_MOVESTAGE_LEFT_DOWN = wx.NewEventType()
    EVT_TYPE_TOMO_MOVESTAGE_MOTION = wx.NewEventType()

    # Event binders
    EVT_TOMO_MOVESTAGE_LEFT_DOWN = wx.PyEventBinder(EVT_TYPE_TOMO_MOVESTAGE_LEFT_DOWN)
    EVT_TOMO_MOVESTAGE_MOTION = wx.PyEventBinder(EVT_TYPE_TOMO_MOVESTAGE_MOTION)

    def __init__(self, canvas):
        GUIMode.GUIBase.__init__(self, canvas)
        self.Cursor = self.MakeMoveStageCursor()

    def MakeMoveStageCursor(self):
        img = resources.movestage.GetImage()
        img.SetOption(wx.IMAGE_OPTION_CUR_HOTSPOT_X, 11)
        img.SetOption(wx.IMAGE_OPTION_CUR_HOTSPOT_Y, 23)
        return wx.Cursor(img)

    def OnLeftDown(self, event):
        # print('Mark tool: left mouse button down {} {}'.format(event, event.GetPosition()))
        EventType = self.EVT_TYPE_TOMO_MOVESTAGE_LEFT_DOWN
        self.Canvas._RaiseMouseEvent(event, EventType)

    def OnMove(self, event):
        # print('Mark tool: mouse move {} {}'.format(event, event.GetPosition()))
        EventType = self.EVT_TYPE_TOMO_MOVESTAGE_MOTION
        self.Canvas._RaiseMouseEvent(event, EventType)