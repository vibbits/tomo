# Prototype tomography with secom
# Frank Vernaillen
# Vlaams Instituut voor Biotechnologie (VIB)
# September 2018

import numpy as np
import subprocess
import cv2
import sys
import os
import re
import json
import math
import time
import wx  # installed on Windows with "conda install -c anaconda wxpython"

# Installing Python packages and setting up environment
#
# 1. Install Miniconda
# 2. conda create -n tomo-py37 python=3.7
# 3. source activate tomo-py37
# 4. pip install numpy
# 5. pip install opencv-python
# 6. conda install -c anaconda wxpython


# OpenCV notes:
# - the origin is in the top-left corner of the image, with the positive y axis pointing down.

# Some useful colors (in BGR)
red = (0, 0, 255)
yellow = (0, 255, 255)
green = (0, 255, 0)

def get_best_window_size(img, max_width = 1800, max_height = 1000):
    """Returns the maximal dimensions of a window that has the same aspect ratio as the image,
       but is no larger than a certain size."""
    yscale = min(1.0, max_height / float(img.shape[0]))
    xscale = min(1.0, max_width / float(img.shape[1]))
    scale = min(xscale, yscale)
    width = int(scale * img.shape[1])
    height = int(scale * img.shape[0])
    return (width, height)

def display(img, title = ''):
    """Display the image in a window, wait for a keypress and close it."""
    cv2.namedWindow(title, cv2.WINDOW_NORMAL)
    width, height = get_best_window_size(img)
    cv2.resizeWindow(title, width, height)

    cv2.moveWindow(title, 0, 0)
    cv2.imshow(title, img)    # IMPROVEME: on Windows we typically have an opencv without Qt support and this window then has no ui controls to zoom/pan
    cv2.waitKey(0)
    cv2.destroyAllWindows()

# Reads the image file 'filename' and returns it as an OpenCV image object.
# filename: full path to the image file
# returns None on error.
def read_image(filename):
    # Read overview image with the ribbon
    # (We read it as a color image so we can draw colored contours on it later.)
    if (cv2.__version__[0] == '2'):
        img = cv2.imread(filename, cv2.CV_LOAD_IMAGE_COLOR)
    else:
        img = cv2.imread(filename, cv2.IMREAD_COLOR)

    return img

def draw_slice_polygons(img, slice_polygons):
    for slice_polygon in slice_polygons:
        # cv2.polylines() expects an array of shape ROWSx1x2,
        # where ROWS is the number of vertices, so reshape the array accordingly
        poly = slice_polygon.reshape((-1, 1, 2))
        cv2.polylines(img, [poly], True, green, thickness = 20)

# Draw the points of interest onto the overview image.
# The first point in points_of_interest is the point-of-interest as specified by the user.
# The other points are the points that were calculated automatically from this first point.
# The original point is drawn in green, the derived points in red.
def draw_points_of_interest(img, points_of_interest):
    mt = cv2.MARKER_CROSS
    cv2.drawMarker(img, tuple(points_of_interest[0].astype(np.int32)), green, markerType = mt, markerSize = 100, thickness = 20)
    for point_of_interest in points_of_interest[1:]:
        cv2.drawMarker(img, tuple(point_of_interest.astype(np.int32)), red, markerType = mt, markerSize = 100, thickness = 20)

# def json_write_polygons(filename, polygon_list):
#     n = len(polygon_list)
#     with open(filename, "w") as f:
#         f.write('[\n')
#         for i in range(0, n):
#             json.dump(polygon_list[i].tolist(), f)
#             if i < n - 1:
#                 f.write(',\n')
#         f.write(']')

# filename: full path to a text file with the slice polygon coordinates
# Returns a Python list of numpy arrays.
# Each numpy array is v x 2, with v the number
# of vertices in the polygon, and the columns representing
# the x,y coordinates of the vertices
def json_load_polygons(filename):
    with open(filename) as f:
        d = json.load(f)
    polygons_list = [np.array(a, dtype = np.int32) for a in d]
    return polygons_list

# Takes the (x, y) coordinates of a point p and of a quadrilateral
# and returns normalized coordinates (xi, eta) of this point
# relative to a square centered on the origin and with corners (-/+1, -/+1).
def normalize_point_position(quad, p):
    # note: y-axis gets flipped
    p_x = p[0]; p_y = -p[1]
    x1 = quad[0][0]; y1 = -quad[0][1]
    x2 = quad[1][0]; y2 = -quad[1][1]
    x3 = quad[2][0]; y3 = -quad[2][1]
    x4 = quad[3][0]; y4 = -quad[3][1]

    A = -x1 + x2 + x3 - x4
    B = -x1 - x2 + x3 + x4
    C =  x1 - x2 + x3 - x4
    D = -y1 + y2 + y3 - y4
    E = -y1 - y2 + y3 + y4
    F =  y1 - y2 + y3 - y4

    G = 4 * p_x - (x1 + x2 + x3 + x4)
    H = 4 * p_y - (y1 + y2 + y3 + y4)

    a = E * C - B * F
    b = F * G + E * A - B * D - C * H
    c = G * D - H * A

    aa = a / min(a, b, c)
    bb = b / min(a, b, c)
    cc = c / min(a, b, c)

    # TODO: check what division by zero in the expressions below means geometrically, and test for it.

    discriminant = bb ** 2 - 4 * aa * cc
    eta = (-bb - math.sqrt(discriminant)) / (2 * aa)
    xi = (G - B * eta) / (A + C * eta)

    print(f"A={A} B={B} C={C} D={D} E={E} F={F} G={G} H={H} a={a} b={b} c={c} a'={aa} b'={bb} c'={cc} raiz={discriminant} eta={eta} xi={xi}")

    return np.array([xi, eta])

