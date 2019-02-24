# Parse output from the ImageJ MIST plugin.
# Frank Vernaillen

import sys
import ast
import numpy as np

#TODO: make a class MISTGridInfo, initialized with the GRID output + tile size in pixels + tile overlap in x and y (in pixels or percents?)

class MISTGridInfo:
    def __init__(self, log_filename, tile_size, tile_overlap):
        # tile_size = (tile width, tile height)
        # tile_overlap = (overlap horizontally, overlap vertically)
        assert tile_size[0] > 0
        assert tile_size[1] > 0
        assert tile_overlap[0] > 0
        assert tile_overlap[1] > 0
        parsed_lines = self.process(log_filename)
        self.grid_info = self.get_grid_info(parsed_lines)  # numpy array of (#tiles vertically, #tiles horizontally) containing the tile's top left corner image coordinates (x, y)
        self.tile_size = tile_size
        self.tile_overlap = tile_overlap

    def get_tile_index(self, point):
        # point are the image coordinates of a point in the tiled image; it returns one (row,col) index of one of possibly multiple tiles that contain the given point
        dims = self.grid_info.shape[:2]
        for tile_index in np.ndindex(dims):
            if self.is_inside(point, tile_index):
                return tile_index
        return (-1, -1)  # FIXME - point not in any tile - throw exception instead

    def is_inside(self, point, tile_index):  # point is (x,y)
        tile_top_left = self.grid_info[tile_index]
        xmin = tile_top_left[0]
        ymin = tile_top_left[1]
        xmax = xmin + self.tile_size[0]
        ymax = ymin + self.tile_size[1]
        x, y = point
        print(x,y,xmin,xmax,ymin,ymax)
        return xmin <= x and x <= xmax and ymin <= y and y <= ymax

    def parse_line(self, line):
        # Each line looks like this:
        # file: 20190123-131520-00005x00000-00005x00002.ome.tiff; corr: -1,0000000000; position: (51, 0); grid: (0, 0);
        # This function returns the parsed fields as a dictionary:
        # { 'file': '20190123-131520-00005x00000-00005x00002.ome.tiff', 'corr': -1.0, 'position': (51, 0), 'grid': (0, 0) }
        fields = line.split(';')

        file_keyvalue = fields[0]
        corr_keyvalue = fields[1]
        position_keyvalue = fields[2]
        grid_keyvalue = fields[3]

        # Extract values from the "key: value" strings
        file_value = file_keyvalue[len('file: '):]
        corr_value = self.string_to_float(corr_keyvalue[len(' corr: '):])
        position_value = ast.literal_eval(position_keyvalue[len(' position: '):])
        grid_value = ast.literal_eval(grid_keyvalue[len(' grid: '):])

        # Return the parsed values as a dictionary
        return {'file': file_value,
                'corr': corr_value,
                'position': position_value,
                'grid': grid_value}

    def string_to_float(self, str):
        # returns the float value for a string;
        # the string might use a comma instead of a dot as a decimal separator
        return float(str.replace(',', '.'))

    def process(self, filename):
        with open(filename) as f:
            lines = f.readlines()
            return [self.parse_line(line) for line in lines]

    def get_grid_info(self, parsed_lines):  # parsed_lines is a list of dictionaries; returns a numpy array where each element corrsponds to a MIST tile, and its value is the (x,y) pair of the top-left corner of that MIST tile in the tiled image
        cells = [line['grid'] for line in parsed_lines]
        num_rows = max([row for (col, row) in cells]) + 1
        num_cols = max([col for (col, row) in cells]) + 1
        grid = np.zeros((num_rows, num_cols), dtype=(np.int, 2))
        for line in parsed_lines:
            (col, row) = line['grid']
            (x, y) = line['position']
            grid[row, col] = (x, y)
        return grid


if __name__ == "__main__":
    if len(sys.argv) == 4:
        filename = sys.argv[1]
        size = ast.literal_eval(sys.argv[2])
        overlap = ast.literal_eval(sys.argv[3])

        tile_size = (size, size)  # (tile width, tile height)   # CHECKME: this is an example; are tiles always square?
        tile_overlap = (overlap, overlap)  # (overlap horizontally, overlap vertically)

        grid_info = MISTGridInfo(filename, tile_size, tile_overlap)
        point = (3000, 2000)  # random point for testing
        print(grid_info.get_tile_index(point))
        print(grid_info)
    else:
        print('Usage: mist.py [mist output file.txt tile_size tile_overlap]')
        print('       tile_size: an integer, in pixels; tiles are assumed to be square')
        print('       tile_overlap: an integer, in pixels; tiles are assumed to overlap the same distance horizontally and vertically')
        sys.exit(1)