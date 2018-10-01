
# Experiment for detecting and isolating sample slices in a ribbon
# Frank Vernaillen
# April 2018

# Ideas:
# - https://www.math.uci.edu/icamp/summer/research_11/park/shape_descriptors_survey_part3.pdf

# TODO
# - approximate each slice by a trapezoid
# - connect slices back into ribbons (via shared edge)
# - output the slices (note: corresponding points of the trapezoid are given in same order)
# - transformation of each (trapezoid) slice into the next slice (Sergio)

import numpy as np
import networkx as nx
import cv2
import sys
import math
import time

# Setup code for memoization
# (see @memory.cache decorator below)
from tempfile import mkdtemp
from joblib import Memory
cachedir = mkdtemp()
memory = Memory(cachedir=cachedir, verbose=0)

# Some useful colors (in BGR)
red = (0, 0, 255)
yellow = (0, 255, 255)
green = (0, 255, 0)

# OpenCV notes:
# - the origin is in the top-left corner of the image, with the positive y axis pointing down.
# - segmented contours are oriented clockwise

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
    cv2.imshow(title, img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def simplify_contours(contours, eps, closed = True):
    return [cv2.approxPolyDP(cnt, eps, closed) for cnt in contours]

def contour_center(contour):
    """Returns the centroid of the contour."""
    M = cv2.moments(contour)
    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
    return (cx, cy)

def extract_subcontour(cnt, start_index, end_index):
    num_points = len(cnt)
    assert (start_index >= 0) and (start_index < num_points)
    assert (end_index >= 0) and (end_index < num_points)
    cnt = np.roll(cnt, -start_index, axis=0)
    n = (end_index + num_points - start_index) % num_points
    return cnt[0 : (n + 1)]

def difference_area(cnt, template_cnt):  # large difference means dissimilar contours, small difference values for similar contours
    area = cv2.contourArea(cnt)
    template_area = cv2.contourArea(template_cnt)
    return abs(area - template_area)

def difference_hu(cnt, template_cnt): # doesn't work *at all* (maybe because of the scale invariance?)
    d = cv2.matchShapes(cnt, template_cnt, method = 3, parameter = 0) # cv2.CONTOURS_MATCH_I3) #.CV_CONTOURS_MATCH_I2)  # the lower the matchShapes() result, the more similar
    return d

def get_contour_descriptors(cnt):
    rect = cv2.minAreaRect(cnt)
    width, height = rect[1]   # CHECKME: rect is (cx,cy),(width,height),angle
    if height > width:
        t = width
        width = height
        height = t
    areasqrt = math.sqrt(cv2.contourArea(cnt))
    # print('{} {} {}'.format(width, height, areasqrt))
    return (width, height, areasqrt)

def difference(cnt, template_cnt):
    (cnt_w, cnt_h, cnt_as) = get_contour_descriptors(cnt)
    (template_w, template_h, template_as) = get_contour_descriptors(template_cnt)
    return (template_w - cnt_w)**2 + (template_h - cnt_h)**2 + (template_as - cnt_as)**2

def is_left_turn(p1, p2, p3):  # p1, p2, p3 are numpy vectors of (x,y) points
    return np.cross((p2 - p1), (p3 - p2)) < 0

# Returns whether the cnt is concave at point i
# (=if it has an indentation at the point with index i of its contour).
# Points on contour are assumed to be in clockwise order
# (on a coordinate system with origin at the top left and y-axis pointing down)
def is_concave(cnt, i):
    n = len(cnt)
    p1 = cnt[(i - 1 + n) % n]
    p2 = cnt[i]
    p3 = cnt[(i + 1) % n]
    return not is_left_turn(p1, p2, p3)  # FIXME FIXME -  need to define orientation and axes up/down

def best_split_in_two(cnt, template_cnt):
    num_points = len(cnt)
    best_split_indices = None
    best_difference = 1.0e10
    # Try out all pairs of vertices as a split line
    # and perform the split such that the chunk we clip off
    # resembles the template slice as much as possible.
    for i in range(0, num_points):   # i = 0, 1, ..., num_points-1
        for j in range(0, i):        # j = 0, 1, ..., i - 1
            if (abs(i-j) == 1) or (abs(i-j) == num_points - 1):
                continue  # skip, this wouldn't really cut off anything

            if (not is_concave(cnt, i)) or (not is_concave(cnt, j)):
                continue  # skip, the trapezoid slice shape implies inward corners between consecutive slices; so for efficiency we only consider cuts there.

            # POSSIBLE IMPROVEME
            # If line i-j intersects the contour itself,
            # then reject it as a split line. We didn't implement this
            # because the contours are most of the time so well behaved
            # that this happens only infrequently.

            chunk = extract_subcontour(cnt, i, j)
            chunk_error = difference(chunk, template_cnt)
            if chunk_error < best_difference:
                best_split_indices = (i, j)
                best_difference = chunk_error

    if best_split_indices is None:
        print('BAM! Bug!')
    (i0, i1) = best_split_indices
    cnt1 = extract_subcontour(cnt, i0, i1)
    cnt2 = extract_subcontour(cnt, i1, i0)
    return (cnt1, cnt2)

def greedy_contour_segmentation_into_slices(cnt, template_contour):
    slices = []

    cnt_area = cv2.contourArea(cnt)
    template_area = cv2.contourArea(template_contour)

    # FIXME: code below is sloppy
    if (len(cnt) == 3):
        # cnt is a triangle, can't subdivide further
        slices.append(cnt)
    elif (cnt_area > template_area * 0.5) and (cnt_area < template_area * 1.5):
        slices.append(cnt)
    else:
        while (len(cnt) > 3) and (cnt_area >= 1.5 * template_area):
            (cnt1, cnt2) = best_split_in_two(cnt, template_contour)
            slices.append(cnt1)
            cnt = cnt2
            cnt_area = cv2.contourArea(cnt)
        slices.append(cnt2)

    return (None, slices)

# Returns a (cost value, list of slice contours) for the
# optimal split of cnt into contours of the slices
@memory.cache
def best_contour_segmentation_into_slices(cnt, template_slice_contour):

    cost_nosplit = difference(cnt, template_slice_contour)

    best_cost = cost_nosplit
    best_split = [cnt]

    num_points = len(cnt)
    if num_points > 120:
        return (best_cost, best_split)

    # Note: A possible performance improvement is to assume no ribbon contains more than x slices,
    #       and to not try to subdivide any further if we've hit x slices already.

    # Try out all pairs of vertices as a split line
    for i in range(0, num_points):   # i = 0, 1, ..., num_points-1
        for j in range(0, i):        # j = 0, 1, ..., i - 1
            if (abs(i-j) == 1) or (abs(i-j) == num_points - 1):
                continue  # skip, this wouldn't really cut off anything

            if (not is_concave(cnt, i)) or (not is_concave(cnt, j)):
                continue

            chunk1 = extract_subcontour(cnt, i, j)
            chunk2 = extract_subcontour(cnt, j, i)

            # Assume the first contour is a single slice.
            # (we don't lose generality because all possible chunks are considered, so also the chunk that is a single slice)
            cost1 = difference(chunk1, template_slice_contour)
            slices1 = [chunk1]

            if cost1 >= best_cost:
                continue

            (cost2, slices2) = best_contour_segmentation_into_slices(chunk2, template_slice_contour)
            if cost1 + cost2 < best_cost:
                best_cost = cost1 + cost2
                best_split = slices1 + slices2

    return (best_cost, best_split)

def segment_contours_into_slices(contours, template_slice_contour, junk_contours = [], greedy = False):
    """Returns a list of ribbons, where each ribbon is a list of slice contours.
    The list of slice contours in each ribbon is ordered in the same order they are physically connected.
    """
    ribbons = []

    num_contours = len(contours)
    for i, cnt in enumerate(contours):
        print('Processing contour {}/{} ({} vertices)'.format(i, num_contours-1, len(cnt)))
        if i in junk_contours:
            print('   Skipped')
        else:
            t0 = time.clock()
            if greedy:
                (_, new_ribbon) = greedy_contour_segmentation_into_slices(cnt, template_slice_contour)
            else:
                (_, new_ribbon) = best_contour_segmentation_into_slices(cnt, template_slice_contour)
            ribbons.append(new_ribbon)
            t1 = time.clock()
            print('   {} slice(s), {:.1f} sec'.format(len(new_ribbon), t1-t0))

    # At this point the slices in each ribbon are ordered randomly.
    # We now reorder them so that consecutive slices in the ribbon are also
    # physically connected in the same order.
    # TODO ribbons = [order_slices_sequentially(ribbon) for ribbon in ribbons]

    return ribbons

# def order_slices_sequentially(ribbon):
#     """Given a ribbon (an unordered list of slices), it returns
#     the same ribbon but with the slices ordered sequentially. (In the same order that the slices are connected physically).
#  #   TODO: what about the (exceptional) case of a slice that has more than two neighboring slices?"""
#
#  #   TODO TODO
#
#     G = nx.Graph()
#     for slice_idx, slice in enumerate(ribbon):
#         n = len(slice)
#         for i in range(0, n):
#             x1 = slice[i      ][0]
#             y1 = slice[i      ][1]
#             x2 = slice[(i+1)%n][0]
#             y2 = slice[(i+1)%n][1]
#             p1 = (x1, y1)
#             p2 = (x2, y2)
#             if G.has_edge(p1, p2):
#                 # append slice_idx to the edge attr
#                 # attr.append(slice_idx)
#                 pass
#             else:
#                 G.add_edge(p1, 2)
#                 # create new edge with [slice_idx] as attribute
#                 pass
#             # if coords in pts:
#             #     pts[coords].append(slice_idx)
#             # else:
#             #     pts[coords] = [slice_idx]
#
#     # build a graph
#     for k, v in pts.items():
#         G.add_edge()
#
#     print(pts)
#
#     return ribbon

def draw_contour_vertices(img, contours, color):
    for cnt in contours:
        for i, pt in enumerate(cnt):  # pt is a 1x2 matrix with the vertex coordinates, so [[x, y]]
            x = pt[0][0]
            y = pt[0][1]
            cv2.circle(img, (x, y), 3, color)

def draw_contour_numbers(img, contours, color, font_scale = 1.0, thickness = 1):
    """Draw the index number of each contour on the image."""
    for i, cnt in enumerate(contours):
        #print('{} {}'.format(i, cnt))
        (cx, cy) = contour_center(cnt)
        cv2.putText(img, str(i), (int(cx - 5 * font_scale) , int(cy + 5 * font_scale)), cv2.FONT_HERSHEY_PLAIN, font_scale, color, thickness)

def read_image(filename):
    # Read overview image with the ribbon
    # (We read it as a color image so we can draw colored contours on it later.)
    if (cv2.__version__[0] == '2'):
        img = cv2.imread(filename, cv2.CV_LOAD_IMAGE_COLOR)
    else:
        img = cv2.imread(filename, cv2.IMREAD_COLOR)

    if img is None:
        sys.exit('Failed to open {}'.format(filename))
    return img

def extract_contours(img, threshold = 128, min_contour_area = 0, contour_simplification_eps = 10):
    # Convert to grayscale, needed for thresholding
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Threshold the image (values lower then threshold become 0, higher become 255)
    _, img_thresh = cv2.threshold(img_gray, threshold, 255, cv2.THRESH_BINARY)
    # display(img_thresh, 'Thresholded image')

    # Find the contours
    if (cv2.__version__[0] == '2'):
        contours, _ = cv2.findContours(img_thresh, cv2.RETR_LIST, method=cv2.CHAIN_APPROX_SIMPLE)
    else:
        _, contours, _ = cv2.findContours(img_thresh, cv2.RETR_LIST, method=cv2.CHAIN_APPROX_SIMPLE)

    # Discard contours with a small area
    contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_contour_area]

    # Draw contours on top of the original image
    imgc = img.copy()
    cv2.drawContours(imgc, contours, -1, red, 1)
    display(imgc, 'Detected contours')

    # Simplify the contours
    simple_contours = simplify_contours(contours, contour_simplification_eps)

    return simple_contours

