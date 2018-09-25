# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx
from wx.lib.floatcanvas import NavCanvas, FloatCanvas

class OverviewPanel(NavCanvas.NavCanvas):  # TODO: rename to OverviewPanel or so, it has rather dedicated methods dealing with POIs and slices
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

    def add_slice_outlines(self, slice_outlines):
        for outline in slice_outlines:
            pts = [(p[0], -p[1]) for p in outline]
            self.Canvas.AddPolygon(pts, LineColor = "Green")

    # The first point is user-specified, drawn in green.
    # The other points are calculated, drawn in red.
    def add_points_of_interest(self, points_of_interest):
        pts = [(p[0], -p[1]) for p in points_of_interest]
        self._add_cross(pts[0], line_color = "Green")
        for pt in pts[1:]:
            self._add_cross(pt, line_color = "Red")

    def _add_cross(self, pt, line_color, size = 25):
        self.Canvas.AddLine([(pt[0] - size, pt[1]), (pt[0] + size, pt[1])], LineColor = line_color)
        self.Canvas.AddLine([(pt[0], pt[1] - size), (pt[0], pt[1] + size)], LineColor = line_color)

    def zoom_to_fit(self):
        self.Canvas.ZoomToBB()

    def redraw(self):
        self.Canvas.Draw()