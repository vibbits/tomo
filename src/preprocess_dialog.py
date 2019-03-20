# Frank Vernaillen
# March 2019
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import numpy as np
import math
import cv2
import wx
import matplotlib
matplotlib.use('wxagg')
from matplotlib import pyplot as plt

# IMPROVEME: rather than use a tile x/y slider, it would be nice if the user could click and drag on the preview tile
#            to move its position with respect to the complete overview image

class PreprocessDialog(wx.Dialog):
    def __init__(self, img, model, parent, ID, title, size=wx.DefaultSize, pos=wx.DefaultPosition, style=wx.DEFAULT_DIALOG_STYLE):
        wx.Dialog.__init__(self, parent, ID, title, pos, size, style)

        self.orig_img = img
        self._model = model

        # Preprocessing parameters
        self.histogram, self.lo_percentile_val, self.hi_percentile_val = relevant_intensity_range(self.orig_img, 2, 98)  # we need to do this on the full original image, but rest of interactive preprocessing will be on a cropped version of the original, for speed.
        self.step = 5   # preprocessing step (0=original image, 1=blurred image, 2=..., 5=final preprocessed result)
        self.gaussian_kernel1_size = 29  # must be odd; larger kernels will suppress noise more
        self.gaussian_kernel2_size = 63  # must be odd; larger kernels will result in a wider edge, useful for attracting approximate slice contours from further away
        self.laplacian_delta = -270

        # Figure out number of tiles in the image
        img_height, img_width = img.shape
        num_tiles_vertical = int(math.ceil(float(img_height) / TILE_SIZE))
        num_tiles_horizontal = int(math.ceil(float(img_width) / TILE_SIZE))

        # Show preview of approximately the middle tile
        self.tile_x = num_tiles_horizontal / 2
        self.tile_y = num_tiles_vertical / 2
        self.orig_img_crop = get_tile(img, self.tile_x, self.tile_y)

        # Results of different preprocessing steps
        self.contrast_enhanced_img = None
        self.blurred_img = None
        self.laplacian = None
        self.abs_laplacian = None
        self.result = None

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

        # Build UI
        button_size = (125, -1)
        cancel_button = wx.Button(self, wx.ID_ANY, "Cancel", size=button_size)
        accept_button = wx.Button(self, wx.ID_ANY, "Accept", size=button_size)
        histogram_button = wx.Button(self, wx.ID_ANY, "Show Histogram", size=button_size)

        slider_size = (250, -1)
        self.step_slider = wx.Slider(self, value=self.step, minValue=0, maxValue=5, style=wx.SL_HORIZONTAL | wx.SL_LABELS, size=slider_size)
        self.tile_x_slider = wx.Slider(self, value=self.tile_x, minValue=0, maxValue=num_tiles_horizontal-1, style=wx.SL_HORIZONTAL | wx.SL_LABELS, size=slider_size)
        self.tile_y_slider = wx.Slider(self, value=self.tile_y, minValue=0, maxValue=num_tiles_vertical-1, style=wx.SL_HORIZONTAL | wx.SL_LABELS, size=slider_size)
        self.blur1_slider = wx.Slider(self, value=(self.gaussian_kernel1_size - 3) / 2, minValue=0, maxValue=20, style=wx.SL_HORIZONTAL | wx.SL_LABELS, size=slider_size)
        self.delta_slider = wx.Slider(self, value=self.laplacian_delta, minValue=-500, maxValue=500, style=wx.SL_HORIZONTAL | wx.SL_LABELS, size=slider_size)
        self.blur2_slider = wx.Slider(self, value=(self.gaussian_kernel2_size - 3) / 2, minValue=0, maxValue=80, style=wx.SL_HORIZONTAL | wx.SL_LABELS, size=slider_size)

        self.step_slider.Bind(wx.EVT_SLIDER, self._on_preprocessing_step)
        self.tile_x_slider.Bind(wx.EVT_SLIDER, self._on_tile_x)
        self.tile_y_slider.Bind(wx.EVT_SLIDER, self._on_tile_y)
        self.blur1_slider.Bind(wx.EVT_SLIDER, self._on_gaussian1_kernel_size)
        self.delta_slider.Bind(wx.EVT_SLIDER, self._on_laplacian_delta)
        self.blur2_slider.Bind(wx.EVT_SLIDER, self._on_gaussian2_kernel_size)
        self.Bind(wx.EVT_BUTTON, self._on_show_histogram, histogram_button)
        self.Bind(wx.EVT_BUTTON, self._on_accept, accept_button)
        self.Bind(wx.EVT_BUTTON, self._on_cancel, cancel_button)

        b = 5  # border size

        self.image_ctrl = wx.StaticBitmap(self, wx.ID_ANY, empty_bitmap())

        sliders_sizer = wx.FlexGridSizer(cols=2, vgap=4, hgap=14)
        sliders_sizer.Add(wx.StaticText(self, wx.ID_ANY, "Preprocessing Step:"), flag=wx.LEFT | wx.ALIGN_RIGHT)
        sliders_sizer.Add(self.step_slider, flag=wx.RIGHT)
        sliders_sizer.Add(wx.StaticText(self, wx.ID_ANY, "Tile X:"), flag=wx.LEFT | wx.ALIGN_RIGHT)
        sliders_sizer.Add(self.tile_x_slider, flag=wx.RIGHT)
        sliders_sizer.Add(wx.StaticText(self, wx.ID_ANY, "Tile Y:"), flag=wx.LEFT | wx.ALIGN_RIGHT)
        sliders_sizer.Add(self.tile_y_slider, flag=wx.RIGHT)
        sliders_sizer.Add(wx.StaticText(self, wx.ID_ANY, "Denoising Blur:"), flag=wx.LEFT | wx.ALIGN_RIGHT)
        sliders_sizer.Add(self.blur1_slider, flag=wx.RIGHT)
        sliders_sizer.Add(wx.StaticText(self, wx.ID_ANY, "Laplacian Delta:"), flag=wx.LEFT | wx.ALIGN_RIGHT)
        sliders_sizer.Add(self.delta_slider, flag=wx.RIGHT)
        sliders_sizer.Add(wx.StaticText(self, wx.ID_ANY, "Edge Blur:"), flag=wx.LEFT | wx.ALIGN_RIGHT)
        sliders_sizer.Add(self.blur2_slider, flag=wx.RIGHT)

        controls = wx.BoxSizer(wx.VERTICAL)
        controls.Add(sliders_sizer, 0, wx.ALL | wx.EXPAND, border=b)
        controls.AddSpacer(14)
        controls.Add(histogram_button, 0, wx.ALL | wx.CENTER, border=b)
        controls.AddSpacer(20)
        controls.Add(cancel_button, 0, wx.ALL | wx.CENTER, border=b)
        controls.Add(accept_button, 0, wx.ALL | wx.CENTER, border=b)

        contents = wx.BoxSizer(wx.HORIZONTAL)
        contents.Add(self.image_ctrl, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(controls, 0, wx.ALL | wx.EXPAND, border=b)

        self.SetSizer(contents)
        contents.Fit(self)

        # Preprocess the selected tile and show it in the window
        self.preprocess(self.orig_img_crop)
        self._redraw_window()

    def preprocess(self, img):
        # Imporant note: for the iterative contour finding to work well, the preprocessed image should have an intensity profile around the edges
        # that varies smoothly, from relatively "far" from the edge, and with no local minima/maxima in the neighborhood. I suspect that local minima are the cause
        # for the behaviour where the contour seems to get stuck in the neighborhood of the true contour. These local minima are probably caused by intensity variations in background or lighting.
        # Ideally preprocessing would turn the overview image first into a binary image with edges/no edges, which we then gaussian blur.
        # Applying an edge detector which does not binarize the image, and no thresholding, followed by gaussian blur preserves these local intensity variations and results
        # in an iterative contour finding which seems to get stuck sometimes. (At least these local minima are my theory of what happens...)

        # Example:
        # bisstitched-0.tif (=16 bit, a few black 0 pixels at the border, rest is a peak around 35000 to 41000)
        # - Fiji > shift-ctrl c: contrast enhance (min=35779, max=42819, set, apply => histogram now more or less a bump between 0 and 65535)
        # - Fiji > Plugins > Mexican Hat Filter > Separable, r=20 (=> image is now a binary image, with background=white=65535 and edges=black=0; edges are about 17 black pixels wide)
        # . Optional, probably interesting: remove small specks (Fiji: particle analysis etc.)
        # - Fiji > Process > Filters > Gaussian Blur, Sigma (Radius)=20  (=image is now a 16-bit image where near edges the intensity drop from 65000 to 46386 and back up over a distance of about 110 px)
        # bisstitched-0-contrast-enhanced-mexicanhat_separable_radius20-gaussianblur20pix.tif

        # Contrast enhancement
        lo_val, hi_val = self.lo_percentile_val, self.hi_percentile_val
        self.contrast_enhanced_img = enhance_contrast(img, lo_val, hi_val)
        # print('Contrast enhanced: shape={} dtype={} min={} max={}'.format(self.contrast_enhanced_img.shape, self.contrast_enhanced_img.dtype, np.min(self.contrast_enhanced_img), np.max(self.contrast_enhanced_img)))

        # Gaussian blurring to remove some of the noise,
        # Needed because afterwards we will use the Laplacian to detect edges,
        # and this is very sensitive to the presence of noise.
        kernel_size = (self.gaussian_kernel1_size, self.gaussian_kernel1_size)  # must be odd
        sigma_x, sigma_y = 0, 0   # 0 means calculate sigma from the kernel size
        self.blurred_img = cv2.GaussianBlur(self.contrast_enhanced_img, kernel_size, sigma_x, sigma_y)

        # Laplacian (of the Gaussian) to detect edges.
        # Note the use of an offset (self.laplacian_delta).
        self.laplacian = cv2.Laplacian(self.blurred_img, cv2.CV_64F, 5, scale=1, delta=self.laplacian_delta)
        # print('Laplacian (of Gaussian) 5 scale=1, delta={}: shape={} dtype={} min={} max={}'.format(self.laplacian_delta, self.laplacian.shape, self.laplacian.dtype, np.min(self.laplacian), np.max(self.laplacian)))

        # The Laplacian is now a floating point image, having negative values.
        # Threshold it to positive values to keep only the edges.
        self.abs_laplacian = (self.laplacian > 0).astype(np.uint16) * 65535  # self.laplacian > 0  means edges

        # Perform Gaussian blur on the detected edges, this is needed for the active contours lateron
        # to feel the attraction of an edge even some distance away from the edge.
        kernel_size = (self.gaussian_kernel2_size, self.gaussian_kernel2_size)  # must be odd
        sigma_x, sigma_y = 0, 0   # 0 means calculate sigma from the kernel size
        self.result = cv2.GaussianBlur(self.abs_laplacian, kernel_size, sigma_x, sigma_y)
        # print('Gaussian of Laplacian of Gaussian: shape={} dtype={} min={} max={}'.format(self.abs_laplacian.shape, self.abs_laplacian.dtype, np.min(self.abs_laplacian), np.max(self.abs_laplacian)))

        # Convert images to 8-bit so they can be more easily turned into wxPython bitmaps for viewing
        self.result = grayscale_image_16bit_to_8bit(self.result)
        return self.result

    def get_preprocessed_image(self):
        """
        Returns either the most recently preprocessed image or image tile; call this after "preprocess()"
        """
        return self.result

    def _on_accept(self, event):
        self.EndModal(wx.OK)

    def _on_cancel(self, event):
        self.EndModal(wx.CANCEL)

    def _redraw_window(self):
        images = { 0: self.orig_img_crop,
                   1: self.contrast_enhanced_img,
                   2: self.blurred_img,
                   3: self.laplacian,
                   4: self.abs_laplacian,
                   5: self.result }
        img = images.get(self.step)

        # Pad the image in case it is smaller than the tile size (this occurs for tiles at the right and bottom of the image),
        # so that the previously drawn tile (possible larger) is erased.
        # FIXME: this hack is far from ideal, the user can't see that this (black) padding is artifical and does not belong to the image.
        img = pad_image(img, TILE_SIZE, TILE_SIZE)

        bitmap = wx_bitmap_from_OpenCV_image(img)
        self.image_ctrl.SetBitmap(bitmap)

    def _on_show_histogram(self, event):
        plot_intensity_histogram(self.orig_img, self.histogram, self.lo_percentile_val, self.hi_percentile_val)

    def _on_preprocessing_step(self, event):
        self.step = event.GetEventObject().GetValue()
        self._redraw_window()

    def _on_tile_x(self, event):
        self.tile_x = event.GetEventObject().GetValue()
        self._on_tile()

    def _on_tile_y(self, event):
        self.tile_y = event.GetEventObject().GetValue()
        self._on_tile()

    def _on_tile(self):
        self.orig_img_crop = get_tile(self.orig_img, self.tile_x, self.tile_y)
        self.preprocess(self.orig_img_crop)
        self._redraw_window()

    def _on_gaussian1_kernel_size(self, event):
        size = event.GetEventObject().GetValue()
        self.gaussian_kernel1_size = 2 * size + 3  # kernel size must be odd, and our sliders have steps of 1 (we could use +1 instead of +3 if we use 1 als the lowest slider value instead of 0)
        self.preprocess(self.orig_img_crop)
        self._redraw_window()

    def _on_gaussian2_kernel_size(self, event):
        size = event.GetEventObject().GetValue()
        self.gaussian_kernel2_size = 2 * size + 3  # kernel size must be odd, and our sliders have steps of 1
        self.preprocess(self.orig_img_crop)
        self._redraw_window()

    def _on_laplacian_delta(self, event):
        self.laplacian_delta = event.GetEventObject().GetValue()
        self.preprocess(self.orig_img_crop)
        self._redraw_window()

# To speedup previewing the result of image processing,
# we only show a chunk (a "tile") of the complete image.
TILE_SIZE = 768

def grayscale_image_16bit_to_8bit(image):
    # Convert a 16-bit OpenCV grayscale image to 8-bit.
    # The full 16-bit range is mapped onto 0 to 255.
    assert image.dtype == np.uint16
    return (image / 257).astype(np.uint8)  # Note: 65535 = 255 * 257 (exactly)


def grayscale_image_float_to_8bit(image):
    # Convert a floating point OpenCV grayscale image to 8-bit.
    # The range between the lowest and the highest floating point pixel intensity
    # is mapped linearly onto 0 to 255.
    assert image.dtype == np.float
    min_val = np.min(image)
    max_val = np.max(image)
    # linearly map min to max -> 0 to 255
    image = ((image - min_val) / (max_val - min_val) * 255).astype(np.uint8)
    return image


def empty_bitmap():
    # wx.EmptyBitmap() is deprecated but needed for wxPython Classic on the SECOM computer:
    # return wx.Bitmap(TILE_SIZE, TILE_SIZE)
    # does not work there.
    return wx.EmptyBitmap(TILE_SIZE, TILE_SIZE)

def get_tile(image, tile_x, tile_y):
    # The given image is assumed to consist of tiles of size TILE_SIZE x TILE_SIZE pixels. The tile (tile_x, tile_y)
    # is returned. tile_x and tile_y are 0-based indices, counting from the top left corner of image.
    img_height, img_width = image.shape
    tile_start_x = tile_x * TILE_SIZE
    tile_start_y = tile_y * TILE_SIZE
    tile_end_x = min((tile_x + 1) * TILE_SIZE, img_width)
    tile_end_y = min((tile_y + 1) * TILE_SIZE, img_height)
    return image[tile_start_y: tile_end_y,
               tile_start_x: tile_end_x]


def get_max_possible_intensity(image):
    """
    Returns the maximum intensity value that can be represented by the data type used to represent a pixel in the image.
    """
    if image.dtype == np.uint16:
        return 65535
    elif image.dtype == np.uint8:
        return 255
    else:
        raise RuntimeError('Only 8-bit and 16-bit images are supported.')


def enhance_contrast(image, lo_val, hi_val):
    """
    Enhances the contrast of a given image by stretching the pixel intensities between lo_val and hi_val
    to the maximum range possible for the image's pixel data type (e.g. it stretches to 0-255 for 8-bit images).
    Returns the contrast enhanced image.
    """

    assert lo_val < hi_val

    # note: Numpy subtract() and multiply() perform saturating arithmetic, so we're protected from overflow
    image = cv2.subtract(image, lo_val)
    one = np.ones(image.shape, dtype=image.dtype)
    max_val = float(get_max_possible_intensity(image))
    image = cv2.multiply(image, one, scale=max_val / (hi_val - lo_val))
    return image


def relevant_intensity_range(image, lo_percentile, hi_percentile):
    """
    Calculates the intensity histogram of the given image, as well as the pixel intensities for lo_percentile and hi_percentile percentiles.
    :param image:
    :param lo_percentile:
    :param hi_percentile:
    :return: a tuple with the histogram and the pixel intensities for the requested low and high percentiles.
    """
    # Build image histogram
    max_intensity = get_max_possible_intensity(image)
    num_bins = max_intensity + 1
    histogram = cv2.calcHist([image], [0], None, [num_bins], [0, max_intensity])

    # Find intensity value for the low and hi percentiles
    # (e.g. 1 and 99-th percentile, of 0.5 and 99.5th percentile)
    # These percentiles produce better contrast enhancement than just the minimum and maximum image intensity values,
    # because the microscope images often have a thin but very dark border that we want to ignore.
    lo_val = get_histogram_percentile(histogram, lo_percentile)
    hi_val = get_histogram_percentile(histogram, hi_percentile)

    return histogram, lo_val, hi_val


def plot_intensity_histogram(image, histogram, lo_val, hi_val):
    """
    Uses matplotlib to plot the intensity histogram of an image
    :param image:
    :param histogram: intensity histogram for the image
    :param lo_val:
    :param hi_val:
           lo_val, hi_val: low and high image intensities, typically derived by calculating e.g 2th and 98th intensity percentiles in the image
           (so the bulk - but not all - of the pixel intensities lie between lo_val and hi_val)
    """

    max_intensity = get_max_possible_intensity(image)
    min_val = np.min(image)
    max_val = np.max(image)
    plt.plot(histogram, '-')
    plt.axvline(min_val, color='b', linestyle=':')
    plt.axvline(max_val, color='b', linestyle=':')
    plt.axvline(lo_val, color='r', linestyle=':')
    plt.axvline(hi_val, color='r', linestyle=':')
    plt.legend(['histogram', 'min', 'max', 'lo percentile', 'hi percentile'])
    margin = 5  # expand x limits a bit so extreme values do not overlap with plot outline box.
    plt.xlim([-margin, max_intensity + margin])
    plt.show()


def get_histogram_percentile(histogram, percentile):
    """
    :param histogram: intensity histogram of an image, assumed to have a histogram bin for each possible intensity (e.g bins for 0, 1, 2,...65535 for a 16-bit image)
    :param percentile: the request intensity percentile e.g 95 for the 95th-percentile
    :return: the intensity value corresponding to the given percentile
    """

    total = np.sum(histogram)
    needed = total * (percentile / 100.0)
    running_total = 0
    for i, val in enumerate(histogram):
        running_total += val[0]
        if running_total >= needed:
            break
    return i


def wx_bitmap_from_OpenCV_image(image):
    """
    :param image: an grayscale OpenCV image (i.e a 2D numpy array)
    :return: a wxPython bitmap
    """
    assert len(image.shape) == 2  # image must be a single channel, so shape is only (rows, cols)
    if image.dtype == np.uint16:
        image = grayscale_image_16bit_to_8bit(image)
    elif image.dtype == np.float:
        image = grayscale_image_float_to_8bit(image)
    else:
        assert image.dtype == np.uint8

    conversion = cv2.COLOR_GRAY2RGB
    image = cv2.cvtColor(image, conversion)
    height, width = image.shape[:2]
    bitmap = wx.BitmapFromBuffer(width, height, image)
    # wx.BitmapFromBuffer() is deprecated but needed for wxPython Classic on the SECOM computer:
    # bitmap = wx.Bitmap.FromBuffer(width, height, image)
    # does not work there.
    return bitmap


def pad_image(image, min_height, min_width):
    """
    Returns the image padded (if needed) with zeroes so that it is at least min_height x min_width pixels.
    """
    height, width = image.shape[:2]
    padh = max(0, min_height - height)
    padw = max(0, min_width - width)
    if padh != 0 or padw != 0:
        return np.pad(image, ((0, padh), (0, padw)), 'constant')
    else:
        return image