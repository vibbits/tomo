import wx
from wx.lib.floatcanvas import GUIMode

import resources

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

    def __init__(self, canvas):
        GUIMode.GUIBase.__init__(self, canvas)
        self.Cursor = self.MakePolygonSelectionCursor()

    def MakePolygonSelectionCursor(self):
        img = resources.crosshair.GetImage()   # FIXME This must be a different cursor!
        hotspot_x = 12
        hotspot_y = 12
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

    def OnLeftUp(self, event):
        # print('Polygon selection tool: left mouse button up {} {}'.format(event, event.GetPosition()))
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
