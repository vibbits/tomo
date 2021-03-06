from __future__ import print_function  # so we can use Python 3's print('something', end='') to avoid newline
import re
import sys
import cv2
import json
import wx
import numpy as np
import subprocess

# We need the Python2 backport pathlib2 (instead of pathlib)
# so we can use the exist_ok parameter of mkdir()
from pathlib2 import Path

# # Some useful colors (in BGR) for OpenCV
# red = (0, 0, 255)
# yellow = (0, 255, 255)
# green = (0, 255, 0)


def get_best_window_size(img, max_width=1800, max_height=1000):
    """Returns the maximal dimensions of a window that has the same aspect ratio as the image,
       but is no larger than a certain size."""
    yscale = min(1.0, max_height / float(img.shape[0]))
    xscale = min(1.0, max_width / float(img.shape[1]))
    scale = min(xscale, yscale)
    width = int(scale * img.shape[1])
    height = int(scale * img.shape[0])
    return (width, height)


def display(img, title=''):
    """Display the image in a window, wait for a keypress and close it."""
    cv2.namedWindow(title, cv2.WINDOW_NORMAL)
    width, height = get_best_window_size(img)
    cv2.resizeWindow(title, width, height)

    cv2.moveWindow(title, 0, 0)
    cv2.imshow(title, img)    # IMPROVEME: on Windows we typically have an opencv without Qt support and this window then has no ui controls to zoom/pan
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def opencv_contour_to_list(contour):
    """
    :param contour: a numpy array of shape (numvertices, 1, 2); a list of such contours is returned by cv2.findContours()
    :return: a list of (x,y) coordinates representing the contour
    """
    return [(v[0][0], v[0][1]) for v in contour]


def list_to_opencv_contour(coords_list):
    """
    :param coords_list: a list of (x,y) coordinates
    :return: a numpy array of shape (numvertices, 1, 2); a list of such contours can be drawn using cv2.drawContours()
    """
    return np.expand_dims(np.asarray(coords_list), axis = 1)


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


def read_image_as_color_image(filename):
    """
    Reads an image file and returns it as an OpenCV image object.
    :param filename: full file path of the image to read
    :return: an OpenCV _color_ image object, or None on error
    """
    # Read overview image with the ribbon
    # (We read it as a color image so we can draw colored contours on it later.)
    if cv2.__version__[0] == '2':
        img = cv2.imread(filename, cv2.CV_LOAD_IMAGE_COLOR)
    else:
        img = cv2.imread(filename, cv2.IMREAD_COLOR)

    return img


def read_image_as_grayscale(filename, flags=cv2.IMREAD_GRAYSCALE):
    """
    Reads an image file and returns it as an OpenCV image object.
    This may be preferable over reading it through wxPython since (I think) wxPython expands grayscale images to RGB,
    and this is not ideal since we are dealing with potentially large images.
    :param filename: full file path of the image to read
    :param flags: XXX e.g. cv2.IMREAD_GRAYSCALE to convert image to grayscale after reading;
                           cv2.IMREAD_ANYDEPTH to preserve 16-bit images as 16-bit (otherwise we get 8-bit automatically)
    :return: An OpenCV grayscale image object, or None on error.
             The image is indexed like this: img[y, x].
    """
    img = cv2.imread(filename, flags)
    return img

def save_image(image, filename):
    """
    :param image: the image data as a numpy array (8-bit and 16-bit grayscale images are supported, when saving to TIFF)
    :param filename: filename to save the image to; extension determines the file format type
    :return: True if saving was successful, False otherwise
    """
    assert len(image.shape) == 2  # only grayscale has been tested
    return cv2.imwrite(filename, image)


