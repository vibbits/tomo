import os
import re
import sys
import cv2
import json
import time
import numpy as np
import subprocess

# # Some useful colors (in BGR)
# red = (0, 0, 255)
# yellow = (0, 255, 255)
# green = (0, 255, 0)

# def get_best_window_size(img, max_width = 1800, max_height = 1000):
#     """Returns the maximal dimensions of a window that has the same aspect ratio as the image,
#        but is no larger than a certain size."""
#     yscale = min(1.0, max_height / float(img.shape[0]))
#     xscale = min(1.0, max_width / float(img.shape[1]))
#     scale = min(xscale, yscale)
#     width = int(scale * img.shape[1])
#     height = int(scale * img.shape[0])
#     return (width, height)

# def display(img, title = ''):
#     """Display the image in a window, wait for a keypress and close it."""
#     cv2.namedWindow(title, cv2.WINDOW_NORMAL)
#     width, height = get_best_window_size(img)
#     cv2.resizeWindow(title, width, height)
#
#     cv2.moveWindow(title, 0, 0)
#     cv2.imshow(title, img)    # IMPROVEME: on Windows we typically have an opencv without Qt support and this window then has no ui controls to zoom/pan
#     cv2.waitKey(0)
#     cv2.destroyAllWindows()

# # Reads the image file 'filename' and returns it as an OpenCV image object.
# # filename: full path to the image file
# # returns None on error.
# def read_image(filename):
#     # Read overview image with the ribbon
#     # (We read it as a color image so we can draw colored contours on it later.)
#     if (cv2.__version__[0] == '2'):
#         img = cv2.imread(filename, cv2.CV_LOAD_IMAGE_COLOR)
#     else:
#         img = cv2.imread(filename, cv2.IMREAD_COLOR)
#
#     return img

# def draw_slice_polygons(img, slice_polygons):
#     for slice_polygon in slice_polygons:
#         # cv2.polylines() expects an array of shape ROWSx1x2,
#         # where ROWS is the number of vertices, so reshape the array accordingly
#         poly = slice_polygon.reshape((-1, 1, 2))
#         cv2.polylines(img, [poly], True, green, thickness = 20)

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
# Each numpy array is v x 2, with v the number
# of vertices in the polygon, and the columns representing
# the x,y coordinates of the vertices
def json_load_polygons(filename):
    with open(filename) as f:
        d = json.load(f)
    polygons_list = [np.array(a, dtype = np.int32) for a in d]
    return polygons_list

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

# This function uses the Odemis command line tool to repeatedly move the stage and acquire an LM or EM image.
# It assumes that the microscope parameters are already set correctly in Odemis, and that the stage is positioned
# at the initial point of interest. It the repeatedly moves the stage and acquires an LM/EM image. The image is saved
# to 'images_output_folder' with filename images_prefix + number + ome.tiff. The stage movement distances
# are specified in 'physical_offsets_microns'.
# (physical_offsets_microns: an offset per slice; with the first slice always having offset (0,0))
# The 'mode' must be 'EM' or 'LM' to acquire electron resp. light microscope images.
def acquire_microscope_images(mode, physical_offsets_microns, delay_between_image_acquisition_secs,
                              odemis_cli, images_output_folder, images_prefix):

    # Ensure that the output folder for the images exists
    os.makedirs(images_output_folder, exist_ok = True)

    print('Acquiring {} images'.format(mode))
    for i, offset_microns in enumerate(physical_offsets_microns):
        # Move the stage
        move_stage(odemis_cli, offset_microns)

        # Acquire an LM/EM image and save it to the output folder
        image_path = os.path.join(images_output_folder, '{}{}.ome.tiff'.format(images_prefix, i))
        if mode == "LM":
            commandline_exec([odemis_cli, "--acquire", "ccd", "--output", image_path])
        else:  # EM
            commandline_exec([odemis_cli, "--se-detector", "--output", image_path])

        # Wait a short time for the image acquisition to finish
        # CHECKME: Is this needed? Maybe odemis_cli will automatically buffer commands until it is finished?
        time.sleep(delay_between_image_acquisition_secs)

def move_stage(odemis_cli, offset_microns):
    dx_microns, dy_microns = offset_microns
    commandline_exec([odemis_cli, "--move", "stage", "x", str(dx_microns)])
    commandline_exec([odemis_cli, "--move", "stage", "y", str(dy_microns)])


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
