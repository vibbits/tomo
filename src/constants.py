
# A couple of common constants used in Tomo.

NOTHING = -1                     # An invalid index indicating no slice or no handle.

REGULAR_LINE_WIDTH = 1           # Normal line width for drawing slice contours
HIGHLIGHTED_LINE_WIDTH = 3       # Line width for drawing the contours of a highlighted slice

# IMPROVEME: The size of these markers are in world space, so they change in size when zooming in/out.
#            Perhaps they should be in screen space? But I'm not sure we can do so easily in wxPython.
MARKER_SIZE = 25                 # Size of point-of-interest, focus value, etc. markers
HANDLE_SIZE = 8                  # Size of polygon vertex handle

NORMAL_COLOR = 'GREEN'           # Color for drawing slice contours
ACTIVE_COLOR = 'RED'             # Color for drawing an 'active' slice polygon handle
POINT_OF_INTEREST_COLOR = 'RED'  # Color for drawing the point-of-interest markers
FOCUS_POSITION_COLOR = 'RED'     # Color for drawing the markers showing where z-focus values were measured

# Names of the default modes, as defined in NavCanvas.
POINTER_MODE_NAME = 'Pointer'
ZOOM_IN_MODE_NAME = 'Zoom In'
ZOOM_OUT_MODE_NAME = 'Zoom Out'
PAN_MODE_NAME = 'Pan'
