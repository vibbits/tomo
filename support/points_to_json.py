import sys

def extract_coords(line):
    vals = line.split()
    x = int(vals[0])
    y = -int(vals[1])
    return (x, y)

def textfile_to_json(filename):
    # Read file
    with open(filename) as fp:
        lines = (line.rstrip() for line in fp) 
        # Strip all empty lines
        lines = list(line for line in lines if line)

    # Take lines by 4, each represents a slice
    i = 0
    done = False

    print('[')
    while not done:
        #
        p1 = extract_coords(lines[i  ])
        p2 = extract_coords(lines[i+1])
        p3 = extract_coords(lines[i+2])
        p4 = extract_coords(lines[i+3])

        # 
        print('[')
        print('  [{}, {}],'.format(p1[0], p1[1]))
        print('  [{}, {}],'.format(p2[0], p2[1]))
        print('  [{}, {}],'.format(p3[0], p3[1]))
        print('  [{}, {}] '.format(p4[0], p4[1]))
        print(']')

        # move to next slice
        i += 4

        # 
        done = (i >= len(lines))
        if not done:
            print(',')  # IMPROVEME: suppress newline
    print(']')

if __name__ == "__main__":
    # IMPROVEME: check arguments, print help if user did not specify argument(s)
    # IMPROVEME: add output file (.json) argument
    # For now, example usage on Windows:
    #   python points_to_json.py F:\Secom\Corners_list_20xlens_tens_of_slices.txt > F:\Secom\Corners_list_20xlens_tens_of_slices.json
    filename = sys.argv[1]
    textfile_to_json(filename)

