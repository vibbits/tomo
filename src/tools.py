import os
import re
import sys
import cv2
import json
import time
import numpy as np
import subprocess

# # Some useful colors (in BGR) for OpenCV
# red = (0, 0, 255)
# yellow = (0, 255, 255)
# green = (0, 255, 0)


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


def read_image(filename):
    """
    Reads an image file and returns it as an OpenCV image object.
    :param filename: full file path of the image to read
    :return: an OpenCV image object, or None on error
    """
    # Read overview image with the ribbon
    # (We read it as a color image so we can draw colored contours on it later.)
    if (cv2.__version__[0] == '2'):
        img = cv2.imread(filename, cv2.CV_LOAD_IMAGE_COLOR)
    else:
        img = cv2.imread(filename, cv2.IMREAD_COLOR)

    return img


def read_grayscale_image(filename):
    img = cv2.imread(filename)
    print(img.shape)
    return img


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


# def is_inside(polygon, point):
#     inside = cv2.pointPolygonTest(polygon, point, measureDist = False)
#     return inside >= 0


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
        cv2.polylines(img, [poly], True, green, thickness = 20)

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
    polygons_list = [np.array(a, dtype = np.int32) for a in d]
    if opencv_style:
        polygons_list = [np.expand_dims(a, axis = 1) for a in polygons_list]
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
        print('| {:3d} | {:15f} {:15f} | {:15f} {:15f} | {:15f} {:15f} |'.format(i+1, slice_offsets_microns[i][0], slice_offsets_microns[i][1],
                                                                                      sift_offsets_microns[i][0], sift_offsets_microns[i][1],
                                                                                      combined_offsets_microns[i][0], combined_offsets_microns[i][1]))
    print('+-----+---------------------------------+---------------------------------+---------------------------------+')


# Execute a shell command (lst) and return (command return code, standard output, standard error).
def commandline_exec(lst):
    print('Command: ' + ' '.join(lst))

    proc = subprocess.Popen(lst, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    out, err = proc.communicate()

    encoding = sys.stdout.encoding  # I'm not sure that this is correct on all platforms
    return proc.returncode, out.decode(encoding), err.decode(encoding)
