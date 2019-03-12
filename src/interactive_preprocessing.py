import numpy as np
import math
import tools
import cv2
import wx
import os
from matplotlib import pyplot as plt


class InteractivePreprocessing:

    def __init__(self, img):
        self.window = 'Preprocessing'

        self.orig_img = img

        # preprocessing parameters
        self.lo_percentile_val, self.hi_percentile_val = relevant_intensity_range(self.orig_img, 2, 98, plot_histogram=True)  # we need to do this on the full original image, but rest of interactive preprocessing will be on a cropped version of the original, for speed.
        self.step = 5   # preprocessing step (0=original image, 1=blurred image, 2=..., 5=final preprocessed result)
        self.gaussian_kernel1_size = 31
        self.gaussian_kernel2_size = 31
        self.laplacian_delta = -100

        # Figure out number of tiles in the image
        # (Hack: we don't draw the rightmost tiles since they be be less wide than the other tiles,
        # which then ruins the very basic OpenCV image window layout.)
        img_height, img_width = img.shape
        num_tiles_vertical = int(math.ceil(float(img_height) / TILE_SIZE))
        num_tiles_horizontal = max(1, int(img_width / TILE_SIZE))  # instead of "int(math.ceil(float(img_width) / TILE_SIZE))" which would draw the narrower right-most column of tiles too, but automatically resizes the window but not the sliders :-(

        # Show preview of approximately the middle tile
        self.tile_x = num_tiles_horizontal / 2
        self.tile_y = num_tiles_vertical / 2
        self.orig_img_crop = get_tile(img, self.tile_x, self.tile_y)

        # results of different preprocessing steps
        self.contrast_enhanced_img = None
        self.blurred_img = None
        self.laplacian = None
        self.abs_laplacian = None
        self.result = None

        # Build UI
        # note: trackbars minimum value is always 0 :-(
        cv2.namedWindow(self.window) #, flags=cv2.WINDOW_NORMAL)
        cv2.createTrackbar('Step', self.window, self.step, 5, self.on_preprocessing_step)
        cv2.createTrackbar('Tile X', self.window, self.tile_x, num_tiles_horizontal - 1, self.on_tile_x)
        cv2.createTrackbar('Tile Y', self.window, self.tile_y, num_tiles_vertical - 1, self.on_tile_y)
        cv2.createTrackbar('Blur1', self.window, (self.gaussian_kernel1_size - 3) / 2, 20, self.on_gaussian1_kernel_size)
        cv2.createTrackbar('Delta', self.window, self.laplacian_delta + 500, 1000, self.on_laplacian_delta)
        cv2.createTrackbar('Blur2', self.window, (self.gaussian_kernel2_size - 3) / 2, 40, self.on_gaussian2_kernel_size)

        self.preprocess(self.orig_img_crop)
        self.redraw_window()

    def redraw_window(self):
        images = { 0: self.orig_img_crop,
                   1: self.contrast_enhanced_img,
                   2: self.blurred_img,
                   3: self.laplacian,
                   4: self.abs_laplacian,
                   5: self.result }
        img = images.get(self.step)
        cv2.imshow(self.window, img)

    def on_preprocessing_step(self, val):
        self.step = val
        self.redraw_window()

    def on_tile_x(self, val):
        self.tile_x = val
        self.on_tile()

    def on_tile_y(self, val):
        self.tile_y = val
        self.on_tile()

    def on_tile(self):
        self.orig_img_crop = get_tile(self.orig_img, self.tile_x, self.tile_y)
        self.preprocess(self.orig_img_crop)
        self.redraw_window()

    def on_gaussian1_kernel_size(self, val):
        self.gaussian_kernel1_size = 2 * val + 3  # kernel size must be odd, we want it to be at least 4, and opencv trackbars always start at 0, so convert here
        self.preprocess(self.orig_img_crop)
        self.redraw_window()

    def on_gaussian2_kernel_size(self, val):
        self.gaussian_kernel2_size = 2 * val + 3  # kernel size must be odd, we want it to be at least 4, and opencv trackbars always start at 0, so convert here
        self.preprocess(self.orig_img_crop)
        self.redraw_window()

    def on_laplacian_delta(self, val):
        self.laplacian_delta = val-500
        self.preprocess(self.orig_img_crop)
        self.redraw_window()

    def preprocess(self, img):
        # Contrast enhancement
        lo_val, hi_val = self.lo_percentile_val, self.hi_percentile_val
        self.contrast_enhanced_img = enhance_contrast(img, lo_val, hi_val)
        print('Contrast enhanced: shape={} dtype={} min={} max={}'.format(self.contrast_enhanced_img.shape, self.contrast_enhanced_img.dtype, np.min(self.contrast_enhanced_img), np.max(self.contrast_enhanced_img)))

        # Gaussian blurring to remove some of the noise,
        # Needed because afterwards we will use the Laplacian to detect edges,
        # and this is very sensitive to the presence of noise.
        kernel_size = (self.gaussian_kernel1_size, self.gaussian_kernel1_size)  # must be odd
        sigma_x, sigma_y = 0, 0   # 0 means calculate sigma from the kernel size
        self.blurred_img = cv2.GaussianBlur(self.contrast_enhanced_img, kernel_size, sigma_x, sigma_y)

        # Laplacian (of the Gaussian) to detect edges.
        # Note the use of an offset (self.laplacian_delta).
        self.laplacian = cv2.Laplacian(self.blurred_img, cv2.CV_64F, 5, scale=1, delta=self.laplacian_delta)
        print('Laplacian (of Gaussian) 5 scale=1, delta={}: shape={} dtype={} min={} max={}'.format(self.laplacian_delta, self.laplacian.shape, self.laplacian.dtype,
                                                                         np.min(self.laplacian), np.max(self.laplacian)))

        # The Laplacian is now a floating point image, having negative values.
        # Threshold it to positive values to keep only the edges.
        self.abs_laplacian = (self.laplacian > 0).astype(np.uint16) * 65535  # self.laplacian > 0  means edges

        # Perform Gaussian blur on the detected edges, this is needed for the active contours lateron
        # to feel the attraction of an edge even some distance away from the edge.
        kernel_size = (self.gaussian_kernel2_size, self.gaussian_kernel2_size)  # must be odd
        sigma_x, sigma_y = 0, 0   # 0 means calculate sigma from the kernel size
        self.result = cv2.GaussianBlur(self.abs_laplacian, kernel_size, sigma_x, sigma_y)
        print('Gaussian of Laplacian of Gaussian: shape={} dtype={} min={} max={}'.format(self.abs_laplacian.shape, self.abs_laplacian.dtype, np.min(self.abs_laplacian), np.max(self.abs_laplacian)))

        # Convert to 8-bit
        self.result = (self.result / 257).astype(np.uint8)   # Note: 65535 = 255 * 257 (exactly)
        return self.result




