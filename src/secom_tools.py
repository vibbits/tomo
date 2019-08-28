import os
import time
from tools import commandline_exec, make_dir

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

# IMPROVEME? Use the Odemis Python API instead of odemis_cli? This is more elegant, but has the disadvantage that we cannot
# easily reproduce bugs or test issues using an Odemis command line (removing Tomo as a possible cause of the problem).
# Another issue with the API is that starting Odemis, starting Tomo, then stopping and restarting Odemis, seems to result
# in Tomo having Odemis objects that are "obsolete": e.g. model.getComponent(role="stage") then fails with a Pyro4 error/exception.

# This function automatically acquires multiple LM images.
# It assumes that the microscope parameters are already set correctly in Odemis, and that the stage is positioned
# at the initial point of interest. It then repeatedly moves the stage and acquires an LM image. The image is saved
# to 'images_output_folder' with filename images_prefix + number + ome.tiff. The relative stage movement distances
# are specified in 'physical_offsets_microns'.
# (physical_offsets_microns: an offset per slice; with the first slice always having offset (0,0))
# If the user manually acquired focus z-values in a couple of positions these values will be interpolated
# and used as focus-z for each image.
def acquire_lm_microscope_images(physical_offsets_microns, stabilization_time, delay_between_image_acquisition_secs,
                                 odemis_cli, images_output_folder, images_prefix, focus_map=None):
    print('Acquiring LM images')

    # Ensure that the output folder for the images exists
    make_dir(images_output_folder)

    # Acquire an image at each section
    for i, offset_microns in enumerate(physical_offsets_microns):
        # Move the stage
        move_stage_relative(odemis_cli, offset_microns)

        # Improve the focus (if we have user-defined focus points in the neighborhood of our current x,y position)
        # (Currently only for LM imaging.)
        if focus_map:
            pos = get_absolute_stage_position()
            z = focus_map.get_focus_value(pos)
            if z is not None:
                set_absolute_focus_z_position(z)

        # Wait for everything to settle (e.g. we suspect the viscous (vicious ;-) immersion oil droplet to be deformed
        # a bit after moving the stage, resulting in out of focus images. So wait a little while before imaging.
        time.sleep(stabilization_time)

        # Acquire an LM image and save it to the output folder
        image_path = os.path.join(images_output_folder, '{}{}.ome.tiff'.format(images_prefix, i))
        commandline_exec([odemis_cli, "--acquire", "ccd", "--output", image_path])

        # Wait a short time for the image acquisition to finish
        # CHECKME: Is this needed? Maybe odemis_cli will automatically buffer commands until it is finished?
        time.sleep(delay_between_image_acquisition_secs)


def acquire_em_microscope_images(physical_offsets_microns, delay_between_image_acquisition_secs,
                                 odemis_cli, images_output_folder, images_prefix, scale_string, magnification, dwell_time_microsecs):
    print('Acquiring EM images')

    # Ensure that the output folder for the images exists
    make_dir(images_output_folder)

    # Setup microscope
    commandline_exec([odemis_cli, "--set-attr", "e-beam", "scale", scale_string])
    commandline_exec([odemis_cli, "--set-attr", "e-beam", "magnification", str(magnification)])
    commandline_exec([odemis_cli, "--set-attr", "e-beam", "dwellTime", '{:.10f}'.format(dwell_time_microsecs * 1.0e-6)])  # the dwellTime argument for odemis_cli presumably is in seconds

    # FIXME/Note: it seems that setting the magnification here has no effect on the actual microscope - apparently it needs to be set on the JEOL software?!
    # FIXME/Note: it seems that setting the dwell time here also does not work - apparently the dwell time from Odemis is used?! Or is something wrong with the format of the floating point number (we use scientific notation such as "1e-6", is that not understood by odemis-cli perhaps)?!

    # Acquire an image at each section
    for i, offset_microns in enumerate(physical_offsets_microns):
        # Move the stage
        move_stage_relative(odemis_cli, offset_microns)

        # Acquire an LM/EM image and save it to the output folder
        image_path = os.path.join(images_output_folder, '{}{}.ome.tiff'.format(images_prefix, i))
        commandline_exec([odemis_cli, "--acquire", "se-detector", "--output", image_path])

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
    # CHECKME: moveRelSync or moveRel? Answer: most likely MoveRelSync to ensure the move is completed before we continue and acquire and image, for example
    # CHECKME: moveRel() returns a future?? Do we need to apply


def set_absolute_stage_position(pos):
    """
    Move the stage to the specified absolute position (in meters)
    """
    # IMPROVEME: is there a way to protect against stage movements that are too large (and will jam the stage)?
    #            this could happen if for example the user clicks outside the overview image (FIXME: need to protect against that)
    #            but also if the overview image resolution entered by the user is too large.
    x, y = pos
    print("Move stage to absolute position x={} y={} [m]".format(x, y))
    stage = model.getComponent(role="stage")
    stage.moveAbsSync({"x": x, "y": y})


def get_absolute_stage_position():   # return the absolute (x,y) stage position (in meters)
    stage = model.getComponent(role="stage")
    x = stage.position.value["x"]
    y = stage.position.value["y"]
    print("Get stage absolute position: x={} y={} [m]".format(x, y))
    return x, y


def get_absolute_focus_z_position():    # returns the focus z value (CHECKME: in what units?)
    focus = model.getComponent(role="focus")
    z = focus.position.value["z"]
    print("Get focus absolute position: z={}".format(z))
    return z


def set_absolute_focus_z_position(z):
    # z is the absolute focus value  (use the same units as get_absolute_focus_z_position...)
    # (CHECKME: what are those units?)
    print("Set absolute focus position to z={}".format(z))
    focus = model.getComponent(role="focus")
    focus.moveAbsSync({"z": z})


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

