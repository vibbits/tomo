# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx
from wx.lib.floatcanvas import FloatCanvas
from tomo_canvas import TomoCanvas

# Note: See https://wxpython.org/Phoenix/docs/html/wx.ColourDatabase.html for a list of color names

# IMPROVEME: I think the API should return the handles to the objects that it created, and have the caller keep track of it.
# (Otherwise this class will need many different functions to keep semantically different "lines" or "squares" or ... apart
# since they may have to be removed separately.)
# THOUGHT: I think this class *can* keep track of objects, but maybe only those that need to be rendered independent of which side panel is active, and
# even if no side panel is activate. Some objects are tied tightly to a specific panel (e.g. polygon editing handles) and those should probably
# be left out of the OverviewCanvas.

class OverviewCanvas(TomoCanvas):
    _poi_lines = []
    _focus_lines = []
    _slice_outlines = []
    _wximage = None  # the original wx.Image
    _image = None  # the canvas image object handle

    def __init__(self, parent, custom_modes=None):
        if custom_modes is None:
            custom_modes = []
        TomoCanvas.__init__(self, parent, custom_modes, id=wx.ID_ANY, size=(800, -1))
        wx.CallAfter(self.Canvas.ZoomToBB)  # so it will get called after everything is created and sized

    def set_image(self, filename):
        print('Loading ' + filename)

        wait = wx.BusyInfo("Loading overview image...")
        try:
            self._wximage = wx.Image(filename)
        finally:
            del wait

        if not self._wximage.IsOk():
            return

        img = FloatCanvas.ScaledBitmap2(self._wximage,
                                        (0, 0),
                                        Height=self._wximage.GetHeight(),
                                        Position='tl')
        # CHECKME: why use ScaledBitmap2 instead of ScaledBitmap?
        # CHECKME: can we use a different Position (e.g. 'bl') to avoid flipping the y-axis in different places?
        if self._image != None:
            self._remove_image()
        self._image = self.Canvas.AddObject(img)

    def get_wximage(self):
        return self._wximage

    def _remove_image(self):
        self.Canvas.RemoveObject(self._image)
        self._image = None
        self._wximage = None

    def set_slice_outlines(self, slice_outlines, line_color="Green"):  # slice outlines in overview image coordinates (y >= 0)
        # Add previous slice outlines (if any)
        if self._slice_outlines:
            self._remove_slice_outlines()
        # Add new slice outlines
        for outline in slice_outlines:
            pts = [(p[0], -p[1]) for p in outline]  # note: flip y to convert from image coordinates (with y >= 0) back to canvas coords
            polygon = self.Canvas.AddPolygon(pts, LineColor=line_color)
            self._slice_outlines.append(polygon)

    def set_slice_outline_linewidth(self, outline, line_width):
        obj = self._slice_outlines[outline]
        obj.SetLineWidth(line_width)

    def set_slice_outline_vertex_position(self, outline, vertex, pos):
        obj = self._slice_outlines[outline]
        obj.Points[vertex] = pos

    def remove_slice_outline(self, index):
        obj = self._slice_outlines.pop(index)
        self.remove_objects([obj])

    def _remove_slice_outlines(self):
        self.remove_objects(self._slice_outlines)
        self._slice_outlines = []

    def set_points_of_interest(self, points_of_interest):  # points of interest in overview image coordinates; if pois were set before, they are replaced by the new ones; points_of_interest can be the empty list
        # Remove old POIs (if any)
        if self._poi_lines:
            self._remove_points_of_interest()

        if not points_of_interest:
            return

        # Add new POIs
        pts = [(p[0], -p[1]) for p in points_of_interest]
        for pt in pts:
            self._add_point_of_interest(pt, line_color="red")

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

    # FIXME: if we first add slice outlines and then the overview image, the image will completely obscure the slice outlines. To avoid this, either somehow move the slice outlines back to the top, or remove and add them again in the correct order.

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

    def redraw(self, force=False):
        self.Canvas.Draw(force)

    ##### FIXME PROTOTYPE FOR RIBBON SEGMENTATION - NEEDS TO BE CLEANED UP

    def seg_add_image(self, filename):
        print('Loading ' + filename)
        image = wx.Image(filename)
        img = FloatCanvas.ScaledBitmap2(image,
                                        (0,0),
                                        Height = image.GetHeight(),
                                        Position = 'tl')
        self.Canvas.AddObject(img)

    def seg_add_polygon(self, outline, line_color, line_width):
        pts = [(p[0], -p[1]) for p in outline]
        self.Canvas.AddPolygon(pts, LineColor = line_color, LineWidth = line_width)

    def seg_add_text(self, text, position, text_color, font_size):
        # http://docs.huihoo.com/wxpython/2.8.3.0/api/wx.lib.floatcanvas.FloatCanvas.FloatCanvas-class.html#addshape
        self.Canvas.AddScaledText(text, (position[0], -position[1]), Position = "cc", Color = text_color, Size = font_size)

    #####