def sample_image(image, pos):
    """
    Returns the pixel value in the image at a given position. The position can be specified with sub-pixel accuracy,
    the pixel value is then estimated via bilinear interpolation of the 4 surrounding pixels.
    :param image: an OpenCV grayscale image, image[0][0] is the top left pixel, the first index is the y-coordinate, y-axis points down
    :param pos: (x, y) position in the image; x and y are floating point; x=horizontal, y=vertical; origin is at the top left of image, y-axis is running down.
    :return: the (interpolated) pixel value
    """

    # Clip pos to image boundaries
    # We clip the right and bottom edges by 'eps' to make it easier for the code below to handle the case where pos=(_, image_width-1) or (image_height-1, _).
    eps = 1e-4
    image_height, image_width = image.shape
    pos[0] = max(0, min(pos[0], image_width-1-eps))
    pos[1] = max(0, min(pos[1], image_height-1-eps))

    # Find interpolation factors
    x_left = int(pos[0])
    y_top = int(pos[1])

    x_right = x_left + 1
    y_bottom = y_top + 1

    x_fraction = float(pos[0] - x_left)
    y_fraction = float(pos[1] - y_top)

    assert 0.0 <= x_fraction < 1.0001
    assert 0.0 <= y_fraction < 1.0001

    # Note the conversion from unsigned byte pixels to float for safe calculations
    val_tl = float(image[y_top][x_left])
    val_tr = float(image[y_top][x_right])
    val_bl = float(image[y_bottom][x_left])
    val_br = float(image[y_bottom][x_right])

    # Bilinear interpolation (val is the image intensity)
    val_top    = val_tl + x_fraction * (val_tr - val_tl)
    val_bottom = val_bl + x_fraction * (val_br - val_bl)
    val = val_top + y_fraction * (val_bottom - val_top)
    return val


def polygon_area(polygon):  # polygon is a list of (x,y) coordinates
    pts = np.asarray(polygon).astype(np.float)
    pts = np.vstack([pts, pts[0]])  # close the polygon (TODO: check if open or not, or document requirement for open)
    area = 0
    for i in range(0, pts.shape[0]-1):
        x1 = pts[i  ][0]
        x2 = pts[i+1][0]
        y1 = pts[i  ][1]
        y2 = pts[i+1][1]
        area += x1 * y2 - x2 * y1
    return area / 2.0


def polygon_center(polygon):
    """
    Calculate the center of mass of a polygon.
    :param polygon: a list of (x,y) coordinates of the vertices
    :return: the center of mass (cx, cy) of the polygon
    """
    pts = np.asarray(polygon).astype(np.float)
    pts = np.vstack([pts, pts[0]]) # close the polygon (TODO: check if open or not, or document requirement for open)
    cx = 0
    cy = 0
    for i in range(0, pts.shape[0]-1):
        x1 = pts[i  ][0]
        x2 = pts[i+1][0]
        y1 = pts[i  ][1]
        y2 = pts[i+1][1]
        cross = (x1 * y2 - x2 * y1)
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross

    six_area = 6.0 * polygon_area(polygon)
    return (cx / six_area, cy / six_area)


# Example usage of pointPolygonTest():
# >>> cnt = np.array([[1,1],[10,50],[50,50]], dtype=np.int32)
# >>> cv2.pointPolygonTest(cnt, (40,40),True)
# -0.0
# >>> cv2.pointPolygonTest(cnt, (40,45),True)
# 3.5355339059327378
# >>> cv2.pointPolygonTest(cnt, (200,45),True)
# -150.08331019803634
# >>> cv2.pointPolygonTest(cnt, (40,45),False)
# 1.0
# >>> cv2.pointPolygonTest(cnt, (40,33345),False)
# -1.0
#
# Assuming a coordinate system where the y-axis points down (and x to the right),
# and the contour's vertices are specified in counter-clockwise order, then:
#
#                                         < 0 means the point is outside the contour
#    cv2.pointPolygonTest(contour, point) = 0 means the point is on contour
#                                         >  0 means the point is inside the contour
#

def is_strictly_inside(polygon, point):
    inside = cv2.pointPolygonTest(polygon, point, measureDist=False)
    return inside > 0


def polygons_hit(polygons, point):
    """
    :param point: x,y coordinates of the point to check (a tuple, not a numpy array)
    :return: a list with the (0-based) index of all the polygons containing the given point.
             The list can contain 0 polygon indices (point not in any of the polygons),
             1 index (the point is inside exactly one polygon and it overlaps with no other polygons),
             or more polygon indices (some polygons overlap and the point is inside them).
    """
    hit = []
    for i, polygon in enumerate(polygons):
        cnt = np.array(polygon, dtype=np.int32)
        if is_strictly_inside(cnt, point):
            hit.append(i)
    return hit


