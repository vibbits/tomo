
import numpy as np
import naturalneighbor
from interpolator import Interpolator

# https://github.com/innolitics/natural-neighbor-interpolation
# pip install naturalneighbor
# (Works on Linux. On Windows the C++ part of the package fails to compile because Visual Studio for Python
# does not have C++11 threads support, it seems.)

class NaturalNeighborInterpolator(Interpolator):

    def prepare(self, xmin, xmax, ymin, ymax, step):
        self._xmin = xmin
        self._ymin = ymin
        # self._xmax = xmax
        # self._ymax = ymax
        self._step = step

        # The natural neighbor interpolation library that we use only works for 3D data,
        # so we must add a dummy 3rd dimension to our 2D data.
        dummy = np.zeros((self._known_points.shape[0], 1))
        points = np.hstack((self._known_points, dummy))

        # Interpolate at all positions in a rectangular grid
        # (note again the dummy 3rd dimension).
        zmin, zmax, zstep = 0, 1, 1
        grid = [[xmin, xmax, step], [ymin, ymax, step], [zmin, zmax, zstep]]
        nn = naturalneighbor.griddata(points, self._known_values, grid) ## CHECKME: does this include the end point?

        # Drop dummy 3rd dimension from the result
        self._grid = nn[:, :, 0].T    # CHECKME: we can probably avoid the transpose if we build the grid differently

    def get_grid_samples(self):
        return self._grid

    def get_position_sample(self, pos):
        # Note: interpolating just a single point via the naturalneighbor package does not seem to be possible; apparently the library cannot handle it / is not designed for it.
        # So to obtain samples a any position, we first calculate interpolated points on a rather dense grid, and then interpolate between these grid values to obtain an interpolated value at non-grid positions too.
        assert self._grid is not None, "The interpolation grid was not initialized yet. Maybe prepare() did not get called?"
        x, y = pos[0], pos[1]
        xindex = int((x - self._xmin) / self._step)
        yindex = int((y - self._ymin) / self._step)
        # TODO: maybe use bilinear interpolation instead?
        return self._grid[xindex, yindex]
