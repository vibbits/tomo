# Frank Vernaillen
# VIB
# September 2018

import wx
from wx.lib.floatcanvas import NavCanvas, FloatCanvas

filename = r'F:\Secom\sergio_x20_LM_objective_overview_image\bisstitched-0.tif'

class DrawFrame(wx.Frame):
    navpanel = None
    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)
        self.CreateStatusBar() 

        self.navpanel = NavPanel(self)        
        self.navpanel.Bind(FloatCanvas.EVT_MOTION, self.OnMove)
        #self.navpanel.Canvas.ZoomToBB()

        imagebutton = wx.Button(self, wx.ID_ANY, "Load Image")
        self.Bind(wx.EVT_BUTTON, self.OnImageButtonClick, imagebutton)

        polybutton = wx.Button(self, wx.ID_ANY, "Add Polygon")
        self.Bind(wx.EVT_BUTTON, self.OnPolygonButtonClick, polybutton)

        MainSizer = wx.BoxSizer(wx.VERTICAL)
        MainSizer.Add(imagebutton, 0, wx.CENTER | wx.EXPAND | wx.ALL, 1)  # Add(item, proportion, flags, border)
        MainSizer.Add(polybutton, 0, wx.CENTER | wx.EXPAND | wx.ALL, 1)   # wx.ALL=add border along all 4 edges
        MainSizer.Add(self.navpanel, 1, wx.EXPAND)  # note: proportion=1 here is crucial, 0 will not work
        self.SetSizer(MainSizer)

    def OnImageButtonClick(self, event):
        self.navpanel.add_image(filename)
        self.navpanel.Canvas.ZoomToBB()

    def OnPolygonButtonClick(self, event):
        self.navpanel.add_polygon()
        self.navpanel.Canvas.ZoomToBB()

    def OnMove(self, event): 
        self.SetStatusText("%i, %i" % (event.Coords[0], -event.Coords[1]))   # flip y so we have the y-axis pointing down and (0,0)= top left corner of the image

class NavPanel(NavCanvas.NavCanvas):
    def __init__(self, parent):
        NavCanvas.NavCanvas.__init__(self, parent) #, BackgroundColor = "LIGHT GREY")
        wx.CallAfter(self.Canvas.ZoomToBB) # so it will get called after everything is created and sized

    def add_polygon(self):
        self.Canvas.AddPolygon(((0,0), (13000,0), (13000,13000), (0, 13000)), FillColor = "red")

    def add_image(self, filename):
        print('Reading ' + filename)
        image = wx.Image(filename) 
        img = FloatCanvas.ScaledBitmap2(image, 
                                        (0,0), 
                                        Height = image.GetHeight(), 
                                        Position = 'tl') 
        self.Canvas.AddObject(img) 

app = wx.App(False)
dlg = DrawFrame(None, title="NavCanvas Demo", size=(700, 700))
dlg.Show()
app.MainLoop()