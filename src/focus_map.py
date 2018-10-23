import numpy as np
from inverse_distance_weighing_interpolator import InverseDistanceWeighingInterpolator

class FocusMap:
    _focus_positions = []  # an unordered list of (x, y, focus z) LM focus positions; each of these was set by the user

    def add_user_defined_focus_position(self, pos, z):  # pos = (x, y) coordinates of the stage; z = focus
        x, y = pos
        focus_position = (x, y, z)
        self._focus_positions.append(focus_position)

    def get_user_defined_focus_positions(self):
        return self._focus_positions

    def reset(self):
        self._focus_positions = []

    def get_focus(self, point):
        """
        Estimates the focus z-value at a given position on the sample based on surrounding user-specified focus z values.
        :param point: (x,y) pair; coordinates of position where we want to estimate the focus z-value
        :return: the (possibly estimated) focus z-value, or None if no z value could be estimated
        """
        scatter_points = np.array(self._focus_positions)
        idwi = InverseDistanceWeighingInterpolator(scatter_points, k = 1.0)
        z = idwi.interpolate(np.array(point))
        return z
