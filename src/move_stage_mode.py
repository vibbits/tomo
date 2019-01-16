import wx

import resources
from base_mode import BaseMode

class MoveStageMode(BaseMode):
    # Mode label, shown in the tool bar.
    NAME = "Move Stage"

    # Event types
    EVT_TYPE_TOMO_MOVESTAGE_LEFT_DOWN = wx.NewEventType()
    EVT_TYPE_TOMO_MOVESTAGE_MOTION = wx.NewEventType()

    # Event binders
    EVT_TOMO_MOVESTAGE_LEFT_DOWN = wx.PyEventBinder(EVT_TYPE_TOMO_MOVESTAGE_LEFT_DOWN)
    EVT_TOMO_MOVESTAGE_MOTION = wx.PyEventBinder(EVT_TYPE_TOMO_MOVESTAGE_MOTION)

    def __init__(self, canvas=None):
        BaseMode.__init__(self, canvas)
        self.Cursor = self.MakeCursor(resources.movestage.GetImage(), 11, 23)

    def OnLeftDown(self, event):
        # print('Mark tool: left mouse button down {} {}'.format(event, event.GetPosition()))
        EventType = self.EVT_TYPE_TOMO_MOVESTAGE_LEFT_DOWN
        self.Canvas._RaiseMouseEvent(event, EventType)

    def OnMove(self, event):
        # print('Mark tool: mouse move {} {}'.format(event, event.GetPosition()))
        EventType = self.EVT_TYPE_TOMO_MOVESTAGE_MOTION
        self.Canvas._RaiseMouseEvent(event, EventType)
