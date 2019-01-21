import wx
import wx.grid
import tools
from contour_finder import ContourFinder

class ContourFinderPanel(wx.Panel):
    _canvas = None
    _model = None

    done_button = None
    _step_button = None

    _cf = None
    _preprocessed_image = None
    _current_contour = None

    def __init__(self, parent, model, canvas):
        wx.Panel.__init__(self, parent, size = (350, -1))
        self._canvas = canvas
        self._model = model

        title = wx.StaticText(self, wx.ID_ANY, "Slices finder")
        title.SetFont(wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.BOLD))
        separator = wx.StaticLine(self, wx.ID_ANY)

        label = wx.StaticText(self, wx.ID_ANY, "Just a little experiment for now.")
        label.Wrap(330)  # force line wrapping

        button_size = (125, -1)
        start_button = wx.Button(self, wx.ID_ANY, "Start", size = button_size)

        self._step_button = wx.Button(self, wx.ID_ANY, "Step", size = button_size)
        self._step_button.Enable(False)
        self.done_button = wx.Button(self, wx.ID_ANY, "Done", size = button_size)  # Not this panel but the ApplicationFame will listen to clicks on this button.

        self.Bind(wx.EVT_BUTTON, self._on_start_button_click, start_button)
        self.Bind(wx.EVT_BUTTON, self._on_step_button_click, self._step_button)

        b = 5  # border size
        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(title, 0, wx.ALL | wx.EXPAND, border = b)
        contents.Add(separator, 0, wx.ALL | wx.EXPAND, border = b)
        contents.Add(label, 0, wx.ALL | wx.EXPAND, border = b)
        contents.Add(start_button, 0, wx.ALL | wx.CENTER, border = b)
        contents.Add(self._step_button, 0, wx.ALL | wx.CENTER, border = b)
        contents.Add(self.done_button, 0, wx.ALL | wx.CENTER, border = b)

        self.SetSizer(contents)
        contents.Fit(self)


    def _on_start_button_click(self, event):
        # Load the user-defined ground truth slice outlines (not really needed, but we can use them for assessing our result)
        slice_polygons = tools.json_load_polygons(self._model.slice_polygons_path)
        print('Loaded {} slice polygons from {}'.format(len(slice_polygons), self._model.slice_polygons_path))
        true_slice1 = slice_polygons[0]
        print(true_slice1)
        # true_slice1 = [(1540, 1886),
        #                (3142, 1931),
        #                (2944,  848),
        #                (1630,  806)]

        self._cf = ContourFinder()

        if True:  # FIXME
            self._preprocessed_image = tools.read_image_as_grayscale('E:\\git\\bits\\bioimaging\\Secom\\tomo\\data\\20x_lens\\bisstitched-0-contrast-enhanced-mexicanhat_separable_radius40.tif')
            #self._preprocessed_image = tools.read_image_as_grayscale('e:\\Datasets\\tiny_grayscale.tif')
        else:
            opencv_gray_img = tools.read_image_as_grayscale(self._model.overview_image_path)
            self._preprocessed_image = cf.preprocess(opencv_gray_img)

        print('Score of ground truth slice outline={}'.format(self._cf.calculate_contour_score(self._preprocessed_image,self._cf.contour_to_vector(true_slice1))))

        self._current_contour = [(1540, 1886),
                                 (3142, 1931),
                                 (2944,  848),
                                 (1630,  836)]
        self._draw_contour(self._current_contour, "Blue")  # initial contour
        self._canvas.Canvas.Draw()

        self._step_button.Enable(True)

    def _on_step_button_click(self, event):

            optimized_contour = self._cf.optimize_contour(self._preprocessed_image, self._current_contour, h_for_gradient_approximation=1.0, max_iterations=20, gradient_step_size=1e-3)
            print(optimized_contour)

            self._draw_contour(optimized_contour, "Red")
            self._canvas.Canvas.Draw()

            self._current_contour = optimized_contour

    def _draw_contour(self, contour, color = "Green"):
        pts = [(p[0], -p[1]) for p in contour]
        polygon = self._canvas.Canvas.AddPolygon(pts, LineColor=color)
