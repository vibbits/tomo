import wx
from wx.lib.floatcanvas import GUIMode

import resources

class MoveStageMode(GUIMode.GUIBase):
    # Mode label, shown in the tool bar.
    NAME = "Move Stage"

    # Event types
    EVT_TYPE_TOMO_MOVESTAGE_LEFT_DOWN = wx.NewEventType()
    EVT_TYPE_TOMO_MOVESTAGE_MOTION = wx.NewEventType()

    # Event binders
    EVT_TOMO_MOVESTAGE_LEFT_DOWN = wx.PyEventBinder(EVT_TYPE_TOMO_MOVESTAGE_LEFT_DOWN)
    EVT_TOMO_MOVESTAGE_MOTION = wx.PyEventBinder(EVT_TYPE_TOMO_MOVESTAGE_MOTION)

    def __init__(self, canvas=None):
        GUIMode.GUIBase.__init__(self, canvas)
        self.Cursor = self.MakeMoveStageCursor()

    def MakeMoveStageCursor(self):
        img = resources.movestage.GetImage()
        hotspot_x = 11
        hotspot_y = 23
        if wx.Platform == '__WXMSW__':
            img.SetOption(wx.IMAGE_OPTION_CUR_HOTSPOT_X, hotspot_x)
            img.SetOption(wx.IMAGE_OPTION_CUR_HOTSPOT_Y, hotspot_y)
            return wx.Cursor(img)
        elif wx.Platform == '__WXGTK__':
            img.SetOptionInt(wx.IMAGE_OPTION_CUR_HOTSPOT_X, hotspot_x)
            img.SetOptionInt(wx.IMAGE_OPTION_CUR_HOTSPOT_Y, hotspot_y)
            return wx.CursorFromImage(img)
        else:
            return None

    def OnLeftDown(self, event):
        # print('Mark tool: left mouse button down {} {}'.format(event, event.GetPosition()))
        EventType = self.EVT_TYPE_TOMO_MOVESTAGE_LEFT_DOWN
        self.Canvas._RaiseMouseEvent(event, EventType)

    def OnMove(self, event):
        # print('Mark tool: mouse move {} {}'.format(event, event.GetPosition()))
        EventType = self.EVT_TYPE_TOMO_MOVESTAGE_MOTION
        self.Canvas._RaiseMouseEvent(event, EventType)