def is_point_in_rect(point, rect):
    # rect: a pair (p1, p2) of opposite corners of a rectangle; p1 and p2 are numpy arrays of [x, y] coordinates
    # point: a numpy array [x, y] of point's coordinates
    x = point[0]
    y = point[1]
    xmin = min(rect[0][0], rect[1][0])
    xmax = max(rect[0][0], rect[1][0])
    ymin = min(rect[0][1], rect[1][1])
    ymax = max(rect[0][1], rect[1][1])
    return x >= xmin and x <= xmax and y >= ymin and y <= ymax

def is_polygon_inside_rect(polygon, rect):
    # returns (True/False) whether all vertices of polygon are inside a given axis-aligned rectangle
    # rect: a pair (p1, p2) of opposite corners of a rectangle; p1 and p2 are numpy arrays of [x, y] coordinates
    for point in polygon:
        if not is_point_in_rect(point, rect):
            return False
    return True


# def interpolate_along_line_segment(pos1, val1, pos2, val2, pos):
#     """
#     Returns a scalar value linearly interpolated between val1 and val2.
#     :param pos1: numpy array; x,y coords of starting point of line segment
#     :param val1: scalar value at starting point
#     :param pos2: numpy array; x,y coords of end point of line segment
#     :param val2: scalar value at end point
#     :param pos: numpy array; x,y coords of point where we want to estimate an interpolated scalar value
#     :return:
#     """
#     segment_length = np.linalg.norm(pos2, pos1)
#     if segment_length < 1e-10:
#         return (val1 + val2) / 2.0
#     else:
#         proj_length = np.dot(pos - pos1, pos2 - pos1) / segment_length  # distance to pos1 of pos projected onto the line pos1-pos2
#         t = proj_length / segment_length
#         t = min(1, max(0, t))   # clamp t to [0, 1]
#         return val1 + t * (val2 - val1)


def draw_slice_polygons(img, slice_polygons):
    green = (0, 255, 0)
    for slice_polygon in slice_polygons:
        # cv2.polylines() expects an array of shape ROWSx1x2,
        # where ROWS is the number of vertices, so reshape the array accordingly
        poly = slice_polygon.reshape((-1, 1, 2))
        cv2.polylines(img, [poly], True, green, thickness=20)

# # Draw the points of interest onto the overview image.
# # The first point in points_of_interest is the point-of-interest as specified by the user.
# # The other points are the points that were calculated automatically from this first point.
# # The original point is drawn in green, the derived points in red.
# def draw_points_of_interest(img, points_of_interest):
#     mt = cv2.MARKER_CROSS
#     cv2.drawMarker(img, tuple(points_of_interest[0].astype(np.int32)), green, markerType = mt, markerSize = 100, thickness = 20)
#     for point_of_interest in points_of_interest[1:]:
#         cv2.drawMarker(img, tuple(point_of_interest.astype(np.int32)), red, markerType = mt, markerSize = 100, thickness = 20)


# filename: full path to a text file with the slice polygon coordinates
# Returns a Python list of numpy arrays.
# Each numpy array is v x 2 (if opencv_style=False) or v x 1 x 2 (if opencv_style=True),
# with v the number of vertices in the polygon, and the columns representing
# the x,y coordinates of the vertices
def json_load_polygons(filename, opencv_style = False):
    with open(filename) as f:
        d = json.load(f)
    polygons_list = [np.array(a, dtype=np.int32) for a in d]
    if opencv_style:
        polygons_list = [np.expand_dims(a, axis=1) for a in polygons_list]
    return polygons_list


# filename: full path of the text file with the slice polygon coordinates
# polygons_list: a list of polyons. Each polygon is itself a list of (x,y) coordinates of its vertices.
def json_save_polygons(filename, polygons_list):
    # We want this:
    #    with open(filename, 'w') as f:
    #        json.dump(polygons_list, f, indent = 4)
    # but with more flexibility in formatting (x,y on one line) and no issues with numpy data types such as int32 not being JSON serializable
    with open(filename, 'w') as f:
        f.write('[\n')
        for i, polygon in enumerate(polygons_list):
            f.write('[\n')
            for j, vertex in enumerate(polygon):
                x, y = vertex
                f.write('[{}, {}]'.format(x, y))
                if j < len(polygon) - 1:
                    f.write(',')
                f.write('\n')
            f.write(']')
            if i < len(polygons_list) - 1:
                f.write(',')
            f.write('\n')
        f.write(']\n')


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