# Takes the (x, y) coordinates of a quadrilateral, and the normalized coordinates (xi, eta)
# of a point relative to a square, and returns the (x, y) coordinates of this point when mapped
# onto the quad.
def unnormalize_point_position(quad, p_normalized):
    # note: quad y-axis gets flipped (p_normalized already assumes a flipped y-axis)
    x1 = quad[0][0]; y1 = -quad[0][1]
    x2 = quad[1][0]; y2 = -quad[1][1]
    x3 = quad[2][0]; y3 = -quad[2][1]
    x4 = quad[3][0]; y4 = -quad[3][1]

    xi = p_normalized[0]
    eta = p_normalized[1]

    Ni_1 = (1 - xi) * (1 - eta) / 4.0
    Ni_2 = (1 + xi) * (1 - eta) / 4.0
    Ni_3 = (1 + xi) * (1 + eta) / 4.0
    Ni_4 = (1 - xi) * (1 + eta) / 4.0

    x = Ni_1 * x1 + Ni_2 * x2 + Ni_3 * x3 + Ni_4 * x4
    y = Ni_1 * y1 + Ni_2 * y2 + Ni_3 * y3 + Ni_4 * y4

    print(f"eta={eta} xi={xi} Ni_1={Ni_1} Ni_2={Ni_2} Ni_3={Ni_3} Ni_4={Ni_4} x={x} y={y}")

    return np.array([x, -y])

# Takes a point-of-interest poi relative to quad1,
# and returns the analogous point relative to quad2.
def transform_point(quad1, quad2, poi):
    poi_normalized = normalize_point_position(quad1, poi)
    new_poi = unnormalize_point_position(quad2, poi_normalized)
    return new_poi

# This function takes a point-of-interest (original_point_of_interest) and a list of N
# consecutive slice polygons. It then repeatedly maps the point of interest in one slice
# onto its analogous position in the next slice. A list of N-1 new points of interest
# is returned: the positions of the point-of-interest in slice polygons 2 to N.
# (original_point_of_interest is of course the position in slice polygon 1).
def repeatedly_transform_point(slice_polygons, original_point_of_interest):
    num_slices = len(slice_polygons)
    transformed_points_of_interest = []
    poi = original_point_of_interest
    for i in range(0, num_slices-1):
        poi = transform_point(slice_polygons[i], slice_polygons[i+1], poi)
        transformed_points_of_interest.append(poi)

    return transformed_points_of_interest

# all_points_of_interest: list of poi's, coordinates expressed in pixels of the overview image
# pixelsize_in_microns: physical size of a pixel in the overview image
def physical_point_of_interest_offsets_in_microns(all_points_of_interest, pixelsize_in_microns):
    physical_offsets_microns = []
    prev_poi = all_points_of_interest[0]
    for i in range(0, len(all_points_of_interest)):
        poi = all_points_of_interest[i]
        dx_microns = (poi[0] - prev_poi[0]) * pixelsize_in_microns
        dy_microns = -(poi[1] - prev_poi[1]) * pixelsize_in_microns  # note: flip y-axis once more
        offset_microns = np.array([dx_microns, dy_microns])
        physical_offsets_microns.append(offset_microns)
        prev_poi = poi

    return physical_offsets_microns

# This function uses the Odemis command line tool to repeatedly move the stage and acquire an LM image.
# It assumes that the microscope parameters are already set correctly in Odemis, and that the stage is positioned
# at the initial point of interest. It the repeatedly moves the stage and acquires an LM image. The image is saved
# to 'lm_images_output_folder' with filename lm_images_prefix + number + ome.tiff. The stage movement distances
# are specified in 'physical_offsets_microns'.
# (physical_offsets_microns: an offset per slice; with the first slice always having offset (0,0))
def acquire_light_microscope_images(physical_offsets_microns, delay_between_LM_image_acquisition_secs,
                                    odemis_cli, lm_images_output_folder, lm_images_prefix):
    # Ensure the output folder for LM images exists
    os.makedirs(lm_images_output_folder, exist_ok = True)

    print('Acquiring LM images')
    for i, offset_microns in enumerate(physical_offsets_microns):
        dx_microns, dy_microns = offset_microns
        lm_image_path = os.path.join(lm_images_output_folder, '{}{}.ome.tiff'.format(lm_images_prefix, i))
        commandline_exec([odemis_cli, "--move", "stage", "x", str(dx_microns)])
        commandline_exec([odemis_cli, "--move", "stage", "y", str(dy_microns)])
        commandline_exec([odemis_cli, "--acquire", "ccd", "--output", lm_image_path])
        time.sleep(delay_between_LM_image_acquisition_secs)

