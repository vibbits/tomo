class Interpolator:
    def __init__(self, known_points, known_values):
        self._known_points = known_points  # shape (n,2)
        self._known_values = known_values  # shape (n,)
        self._grid = None

    def prepare(self, xmin, xmax, ymin, ymax, step):
        pass

    def get_grid_samples(self):
        pass

    def get_position_sample(self, pos):
        pass
