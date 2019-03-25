# Frank Vernaillen
# Simple script for combining overlapping image tile into a larger image.
# No registration is performed whatsoever, the tiles are simply pasted
# together based on their assumed x,y position in a rectangular array.
# No flat-field correction is performed either.
# Typically the merged image will have visible tiling artefacts.

import numpy as np
import tools

num_tiles_x = 20
num_tiles_y = 10
tile_width = 2048
tile_height = 2048
overlap_percent = 20
folder = 'E:\\git\\bits\\bioimaging\\Secom\\overview_images\\20x10'
output_file = 'E:\\merged.tiff'

# Predict size of merged image
overlap_x = int(tile_width * overlap_percent / 100)
overlap_y = int(tile_height * overlap_percent / 100)
trimmed_tile_width = tile_width - overlap_x
trimmed_tile_height = tile_height - overlap_y
width = num_tiles_x * tile_width - overlap_x * (num_tiles_x - 1)
height = num_tiles_y * tile_height - overlap_y * (num_tiles_y - 1)

# Create empty image. We'll paste the tile onto this "canvas".
merged_img = np.zeros((height, width), np.uint16)

# Paste each of the tiles onto the empty image
for y in range(num_tiles_y):
    for x in range(num_tiles_x):
        path = folder + '\\' + '20190322-152756-{:05d}x{:05d}.tiff'.format(x, y)
        img = tools.read_image_as_grayscale(path)
        i = trimmed_tile_height * y
        j = trimmed_tile_width * x
        print('y={} x={} tile_height={} tile_width={} imgw={} imgh={}'.format(y, x, tile_height, tile_width, img.shape[1], img.shape[0]))
        merged_img[i:i+tile_height, j:j+tile_width] = img

# Save the merged image to file
print('Saving...')
tools.save_image(merged_img, output_file)
print('Saved!')