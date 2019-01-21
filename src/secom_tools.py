import os
import wx  # for confirmation dialog
import time
from tools import commandline_exec

# We need the Python2 backport pathlib2 (instead of pathlib)
# so we can use the exist_ok parameter of mkdir()
from pathlib2 import Path

# Try to import actual Odemis modules. If they are not available, for example on our Windows
# development machine, we load stub modules instead.
try:
    from odemis import model
    from odemis.acq import align
    odemis_stubbed = False
except ImportError:
    from odemis_stubs import model
    from odemis_stubs import align
    odemis_stubbed = True


# This function automatically acquires multiple LM or EM images.
# It assumes that the microscope parameters are already set correctly in Odemis, and that the stage is positioned
# at the initial point of interest. It then repeatedly moves the stage and acquires an LM/EM image. The image is saved
# to 'images_output_folder' with filename images_prefix + number + ome.tiff. The stage movement distances
# are specified in 'physical_offsets_microns'.
# (physical_offsets_microns: an offset per slice; with the first slice always having offset (0,0))
# The 'mode' must be 'EM' or 'LM' to acquire electron resp. light microscope images.
# If the user manually acquired focus z-values in a couple of positions these values will be interpolated
# and used as focus-z for each image.
def acquire_microscope_images(mode, physical_offsets_microns, delay_between_image_acquisition_secs,
                              odemis_cli, images_output_folder, images_prefix, focus_map = None):

    # Ensure that the output folder for the images exists
    Path(images_output_folder).mkdir(exist_ok=True)

    print('Acquiring {} images'.format(mode))
    for i, offset_microns in enumerate(physical_offsets_microns):
        # Move the stage
        move_stage_relative(odemis_cli, offset_microns)

        # Improve the focus (if we have user-defined focus points in the neighborhood of our current x,y position)
        # (Currently only for LM imaging.)
        if focus_map:
            pos = get_absolute_stage_position()
            z = focus_map.get_focus_value(pos)
            if z != None:
                set_absolute_focus_z_position(z)

        # Acquire an LM/EM image and save it to the output folder
        image_path = os.path.join(images_output_folder, '{}{}.ome.tiff'.format(images_prefix, i))
        if mode == "LM":
            detector = "ccd"
        else:  # EM
            detector = "se-detector"
        commandline_exec([odemis_cli, "--acquire", detector, "--output", image_path])  # IMPROVEME: use the Odemis Python API instead of odemis_cli

        # Wait a short time for the image acquisition to finish
        # CHECKME: Is this needed? Maybe odemis_cli will automatically buffer commands until it is finished?
        time.sleep(delay_between_image_acquisition_secs)


def move_stage_relative(odemis_cli, offset_microns):   # move the stage a certain distance relative to its current position
    dx_microns, dy_microns = offset_microns
    commandline_exec([odemis_cli, "--move", "stage", "x", str(dx_microns)])
    commandline_exec([odemis_cli, "--move", "stage", "y", str(dy_microns)])
    # Better alternative - TO BE TESTED/CHECKED
    # stage = model.getComponent(role = "stage")
    # stage.moveRel({"x": dx_microns, "y": dy_microns})   # in what units is x and y?? Possibly meters instead of microns
    # CHECKME: moveRelSync or moveRel ?
    # CHECKME: moveRel() returns a future?? Do we need to apply

def set_absolute_stage_position(pos):  # move the stage to the specified absolute position (in meters)
    stage = model.getComponent(role="stage")
    x, y = pos
    msg = "Move stage to absolute position x={} y={}".format(x, y)

    # # For minimal safety, pop up a confirmation dialog for now.
    # dlg = wx.MessageDialog(None, msg + " ?", "Move stage?", style=wx.YES | wx.NO)
    # if dlg.ShowModal() == wx.ID_YES:
    print(msg)
    stage.moveAbs({"x": x, "y": y})
    # else:
    #     print(msg + " -- CANCELLED")
    # dlg.Destroy()

    # CHECKME: moveAbs() actually returns a future, need to do something special?
    # <ClientFuture at 0x7f5d91218c50 for Proxy of Component 'Sample Stage'>

    # IMPROVEME: is there a way to protect against stage movements that are too large (and will jam the stage)?
    #            this could happen if for example the user clicks outside the overview image (FIXME: need to protect against that)
    #            but also if the overview image resolution entered by the user is too large.