def segment_image(filename, threshold = 128, min_contour_area = 0, contour_simplification_eps = 10, template_contour = None, junk_contours = [], greedy = True):
    img = read_image(filename)
    print('Input image: shape={} type={}'.format(img.shape, img.dtype))
    display(img, 'Input image')

    simple_contours = extract_contours(img, threshold, min_contour_area, contour_simplification_eps)

    # # Show contour info
    # template_area = cv2.contourArea(template_contour)
    # for i, cnt in enumerate(simple_contours):
    #     cnt_area = cv2.contourArea(cnt)
    #     print('Contour {}: area={} num_slices_estimate={:2f}'.format(i, cnt_area, cnt_area / template_area))

    # Draw the result: original image + simplified contours + contour endpoints
    imgc = img.copy()
    cv2.drawContours(imgc, simple_contours, -1, yellow, 1)
    # draw_contour_vertices(imgc, simple_contours, yellow)
    draw_contour_numbers(imgc, simple_contours, yellow)
    # display(imgc, 'Detected contours')

    # Isolate the individual slices
    ribbons = segment_contours_into_slices(simple_contours, template_contour, junk_contours, greedy)

    # Flatten the list with ribbons with slices, into a list of slices.
    slices = [slice for ribbon in ribbons for slice in ribbon]

    # Draw the slices
    cv2.drawContours(img, slices, -1, green, thickness=1)
    display(img, 'Detected slices')

