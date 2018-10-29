# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

from wx.lib.floatcanvas import NavCanvas

class TomoCanvas(NavCanvas.NavCanvas):
    _custom_modes = None

    def __init__(self, parent, custom_modes, id, size):
        self._custom_modes = custom_modes  # CHECKME: is this assignment before __init__() safe? It is needed because NavCanvas.__init__() calls BuildToolbar and we need access to the custom modes there.
        NavCanvas.NavCanvas.__init__(self, parent, id, size)

    def BuildToolbar(self):  # overrides implementation in NavCanvas
        self.Modes.extend(self._custom_modes)
        super(TomoCanvas, self).BuildToolbar()

    def EnableToolByLabel(self, label, enable):
        tool = self.FindToolByLabel(label)
        if tool:
            self.ToolBar.EnableTool(tool.GetId(), enable)

    def FindToolByLabel(self, label):
        tb = self.ToolBar
        num_tools = tb.GetToolsCount()
        for pos in range(num_tools):
            tool = tb.GetToolByPos(pos)
            # print("tool {}: {}".format(pos, tool.GetLabel()))
            if tool.GetLabel() == label:
                return tool
        return None