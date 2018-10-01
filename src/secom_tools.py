import os
import time
from tools import commandline_exec

# This function uses the Odemis command line tool to repeatedly move the stage and acquire an LM or EM image.
# It assumes that the microscope parameters are already set correctly in Odemis, and that the stage is positioned
# at the initial point of interest. It the repeatedly moves the stage and acquires an LM/EM image. The image is saved
# to 'images_output_folder' with filename images_prefix + number + ome.tiff. The stage movement distances
# are specified in 'physical_offsets_microns'.
# (physical_offsets_microns: an offset per slice; with the first slice always having offset (0,0))
# The 'mode' must be 'EM' or 'LM' to acquire electron resp. light microscope images.
# do_autofocus: boolean
# max_focus_change_microns: float, maximum change in focus distance z between each image acquisition
def acquire_microscope_images(mode, physical_offsets_microns, delay_between_image_acquisition_secs,
                              odemis_cli, images_output_folder, images_prefix, do_autofocus, max_focus_change_microns):

    # Ensure that the output folder for the images exists
    os.makedirs(images_output_folder, exist_ok = True)

    # Prepare for autofocus
    det, emt, focuser = setup_autofocus()

    # Get current focus
    z = focuser.position.value["z"]  # CHECKME: is this the focus position in meter?
    print(f"Original focus position: {z} m")

    print('Acquiring {} images'.format(mode))
    for i, offset_microns in enumerate(physical_offsets_microns):
        # Move the stage
        move_stage(odemis_cli, offset_microns)

        # Autofocus
        if do_autofocus:
            if i > 0:
                max_z_change = max_focus_change_microns * 1e-6  # FIXME - good value? (probably should be a user option) + what units, meters?
                z = autofocus(det, emt, focuser, good_focus = z, focus_range = (z - max_z_change, z + max_z_change))
                print(f'... autofocus sanity check: {z} ?= {focuser.position.value["z"]}')

        # Acquire an LM/EM image and save it to the output folder
        image_path = os.path.join(images_output_folder, '{}{}.ome.tiff'.format(images_prefix, i))
        if mode == "LM":
            commandline_exec([odemis_cli, "--acquire", "ccd", "--output", image_path])
        else:  # EM
            commandline_exec([odemis_cli, "--se-detector", "--output", image_path])

        # Wait a short time for the image acquisition to finish
        # CHECKME: Is this needed? Maybe odemis_cli will automatically buffer commands until it is finished?
        time.sleep(delay_between_image_acquisition_secs)


def move_stage(odemis_cli, offset_microns):
    dx_microns, dy_microns = offset_microns
    commandline_exec([odemis_cli, "--move", "stage", "x", str(dx_microns)])
    commandline_exec([odemis_cli, "--move", "stage", "y", str(dy_microns)])


# For autofocus
import platform
if platform.system() == "Windows":
    # Stubs
    from odemis_stubs import model
    from odemis_stubs import align
    from odemis_stubs import MTD_BINARY
else:
    from odemis import model
    from odemis.acq import align


def setup_autofocus():
    try:
        det = model.getComponent(role = "ccd")
    except LookupError:
        raise ValueError("Failed to find detector 'ccd'")

    try:
        focuser = model.getComponent(role = "focus")
    except LookupError:
        raise ValueError("Failed to find focuser 'focus'")

    emt = None
    if det.role in ("se-detector", "bs-detector", "cl-detector"):
        # For EM images, the emitter is not necessary, but helps to get a
        # better step size in the search (and time estimation)
        try:
            emt = model.getComponent(role = "e-beam")
        except LookupError:
            print("Failed to find e-beam emitter")
            pass

    return det, emt, focuser


def autofocus(det, emt, focuser, good_focus = None, focus_range = None, focus_method = MTD_BINARY):
    # good_focus = float
    # focus_range = tuple
    # See https://github.com/delmic/odemis/blob/master/scripts/autofocus.py
    # and https://github.com/delmic/odemis/blob/master/src/odemis/acq/align/autofocus.py
    try:
        future = align.Autofocus(det, emt, focuser, good_focus = good_focus, rng_focus = focus_range, method = focus_method)
        foc_pos, fm_final = future.result(1000)  # putting a timeout allows to get KeyboardInterrupts
        print(f"Focus level after applying autofocus: {fm_final} @ {foc_pos} m")
        # fm_final is the "focus level", I don't know what that means...!
        # foc_pos is the focus z-position
        return foc_pos
    except KeyboardInterrupt:
        future.cancel()
        raise
    # FIXME: we don't want to check for keyboard interrupts