# To speedup previewing the result of image processing,
# we only show a chunk (a "tile") of the complete image.
TILE_SIZE = 512

def get_tile(img, tile_x, tile_y):
    img_height, img_width = img.shape
    tile_start_x = tile_x * TILE_SIZE
    tile_start_y = tile_y * TILE_SIZE
    tile_end_x = min((tile_x + 1) * TILE_SIZE, img_width)
    tile_end_y = min((tile_y + 1) * TILE_SIZE, img_height)
    print('Tile x:{}..{} y:{}..{} w={} h={}'.format(tile_start_x, tile_end_x, tile_start_y, tile_end_y, tile_end_x - tile_start_x, tile_end_y - tile_start_y))
    return img[tile_start_y: tile_end_y,
               tile_start_x: tile_end_x]


def get_max_possible_intensity(img):
    if img.dtype == np.uint16:
        return 65535
    elif img.dtype == np.uint8:
        return 255
    else:
        raise RuntimeError('Only 8-bit and 16-bit images are supported.')


def enhance_contrast(img, lo_val, hi_val):
    max_val = float(get_max_possible_intensity(img))

    # note: Numpy subtract() and multiply() perform saturating arithmetic, so we're protected from overflow
    img = cv2.subtract(img, lo_val)
    one = np.ones(img.shape, dtype=img.dtype)
    img = cv2.multiply(img, one, scale=max_val / (hi_val - lo_val))
    return img


def relevant_intensity_range(img, lo_percentile, hi_percentile, plot_histogram=True):
    # Build image histogram
    max_intensity = get_max_possible_intensity(img)
    num_bins = max_intensity + 1
    histogram = cv2.calcHist([img], [0], None, [num_bins], [0, max_intensity])

    # Find intensity value for the low and hi percentiles
    # (e.g. 1 and 99-th percentile, of 0.5 and 99.5th percentile)
    # These percentiles produce better contrast enhancement than just the minimum and maximum image intensity values,
    # because the microscope images often have a thin but very dark border that we want to ignore.
    lo_val = get_histogram_percentile(histogram, lo_percentile)
    hi_val = get_histogram_percentile(histogram, hi_percentile)

    if plot_histogram:
        min_val = np.min(img)
        max_val = np.max(img)
        plt.plot(histogram, '-')
        plt.axvline(min_val, color='b', linestyle=':')
        plt.axvline(max_val, color='b', linestyle=':')
        plt.axvline(lo_val, color='r', linestyle=':')
        plt.axvline(hi_val, color='r', linestyle=':')
        plt.legend(['histogram', 'min', 'max', 'lo percentile', 'hi percentile'])
        plt.xlim([0, max_intensity])
        plt.show()

    return lo_val, hi_val


def get_histogram_percentile(hist, percentile):
    total = np.sum(hist)
    needed = total * (percentile / 100.0)
    running_total = 0
    for i, val in enumerate(hist):
        running_total += val[0]
        if running_total >= needed:
            break
    return i


