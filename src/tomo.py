# Prototype tomography with Secom
# Frank Vernaillen
# Vlaams Instituut voor Biotechnologie (VIB)
# September 2018

import sys
import cv2
import wx

from application_frame import ApplicationFrame

# Notes:
# - In OpenCV and in Fiji the origin is in the top-left corner of the image, with the positive y axis pointing down.
#   Elsewhere we assume a coordinate system with the y-axis point "up". Hence, occasionally we will flip the sign of
#   the y-coordinate of our points.
#
# - Installing Python packages and setting up environment
#   1. Install Miniconda
#   2. conda create -n tomo-py37 python=3.7
#   3. source activate tomo-py37
#   4. pip install numpy
#   5. pip install opencv-python
#   6. conda install -c anaconda wxpython
#   7. pip install PyPubSub

def main():
    # Check that we're running Python 3.6+
    if sys.version_info[0] < 3:
        raise Exception("Must be running Python 3.6 or higher")
    else:
        if sys.version_info[1] < 6:
            raise Exception("Must be running Python 3.6 or higher")

    print('Environment:\n  Python: {}.{}.{}\n  OpenCV: {}\n  wxWindows: {}'.format(*sys.version_info[:3], cv2.__version__, wx.version()))

    app = wx.App()
    frame = ApplicationFrame(None, wx.ID_ANY, "Tomography")
    frame.CenterOnScreen()
    frame.Show(True)
    app.MainLoop()

if __name__ == "__main__":
    main()
