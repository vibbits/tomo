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
def acquire_microscope_images(mode, physical_offsets_microns, delay_between_image_acquisition_secs,
                              odemis_cli, images_output_folder, images_prefix):

    # Ensure that the output folder for the images exists
    os.makedirs(images_output_folder, exist_ok = True)

    print('Acquiring {} images'.format(mode))
    for i, offset_microns in enumerate(physical_offsets_microns):
        # Move the stage
        move_stage(odemis_cli, offset_microns)

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