# Turns a string like '[0.9999774253040736, -0.006719291795643401, 0.006719291795643401, 0.9999774253040736, 344.7268472712018, 34.41100247082332]'
# into a 2 x 3 numpy array
def matrix_string_to_numpy_array(str):
    elems = str[1:-1].split(',')  # drop [ and ] and split into matrix elements
    nums = [float(e) for e in elems]  # convert from strings to numbers
    a, b, c, d, tx, ty = nums
    return np.array([[a, c, tx], [b, d, ty]])

# The output of the (modified) SIFT registration plugin looks like this:
#    ...
#    Processing SIFT ...
#     took 1873ms.
#    373 features extracted.
#    identifying correspondences using brute force ... took 253ms
#    33 potentially corresponding features identified
#    Slice 3 to 4 transformation: [1.0, 0.0, 0.0, 1.0, 45.05236873053536, 9.754784450831266]    <-- this is a private modification
#    Slice 1 to 4 transformation: [1.0, 0.0, 0.0, 1.0, 93.45191660749424, -5.962104282614291]   <-- this is a private modification
#    Processing SIFT ...
#    ...
# From this text string (sift_plugin_log_string) we extract the transformation matrices
# between slice i and i+1, for all slices. This function returns a list with numpy arrays (of shape 2 x 3)
# representing these transformation matrices.
def extract_sift_alignment_matrices(sift_plugin_log_string):
    # Split the log string in individual lines
    lines = sift_plugin_log_string.splitlines()

    # Keep only the lines mentioning SIFT transformation matrices
    pattern = "^Slice \d+ to \d+ transformation: (\[.+\])"
    trf_lines = [line for line in lines if re.search(pattern, line)]

    # trf_lines now consists of pairs of lines: the first one with info about the transformation
    # between slice i-1 and i, and the second one the transformation between slice 1 and i.
    # We only need the former, so discard every second line.
    trf_lines = trf_lines[::2]   # list[start:end:step]

    # Now extract the transformation matrices as strings
    trf_matrix_strings = [re.search(pattern, trf_line).group(1) for trf_line in trf_lines]

    # Turn matrix strings into 2 x 3 numpy arrays. The 3rd column is the translation vector.
    trf_matrices = [matrix_string_to_numpy_array(str) for str in trf_matrix_strings]
    return trf_matrices

def show_offsets_table(slice_offsets_microns, sift_offsets_microns, combined_offsets_microns):
    num_slices = len(slice_offsets_microns)
    assert(len(sift_offsets_microns) == num_slices)
    assert(len(combined_offsets_microns) == num_slices)
    print('')
    print('      +-----------------------------------------------------------------------------------------------------+')
    print('      |                             Offsets from slice to slice, in micrometer.                             |')
    print('      +---------------------------------+---------------------------------+---------------------------------+')
    print('      |           slice mapping         |               SIFT              |     combined = mapping + SIFT   |')
    print('      |         dx              dy      |         dx              dy      |         dx              dy      |')
    print('+-----+---------------------------------+---------------------------------+---------------------------------+')
    for i in range(0, num_slices):
        print('| {:3d} | {:15f} {:15f} | {:15f} {:15f} | {:15f} {:15f} |'.format(i+1, *slice_offsets_microns[i], *sift_offsets_microns[i], *combined_offsets_microns[i]))
    print('+-----+---------------------------------+---------------------------------+---------------------------------+')

