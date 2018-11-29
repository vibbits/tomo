import wx
import numpy as np
import secom_tools
from mark_mode import MarkMode


# Align stage and overview image
#    + first, in odemis:
#      - move stage to landmark of choice
#    + then, in tomo:
#       - using the mark tool click on the same landmark on the overview image
#       - fill in the input field to specify the overview image physical size or resolution
#    + tomo then queries the stage position and calculates the transformation absolute stage position to overview image pixel coords

class StageAlignmentPanel(wx.Panel):
    _canvas = None
    _model = None

    _landmark_obj = None  # a list with FloatCanvas objects used for drawing the alignment mark on the canvas; None if no mark is on the canvas yet

    # user interface
    done_button = None
    _overview_pixel_size_edit = None
    _alignment_state = None

    def __init__(self, parent, model, canvas):
        wx.Panel.__init__(self, parent, size=(350, -1))

        self._canvas = canvas
        self._model = model

        # Build the user interface
        title = wx.StaticText(self, wx.ID_ANY, "Stage alignment")
        title.SetFont(wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.BOLD))
        separator = wx.StaticLine(self, wx.ID_ANY)

        w = 330
        label0 = wx.StaticText(self, wx.ID_ANY, "Please specify the resolution of the overview image.")
        label0.Wrap(w)  # force line wrapping

        overview_pixel_size_label = wx.StaticText(self, wx.ID_ANY, "Pixel size (mm/pixel):")
        self._overview_pixel_size_edit = wx.TextCtrl(self, wx.ID_ANY, str(self._model.overview_image_mm_per_pixel), size=(100, -1))

        pixel_size_sizer = wx.BoxSizer(wx.HORIZONTAL)
        pixel_size_sizer.AddSpacer(30)
        pixel_size_sizer.Add(overview_pixel_size_label, flag = wx.ALIGN_CENTER_VERTICAL)
        pixel_size_sizer.AddSpacer(5)
        pixel_size_sizer.Add(self._overview_pixel_size_edit, flag = wx.ALIGN_CENTER_VERTICAL)

        label = wx.StaticText(self, wx.ID_ANY, "In Odemis, move the stage to an easy to recognize landmark. Then in Tomo use the Mark tool (+) to precisely indicate the same landmark on the overview image.")
        label.Wrap(w)  # force line wrapping

        self._alignment_state = wx.StaticText(self, wx.ID_ANY, "The stage is not aligned yet.")

        button_size = (125, -1)
        self.done_button = wx.Button(self, wx.ID_ANY, "Done", size=button_size)  # The ApplicationFame will listen to clicks on this button.

        self.Bind(wx.EVT_TEXT, self._on_overview_pixel_size_change, self._overview_pixel_size_edit)

        b = 5  # border size
        contents = wx.BoxSizer(wx.VERTICAL)
        contents.Add(title, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(separator, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(label0, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(pixel_size_sizer, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(label, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(self._alignment_state, 0, wx.ALL | wx.EXPAND, border=b)
        contents.Add(self.done_button, 0, wx.ALL | wx.CENTER, border=b)

        self.SetSizer(contents)
        contents.Fit(self)

    def activate(self):
        # Listen to mark tool mouse clicks so we can place the mark
        self._canvas.Canvas.Bind(MarkMode.EVT_TOMO_MARK_LEFT_DOWN, self._on_left_mouse_button_down)

    def deactivate(self):
        self._canvas.Canvas.Unbind(MarkMode.EVT_TOMO_MARK_LEFT_DOWN)

    def _on_left_mouse_button_down(self, event):
        print("Event = {}".format(event))
        coords = event.GetCoords()
        pos = (coords[0], -coords[1])
        print("Left mouse button clicked: %i, %i" % pos)
        self._place_landmark(pos)

    def _on_overview_pixel_size_change(self, event):
        self._model.overview_image_mm_per_pixel = float(self._overview_pixel_size_edit.GetValue())
        print('overview_image_mm_per_pixel={}'.format(self._model.overview_image_mm_per_pixel))

    def _place_landmark(self, landmark_image_pos):
        """
        Called when user clicks on the overview image to specify the landmark
        :param landmark_image_pos: landmark position in overview image coordinates (xi, yi in principle >= 0)
        :return:
        """
        # Calculate the alignment of stage and overview image.
        pixel_size_meters = self._model.overview_image_mm_per_pixel / 1000.0
        landmark_stage_pos = secom_tools.get_absolute_stage_position()  # in meters
        self._model.overview_image_to_stage_coord_trf = self._calculate_overview_image_to_stage_transformation_matrix(landmark_stage_pos, landmark_image_pos, pixel_size_meters)
        print('Overview image and stage are now aligned. Landmark position stage={} image={}. Pixel size={} m. Image to stage trf={}'.format(landmark_stage_pos, landmark_image_pos, pixel_size_meters, self._model.overview_image_to_stage_coord_trf))

        # Show alignment state in user interface
        self._update_alignment_state_text(landmark_stage_pos, landmark_image_pos)

        # Remove previous landmark from the overview image (if any)
        if self._landmark_obj:
            self._canvas.remove_objects(self._landmark_obj)

        # Draw a landmark on the overview image as feedback
        # IMPROVEME: the landmark bullseye should be drawn the same size independent of the zoom factor, so it is visible even if the user zoomed out
        self._landmark_obj = self._canvas.add_bullseye(landmark_image_pos, "Red")
        self._canvas.redraw()

    def _update_alignment_state_text(self, landmark_stage_pos, landmark_image_pos):
        self._alignment_state.SetLabelText("The stage is now aligned! The stage position is {}; the landmark image coordinates are {} ".format(landmark_stage_pos, landmark_image_pos))
        # IMPROVEME: that text line is ugly, break it up.
        self._alignment_state.Wrap(330)  # force line wrapping
        self.GetTopLevelParent().Layout()

    @staticmethod
    def _calculate_overview_image_to_stage_transformation_matrix(landmark_stage_pos, landmark_image_pos, pixel_size):
        """
        XXXX
        The stage y-axis points up, the image y-axis down. The top-level corner of the stage area visible on the overview image is at pixel coordinates(0,0)
        TODO: specify whether stage coordinates correspond to pixel centers or a pixel corner; possibly slightly change the transformation calculation below
        The transformation matrix from image coordinates (xi, yi) to stage coordinates (xs, ys) is as follows
            [ xs ]   [ s   0  tx ] [ xi ]
            [ ys ] = [ 0  -s  ty ] [ yi ]   (note the minus sign in -s, it flips the y-axis)
            [  1 ]   [ 0   0   1 ] [  1 ]
        where s is the pixel size (in meter/pixel), xs and ys are expressed in meters, and xi and yi are expressed in pixels.
        By specifying the correspondance of a single landmark and the pixel size, the translation tx, ty can be determined
        and the transformation matrix is then known.
        :param landmark_stage_pos: (xs, ys) position of the stage (in meters) when exactly over a landmark
        :param landmark_image_pos: (xi, yi) position in the overview image (in pixels) of that same landmark
        :param pixel_size: size in meter of a pixel in the overview image
        :return: a numpy 2x6 matrix, specifying the transformation from image coordinates to stage coordinates
        """

        xs, ys = landmark_stage_pos
        xi, yi = landmark_image_pos

        # Plug the known (xi, yi), (xs, ys) and pixel_size into the linear system shown above in matrix form
        # and trivially solve for the unknown tx and ty.
        tx = xs - pixel_size * xi
        ty = ys + pixel_size * yi

        trf = np.array([[pixel_size,           0, tx],
                        [         0, -pixel_size, ty],
                        [         0,           0,  1]])
        return trf
