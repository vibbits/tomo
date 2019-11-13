# Small test script that spins up a headless Fiji and has it run the registration script.
# Useful for debugging the registration script "offline".

import tools

ubuntu = False
if ubuntu:
    fiji_path = '/home/frank/Fiji.app/ImageJ-linux64'
    registration_script = '/home/frank/development/tomo/src/fiji_registration.py'
    input_folder = '/media/frank/FRANK EXTERNAL/Secom/Frank-x100-LM-Stacks-examples/cell2/'
    output_folder = '/media/frank/FRANK EXTERNAL/Secom/Frank-x100-LM-Stacks-examples/cell2/output_frank'
else:
    fiji_path = 'e:\\Fiji.app\\ImageJ-win64.exe'
    registration_script = 'E:\\git\\bits\\bioimaging\Secom\\tomo\\src\\fiji_registration.py'
    input_folder = 'g:\\Secom\\Frank-x100-LM-Stacks-examples\\cell2\\'
    output_folder = 'g:\\Secom\\Frank-x100-LM-Stacks-examples\\cell2\\output_frank'

lm_images_prefix = 'lmsection'
numimages = 3 #18
do_enhance_contrast = True
do_crop = True
roi_x = 520
roi_y = 460
roi_width = 1030
roi_height = 1072
method = 'stackreg'  # possible methods: 'sift' (=Linear Stack Alignment with SIFT) or 'stackreg' (requires the StackReg and TurboReg plugin jars).

# Note: the style below for passing arguments to Fiji seems to work both on Windows and Ubuntu.
script_args = "srcdir='{}',dstdir='{}',prefix='{}',method='{}',numimages='{}',do_enhance_contrast='{}',do_crop='{}',roi_x='{}',roi_y='{}',roi_width='{}',roi_height='{}'".format(
    input_folder, output_folder, lm_images_prefix, method, numimages, do_enhance_contrast, do_crop, roi_x, roi_y,
    roi_width, roi_height)

# Info about headless ImageJ: https://imagej.net/Headless#Running_macros_in_headless_mode
print('Starting a headless Fiji and calling the image registration plugin. Please be patient...')

retcode, out, err = tools.commandline_exec(
    [fiji_path, "-Dpython.console.encoding=UTF-8", "--ij2", "--headless", "--console", "--run",
     registration_script, script_args])

print('retcode={}\nstdout=\n{}\nstderr={}\n'.format(retcode, out, err))
