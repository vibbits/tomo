# Prototype tomography with Secom
# Frank Vernaillen
# Vlaams Instituut voor Biotechnologie (VIB)
# September 2018

import sys
import cv2
import wx

from application_frame import ApplicationFrame

# Notes:
#
# Coordinate system
# =================
#   In OpenCV and in Fiji the origin is in the top-left corner of the image, with the positive y axis pointing down.
#   Elsewhere we assume a coordinate system with the y-axis point "up". Hence, occasionally we will flip the sign of
#   the y-coordinate of our points.
#
# Setting up a development environment On Windows (WITHOUT Odemis)
# ================================================================
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
#   6. pip install pypubsub==3.3.0          # we use an old version of PyPubSub because newer versions are Python 3 only (https://github.com/schollii/pypubsub/issues/9)
#   7. pip install networkx
#   8. pip install joblib
#   9. pip install pathlib2
#   Note that on Windows we do *not* install Odemis (presumably it does not work or is hard to install on Windows.)
#
# Windows development environment for Tomo:
#   Python: 2.7.13
#   OpenCV: 3.4.3
#   wxPython: 4.0.3 msw (phoenix) wxWidgets 3.0.5
#
# Setting up an Ubuntu 16.04.1 development environment (WITHOUT Odemis)
# =====================================================================
# - conda create -n tomo_py27 python=2.7 wxpython=4
# - conda activate tomo_py27
# - conda install -c menpo opencv3
# - conda install pathlib2
# - conda install networkx
# - conda install joblib
# - pip install naturalneighbor    # there is no conda package
# - pip install pypubsub==3.3.0
#
# And for some experiments also:
# - conda install scipy
# - conda install matplotlib

# This results in this environment:
#   Python: 2.7.15
#   OpenCV: 3.1.0
#   wxPython: 4.0.3 gtk2 (phoenix) wxWidgets 3.0.5
#
# Production SECOM environment
# ============================
#   - OS: Ubuntu 16.04 LTS
#     Python: 2.7.12
#     OpenCV: 2.4.11
#     wxPython: 3.0.2.0 gtk2 (classic)
#   - On this actual SECOM computer we have a full Odemis installation.
#   - We do *not* use Anaconda here.
#   - The wxPython sources are in /usr/lib/python2.7/dist-packages/wx-3.0-gtk2/wx
#   - PyPubSub 3.3.0  (PyPubSub version 4.0 is NOT compatible with Python 2)

def main():
    print('Environment:\n  Python: {}.{}.{}\n  OpenCV: {}\n  wxPython: {}'.format(sys.version_info[0], sys.version_info[1], sys.version_info[2], cv2.__version__, wx.version()))

    app = wx.App()
    frame = ApplicationFrame(None, wx.ID_ANY, "Tomo")
    frame.CenterOnScreen()
    frame.Show(True)
    app.MainLoop()

if __name__ == "__main__":
    main()
