import wx
import cv2
import polygon_simplification
import tools

from ribbon_splitter import segment_contours_into_slices
from ribbons_mask_dialog import RibbonsMaskDialog

# WORK IN PROGRESS - WORK IN PROGRESS - WORK IN PROGRESS - WORK IN PROGRESS

class SegmentationPanel(wx.Panel):
    _canvas = None
    _model = None

    # user interface
    done_button = None
    _segment_button = None
    _save_button = None

    #
    _slices = None  # slice outlines (=ribbon mask segmentation result)
    _template_slice_contour = None

    def __init__(self, parent, model, canvas):
        wx.Panel.__init__(self, parent, size=(350, -1))

        self._canvas = canvas
        self._model = model

        # Build the user interface
        title = wx.StaticText(self, wx.ID_ANY, "Segmentation")
        title.SetFont(wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.BOLD))
        separator = wx.StaticLine(self, wx.ID_ANY)

        instructions_label = wx.StaticText(self, wx.ID_ANY, ("Not art and science serve alone, \n"
                                                             "patience must in the work be shown. \n"
                                                             "A quiet spirit plods and plods at length. \n"
                                                             "Nothing but time can give the brew its strength."))
        w = 330
        instructions_label.Wrap(w)  # force line wrapping

        button_size = (175, -1)
        self.done_button = wx.Button(self, wx.ID_ANY, "Done", size=button_size)  # The ApplicationFame will listen to clicks on this button.

        load_button = wx.Button(self, wx.ID_ANY, "Load Mask and Template", size=button_size)
        self._segment_button = wx.Button(self, wx.ID_ANY, "Segment", size=button_size)
        self._segment_button.Enable(False)
        self._save_button = wx.Button(self, wx.ID_ANY, "Save", size=button_size)
        self._save_button.Enable(False)

        self.Bind(wx.EVT_BUTTON, self._on_load_button_click, load_button)
        self.Bind(wx.EVT_BUTTON, self._on_segment_button_click, self._segment_button)
        self.Bind(wx.EVT_BUTTON, self._on_save_button_click, self._save_button)

        b = 5  # border size
        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(title, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(separator, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(instructions_label, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(load_button, 0, wx.ALL | wx.CENTER, border=b)
        contents.Add(self._segment_button, 0, wx.ALL | wx.CENTER, border=b)
        contents.Add(self._save_button, 0, wx.ALL | wx.CENTER, border=b)
        contents.Add(self.done_button, 0, wx.ALL | wx.CENTER, border=b)

        self.SetSizer(contents)
        contents.Fit(self)

    def _on_load_button_click(self, event):
        print('_on_load_button_click')

        with RibbonsMaskDialog(self._model, None, wx.ID_ANY, "Ribbons Mask") as dlg:
            dlg.CenterOnScreen()
            if dlg.ShowModal() != wx.ID_OK:
                return

        # TODO: draw the ribbons mask transparently in case the user already loaded the the overview image?
        self._canvas.seg_add_image(self._model.ribbons_mask_path)
        self._canvas.zoom_to_fit()
        self._canvas.redraw()

        self._template_slice_contour = SegmentationPanel._load_template_slice(self._model.template_slice_path)
        self._canvas.seg_add_polygon(self._template_slice_contour, "Green", line_width = 4)
        self._canvas.seg_add_text("template", tools.polygon_center(self._template_slice_contour), "Green", font_size = 100)
        self._canvas.redraw()

        self._segment_button.Enable(True)

    def _on_segment_button_click(self, event):
        print('_on_segment_button_click')

        #######################################

        # cf = ContourFinder()
        # gray_image = read_grayscale_image('xxxx')
        # initial_contour = template_slice_contour
        # # TODO: randomly disturb initial_contour a bit for testing, and see if the optimization manages to find the template_slice_contour again.
        # cf.optimize_contour(self, gray_image, initial_contour)

        #######################################

        # ribbon splitting code: "F:\Manual Backups\Ubuntu_26sep2018\development\DetectSlices\SplitRibbon\SplitRibbon.py"
        # OpenCV watershed: https://docs.opencv.org/3.1.0/d3/db4/tutorial_py_watershed.html (maybe it can be used to imitate Fiji > Process > Binary > Watershed ?)

        (img, ribbons) = SegmentationPanel._find_ribbons(self._model.ribbons_mask_path)
        ribbons = [tools.opencv_contour_to_list(ribbon) for ribbon in ribbons]

        # TODO - we should probably do the segmentation ribbon by ribbon, and only afterwards combine the different slices.
        # TODO: try to implement Fiji-style watershed segmentation of binary images
        #
        print('Simplifying ribbon contours. May be slow, please be patient.')
        wait = wx.BusyInfo("Simplifying contours. Please wait...")
        green = (0, 255, 0)
        simplified_ribbons = []
        for ribbon in ribbons:
            estimated_num_slices_in_ribbon = round(tools.polygon_area(ribbon) / tools.polygon_area(self._template_slice_contour))
            print('Estimated number of slices in ribbon: {}'.format(estimated_num_slices_in_ribbon))
            desired_num_vertices_in_ribbon = estimated_num_slices_in_ribbon * 5  # we want at least 4 points per slice, plus some extra to handle accidental dents in the slice shape
            simplified_ribbon = polygon_simplification.reduce_polygon(ribbon, desired_num_vertices_in_ribbon)
            simplified_ribbons.append(simplified_ribbon)
        del wait

        # Perform greedy/optimal split of ribbon
        wait = wx.BusyInfo("Segmenting ribbons into slices. Please wait...")
        simplified_ribbons_opencv = [tools.list_to_opencv_contour(rib) for rib in simplified_ribbons]
        rbns = segment_contours_into_slices(simplified_ribbons_opencv, self._template_slice_contour, junk_contours = [], greedy = False)
        del wait

        # Merge slices of each ribbon in one single list of slices
        slices = [tools.opencv_contour_to_list(slc) for rbn in rbns for slc in rbn]  # Flatten the list with ribbons with slices, into a list of slices.

        # Reorder slices in probable order - we may need to provide a user interface to let the user influence this
        # TODO

        # Simplify each slice
        # TODO: check if it is possible to end up with a slice that has fewer than 4 vertices...
        acute_threshold_radians = 0 # 30 * math.pi / 180.0
        simplify_slices = True
        if simplify_slices:
            slices = [polygon_simplification.reduce_polygon(slice, 4, acute_threshold_radians) for slice in slices]
            self._slices = slices  # only allow saving the slice contours if each slice has exactly 4 vertices

        # Show each slice, with slice numbers
        for i, slice in enumerate(slices):
            self._canvas.seg_add_polygon(slice, "Red", line_width = 2)
            self._canvas.seg_add_text(str(i), tools.polygon_center(slice), "Red", font_size = 100)
        self._canvas.redraw()

        self._segment_button.Enable(False)
        self._save_button.Enable(self._slices is not None)

        print('...Segmentation done...')

        # CHECKME: Old notes
        # 1: load template slice quad coords (later: let the user define one interactively) (TODO: add path to dialog)
        # 2: extract ribbons outlines
        # 3: simplify ribbons outlines to ~#slices x 4or5 points   (we can estimate the #slices from the ribbon area / template area)
        # 4: apply greedy or best splitting of simplified ribbon outline   (TODO: add best/greedy/watershed choice to dialog)
        # 5: simplify each split slice to exactly 4 points (some may have a few more)
        # 6: save slice outlines to JSON for later use

    def _on_save_button_click(self, event):
        defaultDir = ''
        defaultFile = 'slices.json'
        with wx.FileDialog(self, "Specify name of slice contours file",
                           defaultDir, defaultFile,
                           wildcard="JSON files (*.json)|*.json",
                           style=wx.FD_SAVE) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                tools.json_save_polygons(path, self._slices)
                print('Slice contours saved to {}'.format(path))

    @staticmethod
    def _find_ribbons(ribbons_mask_path):
        img = tools.read_image_as_color_image(ribbons_mask_path)
        print('Ribbons mask image: shape={} type={}'.format(img.shape, img.dtype))

        # e.g. our test image E:\git\bits\bioimaging\Secom\tomo\data\10x_lens\SET_6stitched-0_10xlens_ribbons_mask.tif
        #      has background pixels with value 0, and foreground pixels (=the ribbons) with value 255

        # CHECKME Convert to grayscale, needed for findContours???
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Invert the image. CHECKME findContours expect foreground to be 0? 255? and background to be value 0? 255?
        img_gray = (255-img_gray)

        # Find the contours
        if (cv2.__version__[0] == '2'):
            ribbons, _ = cv2.findContours(img_gray, cv2.RETR_LIST, method = cv2.CHAIN_APPROX_SIMPLE)
        else:
            _, ribbons, _ = cv2.findContours(img_gray, cv2.RETR_LIST, method = cv2.CHAIN_APPROX_SIMPLE)

        # Note: findContours(..., cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE) returns a list of numpy arrays of shape (numvertices, 1, 2)
        print('Found {} ribbons'.format(len(ribbons)))

        return (img, ribbons)

    @staticmethod
    def _load_template_slice(filename):
        # Returns a list of (x,y) coordinates of the slice vertices
        # template_slice_contour = [( 760, 1404), (1572, 1435), (1474,  880), ( 808,  857)]
        polygons = tools.json_load_polygons(filename)
        assert(len(polygons) == 1)
        return polygons[0]
