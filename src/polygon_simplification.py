# Code for simplifying a polygon with many points to a new polygon
# with fewer points while preserving the general appearance of the polygon.
# Based on https://nl.mathworks.com/matlabcentral/fileexchange/45342-polygon-simplification
# Frank Vernaillen, VIB, August, September 2018

import sys
import math


# input:
# - poly: input polygon (a list of vertex (x,y) pairs)
# - num: desired number of vertices in the reduced polygon
# - acute_threshold: XXXX
# output:
# - output polygon with 'num' vertices (or the input polygon in case it had fewer than 'num' vertices already)
def reduce_polygon(poly, num, acute_threshold = 0):
    numv = len(poly)

    # Calculate initial importance of each vertex
    imp = [vertex_importance(v, poly, numv, acute_threshold) for v in range(0, numv)]

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

        imp[vp] = vertex_importance(vp, poly, numv, acute_threshold)
        imp[vm] = vertex_importance(vm, poly, numv, acute_threshold)

    # Return the reduced polygon
    return poly

# inputs
#    v: index of vertex whose importance we will calculate
#    poly: list [(x,y)] with vertex coordinates; only the first numv element are valid
#    numv: number of vertices in the polygon (poly may have more element near the end, but they are obsolete)
#    acute_threshold: XXXX
# returns:
#    The importance of the vertex (a scalar value).
#    Vertices with low importance are likely to be removed during polygon simplification.
def vertex_importance(v, poly, numv, acute_threshold):
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

        angle = math.acos(a)    # 0 <= angle <= pi
        # print(math.degrees(angle))
        if angle > math.pi - acute_threshold:
            return 0
        else:
            return angle * len1_len2
