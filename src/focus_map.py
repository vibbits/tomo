import sys
import numpy as np

# The naturalneigbor module is not present on e.g. our Windows development machine.
# Fall back to inverse distance weighing as an inferior scattered data interpolation technique in that case.
try:
    from natural_neighbor_interpolator import NaturalNeighborInterpolator
except:
    from inverse_distance_weighing_interpolator import InverseDistanceWeighingInterpolator

class FocusMap:

    def __init__(self, xmin, xmax, ymin, ymax, step):
        self._focus_positions = []  # an unordered list of (x, y, focus z) LM focus positions; each of these was set by the user
        self._interpolator = None
        self._xmin = xmin
        self._ymin = ymin
        self._xmax = xmax
        self._ymax = ymax
        self._step = step

    def get_extent(self):
        return self._xmin, self._xmax, self._ymin, self._ymax

    def add_user_defined_focus_position(self, pos, z):  # pos = (x, y) coordinates of the stage; z = focus
        x, y = pos
        focus_position = (x, y, z)
        self._focus_positions.append(focus_position)
        self._interpolator = None  # there are new data points, so if we already have an interpolator, discard it

    def get_user_defined_focus_positions(self):
        return self._focus_positions

    def reset(self):
        self._focus_positions = []
        self._interpolator = None

    def get_focus_grid(self):
        if self._interpolator is None:
            self._make_interpolator()
        return self._interpolator.get_grid_samples()

    def get_focus_value(self, position):
        if self._interpolator is None:
            self._make_interpolator()
        return self._interpolator.get_position_sample(position)

    def _make_interpolator(self):
        scatter_points = np.array(self._focus_positions)
        known_points = scatter_points[:, 0:2]
        known_values = scatter_points[:, 2]
        if 'naturalneighbor' in sys.modules:
            self._interpolator = NaturalNeighborInterpolator(known_points, known_values)
        else:
            self._interpolator = InverseDistanceWeighingInterpolator(known_points, known_values, k=1.0)

        print('Building focus sample grid using {}'.format(self._interpolator))
        self._interpolator.prepare(self._xmin, self._xmax, self._ymin, self._ymax, self._step)
