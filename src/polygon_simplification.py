# Code for simplifying a polygon with many points to a new polygon
# with fewer points while preserving the general appearance of the polygon.
# Based on https://nl.mathworks.com/matlabcentral/fileexchange/45342-polygon-simplification
# Frank Vernaillen, VIB, August, September 2018

import sys
import math

# from ij import IJ
# from ij.plugin.frame import RoiManager
# from ij.gui import Roi
# from ij.gui import PolygonRoi



# input:
# - poly: input polygon (a list of vertex (x,y) pairs)
# - num: desired number of vertices in the reduced polygon
# output:
# - output polygon with 'num' vertices (or the input polygon in case it had fewer than 'num' vertices already)
def reduce_polygon(poly, num):
    numv = len(poly)

    # Calculate initial importance of each vertex
    imp = [vertex_importance(v, poly, numv) for v in range(0, numv)]

    # Repeatedly remove the least important vertex until we end up
    # with a reduced polygon with the desired number of vertices.
    while numv > num:
        # Find least important vertex
        _, i = min((imp[i], i) for i in range(0, len(imp)))  # i = argmin(imp) = index in imp with lowest importance

        # Remove least important vertex
        del (poly[i])
        del (imp[i])
        numv = numv - 1

        # Recalculate the importance values of the vertices
        # next to the vertex that was removed
        vm = (i - 1) % numv
        vp = i % numv

        imp[vp] = vertex_importance(vp, poly, numv)
        imp[vm] = vertex_importance(vm, poly, numv)

    # Return the reduced polygon
    return poly

# inputs
#    v: index of vertex whose importance we will calculate
#    poly: list [(x,y)] with vertex coordinates; only the first numv element are valid
#    numv: number of vertices in the polygon (poly may have more element near the end, but they are obsolete)
# returns:
#    The importance of the vertex (a scalar value).
#    Vertices with low importance are likely to be removed during polygon simplification.
def vertex_importance(v, poly, numv):
    # Indices of vertices adjacent to the vertex with index v
    vp = (v + 1) % numv
    vm = (v - 1) % numv

    #
    dir1 = (poly[v][0] - poly[vm][0], poly[v][1] - poly[vm][1])
    dir2 = (poly[vp][0] - poly[v][0], poly[vp][1] - poly[v][1])

    len1 = math.hypot(dir1[0], dir1[1])
    len2 = math.hypot(dir2[0], dir2[1])

    len1_len2 = len1 * len2
    eps = 1.0e-20
    if len1_len2 < eps:
        return 0
    else:
        a = (dir1[0] * dir2[0] + dir1[1] * dir2[1]) / len1_len2

        # Clip a to the domain of acos ([-1, 1]).
        # Due to numeric inaccuracies a is sometimes slightly outside this interval
        a = max(-1, min(a, 1))

        return abs(math.acos(a)) * len1_len2



# def vertex_list_from_roi_polygon(polygon):
#     vertex_list = []
#     for i in range(polygon.npoints):
#         IJ.log("{} {}".format(polygon.xpoints[i], polygon.ypoints[i]))
#         vertex_list.append((polygon.xpoints[i], polygon.ypoints[i]))
#     return vertex_list


# image = IJ.getImage()
# if image == None:
#     sys.exit("No open image")
#
# roi = image.getRoi()
# if roi == None:
#     sys.exit("Image has no ROI")
# old_roi_name = roi.getName()
#
# polygon = roi.getPolygon()
# if polygon == None:
#     sys.exit("ROI has no polygon??")
#
# IJ.log("ROI polygon has {} points".format(polygon.npoints))
# poly = vertex_list_from_roi_polygon(polygon)
#
# # print(poly)
# print("Reducing number of vertices...")
# desired_num_vertices = 4  # desired number of vertices in the reduced polygon
# reduced_poly = reduce_polygon(poly, desired_num_vertices)
#
# # Get a handle to the ROI manager
# roiManager = RoiManager.getInstance()
# if not roiManager:
#     roiManager = RoiManager()
#
# # Add reduced polygon as a new ROI to the ROI manager
# xs, ys = zip(*reduced_poly)
# roi = PolygonRoi(xs, ys, Roi.POLYGON)
# roiManager.addRoi(roi)
# print("Reduced ROI {} to {}".format(old_roi_name, roi.getName()))
# print("Reduced ROI coordinates: {}".format(reduced_poly))
# print("Done")
