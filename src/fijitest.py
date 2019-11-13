# Small test script that spins up a headless Fiji and has it run the registration script.
# Useful for debugging the registration script "offline".

import tools

fiji_path = '/home/frank/Fiji.app/ImageJ-linux64'
sift_registration_script = '/home/frank/development/tomo/src/fiji_registration.py'

sift_input_folder = '/media/frank/FRANK EXTERNAL/Secom/Frank-x100-LM-Stacks-examples/cell2/'
sift_output_folder = '/media/frank/FRANK EXTERNAL/Secom/Frank-x100-LM-Stacks-examples/cell2/output_frank'
lm_images_prefix = 'lmsection'
numimages = 18
do_enhance_contrast = True
do_crop = True
roi_x = 520
roi_y = 460
roi_width = 1030
roi_height = 1072

# Note: the style below for passing arguments to Fiji seems to work both on Windows and Ubuntu.
script_args = "srcdir='{}',dstdir='{}',prefix='{}',numimages='{}',do_enhance_contrast='{}',do_crop='{}',roi_x='{}',roi_y='{}',roi_width='{}',roi_height='{}'".format(
    sift_input_folder, sift_output_folder, lm_images_prefix, numimages, do_enhance_contrast, do_crop, roi_x, roi_y,
    roi_width, roi_height)

# Info about headless ImageJ: https://imagej.net/Headless#Running_macros_in_headless_mode
print('Starting a headless Fiji and calling the SIFT image registration plugin. Please be patient...')

retcode, out, err = tools.commandline_exec(
    [fiji_path, "-Dpython.console.encoding=UTF-8", "--ij2", "--headless", "--console", "--run",
     sift_registration_script, script_args])

print('retcode={}\nstdout=\n{}\nstderr={}\n'.format(retcode, out, err))
