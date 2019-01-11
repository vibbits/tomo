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
        for mode in self.Modes:
            print("mode: {}".format(mode))
        super(TomoCanvas, self).BuildToolbar()

    def Activate(self, tool):
        self._MakeActive(tool, True)

    def Deactivate(self, tool):
        self._MakeActive(tool, False)

    def _MakeActive(self, tool, active):
        tool = self.FindToolByName(tool)
        self.ToolBar.EnableTool(tool.GetId(), active)  # enable/disable the tool (=make the tool button clickable/not clickable and make sure it is grayed out/not grayed out)
        self.ToolBar.ToggleTool(tool.GetId(), active)  # make the tool button the currently active button in the tool bar
        self.SetMode(tool)  # make the mode corresponding to the tool button the current mode

    def FindToolByName(self, name):
        tb = self.ToolBar
        num_tools = tb.GetToolsCount()
        for pos in range(num_tools):
            tool = tb.GetToolByPos(pos)
            # print("tool {}: label='{}' shortHelp='{}' id={}".format(pos, tool.GetLabel(), tool.GetShortHelp(), tool.GetId()))
            if tool.GetShortHelp() == name:
                return tool
        return None

