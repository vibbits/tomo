import wx
import resources

# A very basic About dialog

class AboutDialog(wx.Dialog):
    def __init__(self, parent=None):
        wx.Dialog.__init__(self, parent, wx.ID_ANY, "About Tomo")

        large_font = wx.Font(wx.FontInfo(18).Bold())
        medium_font = wx.Font(wx.FontInfo().Bold())
        underlined_font = wx.Font(wx.FontInfo().Underlined())

        bitmap = wx.Bitmap(resources.tomo.GetImage().Scale(64, 64, wx.IMAGE_QUALITY_BICUBIC))  # Downscale the Tomo icon
        icon = wx.StaticBitmap(self, wx.ID_ANY, bitmap)
        name = wx.StaticText(self, wx.ID_ANY, 'Tomo 1.2')
        name.SetFont(large_font)
        description = wx.StaticText(self, wx.ID_ANY, "Array tomography on SECOM")
        description.SetFont(medium_font)
        copyright = wx.StaticText(self, wx.ID_ANY, "(c) 2018-2021 VIB - Vlaams Instituut voor Biotechnologie")
        license = wx.StaticText(self, wx.ID_ANY, "Licensed under the GNU General Public License v3.0")
        developer = wx.StaticText(self, wx.ID_ANY, "Frank Vernaillen")
        affiliation = wx.StaticText(self, wx.ID_ANY, "VIB Bioinformatics Core, VIB Bioimaging Core")
        website = wx.StaticText(self, wx.ID_ANY, 'http://www.vib.be')
        website.SetFont(underlined_font)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(icon, 0, wx.ALL | wx.CENTER, 5)
        sizer.Add(name, 0, wx.ALL | wx.CENTER, 5)
        sizer.Add(description, 0, wx.ALL | wx.CENTER, 5)
        sizer.Add(copyright, 0, wx.ALL | wx.CENTER, 5)
        sizer.Add(developer, 0, wx.ALL | wx.CENTER, 5)
        sizer.Add(affiliation, 0, wx.ALL | wx.CENTER, 5)
        sizer.Add(website, 0, wx.ALL | wx.CENTER, 5)
        sizer.Add(license, 0, wx.ALL | wx.CENTER, 5)

        self.SetSizer(sizer)
        self.Fit()