# Turns a string like '[[0.999948185933372, -0.010179658567826, 2.748126743432709], [0.010179658567826, 0.999948185933372, -5.932567328680079]]'
# into the corresponding 2x3 numpy array.
def matrix_string_to_numpy_array(s):
    elems = s.replace(',', ' ').replace('[', ' ').replace(']', ' ').split()
    nums = [float(e) for e in elems]  # convert from strings to numbers
    a, b, tx, c, d, ty = nums
    return np.array([[a, b, tx], [c, d, ty]])


# Tomo supports two different registration plugins: "Linear stack alignment with SIFT" and "StackReg".
#
# The output of the Linear Stack Alignment with SIFT registration plugin (mpicbg_-1.4.1.jar) looks like this:
#    ...
#    Processing SIFT ...
#     took 1261ms.
#    3261 features extracted.
#    Processing SIFT ...
#     took 884ms.
#    3415 features extracted.
#    59 potentially corresponding features identified
#    Transformation Matrix: AffineTransform[[0.999948185933372, -0.010179658567826, 2.748126743432709], [0.010179658567826, 0.999948185933372, -5.932567328680079]]
#    Processing SIFT ...
#     took 906ms.
#    3381 features extracted.
#    58 potentially corresponding features identified
#    Transformation Matrix: AffineTransform[[0.999997767563037, -0.002113023649348, 1.841657708433971], [0.002113023649348, 0.999997767563037, 2.378823142381009]]
#    ...
#
# The output of StackReg patched to output the transformation matrice looks like this:
#    ...
#    [INFO] Reading available sites from https://imagej.net/
#    Transformation Matrix: AffineTransform[[0.9998568836986051, 0.01691780483732866, 23.78881976316677], [-0.01691780483732866, 0.9998568836986051, 43.48101306132037]]
#    Transformation Matrix: AffineTransform[[0.9999992150826272, 0.0012529302173312933, 34.948131111836915], [-0.0012529302173312933, 0.9999992150826272, 30.13283233002437]]
#    Transformation Matrix: AffineTransform[[0.9999975340031375, 0.002220807880910907, -37.83548181304559], [-0.002220807880910907, 0.9999975340031375, 39.439221764493595]]
#    ...
#
# From these text strings (registration_plugin_log_string) we extract the transformation matrices between successive slices.
# This function returns a list with numpy arrays (of shape 2 x 3) representing these transformation matrices.
#
def extract_registration_matrices(registration_method, registration_plugin_log_string):
    assert registration_method == 'SIFT' or registration_method == 'Stackreg'

    # Split the log string in individual lines
    lines = registration_plugin_log_string.splitlines()

    # Keep only the lines mentioning transformation matrices
    pattern = "^Transformation Matrix: AffineTransform(\[.+\])"
    trf_lines = [line for line in lines if re.search(pattern, line)]

    # Extract the transformation matrices as strings
    trf_matrix_strings = [re.search(pattern, trf_line).group(1) for trf_line in trf_lines]

    # Turn matrix strings into 2x3 numpy arrays
    trf_matrices = [matrix_string_to_numpy_array(s) for s in trf_matrix_strings]

    if registration_method == 'SIFT':
        # The matrices are actually the transformation matrix from section i+1 to section i, invert each of them to get
        # the transformation matrix from section i to section i+1, which is what we need.
        trf_matrices = [invert_2_by_3_matrix(mat) for mat in trf_matrices]

    return trf_matrices


def invert_2_by_3_matrix(mat):
    # mat is a 2x3 matrix with an implicit [0 0 1] bottom third row;
    # this function returns its inverse matrix, also with an implied [0 0 1] bottom row.
    full_mat = np.vstack((mat, np.array([0, 0, 1])))
    inv_mat = np.linalg.inv(full_mat)
    return inv_mat[0:2, :]   # return the top two rows; the bottom row is an implicit [0 0 1]


