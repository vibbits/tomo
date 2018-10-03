from ij import IJ
import sys

image = IJ.getImage()
if image == None:
	sys.exit("No open image")
	
roi = image.getRoi()
if roi == None:
	sys.exit("Image has no ROI")
	
polygon = roi.getPolygon()
if polygon == None:
	sys.exit("ROI has no polygon??")

IJ.log("ROI polygon has {} points".format(polygon.npoints))
for i in range(polygon.npoints):
	IJ.log("{} {}".format(polygon.xpoints[i], polygon.ypoints[i]))
