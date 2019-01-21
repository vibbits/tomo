
import numpy as np
from interpolator import Interpolator

# Reference:
# Scattered data interpolation methods for electronic imaging systems: a survey
# Isaac Amidror
# Journal of Electronic Imaging 11(2), 157--176 (April 2002)
# http://molly.magic.rit.edu/~mac/test/paper_pdf.pdf
# We do inverse distance weighing, see section 3 in this paper.

# Note: we could also use the MetPy package:
# https://unidata.github.io/MetPy/latest/api/generated/metpy.interpolate.inverse_distance_to_points.html#metpy.interpolate.inverse_distance_to_points

class InverseDistanceWeighingInterpolator(Interpolator):

    def __init__(self, known_points, known_values, k=1.0):
        Interpolator.__init__(self, known_points, known_values)
        # k: exponent for inverse distance weighing function; k >= 1; larger k yields an interpolated surface with bigger "plateaus" around the sample points
        assert k >= 1.0
        self._k = k

    def prepare(self, xmin, xmax, ymin, ymax, step):
        # Prepare a rectangular grid of interpolated values
        self._xmin = xmin
        self._ymin = ymin
        # self._xmax = xmax
        # self._ymax = ymax
        self._step = step

        xrange = np.arange(xmin, xmax, step)
        yrange = np.arange(ymin, ymax, step)  # CHECKME: includes endpoint? if not, should we include it? perhaps np.linspace(min, max, num_samples) is more predictable in terms of the number of samples

        self._grid = np.zeros((len(yrange), len(xrange)))

        for i, y in enumerate(yrange):
            for j, x in enumerate(xrange):
                pos = np.array([x, y])
                val = self.get_position_sample(pos)
                self._grid[i, j] = val

    def get_grid_samples(self):
        return self._grid

    def get_position_sample(self, pos):

        if len(self._known_points) == 0:
            return None

        posi = self._known_points
        di = np.sqrt(np.sum((posi - pos) ** 2, axis = 1))  # di = Euclidean distance from pos to each data point

        # Check for the special case where pos is really close to a data point, because there d ~= 0 and h ~= infinite.
        index = np.argmin(di)
        di_min = di[index]
        eps = 1.0e-9
        if di_min < eps:
            z = self._known_values[index]   # pos is very close to a data point, simply return its z
        else:
            hi = 1.0 / (di ** self._k) # hi = array with inverse distances
            wi = hi / np.sum(hi)       # wi = array with interpolation weights
            # print(np.sum(wi))        # FOR TESTING - SHOULD BE 1
            zi = self._known_values    # zi = array with sample data z
            z = np.dot(wi, zi)         # z = inverse distance weighted

        return z