# Example output of show_offsets_table(). The number of columns is variable.
#
#       +-----------------------------------------------------------------------------------------------------+
#       |                             Offsets from slice to slice, in micrometer.                             |
#       +-----------------------------------------------------------------------------------------------------+
#       |          Slice mapping          |      LM SIFT registration       |               Sum               |
#       |       dx              dy        |       dx              dy        |       dx              dy        |
# +-----+-----------------------------------------------------------------------------------------------------+
# |   0 |        0.000000        0.000000 |        0.000000        0.000000 |        0.000000        0.000000 |
# |   1 |      -11.507879     -353.818638 |       -1.150788      -35.381864 |      -12.658667     -389.200502 |
# |   2 |      -10.600406     -354.364418 |       -1.060041      -35.436442 |      -11.660446     -389.800860 |
# |   3 |      -13.941941     -354.864500 |       -1.394194      -35.486450 |      -15.336135     -390.350950 |
# |   4 |      -10.531486     -351.935047 |       -1.053149      -35.193505 |      -11.584634     -387.128552 |
# |   5 |      -22.577733     -352.312350 |       -2.257773      -35.231235 |      -24.835507     -387.543585 |
# +-----+-----------------------------------------------------------------------------------------------------+
#
def show_offsets_table(all_offsets_microns, combined_offsets_microns):
    num_offsets = len(all_offsets_microns)
    assert num_offsets > 0

    num_slices = len(all_offsets_microns[0]['offsets'])
    assert num_slices > 0

    # Note: the values 31 and 33 below are because of the 15 character width used for printing dx and dy.
    hline_length = 33 * (num_offsets + 1) + num_offsets
    hline = '-' * hline_length
    hline_long = '+-----+{}+'.format(hline)

    # Print table title
    print('      +{}+'.format(hline))
    print('      |{:^{w}}|'.format('Offsets from slice to slice, in micrometer.', w=hline_length))
    print('      +{}+'.format(hline))

    # Print headers for the different offset correction columns
    print('      |', end='')
    for offset in range(num_offsets):
        print(' {:^31} |'.format(all_offsets_microns[offset]['name']), end='')
    print(' {:^31} |'.format('Sum'))

    print('      |', end='')
    for offset in range(num_offsets + 1):
        print(' {:^15} {:^15} |'.format('dx', 'dy'), end='')
    print()

    # Print correction offsets for each section and for each correction offset (+combined offsets)
    print(hline_long)
    for slice in range(num_slices):
        # Print slice number
        print('| {:3d} |'.format(slice), end='')

        # Print offset for each correction
        for offset in range(num_offsets):
            dx, dy = all_offsets_microns[offset]['offsets'][slice]
            print(' {:15f} {:15f} |'.format(dx, dy), end='')

        # Print combined offset (=sum of offsets)
        dx, dy = combined_offsets_microns[slice][0], combined_offsets_microns[slice][1]
        print(' {:15f} {:15f} |'.format(dx, dy))
    print(hline_long)


# Execute a shell command (lst) and return (command return code, standard output, standard error).
def commandline_exec(lst):
    print('Command: ' + ' '.join(lst))

    proc = subprocess.Popen(lst, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()

    encoding = sys.stdout.encoding  # I'm not sure that this is correct on all platforms
    return proc.returncode, out.decode(encoding), err.decode(encoding)


def make_dir(dir, parents=True, exist_ok=True):
    """
    Creates a directory on the file system.
    :param dir: full path of the directory to create
    :param parents: if true, all intermediate directories will be created too if they don't exist yet
    :param exist_ok: if true, it is not an error for the directory to exist already
    """
    Path(dir).mkdir(parents=parents, exist_ok=exist_ok)


# # Small helper class to work around the issue where wx.BusyInfo(message) method pops up a box without the actual message.
# # Only after calling wx.Yield() does the message text get drawn inside the box. Similarly, 'del' on the wx.BusyInfo object only
# # removes the dialog from the screen after wx.Yield() is called. (This is for wxPython 3 classic; in wxPython 4 Phoenix wx.Yield()
# # does not seem to be required.)
# # NOTE: AFTER ALL THIS DOES NOT SEEM TO WORK IN TOMO,
# # EVEN THOUGH IT SEEMS TO WORK IN A SMALL TEST (ADMITTEDLY ON THE PYTHON COMMAND LINE).
# class BusyInfo:
#     def __init__(self, message):
#         self.dialog = wx.BusyInfo(message)
#         wx.Yield()
#
#     def close(self):
#         del self.dialog
#         wx.Yield()


