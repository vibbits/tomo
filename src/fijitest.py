import tools
import platform

fiji_path = '/home/secom/Downloads/Fiji.app/ImageJ-linux64'
sift_registration_script = '/home/secom/development/tomo/src/sift_registration.py'

sift_input_folder = '/home/secom/development/tomo/data/20x_lens_LM_2ribbons/frank3_in'
sift_output_folder = '/home/secom/development/tomo/data/20x_lens_LM_2ribbons/frank3_out'
lm_images_prefix = 'lmsection'

print('Aligning LM images')
print('Starting a headless Fiji and calling the SIFT image registration plugin. Please be patient...')

if True:   # platform.system() == "Windows":
    print('True!!')
    script_args = "srcdir='{}',dstdir='{}',prefix='{}'".format(sift_input_folder,
                                                               sift_output_folder,
                                                               lm_images_prefix)
else:  # On Ubuntu
    script_args = '"srcdir=\'{}\',dstdir=\'{}\',prefix=\'{}\'"'.format(sift_input_folder,
                                                                       sift_output_folder,
                                                                       lm_images_prefix)

# Info about headless ImageJ: https://imagej.net/Headless#Running_macros_in_headless_mode
print("Aligning LM images...")
retcode, out, err = tools.commandline_exec(
    [fiji_path, "-Dpython.console.encoding=UTF-8", "--ij2", "--headless", "--console", "--run",
     sift_registration_script, script_args])

print('retcode={}\nstdout=\n{}\nstderr={}\n'.format(retcode, out, err))
