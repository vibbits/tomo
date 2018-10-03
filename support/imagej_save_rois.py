
# This is a script/macro for Fiji/ImageJ for saving the coordinates of ROIs to a text file.
#
# How to use:
# 1. Start ImageJ
# 2. Add ROIs to ROI manager via whatever means you like
# 3. Run this script: Plugins > Macros > Run... and select this Python script in the file browser
# 4. The script will pop up a file browser. Specify the output file for the ROIs. Press "Open". The coordinates of all
#    ROI polygons will be save to a text file in JSON format.
#
# Frank Vernaillen
# VIB - Vlaams Instituut voor Biotechnologie
# October 2018


from ij import IJ
from ij.plugin.frame import RoiManager
import sys

rm = RoiManager.getInstance()
if rm == None:
	rm = RoiManager()

rois = rm.getRoisAsArray()
if rois == None or len(rois) == 0:
	sys.exit('The ROI manager has no ROIs')

filename = IJ.getFilePath('Specify the output file for the ROIs in JSON format (e.g. myrois.json)')
if filename == None:
	sys.exit('ROI saving canceled by the user.')

# Save the ROIs as JSON arrays
IJ.log("Saving {} ROIs to {}".format(len(rois), filename))
with open(filename, 'w') as f:
	f.write('[\n')
	for i, roi in enumerate(rois):
		polygon = roi.getPolygon()
		f.write('[\n')
		for j in range(polygon.npoints):
			f.write('[{}, {}]'.format(polygon.xpoints[j], polygon.ypoints[j]))
			if j < polygon.npoints - 1:
				f.write(',')
			f.write('\n')
		f.write(']')
		if i < len(rois) - 1:
			f.write(',')
		f.write('\n')
	f.write("]\n")
