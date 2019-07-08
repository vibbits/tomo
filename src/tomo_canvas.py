# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

from wx.lib.floatcanvas import NavCanvas

class TomoCanvas(NavCanvas.NavCanvas):
    _custom_modes = None
    _tools = {}  # dict of tool_id versus (tool start function, tool stop function)
    _current_tool_id = None

    def __init__(self, parent, custom_modes, id, size):
        self._custom_modes = custom_modes  # CHECKME: is this assignment before __init__() safe? It is needed because NavCanvas.__init__() calls BuildToolbar and we need access to the custom modes there.
        NavCanvas.NavCanvas.__init__(self, parent, id, size)

    def BuildToolbar(self):  # overrides implementation in NavCanvas
        self.Modes.extend(self._custom_modes)
        # for mode in self.Modes:
        #     print("mode: {}".format(mode))
        super(TomoCanvas, self).BuildToolbar()

    def RegisterTool(self, tool_name, start_func, stop_func):
        tool = self.FindToolByName(tool_name)
        tool_id = tool.GetId()
        self._tools[tool_id] = (start_func, stop_func)

    def SetMode(self, mode):
        old_tool = self._current_tool_id
        new_tool = mode.GetId()
        # print('TomoCanvas.SetMode old={} new={}'.format(old_tool, new_tool))

        # Stop the current tool
        if old_tool in self._tools:
            _, stop_func = self._tools[old_tool]
            stop_func()

        # Switch to the new tool
        super(TomoCanvas, self).SetMode(mode)
        self._current_tool_id = new_tool

        # Start the new tool
        if new_tool in self._tools:
            start_func, _ = self._tools[new_tool]
            start_func()

    def EnableTool(self, tool_name, enable):
        tool = self.FindToolByName(tool_name)
        # print('EnableTool name={} id={}'.format(tool_name, tool.GetId()))
        self.ToolBar.EnableTool(tool.GetId(), enable)  # enable/disable the tool (=make the tool button clickable/not clickable and make sure it is grayed out/not grayed out)

    def Activate(self, tool):
        self._MakeActive(tool, True)

    def Deactivate(self, tool):
        self._MakeActive(tool, False)

    def _MakeActive(self, tool_name, active):
        tool = self.FindToolByName(tool_name)
        self.ToolBar.EnableTool(tool.GetId(), active)  # enable/disable the tool (=make the tool button clickable/not clickable and make sure it is grayed out/not grayed out)
        self.ToolBar.ToggleTool(tool.GetId(), active)  # make the tool button the currently active button in the tool bar
        self.SetMode(tool)  # make the mode corresponding to the tool button the current mode

    def IsActive(self, tool_name):
        tool = self.FindToolByName(tool_name)
        return self.ToolBar.GetToolState(tool.GetId())

    def FindToolByName(self, name):
        tb = self.ToolBar
        num_tools = tb.GetToolsCount()
        for pos in range(num_tools):
            tool = tb.GetToolByPos(pos)
            # print("tool {}: label='{}' shortHelp='{}' id={}".format(pos, tool.GetLabel(), tool.GetShortHelp(), tool.GetId()))
            if tool.GetShortHelp() == name:
                return tool
        return None

    def PrintToolbarState(self):
        tb = self.ToolBar
        num_tools = tb.GetToolsCount()
        for pos in range(num_tools):
            tool = tb.GetToolByPos(pos)
            print("tool {}: id={} label='{}' shortHelp='{}' id={} active={}".format(pos, tool.GetId(), tool.GetLabel(), tool.GetShortHelp(),
                                                                                    tool.GetId(), tb.GetToolState(tool.GetId())))

