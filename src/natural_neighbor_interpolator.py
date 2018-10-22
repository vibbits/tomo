
import numpy as np

from metpy.interpolate.points import natural_neighbor_to_points


class NaturalNeighborInterpolator:
    _data = []
    def __init__(self, data):
        """
        XXXXX
        :param data: an n x 3 numpy array; each row is a data point, and the columns are x, y and z respectively; given a new (x,y) we want to calculate an interpolated z
        """
        self._data = data

    def interpolate(self, pos):
        """
        XXXX
        :param pos:
        :param eps:
        :return:
        """
        points = self._data[:, 0:2]  # coordinates of the scatter points
        values = self._data[:, 2]    # values at these scatter points
        xi = np.array([pos])         # position where we need an interpolated value (stored in a 2d array because the metpy api allows for requesting interpolated values at multiple points with one call)

        result = natural_neighbor_to_points(points, values, xi)
        return result[0]


if __name__ == '__main__':
    # NOTE: There are at least two issues with natural neighbor interpolation:
    #       1. Metpy's implementation fails for some trivial but symmetrical cases (see the example below).
    #       2. It does not provide an answer for points outside the convex hull of scatter points. (see example below - nan interpolated values)
    data = np.array([[   0.0,     0, 0.0],
                     [  95.0,     0, 2.0],   # with [99.0, 0, 2.0] we get a ZeroDivisionError in circumcenter
                     [   0.0, 105.0, 5.0],
                     [ 100.0, 100.0, 1.0]])
    print(data)

    nni = NaturalNeighborInterpolator(data)

    p1 = np.array([  1,   3]); print(p1, nni.interpolate(p1))
    p3 = np.array([100, 100]); print(p3, nni.interpolate(p3))

    p2 = np.array([50, 50]); print(p2, nni.interpolate(p2))
    p4 = np.array([  200,   200]); print(p4, nni.interpolate(p4))
    p5 = np.array([ 2000,  2000]); print(p5, nni.interpolate(p5))