# Execute a shell command (lst) and return (command return code, standard output, standard error).
def commandline_exec(lst):
    print('Command: ' + ' '.join(lst))

    proc = subprocess.Popen(lst, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    out, err = proc.communicate()

    encoding = sys.stdout.encoding  # I'm not sure that this is correct on all platforms
    return (proc.returncode, out.decode(encoding), err.decode(encoding))

def go(delay_between_LM_image_acquisition_secs, fiji, lm_images_output_folder, lm_images_prefix, overview_image_mm_per_pixel,
       odemis_cli, original_point_of_interest, overview_image_path, sift_input_folder, sift_output_folder, sift_images_mm_per_pixel,
       sift_registration_script, slice_polygons_path):

    # Read overview image
    print('Loading ' + overview_image_path)
    img = read_image(overview_image_path)
    if img is None:
        sys.exit('Failed to open {}'.format(overview_image_path))

    # Read slice polygon coordinates
    slice_polygons = json_load_polygons(slice_polygons_path)
    print('Loaded {} slice polygons from {}'.format(len(slice_polygons), slice_polygons_path))

    # Draw the slice polygons onto the overview image
    draw_slice_polygons(img, slice_polygons)

    # Transform point-of-interest from one slice to the next
    print('Original point-of-interest: x={} y={}'.format(*original_point_of_interest))
    transformed_points_of_interest = repeatedly_transform_point(slice_polygons, original_point_of_interest)
    all_points_of_interest = [original_point_of_interest] + transformed_points_of_interest

    # Draw the points of interests (POIs) onto the overview image
    draw_points_of_interest(img, all_points_of_interest)

    display(img, overview_image_path)

    # Display overview image pixel size information
    overview_image_pixelsize_in_microns = 1000.0 / overview_image_mm_per_pixel
    print('Overview image pixel size = {} micrometer = {} mm per pixel'.format(overview_image_pixelsize_in_microns, overview_image_mm_per_pixel))

    # Calculate the physical displacements on the sample required for moving between the points of interest.
    slice_offsets_microns = physical_point_of_interest_offsets_in_microns(all_points_of_interest, overview_image_pixelsize_in_microns)
    print('Rough offset from slice polygons (in microns): '+ repr(slice_offsets_microns))

    # Now acquire an LM image at the point of interest location in each slice.
    acquire_light_microscope_images(slice_offsets_microns, delay_between_LM_image_acquisition_secs,
                                    odemis_cli, lm_images_output_folder, lm_images_prefix)

    # Have Fiji execute a macro for aligning the LM images
    # using Fiji's Plugins > Registration > Linear Stack Alignment with SIFT
    # https://imagej.net/Headless#Running_macros_in_headless_mode
    print('Aligning LM images')
    print('Starting a headless Fiji and calling the SIFT image registration plugin. Please be patient...')
    retcode, out, err = commandline_exec([fiji, "-Dpython.console.encoding=UTF-8", "--ij2", "--headless", "--console", "--run", sift_registration_script, "srcdir='{}',dstdir='{}',prefix='{}'".format(sift_input_folder, sift_output_folder, lm_images_prefix)])
    print('retcode={}\nstdout=\n{}\nstderr={}\n'.format(retcode, out, err))

    # Parse the output of the SIFT registration plugin and extract
    # the transformation matrices to register each slice onto the next.
    print('Extracting SIFT transformation for fine slice transformation')
    sift_matrices = extract_sift_alignment_matrices(out)
    print(sift_matrices)

    # In sift_registration.py we asked for translation only transformations.
    # So our matrices should be pure translations. Extract the last column (=the offset) and convert from pixel
    # coordinates to physical distances on the sample.
    # (We also add a (0,0) offset for the first slice.)
    sift_images_pixelsize_in_microns = 1000.0 / sift_images_mm_per_pixel
    sift_offsets_microns = [np.array([0, 0])] + [mat[:, 2] * sift_images_pixelsize_in_microns for mat in sift_matrices]
    print('Fine SIFT offset (in microns): '+ repr(sift_offsets_microns))

    # Invert y of the SIFT offsets
    sift_offsets_microns = [np.array([offset[0], -offset[1]]) for offset in sift_offsets_microns]
    print('Fine SIFT offset y-inverted (in microns): '+ repr(sift_offsets_microns))

    # Combine (=sum) the rough translations obtained by mapping the slice polygons (of an x20 overview image) onto one another
    # with the fine corrections obtained by SIFT registration of (x100) light microscopy images.
    combined_offsets_microns = [trf_pair[0] + trf_pair[1] for i, trf_pair in enumerate(zip(slice_offsets_microns, sift_offsets_microns))]
    print('Rough offset from slice polygons + fine SIFT offset (in microns): '+ repr(combined_offsets_microns))

    # Show overview of the offsets
    show_offsets_table(slice_offsets_microns, sift_offsets_microns, combined_offsets_microns)

    # TODO? Also acquire EM images? Using combined_offsets_microns?
    # odemis-cli --se-detector --output filename.ome.tiff


class ParametersDialog(wx.Dialog):
    KEY_OVERVIEW_IMAGE_PATH = 'overview_image_path'
    KEY_SLICE_POLYGONS_PATH = 'slice_polygons_path'
    KEY_LM_IMAGES_OUTPUT_FOLDER = 'lm_images_output_folder'
    KEY_ORIGINAL_POI_X = 'original_poi_x'
    KEY_ORIGINAL_POI_Y = 'original_poi_y'
    KEY_LM_ACQUISITION_DELAY = 'lm_acquisition_delay'
    KEY_OVERVIEW_IMAGE_MM_PER_PIXEL = 'overview_image_mm_per_pixel'
    KEY_SIFT_IMAGES_MM_PER_PIXEL = 'sift_images_mm_per_pixel'
    KEY_FIJI_PATH = 'fiji_path'
    KEY_ODEMIS_CLI = 'odemis_cli'
    KEY_SIFT_REGISTRATION_SCRIPT = 'sift_registration_script'
    KEY_LM_IMAGES_PREFIX = 'lm_images_prefix'
    KEY_SIFT_INPUT_FOLDER = 'sift_input_folder'
    KEY_SIFT_OUTPUT_FOLDER = 'sift_output_folder'

    # Model parameters
    _overview_image_path = None
    _slice_polygons_path = None
    _lm_images_output_folder = None
    _original_point_of_interest = np.array([0, 0])
    _delay_between_LM_image_acquisition_secs = 0.0  # time in seconds to pause between successive microscope commands to acquire an LM image (maybe 1 or 2 secs in reality)
    _overview_image_mm_per_pixel = 0.0  # of the e.g. x20 lens overview image
    _sift_images_mm_per_pixel = 0.0 # of the e.g. x100 lens LM images that will be acquired and used for SIFT registration
    _fijiPath = None
    _odemis_cli = None
    _sift_registration_script = None
    _lm_images_prefix = None  # prefix of x100 image filenames
    _sift_input_folder = None
    _sift_output_folder = None

    # persistent parameter storage
    _config = None

    # UI elements
    _odemisCliPathEdit = None
    _overviewImagePathEdit = None
    _slicePolygonsPathEdit = None
    _registrationScriptFileEdit = None
    _lmImagesOutputFolderEdit = None
    _fijiPathEdit = None
    _overviewPixelSizeEdit = None
    _siftInputFolderEdit = None
    _siftOutputFolderEdit = None
    _siftPixelSizeEdit = None
    _prefixEdit = None
    _pointOfInterestXEdit = None
    _pointOfInterestYEdit = None
    _lmAcquisitionDelayText = None
    _goButton = None

    def __init__(self, parent, ID, title, size = wx.DefaultSize, pos = wx.DefaultPosition, style = wx.DEFAULT_DIALOG_STYLE):
        wx.Dialog.__init__(self, parent, ID, title, pos, size, style)

        self._config = wx.Config('be.vib.bits.tomo')
        self._readParameters()

        w = 450  # width for long input fields

        #

        overviewImagePathLabel = wx.StaticText(self, wx.ID_ANY, "Image File:")
        self._overviewImagePathEdit = wx.TextCtrl(self, wx.ID_ANY, self._overview_image_path, size = (w, -1))

        overviewPixelSizeLabel = wx.StaticText(self, wx.ID_ANY, "Pixel size (mm/pixel):")
        self._overviewPixelSizeEdit = wx.TextCtrl(self, wx.ID_ANY, str(self._overview_image_mm_per_pixel), size = (100, -1))

        slicePolygonsPathLabel = wx.StaticText(self, wx.ID_ANY, "Slice Polygons File:")
        self._slicePolygonsPathEdit = wx.TextCtrl(self, wx.ID_ANY, self._slice_polygons_path, size = (w, -1))

        pointOfInterestLabel = wx.StaticText(self, wx.ID_ANY, "Point of Interest (X, Y):")
        self._pointOfInterestXEdit = wx.TextCtrl(self, wx.ID_ANY, str(self._original_point_of_interest[0]), size = (50, -1))
        self._pointOfInterestYEdit = wx.TextCtrl(self, wx.ID_ANY, str(self._original_point_of_interest[1]), size = (50, -1))

        lmImagesOutputFolderLabel = wx.StaticText(self, wx.ID_ANY, "Output Folder:")
        self._lmImagesOutputFolderEdit = wx.TextCtrl(self, wx.ID_ANY, self._lm_images_output_folder, size = (w, -1))

        prefixLabel = wx.StaticText(self, wx.ID_ANY, "Filename Prefix:")
        self._prefixEdit = wx.TextCtrl(self, wx.ID_ANY, self._lm_images_prefix, size = (w, -1))

        lmAcquisitionDelayLabel = wx.StaticText(self, wx.ID_ANY, "Acquisition Delay (sec):")
        self._lmAcquisitionDelayText = wx.TextCtrl(self, wx.ID_ANY, str(self._delay_between_LM_image_acquisition_secs), size = (50, -1))

        #

        siftInputFolderLabel = wx.StaticText(self, wx.ID_ANY, "Input Folder:")
        self._siftInputFolderEdit = wx.TextCtrl(self, wx.ID_ANY, self._sift_input_folder, size = (w, -1))

        siftOutputFolderLabel = wx.StaticText(self, wx.ID_ANY, "Output Folder:")
        self._siftOutputFolderEdit = wx.TextCtrl(self, wx.ID_ANY, self._sift_output_folder, size = (w, -1))

        siftPixelSizeLabel = wx.StaticText(self, wx.ID_ANY, "Pixel size (mm/pixel):")
        self._siftPixelSizeEdit = wx.TextCtrl(self, wx.ID_ANY, str(self._sift_images_mm_per_pixel), size = (100, -1))

        #
        
        fijiPathLabel = wx.StaticText(self, wx.ID_ANY, "Fiji Folder:")
        self._fijiPathEdit = wx.TextCtrl(self, wx.ID_ANY, self._fijiPath, size = (w, -1))

        odemisCliPathLabel = wx.StaticText(self, wx.ID_ANY, "Odemis CLI Tool:")
        self._odemisCliPathEdit = wx.TextCtrl(self, wx.ID_ANY, self._odemis_cli, size = (w, -1))

        registrationScriptFileLabel = wx.StaticText(self, wx.ID_ANY, "Registration Script for Fiji:")
        self._registrationScriptFileEdit = wx.TextCtrl(self, wx.ID_ANY, self._sift_registration_script, size = (w, -1))

        #
        
        pointOfInterestSizer = wx.BoxSizer(wx.HORIZONTAL)
        pointOfInterestSizer.Add(self._pointOfInterestXEdit, flag = wx.ALIGN_CENTER_VERTICAL)
        pointOfInterestSizer.AddSpacer(8)
        pointOfInterestSizer.Add(self._pointOfInterestYEdit, flag = wx.ALIGN_CENTER_VERTICAL)

        #

        self._goButton = wx.Button(self, wx.ID_ANY, "Go!", size = (70, -1))

        # Overview image
        overviewFgs = wx.FlexGridSizer(cols = 2, vgap = 4, hgap = 8)
        overviewFgs.Add(overviewImagePathLabel, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        overviewFgs.Add(self._overviewImagePathEdit, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        overviewFgs.Add(overviewPixelSizeLabel, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        overviewFgs.Add(self._overviewPixelSizeEdit, flag =wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        overviewFgs.Add(slicePolygonsPathLabel, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        overviewFgs.Add(self._slicePolygonsPathEdit, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        overviewFgs.Add(pointOfInterestLabel, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        overviewFgs.Add(pointOfInterestSizer, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        overviewBox = wx.StaticBox(self, -1, 'Overview Image')
        overviewSizer = wx.StaticBoxSizer(overviewBox, wx.VERTICAL)
        overviewSizer.Add(overviewFgs, 0, wx.ALL|wx.CENTER, 10)

        # LM Image Acquisition
        lmFgs = wx.FlexGridSizer(cols = 2, vgap = 4, hgap = 8)
        lmFgs.Add(lmImagesOutputFolderLabel, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lmFgs.Add(self._lmImagesOutputFolderEdit, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lmFgs.Add(prefixLabel, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lmFgs.Add(self._prefixEdit, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lmFgs.Add(lmAcquisitionDelayLabel, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        lmFgs.Add(self._lmAcquisitionDelayText, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        lmBox = wx.StaticBox(self, -1, 'LM Image Acquisition')
        lmSizer = wx.StaticBoxSizer(lmBox, wx.VERTICAL)
        lmSizer.Add(lmFgs, 0, wx.ALL|wx.CENTER, 10)

        # SIFT registration
        siftFgs = wx.FlexGridSizer(cols = 2, vgap = 4, hgap = 8)
        siftFgs.Add(siftInputFolderLabel, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        siftFgs.Add(self._siftInputFolderEdit, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        siftFgs.Add(siftOutputFolderLabel, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        siftFgs.Add(self._siftOutputFolderEdit, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        siftFgs.Add(siftPixelSizeLabel, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        siftFgs.Add(self._siftPixelSizeEdit, flag =wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        siftBox = wx.StaticBox(self, -1, 'SIFT Registration')
        siftSizer = wx.StaticBoxSizer(siftBox, wx.VERTICAL)
        siftSizer.Add(siftFgs, 0, wx.ALL|wx.CENTER, 10)

        # Environment
        envFgs = wx.FlexGridSizer(cols = 2, vgap = 4, hgap = 8)
        envFgs.Add(fijiPathLabel, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        envFgs.Add(self._fijiPathEdit, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        envFgs.Add(odemisCliPathLabel, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        envFgs.Add(self._odemisCliPathEdit, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)
        envFgs.Add(registrationScriptFileLabel, flag = wx.LEFT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        envFgs.Add(self._registrationScriptFileEdit, flag = wx.RIGHT | wx.ALIGN_CENTER_VERTICAL)

        envBox = wx.StaticBox(self, -1, 'Environment')
        envSizer = wx.StaticBoxSizer(envBox, wx.VERTICAL)
        envSizer.Add(envFgs, 0, wx.ALL|wx.CENTER, 10)

        self.Bind(wx.EVT_TEXT, self._onDelayChange, self._lmAcquisitionDelayText)
        self.Bind(wx.EVT_TEXT, self._onOdemisCliPathChange, self._odemisCliPathEdit)
        self.Bind(wx.EVT_TEXT, self._onPrefixChange, self._prefixEdit)
        self.Bind(wx.EVT_TEXT, self._onFijiPathChange, self._fijiPathEdit)
        self.Bind(wx.EVT_TEXT, self._onPoiXChange, self._pointOfInterestXEdit)
        self.Bind(wx.EVT_TEXT, self._onPoiYChange, self._pointOfInterestYEdit)
        self.Bind(wx.EVT_TEXT, self._onOverviewPixelSizeChange, self._overviewPixelSizeEdit)
        self.Bind(wx.EVT_TEXT, self._onRegistrationScriptChange, self._registrationScriptFileEdit)
        self.Bind(wx.EVT_TEXT, self._onSiftInputFolderChange, self._siftInputFolderEdit)
        self.Bind(wx.EVT_TEXT, self._onSiftOutputFolderChange, self._siftOutputFolderEdit)
        self.Bind(wx.EVT_TEXT, self._onSiftPixelSizeChange, self._siftPixelSizeEdit)
        self.Bind(wx.EVT_TEXT, self._onOverviewImagePathChange, self._overviewImagePathEdit)
        self.Bind(wx.EVT_TEXT, self._onSlicePolygonsPathChange, self._slicePolygonsPathEdit)
        self.Bind(wx.EVT_TEXT, self._onLmImagesOutputFolderChange, self._lmImagesOutputFolderEdit)
        self.Bind(wx.EVT_BUTTON, self._onGoButtonClick, self._goButton)

        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(overviewSizer, 0, wx.ALL | wx.EXPAND, border = 5)
        box.Add(lmSizer, 0, wx.ALL | wx.EXPAND, border = 5)
        box.Add(siftSizer, 0, wx.ALL | wx.EXPAND, border = 5)
        box.Add(envSizer, 0, wx.ALL | wx.EXPAND, border = 5)
        box.Add(self._goButton, 0, wx.ALL | wx.CENTER, border = 5)

        self.SetSizer(box)
        box.Fit(self)

        # TODO: make the dialog resizable (add wx.EXPAND to the edit fields that can grow, and use FlexGridSizer.AddGrowableColumn())
        # TODO: quit when user presses the dialog close button (and we haven't started go() yet)
        # TODO: IMPORTANT improvement: especially for the numeric fields, deal with situation where the input field is temporarily empty (while entering a number), and also forbid leaving the edit field if the value is not acceptable (or replace it with the last acceptable value)


    def _readParameters(self):
        self._overview_image_path                     = self._config.Read(ParametersDialog.KEY_OVERVIEW_IMAGE_PATH, r'/home/secom/development/tomo/data/bisstitched-0.tif')
        self._slice_polygons_path                     = self._config.Read(ParametersDialog.KEY_SLICE_POLYGONS_PATH, r'/home/secom/development/tomo/data/bisstitched-0.points.json')
        self._lm_images_output_folder                 = self._config.Read(ParametersDialog.KEY_LM_IMAGES_OUTPUT_FOLDER, r'/home/secom/development/tomo/data/output/LM')
        self._original_point_of_interest[0]           = self._config.ReadInt(ParametersDialog.KEY_ORIGINAL_POI_X, 2417)
        self._original_point_of_interest[1]           = self._config.ReadInt(ParametersDialog.KEY_ORIGINAL_POI_Y, 1066)
        self._delay_between_LM_image_acquisition_secs = self._config.ReadFloat(ParametersDialog.KEY_LM_ACQUISITION_DELAY, 2.0)
        self._overview_image_mm_per_pixel             = self._config.ReadFloat(ParametersDialog.KEY_OVERVIEW_IMAGE_MM_PER_PIXEL, 3077.38542)
        self._fijiPath                                = self._config.Read(ParametersDialog.KEY_FIJI_PATH, r'/home/secom/Downloads/Fiji.app/ImageJ-linux64')
        self._odemis_cli                              = self._config.Read(ParametersDialog.KEY_ODEMIS_CLI, r'/usr/bin/odemis-cli')
        self._sift_registration_script                = self._config.Read(ParametersDialog.KEY_SIFT_REGISTRATION_SCRIPT, r'/home/secom/development/tomo/sift_registration.py')
        self._lm_images_prefix                        = self._config.Read(ParametersDialog.KEY_LM_IMAGES_PREFIX, 'section')
        self._sift_input_folder                       = self._config.Read(ParametersDialog.KEY_SIFT_INPUT_FOLDER, r'/home/secom/development/tomo/data/output/LM')
        self._sift_output_folder                      = self._config.Read(ParametersDialog.KEY_SIFT_OUTPUT_FOLDER, r'/home/secom/development/tomo/data/output/LM')
        self._sift_images_mm_per_pixel                = self._config.ReadFloat(ParametersDialog.KEY_SIFT_IMAGES_MM_PER_PIXEL, 1000.0)  # just a random value, probably not typical

    def _writeParameters(self):
        self._config.Write(ParametersDialog.KEY_OVERVIEW_IMAGE_PATH, self._overview_image_path)
        self._config.Write(ParametersDialog.KEY_SLICE_POLYGONS_PATH, self._slice_polygons_path)
        self._config.Write(ParametersDialog.KEY_LM_IMAGES_OUTPUT_FOLDER, self._lm_images_output_folder)
        self._config.WriteInt(ParametersDialog.KEY_ORIGINAL_POI_X, self._original_point_of_interest[0])
        self._config.WriteInt(ParametersDialog.KEY_ORIGINAL_POI_Y, self._original_point_of_interest[1])
        self._config.WriteFloat(ParametersDialog.KEY_LM_ACQUISITION_DELAY, self._delay_between_LM_image_acquisition_secs)
        self._config.WriteFloat(ParametersDialog.KEY_OVERVIEW_IMAGE_MM_PER_PIXEL, self._overview_image_mm_per_pixel)
        self._config.Write(ParametersDialog.KEY_FIJI_PATH, self._fijiPath)
        self._config.Write(ParametersDialog.KEY_ODEMIS_CLI, self._odemis_cli)
        self._config.Write(ParametersDialog.KEY_SIFT_REGISTRATION_SCRIPT, self._sift_registration_script)
        self._config.Write(ParametersDialog.KEY_LM_IMAGES_PREFIX, self._lm_images_prefix)
        self._config.Write(ParametersDialog.KEY_SIFT_INPUT_FOLDER, self._sift_input_folder)
        self._config.Write(ParametersDialog.KEY_SIFT_OUTPUT_FOLDER, self._sift_output_folder)
        self._config.WriteFloat(ParametersDialog.KEY_SIFT_IMAGES_MM_PER_PIXEL, self._sift_images_mm_per_pixel)
        self._config.Flush()

    def _onGoButtonClick(self, event):
        self.Show(False)
        self._writeParameters()
        go(self._delay_between_LM_image_acquisition_secs, self._fijiPath, self._lm_images_output_folder, self._lm_images_prefix, self._overview_image_mm_per_pixel,
           self._odemis_cli, self._original_point_of_interest, self._overview_image_path, self._sift_input_folder, self._sift_output_folder, self._sift_images_mm_per_pixel,
           self._sift_registration_script, self._slice_polygons_path)
        self.Destroy()

    def _onDelayChange(self, event):
        self._delay_between_LM_image_acquisition_secs = float(self._lmAcquisitionDelayText.GetValue())
        print('_delay_between_LM_image_acquisition_secs={}'.format(self._delay_between_LM_image_acquisition_secs))

    def _onPoiXChange(self, event):
        self._original_point_of_interest[0] = float(self._pointOfInterestXEdit.GetValue())
        print('_original_point_of_interest[0]={}'.format(self._original_point_of_interest[0]))

    def _onPoiYChange(self, event):
        self._original_point_of_interest[1] = float(self._pointOfInterestYEdit.GetValue())
        print('_original_point_of_interest[1]={}'.format(self._original_point_of_interest[1]))

    def _onOverviewPixelSizeChange(self, event):
        self._overview_image_mm_per_pixel = float(self._overviewPixelSizeEdit.GetValue())
        print('_overview_image_mm_per_pixel={}'.format(self._overview_image_mm_per_pixel))

    def _onOdemisCliPathChange(self, event):
        self._odemis_cli = self._odemisCliPathEdit.GetValue()
        print('_odemis_cli={}'.format(self._odemis_cli))

    def _onPrefixChange(self, event):
        self._lm_images_prefix = self._prefixEdit.GetValue()
        print('_lm_images_prefix={}'.format(self._lm_images_prefix))

    def _onFijiPathChange(self, event):
        self._fijiPath = self._fijiPathEdit.GetValue()
        print('_fiji={}'.format(self._fijiPath))

    def _onOverviewImagePathChange(self, event):
        self._overview_image_path = self._overviewImagePathEdit.GetValue()
        print('_overview_image_path={}'.format(self._overview_image_path))

    def _onSlicePolygonsPathChange(self, event):
        self._slice_polygons_path = self._slicePolygonsPathEdit.GetValue()
        print('_slice_polygons_path={}'.format(self._slice_polygons_path))

    def _onLmImagesOutputFolderChange(self, event):
        self._lm_images_output_folder = self._lmImagesOutputFolderEdit.GetValue()
        print('_lm_images_output_folder={}'.format(self._lm_images_output_folder))

    def _onSiftInputFolderChange(self, event):
        self._sift_input_folder = self._siftInputFolderEdit.GetValue()
        print('_sift_input_folder={}'.format(self._sift_input_folder))

    def _onSiftOutputFolderChange(self, event):
        self._sift_output_folder = self._siftOutputFolderEdit.GetValue()
        print('_sift_output_folder={}'.format(self._sift_output_folder))

    def _onSiftPixelSizeChange(self, event):
        self._sift_images_mm_per_pixel = float(self._siftPixelSizeEdit.GetValue())
        print('_sift_images_mm_per_pixel={}'.format(self._sift_images_mm_per_pixel))

    def _onRegistrationScriptChange(self, event):
        self._sift_registration_script = self._registrationScriptFileEdit.GetValue()
        print('_sift_registration_script={}'.format(self._sift_registration_script))

def main():
    # Check that we're running Python 3.6+
    if sys.version_info[0] < 3:
        raise Exception("Must be running Python 3.6 or higher")
    else:
        if sys.version_info[1] < 6:
            raise Exception("Must be running Python 3.6 or higher")

    print('Environment:\n  Python: {}.{}.{}\n  OpenCV: {}\n  wxWindows: {}'.format(*sys.version_info[:3], cv2.__version__, wx.version()))

    app = wx.App()
    dlg = ParametersDialog(None, wx.ID_ANY, "Tomography")
    dlg.CenterOnScreen()
    dlg.Show(True)
    app.MainLoop()

    # # Input parameters # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
    # Frank Windows
    # overview_image_path = r'F:\Secom\sergio_x20_LM_objective_overview_image\bisstitched-0.tif'
    # slice_polygons_path = r'E:\git\bits\bioimaging\Secom\tomo\data\bisstitched-0.points.json'
    # lm_images_output_folder = r'E:\git\bits\bioimaging\Secom\tomo\data\output\LM'
    # original_point_of_interest = np.array([2417, 1066]) #[1205, 996])
    # delay_between_LM_image_acquisition_secs = 0.1  # time in seconds to pause between successive microscope commands to acquire an LM image (maybe 1 or 2 secs in reality)
    # mm_per_pixel = 3077.38542  # of the x20 lens overview image
    # fiji = r'e:\Fiji.app\ImageJ-win64.exe'
    # odemis_cli = r'E:\git\bits\bioimaging\Secom\tomo\odemis-cli.bat'
    # sift_registration_script = r'E:\git\bits\bioimaging\Secom\tomo\sift_registration.py'
    # lm_images_prefix = 'section'                      # prefix = 'lm_slice_'   # prefix of x100 image filenames
    # sift_input_folder = r'F:\Secom\cell1'
    # sift_output_folder = r'F:\Secom\cell1\frank'      # os.path.join(lm_images_output_folder, 'xxxxx')
    #
    # Frank Ubuntu
    # overview_image_path = r'/media/frank/FRANK EXTERNAL/Manual Backups/tomo/data/bisstitched-0.tif'
    # slice_polygons_path = r'/media/frank/FRANK EXTERNAL/Manual Backups/tomo/data/bisstitched-0.points.json'    
    # sift_registration_script = r'/media/frank/FRANK EXTERNAL/sift_registration.py'
    # sift_input_folder = r'/media/frank/FRANK EXTERNAL/Secom/cell1'
    # sift_output_folder = r'/media/frank/FRANK EXTERNAL/Secom/cell1/frank' 
    # fiji = r'/home/frank/Fiji.app/ImageJ-linux64'
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

if __name__ == "__main__":
    main()