def main():
    print('Using OpenCV version {}'.format(cv2.__version__))

    template_contour = np.array([[[246, 1401]],
                                 [[266, 1429]],
                                 [[203, 1457]],
                                 [[197, 1422]]])

    # TODO: we may need to pick a contour_simplification_eps which results in a certain maximum number of points
    # (since too many points will result in a very slow non-greedy algorithm) - this eps value can probably be different for each ribbon contour?

    greedy = False
    if greedy:
        junk_contours = [1,2,3,18,16]
        segment_image('/home/frank/Pictures/sampleholder_with_slices1.png',
                      threshold = 144,
                      min_contour_area = 1000,
                      contour_simplification_eps = 3,  # the slices are rather small, so we need  a small eps value or we end up approximating the ribbon by a long quadrilateral
                      template_contour = template_contour,
                      junk_contours = junk_contours,  # some contours are junk (but some have many points, so we skip those for performance)
                      greedy = greedy)
    else:
        # threshold = 138; junk_contours = [1, 2, 3, 17]
        threshold = 142; junk_contours = [1, 2, 3, 18, 16] # threshold = 142 or 144 (142 is faster, 144 slower - takes about 90 sec on my laptop)
        # threshold = 130; junk_contours = []
        segment_image('/home/frank/Pictures/sampleholder_with_slices1.png',
                      threshold = threshold,
                      min_contour_area = 1000,
                      contour_simplification_eps = 2, # 3 also works  # the slices are rather small, so we need  a small eps value or we end up approximating the ribbon by a long quadrilateral
                      template_contour = template_contour,
                      junk_contours = junk_contours,  # some contours are junk (but some of it with many points, so we skip those for performance)
                      greedy = greedy)

if __name__ == "__main__":
    main()
