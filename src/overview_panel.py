# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx
from wx.lib.floatcanvas import NavCanvas, FloatCanvas
from polygon_editor import PolygonEditor

class OverviewPanel(NavCanvas.NavCanvas):
    _poi_lines = []
    _slice_outlines = []
    _image = None

    # PROTOTYPE - for polygon editing
    _polygon_editor = None
    # END PROTOTYPE

    def __init__(self, parent):
        NavCanvas.NavCanvas.__init__(self, parent)
        # PROTOTYPE - for polygon editing
        # _polygon_editor = PolygonEditor(self.Canvas)
        # END PROTOTYPE
        wx.CallAfter(self.Canvas.ZoomToBB) # so it will get called after everything is created and sized

    def set_image(self, filename):
        print('Loading ' + filename)
        image = wx.Image(filename)
        img = FloatCanvas.ScaledBitmap2(image,
                                        (0,0),
                                        Height = image.GetHeight(),
                                        Position = 'tl')
        if self._image != None:
            self._remove_image()
        self._image = self.Canvas.AddObject(img)

    def _remove_image(self):
        self.Canvas.RemoveObject(self._image)
        self._image = None

    def set_slice_outlines(self, slice_outlines):
        # Add previous slice outlines (if any)
        if self._slice_outlines:
            self._remove_slice_outlines()
        # Add new slice outlines
        for outline in slice_outlines:
            pts = [(p[0], -p[1]) for p in outline]
            polygon = self.Canvas.AddPolygon(pts, LineColor = "Green")
            self._slice_outlines.append(polygon)

    def _remove_slice_outlines(self):
        for polygon in self._slice_outlines:
            self.Canvas.RemoveObject(polygon)
        self._slice_outlines = []

    # The first point is user-specified, drawn in green.
    # The other points are calculated, drawn in red.
    def set_points_of_interest(self, points_of_interest):
        # Remove old POIs (if any)
        if self._poi_lines:
            self._remove_points_of_interest();
        # Add new POIs
        pts = [(p[0], -p[1]) for p in points_of_interest]
        self._add_cross(pts[0], line_color = "Green")
        for pt in pts[1:]:
            self._add_cross(pt, line_color = "Red")

    def _remove_points_of_interest(self):
        for line in self._poi_lines:
            self.Canvas.RemoveObject(line)
        self._poi_lines = []

    def _add_cross(self, pt, line_color, size = 25):
        line1 = self.Canvas.AddLine([(pt[0] - size, pt[1]), (pt[0] + size, pt[1])], LineColor = line_color)
        line2 = self.Canvas.AddLine([(pt[0], pt[1] - size), (pt[0], pt[1] + size)], LineColor = line_color)
        self._poi_lines.append(line1)
        self._poi_lines.append(line2)

    def zoom_to_fit(self):
        self.Canvas.ZoomToBB()

    def redraw(self):
        self.Canvas.Draw()