# Prototype tomography with secom
# Frank Vernaillen
# September 2018

import numpy as np
import cv2
import sys
import os
import re
import json
import math
import time
import subprocess

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

# XXX
# physical_offsets_microns: an offset per slice; with the first slice always having offset (0,0)
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

# XXXX
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

def main():
    # Check that we're running Python 3.6+
    if sys.version_info[0] < 3:
        raise Exception("Must be running Python 3.6 or higher")
    else:
        if sys.version_info[1] < 6:
            raise Exception("Must be running Python 3.6 or higher")

    print('Using Python {}.{}.{} and OpenCV {}'.format(*sys.version_info[:3], cv2.__version__))

    # Input parameters # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
    # TODO: add user interface that pops up a dialog asking the user for these input values (and saves them as defaults for next time)
    overview_image_path = r'F:\Secom\sergio_x20_LM_objective_overview_image\bisstitched-0.tif'
    slice_polygons_path = r'E:\git\bits\bioimaging\Secom\tomo\data\bisstitched-0.points.json'
    lm_images_output_folder = r'E:\git\bits\bioimaging\Secom\tomo\data\output\LM'
    original_point_of_interest = np.array([2417, 1066]) #[1205, 996])
    delay_between_LM_image_acquisition_secs = 0.1  # time in seconds to pause between successive microscope commands to acquire an LM image (maybe 1 or 2 secs in reality)
    mm_per_pixel = 3077.38542  # of the x20 lens overview image
    fiji = r'e:\Fiji.app\ImageJ-win64.exe'
    odemis_cli = r'E:\git\bits\bioimaging\Secom\tomo\odemis-cli.bat'
    sift_registration_script = r'E:\git\bits\bioimaging\Secom\tomo\sift_registration.py'
    lm_images_prefix = 'section'                      # prefix = 'lm_slice_'   # prefix of x100 image filenames
    sift_input_folder = r'F:\Secom\cell1'
    sift_output_folder = r'F:\Secom\cell1\frank'      # os.path.join(lm_images_output_folder, 'xxxxx')
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

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

    display(img, 'test')

    # Display overview image pixel size information
    pixelsize_in_microns = 1000.0 / mm_per_pixel
    print('Overview image pixel size = {} micrometer = {} mm per pixel'.format(pixelsize_in_microns, mm_per_pixel))

    # Calculate the physical displacements on the sample required for moving between the points of interest.
    slice_offsets_microns = physical_point_of_interest_offsets_in_microns(all_points_of_interest, pixelsize_in_microns)
    print('Rough offset from slice polygons (in microns): '+ repr(slice_offsets_microns))

    # Now acquire an LM image at the point of interest location in each slice.
    acquire_light_microscope_images(slice_offsets_microns, delay_between_LM_image_acquisition_secs,
                                    odemis_cli, lm_images_output_folder, lm_images_prefix)

    # Have Fiji execute a macro for aligning the LM images
    # using Fiji's Plugins > Registration > Linear Stack Alignment with SIFT
    # https://imagej.net/Headless#Running_macros_in_headless_mode
    print('Aligning LM images')
    print('Starting a headless Fiji and calling the SIFT image registration plugin. Please be patient...')
    retcode, out, err = commandline_exec([fiji, "-Dpython.console.encoding=UTF-8", "--ij2", "--headless", "--run", sift_registration_script, "'srcdir=\"{}\",dstdir=\"{}\",prefix=\"{}\"'".format(sift_input_folder, sift_output_folder, lm_images_prefix)])
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
    sift_offsets_microns = [np.array([0, 0])] + [mat[:, 2] * pixelsize_in_microns for mat in sift_matrices]
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


if __name__ == "__main__":
    main()
