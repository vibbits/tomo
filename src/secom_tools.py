import os
import time
from tools import commandline_exec

try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path # Python 2 backport

# For autofocus
import platform
if platform.system() == "Windows":
    # Stubs
    from odemis_stubs import model
    from odemis_stubs import align
else:
    from odemis import model
    from odemis.acq import align


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
    Path(images_output_folder).mkdir(exist_ok = True)

    print('Acquiring {} images'.format(mode))
    for i, offset_microns in enumerate(physical_offsets_microns):
        # Move the stage
        move_stage_relative(odemis_cli, offset_microns)

        # Improve the focus (if we have user-defined focus points in the neighborhood of our current x,y position)
        # (Currently only for LM imaging.)
        if focus_map:
            pos = get_absolute_stage_position()
            z = focus_map.get_focus(pos)
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
    # stage = model.getComponent(role = "stage")   # CHECKME: it could instead be "name" instead if "role"
    # stage.moveRel({"x": dx_microns, "y": dy_microns})   # in what units is x and y?? Possibly meters instead of microns
    #  # CHECKME: moveRelSync or moveRel ?


def get_absolute_stage_position():   # return the (x,y) stage postion - CHECKME: in what units???
    stage = model.getComponent(role = "stage")   # CHECKME: it could instead be "name" instead if "role"
    x = stage.position.value["x"]
    y = stage.position.value["y"]
    return (x, y)


def get_absolute_focus_z_position():    # returns the focus z value (CHECKME: in what units ???)
    focus = model.getComponent(role = "focus")   # CHECKME: it could instead be "name" instead if "role"
    z = focus.position.value["z"]
    return z


def set_absolute_focus_z_position(z):      # z is the absolute focus value  (CHECKME: in what units ???)
    focus = model.getComponent(role = "focus")   # CHECKME: it could instead be "name" instead if "role"
    focus.moveAbs({"z": z})
    # CHECKME: or should we use moveAbsSync() instead of moveAbs() ?

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

