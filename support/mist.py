# Parse output from the ImageJ MIST plugin.
# Frank Vernaillen

import sys
import ast
import numpy as np

def parse_line(line):
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
    corr_value = string_to_float(corr_keyvalue[len(' corr: '):])
    position_value = ast.literal_eval(position_keyvalue[len(' position: '):])
    grid_value = ast.literal_eval(grid_keyvalue[len(' grid: '):])

    # Return the parsed values as a dictionary
    return {'file': file_value,
            'corr': corr_value,
            'position': position_value,
            'grid': grid_value}

def string_to_float(str):
    # returns the float value for a string;
    # the string might use a comma instead of a dot as a decimal separator
    return float(str.replace(',', '.'))

def process(filename):
    with open(filename) as f:
        lines = f.readlines()
        return [parse_line(line) for line in lines]

if __name__ == "__main__":
    if len(sys.argv) == 2:
        filename = sys.argv[1]
        parsed_lines = process(filename)
        positions = [line['position'] for line in parsed_lines]
        positions_matrix = np.array(positions)
        print(positions_matrix)
    else:
        print('Usage: mist.py [mist output file.txt]')
        sys.exit(1)