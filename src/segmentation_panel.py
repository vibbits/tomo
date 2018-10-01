# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx
from wx.lib.floatcanvas import NavCanvas, FloatCanvas

class SegmentationPanel(NavCanvas.NavCanvas):
    _poi_lines = []
    def __init__(self, parent):
        NavCanvas.NavCanvas.__init__(self, parent)
        wx.CallAfter(self.Canvas.ZoomToBB) # so it will get called after everything is created and sized

    def add_image(self, filename):
        print('Loading ' + filename)
        image = wx.Image(filename)
        img = FloatCanvas.ScaledBitmap2(image,
                                        (0,0),
                                        Height = image.GetHeight(),
                                        Position = 'tl')
        self.Canvas.AddObject(img)

    def add_polygon(self, outline, line_color, line_width):
        pts = [(p[0], -p[1]) for p in outline]
        self.Canvas.AddPolygon(pts, LineColor = line_color, LineWidth = line_width)

    def add_text(self, text, position, text_color, font_size):
        # http://docs.huihoo.com/wxpython/2.8.3.0/api/wx.lib.floatcanvas.FloatCanvas.FloatCanvas-class.html#addshape
        self.Canvas.AddScaledText(text, (position[0], -position[1]), Position = "cc", Color = text_color, Size = font_size)

    def zoom_to_fit(self):
        self.Canvas.ZoomToBB()

    def redraw(self):
        self.Canvas.Draw()