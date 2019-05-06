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

    def __str__(self):
        s = 'Focus map area:\nx={} to {}\ny={} to {}\nstep size={}\n\n'.format(self._xmin, self._xmax, self._ymin, self._ymax, self._step)
        s = s + 'Focus samples:\n'
        for x, y, z in self._focus_positions:
            s = s + 'x={} y={} z={}\n'.format(x, y, z)
        return s

    @classmethod
    def load(cls, filename):
        # Construct a FocusMap object from the text file with the given filename.
        # The file's contents look like this:
        #
        #    xmin xmax ymin ymax stepsize
        #    x1 y1 z1
        #    ...
        #    xn yn zn
        #
        # Lines starting with (optional) whitespace followed by a hash sign are ignored (useful for comments).
        # Lines with only whitespace are ignored as well.

        # Read the focus map text file
        with open(filename) as f:
            lines = f.readlines()

        # Parse the focus map text lines

        # Discard empty lines and comment lines. Comment lines start with a hash sign.
        lines = [line for line in lines if not (line.lstrip().startswith('#') or len(line.strip()) == 0)]

        # Read extent and stepsize
        xmin, xmax, ymin, ymax, step = [float(val) for val in lines[0].split()]

        # Read focus values
        focus_data = []
        for line in lines[1:]:
            x, y, z = [float(val) for val in line.split()]
            focus_data.append((x, y, z))

        # Construct the focus map
        focusmp = cls(xmin, xmax, ymin, ymax, step)
        for focus in focus_data:
            focusmp.add_user_defined_focus_position((focus[0], focus[1]), focus[2])
        return focusmp