def get_absolute_stage_position():   # return the absolute (x,y) stage position (in meters)
    stage = model.getComponent(role="stage")
    x = stage.position.value["x"]
    y = stage.position.value["y"]
    print("Get stage absolute position: x={} y={} (unit: m)".format(x, y))
    return x, y


def get_absolute_focus_z_position():    # returns the focus z value (CHECKME: in what units?)
    focus = model.getComponent(role="focus")
    z = focus.position.value["z"]
    print("Get focus absolute position: z={}".format(z))
    return z


def set_absolute_focus_z_position(z):      # z is the absolute focus value  (use the same units as get_absolute_focus_z_position...)
                                           # (CHECKME: in what units ???)
    focus = model.getComponent(role="focus")
    msg = "Set absolute focus position to z={}".format(z)

    # # For minimal safety, pop up a confirmation dialog for now.
    # dlg = wx.MessageDialog(None, msg + " ?", "Set focus?", style=wx.YES | wx.NO)
    # if dlg.ShowModal() == wx.ID_YES:
    print(msg)
    focus.moveAbs({"z": z})
    # else:
    #     print(msg + " -- CANCELLED")
    # dlg.Destroy()

    # CHECKME: should we use moveAbsSync() instead of moveAbs() ?
    # CHECKME: moveAbs() actually returns a future, need to do something special?
    # <ClientFuture at 0x7f5d91c6c410 for Proxy of Component 'Optical Focus'>


######################################################################################################################
# Command line to get the current focus z-value:
#    odemis-cli --list-prop focus
# which returns several lines:
# ...
# position(RO Vigilant Attribute)
# value: {'z': 5.5256e-05}   ---> in meters
# ...
######################################################################################################################
# Command line to set the absolute focus z:
#    odemis-cli --position focus z -0.05            <--- in microns ??
######################################################################################################################
# Command line for getting the stage position:
#    odemis-cli --list-prop stage
# which returns several lines:
# ...
# position(RO Vigilant Attribute)
# value: {'x': -0.007078522, 'y': 0.005740546} (unit: m)
# ...
######################################################################################################################
# API examples for setting/getting values: the odemis-cli source code:
#    odemis/src/odemis/cli/main.py
######################################################################################################################

# def setup_autofocus():
#     try:
#         det = model.getComponent(role = "ccd")
#     except LookupError:
#         raise ValueError("Failed to find detector 'ccd'")
#
#     try:
#         focuser = model.getComponent(role = "focus")
#     except LookupError:
#         raise ValueError("Failed to find focuser 'focus'")
#
#     emt = None
#     if det.role in ("se-detector", "bs-detector", "cl-detector"):
#         # For EM images, the emitter is not necessary, but helps to get a
#         # better step size in the search (and time estimation)
#         try:
#             emt = model.getComponent(role = "e-beam")
#         except LookupError:
#             print("Failed to find e-beam emitter")
#             pass
#
#     return det, emt, focuser
#

# def autofocus(det, emt, focuser, good_focus = None, focus_range = None, focus_method = align.autofocus.MTD_BINARY):
#     # good_focus = float
#     # focus_range = tuple
#     # See https://github.com/delmic/odemis/blob/master/scripts/autofocus.py
#     # and https://github.com/delmic/odemis/blob/master/src/odemis/acq/align/autofocus.py
#     try:
#         print('Autofocussing...')
#         future = align.AutoFocus(det, emt, focuser, good_focus = good_focus, rng_focus = focus_range, method = focus_method)  # IMPORTANT TODO: try without rng_focus, we might be setting it too small; also try both autofocus methods
#         foc_pos, fm_final = future.result(1000)  # putting a timeout allows to get KeyboardInterrupts
#         print("Focus level after applying autofocus: {} @ {} m".format(fm_final, foc_pos))
#         # fm_final is the "focus level", I don't know what that means... Some value indicating how well the focus is? What does it mean physically?
#         # foc_pos is the focus z-position
#         return foc_pos
#     except KeyboardInterrupt:
#         # CHECKME: we don't want to check for keyboard interrupts - is this harmless? Can it be triggered accidentally?
#         future.cancel()
#         raise

