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
# - Setting up a development environment On Windows (using stubbed Odemis API calls):
#   (We use Python 2.7 because on the actual SECOM computer we will be calling Odemis Python API functions,
#   and Odemis uses Python 2.7)
#
#   1. Install Miniconda
#
#   2. conda create -n tomo-py27 python=2.7
#   3. source activate tomo-py27
#
#   4. pip install opencv-python
#   5. pip install wxpython                  # (this is not needed: conda install -c anaconda wxpython)
#   (6. pip install pypubsub==3.3.0          # we use an old version of PyPubSub because newer versions are Python 3 only (https://github.com/schollii/pypubsub/issues/9)) - probably not used anymore in tomo
#   7. pip install networkx
#   8. pip install joblib
#   9. pip install pathlib2
#   Note that on Windows we do *not* install Odemis (presumably it does not work or is hard to install on Windows.)
#
#   On the actual SECOM computer running Ubuntu, where we have installed a full Odemis, we do *not* use Anaconda
#   because using Anaconda would mean also installing Odemis in an Anaconda environment, which is
#   annoying. (Odemis is not a single package installation...)
#
# - On Ubuntu, the wxPython sources are installed here: 
#   /usr/lib/python2.7/dist-packages/wx-3.0-gtk2/wx
#
#
# Windows environment for Tomo:
#   Python: 2.7.13
#   OpenCV: 3.4.3
#   wxPython: 4.0.3 msw (phoenix) wxWidgets 3.0.5


def main():
    print('Environment:\n  Python: {}.{}.{}\n  OpenCV: {}\n  wxPython: {}'.format(sys.version_info[0], sys.version_info[1], sys.version_info[2], cv2.__version__, wx.version()))

    app = wx.App()
    frame = ApplicationFrame(None, wx.ID_ANY, "Tomography Prototype")
    frame.CenterOnScreen()
    frame.Show(True)
    app.MainLoop()

if __name__ == "__main__":
    main()
