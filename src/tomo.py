# Prototype tomography with Secom
# (c) Vlaams Instituut voor Biotechnologie (VIB)
# Frank Vernaillen
# 2018-2021

import sys
import cv2
import wx
from application_frame import ApplicationFrame

def main():
    print('Environment:\n  Python: {}.{}.{}\n  OpenCV: {}\n  wxPython: {}'.format(sys.version_info[0], sys.version_info[1], sys.version_info[2], cv2.__version__, wx.version()))

    app = wx.App()
    frame = ApplicationFrame(None, wx.ID_ANY, "Tomo")
    frame.CenterOnScreen()
    frame.Show(True)
    app.MainLoop()

if __name__ == "__main__":
    main()
