# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx
from wx.lib.floatcanvas import FloatCanvas
from tomo_canvas import TomoCanvas
# from wx.lib.floatcanvas import NavCanvas
# from polygon_editor import PolygonEditor

# Note: See https://wxpython.org/Phoenix/docs/html/wx.ColourDatabase.html for a list of color names

class OverviewPanel(TomoCanvas):
    _poi_lines = []
    _focus_lines = []
    _slice_outlines = []
    _image = None

    # PROTOTYPE - for polygon editing
    _polygon_editor = None
    # END PROTOTYPE

    def __init__(self, parent, custom_modes=None):
        if custom_modes is None:
            custom_modes = []
        TomoCanvas.__init__(self, parent, custom_modes, id=wx.ID_ANY, size=(800, -1))
        # PROTOTYPE - for polygon editing
        # _polygon_editor = PolygonEditor(self.Canvas)
        # END PROTOTYPE
        wx.CallAfter(self.Canvas.ZoomToBB)  # so it will get called after everything is created and sized

    def set_image(self, filename):
        print('Loading ' + filename)
        image = wx.Image(filename)
        img = FloatCanvas.ScaledBitmap2(image,
                                        (0, 0),
                                        Height=image.GetHeight(),
                                        Position='tl')
        # CHECKME: why use ScaledBitmap2 instead of ScaledBitmap?
        # CHECKME: can we use a different Position (e.g. 'bl') to avoid flipping the y-axis in different places?
        if self._image != None:
            self._remove_image()
        self._image = self.Canvas.AddObject(img)

    def _remove_image(self):
        self.Canvas.RemoveObject(self._image)
        self._image = None

    def set_slice_outlines(self, slice_outlines, line_color="Green"):  # slice outlines in overview image coordinates (y >= 0)
        # Add previous slice outlines (if any)
        if self._slice_outlines:
            self._remove_slice_outlines()
        # Add new slice outlines
        for outline in slice_outlines:
            pts = [(p[0], -p[1]) for p in outline]  # note: flip y to convert from image coordinates (with y >= 0) back to canvas coords
            polygon = self.Canvas.AddPolygon(pts, LineColor=line_color)
            self._slice_outlines.append(polygon)

    def _remove_slice_outlines(self):
        self.remove_objects(self._slice_outlines)
        self._slice_outlines = []

    # The first point is user-specified, drawn in green.
    # The other points are calculated, drawn in red.
    def set_points_of_interest(self, points_of_interest):  # point of interest in overview image coordinates; if a poi was set before it is replaced by the new one
        # Remove old POIs (if any)
        if self._poi_lines:
            self._remove_points_of_interest()

        # Color definitions
        light_green = wx.Colour(0, 255, 0)
        darker_green = wx.Colour(0, 225, 0)

        # Add new POIs
        pts = [(p[0], -p[1]) for p in points_of_interest]
        self._add_point_of_interest(pts[0], line_color=light_green)
        for pt in pts[1:]:
            self._add_point_of_interest(pt, line_color=darker_green)

    def add_focus_position(self, position, color="Blue"):   # note: 'position' is in image space (with the origin in the top-left corner and y-axis pointing upward), so DIFFERENT from raw stage (x,y) position coordinates
        # print('draw focus: {}'.format(position))
        position = (position[0], -position[1])  # note: flip y to convert from image coordinates (with y >= 0) back to canvas coords
        objs = self.add_cross(position, color)
        self._focus_lines.extend(objs)

    def remove_focus_positions(self):
        self.remove_objects(self._focus_lines)
        self._focus_lines = []

    def _remove_points_of_interest(self):
        self.remove_objects(self._poi_lines)
        self._poi_lines = []

    def _add_point_of_interest(self, pt, line_color, size=25):
        # print('draw poi: {}'.format(pt))
        objs = self.add_cross(pt, line_color, size)
        self._poi_lines.extend(objs)

    # FIXME: IMPORTANT: fix inconsistency: sometimes canvas and sometimes image coordinates on the API!

    def add_cross(self, pt, line_color, size=25):  # pt is in *canvas* coordinates (y <= 0 means over the image); returns the list of objects added to the canvas
        # print('draw cross: {}'.format(pt))
        line1 = self.Canvas.AddLine([(pt[0] - size, pt[1]), (pt[0] + size, pt[1])], LineColor=line_color)
        line2 = self.Canvas.AddLine([(pt[0], pt[1] - size), (pt[0], pt[1] + size)], LineColor=line_color)
        return [line1, line2]

    def add_bullseye(self, pt, line_color, size=25):  # returns the list of objects added to the canvas; size is the size of the circle, the cross will be 20% larger; pt in image coordinates (y>=0)
        pt = (pt[0], -pt[1])  # note: flip y to convert from image coordinates (with y >= 0) back to canvas coords
        cross = self.add_cross(pt, line_color, int(round(size * 1.2)))
        circle = self.Canvas.AddCircle(pt, size, LineColor=line_color)
        return cross + [circle]

    def remove_objects(self, objs):  # objs is a list of objects that are currently on the canvas
        for obj in objs:
            self.Canvas.RemoveObject(obj)

    def zoom_to_fit(self):
        self.Canvas.ZoomToBB()

    def redraw(self):
        self.Canvas.Draw()