# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx

class OverviewPanel(wx.Panel):  # TODO: rename to OverviewPanel or so, it has rather dedicated methods dealing with POIs and slices
    _bitmap = None
    _slice_outlines = None
    _points_of_interest = None
    _scale = (1.0, 1.0)

    def __init__(self, parent, title):
        super(OverviewPanel, self).__init__(parent, size = (1024, 1024))  # FIXME: size needed?
        self.init_ui()

    def init_ui(self):
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Show(True)  # FIXME: needed?

    def _rescale_image(self, img, max_size):
        # scale the image, preserving the aspect ratio
        w = img.GetWidth()
        h = img.GetHeight()
        if w > h:
            new_w = max_size
            new_h = max_size * h / w
        else:
            new_h = max_size
            new_w = max_size * w / h

        # TEST TEST
        new_w = new_w * 5
        new_h = new_h * 5

        self._scale = (new_w / float(w), new_h / float(h))

        img = img.Scale(new_w, new_h)
        return img

    def set_image(self, filename, max_size):
        img = wx.Image(filename, wx.BITMAP_TYPE_ANY)
        img = self._rescale_image(img, max_size)
        self._bitmap = wx.Bitmap(img)

    def set_slice_outlines(self, slice_outlines):
        self._slice_outlines = slice_outlines

    def set_points_of_interest(self, points_of_interest):
        self._points_of_interest = points_of_interest

    def _draw_polygon(self, dc, points):
        pts = [wx.Point(p[0] * self._scale[0], p[1] * self._scale[1]) for p in points]
        pts.append(pts[0]) # close the polygon
        dc.DrawLines(pts)

    def _draw_cross(self, dc, pos, size = 5):
        x, y = pos * self._scale
        dc.DrawLine(x-size, y, x+size, y)
        dc.DrawLine(x, y-size, x, y+size)

    def _on_paint(self, event):
        red_pen = wx.Pen(wx.Colour(255, 0, 0))
        green_pen = wx.Pen(wx.Colour(0, 255, 0))

        dc = wx.PaintDC(self)
        white_brush = wx.Brush("white")
        dc.SetBackground(white_brush)
        dc.Clear()

        if self._bitmap:
            dc.DrawBitmap(self._bitmap, 0, 0)  # (0,0) is the top-left corner of the image

        if self._slice_outlines:
            dc.SetPen(green_pen)
            for polygon in self._slice_outlines:
                self._draw_polygon(dc, polygon)

        if self._points_of_interest:
            for i, pos in enumerate(self._points_of_interest):
                if i == 0:
                    dc.SetPen(green_pen)
                else:
                    dc.SetPen(red_pen)
                self._draw_cross(dc, pos)

