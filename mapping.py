# Frank Vernaillen, Sergio Gabarre
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import math
import numpy as np

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

# This function takes a starting point and a list of N
# consecutive quadss. It then repeatedly maps the point from one quad
# onto its analogous position in the next quad. A list of N-1 new points
# is returned: the positions of the points in quads 2 to N.
# (starting_point is of course the position in quad 1).
def repeatedly_transform_point(quads, starting_point):
    num_quads = len(quads)
    transformed_points = []
    p = starting_point
    for i in range(0, num_quads-1):
        p = transform_point(quads[i], quads[i + 1], p)
        transformed_points.append(p)

    return transformed_points