# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import wx
from wx.lib.floatcanvas import FloatCanvas
from tomo_canvas import TomoCanvas
import tools
from constants import NORMAL_COLOR, REGULAR_LINE_WIDTH, POINT_OF_INTEREST_COLOR, FOCUS_POSITION_COLOR, MARKER_SIZE

# Note: See https://wxpython.org/Phoenix/docs/html/wx.ColourDatabase.html for a list of color names

# IMPROVEME: I think the API should return the handles to the objects that it created, and have the caller keep track of it.
# (Otherwise this class will need many different functions to keep semantically different "lines" or "squares" or ... apart
# since they may have to be removed separately.)
# THOUGHT: I think this class *can* keep track of objects, but maybe only those that need to be rendered independent of which side panel is active, and
# even if no side panel is activate. Some objects are tied tightly to a specific panel (e.g. polygon editing handles) and those should probably
# be left out of the OverviewCanvas.

class OverviewCanvas(TomoCanvas):
    _wximage = None  # the original wx.Image
    _show_slice_numbers = True  # flag indicating if slice numbers need to be drawn on the slice outlines
    _slice_polygons = []  # list with the slice polygo the same format as TomoModel.slice_polygons

    # FloatCanvas objects
    _image = None  # the canvas image object handle
    _poi_lines = []
    _focus_lines = []
    _slice_outlines = []  # FloatCanvas polygon objects representing the quadrilateral slice polygons specified in _slice_polygons
    _slice_numbers = []  # FloatCanvas objects of the text objects for the slice numbers

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
        # CHECKME: why use ScaledBitmap2 instead of ScaledBitmap? Performance? - our overview images are really large.

        # Note: we place the image such that the FloatCanvas origin (0,0) is in the top left corner ('tl') of the image,
        # because that is what ImageJ also does. Because we used ImageJ sometimes to experiment with image processing,
        # and since we sometimes export lineart data from ImageJ for use in Tomo, it makes sense to use the same convention.
        # The y-axis in ImageJ however points down, whereas by default in FloatCanvas it points up, so sometimes we will
        # need to flip the sign of the y-coordinates of our lineart objects when drawing them onto the FloatCanvas
        # on top of the image. (CHECKME: It would be nice if we could just use a coordinate transform to flip these
        # objects when drawing, we'll have to look into that...)

        if self._image != None:
            self._remove_image()

        # If we have lineart already, it needs to be on top of the image.
        # Since there apparently is no way to re-order the FloatCanvas objects (?!),
        # it seems we need to remove all lineart first,
        # then add the image, and finally recreate all lineart again.
        # TODO!

        self._image = self.Canvas.AddObject(img)

    def get_wximage(self):
        return self._wximage

    def _remove_image(self):
        self.Canvas.RemoveObject(self._image)
        self._image = None
        self._wximage = None

    def set_slice_outline_linewidth(self, outline, line_width):
        obj = self._slice_outlines[outline]
        obj.SetLineWidth(line_width)

    def set_slice_outline_vertex_position(self, outline, vertex, pos):
        obj = self._slice_outlines[outline]
        obj.Points[vertex] = pos

    def remove_slice_outline(self, slice_index):
        obj = self._slice_outlines.pop(slice_index)
        self.remove_objects([obj])

    def set_slice_number_position(self, slice_index, pos):
        if self._show_slice_numbers:
            obj = self._slice_numbers[slice_index]
            obj.SetPoint(pos)

    def set_slice_polygons(self, polygons):  # slice outlines in overview image coordinates (y >= 0)
        assert polygons is not None  # IMPROVEME: can't we use the empty list instead of None? That would make some None checking unnecessary.
        self._slice_polygons = polygons

        # Handle slice outlines
        self.remove_objects(self._slice_outlines)
        self._slice_outlines = []
        self._add_slice_outlines()

        # Handle slice numbers
        self.remove_objects(self._slice_numbers)
        self._slice_numbers = []
        if self._show_slice_numbers:
            self._add_slice_numbers()

    def _add_slice_outlines(self):
        for polygon in self._slice_polygons:
            pts = [(p[0], -p[1]) for p in polygon]  # note: flip y to convert from image coordinates (with y >= 0) back to canvas coords
            outline = self.Canvas.AddPolygon(pts, LineColor=NORMAL_COLOR, LineWidth=REGULAR_LINE_WIDTH)
            self._slice_outlines.append(outline)

    def set_show_slice_numbers(self, show_numbers):
        if self._show_slice_numbers == show_numbers:
            return

        if show_numbers:
            self._add_slice_numbers()
        else:
            self.remove_objects(self._slice_numbers)
            self._slice_numbers = []

        self._show_slice_numbers = show_numbers

    def _add_slice_numbers(self):
        self._slice_numbers = []
        for i, polygon in enumerate(self._slice_polygons):
            pos = tools.polygon_center(polygon)
            pos = (pos[0], -pos[1])
            obj = self.Canvas.AddText(str(i+1), pos, Size=10, BackgroundColor=None, Color=NORMAL_COLOR, Position="cc")
            self._slice_numbers.append(obj)

    def set_points_of_interest(self, points_of_interest):  # points of interest in overview image coordinates; if pois were set before, they are replaced by the new ones; points_of_interest can be the empty list
        # Remove old POIs (if any)
        if self._poi_lines:
            self.remove_objects(self._poi_lines)
            self._poi_lines = []

        if not points_of_interest:
            return

        # Add new POIs
        pts = [(p[0], -p[1]) for p in points_of_interest]
        for pt in pts:
            self._add_point_of_interest(pt, line_color=POINT_OF_INTEREST_COLOR)

    def add_focus_position(self, position, color=FOCUS_POSITION_COLOR):   # note: 'position' is in image space (with the origin in the top-left corner and y-axis pointing upward), so DIFFERENT from raw stage (x,y) position coordinates
        # print('draw focus: {}'.format(position))
        position = (position[0], -position[1])  # note: flip y to convert from image coordinates (with y >= 0) back to canvas coords
        objs = self.add_cross(position, color)
        self._focus_lines.extend(objs)

    def remove_focus_positions(self):
        self.remove_objects(self._focus_lines)
        self._focus_lines = []

    def _add_point_of_interest(self, pt, line_color, size=MARKER_SIZE):
        # print('draw poi: {}'.format(pt))
        objs = self.add_cross(pt, line_color, size)
        self._poi_lines.extend(objs)

    # IMPROVEME: fix inconsistency: sometimes canvas and sometimes image coordinates on the API!

    # FIXME: If we first add slice outlines and then the overview image, the image will be drawn on top and completely obscure the slice outlines.

    def add_cross(self, pt, line_color, size=MARKER_SIZE):  # pt is in *canvas* coordinates (y <= 0 means over the image); returns the list of objects added to the canvas
        # print('draw cross: {}'.format(pt))
        line1 = self.Canvas.AddLine([(pt[0] - size, pt[1]), (pt[0] + size, pt[1])], LineColor=line_color)
        line2 = self.Canvas.AddLine([(pt[0], pt[1] - size), (pt[0], pt[1] + size)], LineColor=line_color)
        return [line1, line2]

    def add_bullseye(self, pt, line_color, size=MARKER_SIZE):  # returns the list of objects added to the canvas; size is the size of the circle, the cross will be 20% larger; pt in image coordinates (y>=0)
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
        self.Canvas.AddPolygon(pts, LineColor=line_color, LineWidth=line_width)

    def seg_add_text(self, text, position, text_color, font_size):
        # http://docs.huihoo.com/wxpython/2.8.3.0/api/wx.lib.floatcanvas.FloatCanvas.FloatCanvas-class.html#addshape
        self.Canvas.AddScaledText(text, (position[0], -position[1]), Position="cc", Color=text_color, Size=font_size)

    #####
