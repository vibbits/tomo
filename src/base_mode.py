import wx
from wx.lib.floatcanvas import GUIMode

class BaseMode(GUIMode.GUIBase):

    def __init__(self, canvas):
        GUIMode.GUIBase.__init__(self, canvas)

    def MakeCursor(self, img, hotspot_x, hotspot_y):
        phoenix = wx.__version__[0] == '4'
        if phoenix:
            # Options can be set to an integer as well as to a string value with SetOption().
            # There is no SetOptionInt() anymore.
            img.SetOption(wx.IMAGE_OPTION_CUR_HOTSPOT_X, hotspot_x)
            img.SetOption(wx.IMAGE_OPTION_CUR_HOTSPOT_Y, hotspot_y)
            return wx.Cursor(img)
        else:
            # wxPython classic, integer value options must be set via SetOptionInt().
            img.SetOptionInt(wx.IMAGE_OPTION_CUR_HOTSPOT_X, hotspot_x)
            img.SetOptionInt(wx.IMAGE_OPTION_CUR_HOTSPOT_Y, hotspot_y)
            return wx.CursorFromImage(img)

