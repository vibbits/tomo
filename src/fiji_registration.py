# Script for registering a set of images with ImageJ's "Linear Stack Alignment with SIFT"
# or "StackReg" registration plugins.
# This script is typically executed by a headless Fiji started by Tomo.
#
# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

#@String srcdir
#@String dstdir
#@String prefix
#@String method
#@Integer numimages
#@Boolean do_invert
#@Boolean do_enhance_contrast
#@Boolean do_crop
#@Integer roi_x
#@Integer roi_y
#@Integer roi_width
#@Integer roi_height

# Note: we have a lot of parameters already, perhaps we should instead pass them via,
# for example, a JSON file with parameters?

# Note: roi_x, roi_y, roi_width, roi_height are only by the script if do_crop is True.

import os
import re
from ij import IJ, ImagePlus, ImageStack, WindowManager

def atoi(text):
    return int(text) if text.isdigit() else text

def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    '''
    return [ atoi(c) for c in re.split('(\d+)', text) ]

def registration():
    print('Registration parameters:')
    print('- Source directory: {}'.format(srcdir))
    print('- Destination directory: {}'.format(dstdir))
    print('- Input image filename prefix: {}'.format(prefix))
    print('- Registration method: {}'.format(method))
    print('- Number of input images to register: {}'.format(numimages))
    print('- Invert images? {}'.format('yes' if do_invert else 'no'))
    print('- Enhance contrast before registration? {}'.format('yes' if do_enhance_contrast else 'no'))
    print('- Crop images before registration? {}'.format('yes' if do_crop else 'no'))
    if do_crop:
        print('- Crop ROI: x={} y={} width={} height={}'.format(roi_x, roi_y, roi_width, roi_height))

    # Collect the filenames of the images we will load and save as a single stack
    print('Scanning source directory for images')
    images = []
    for filename in os.listdir(srcdir):
        if filename.startswith(prefix):
            full_filename = os.path.join(srcdir, filename)
            if os.path.isfile(full_filename):
                images.append(filename)

    print('Found {} images starting with desired filename prefix "{}"'.format(len(images), prefix))
    if len(images) < numimages:
        print('ERROR: The registration plugin was asked to register {} images but only {} were found!'.format(numimages, len(images)))

    # Sort the image filenames in natural order
    # (so with "prefix2.tif" before "prefix11.tif")
    images.sort(key = natural_keys)

    # Restrict ourselves to the number of images requested by the user.
    # (The numimages parameter is a bit of a workaround to be able to handle the
    # situation where images are written into a folder which is not empty. Just iterating
    # over all files with the correct prefix might then yield an incorrect mix of old and new images.
    # We could erase this folder before acquiring images, but that is annoying for our
    # mock setup on our development machine where we do not actually acquire images but use pre-acquired images
    # because we don't have connection to an actual SECOM. And we prefer not to erase+copy again.)
    images = images[:numimages]

    # Actually load the images and add them to a stack
    print('Loading images and merging them into an image stack')
    stack = None
    for filename in images:
        full_filename = os.path.join(srcdir, filename)
        imp = IJ.openImage(full_filename)
        ip = imp.getProcessor()
        if not stack:
            stack = ImageStack(ip.getWidth(), ip.getHeight())
        stack.addSlice(filename, ip)

    # Save the stack
    stackImp = ImagePlus("unaligned_stack", stack)
    unaligned_stack_filename = os.path.join(dstdir, "unaligned_stack.tif")
    print('Saving image stack to ' + unaligned_stack_filename)

    IJ.save(stackImp, unaligned_stack_filename)
    WindowManager.setTempCurrentImage(stackImp)

    if do_invert:
        print('Inverting')
        IJ.run("Invert", "stack")

    if do_crop:
        print('Cropping')
        stackImp.setRoi(roi_x, roi_y, roi_width, roi_height)
        IJ.run(stackImp, "Crop", "")

    if do_enhance_contrast:
        print('Enhancing contrast')
        IJ.run("Enhance Contrast", "saturated=0.35")
        IJ.run("Apply LUT", "stack")

    IJ.save(stackImp, unaligned_stack_filename)

    # Display the unaligned stack (for debugging, not possible in headless mode)
    # stackImp.show()  # Not allowed when running Fiji in headless mode. Will throw a java.awt.HeadlessException

    # Some plugins, like the SIFT Image registration plugin we want to use,
    # use WindowManager.getCurrentImage() as their input image. However, if Fiji is running in headless mode
    # we cannot display images and getCurrentImage() is null. Fortunately, as a workaround, we can use setTempCurrentImage()
    # on the WindowManager which will then return it when getCurrentImage() is called.

    # Make the unaligned stack the current image for the registration plugin
    WindowManager.setTempCurrentImage(stackImp)   # WindowManager.getCurrentImage() will now return stackImp

    if method == 'SIFT':
        # Align the stack with SIFT. For now we run the ImageJ SIFT plugin,
        # but maybe we ought to use the SIFT class directly?
        # Here are some pointers.
        # Scripting SIFT:
        # - http://imagej.net/Scripting_toolbox#Scripting_SIFT
        # SIFT plugin source code:
        # - https://github.com/axtimwalde/mpicbg/blob/2f411b380cffb580e35410b6517ffeb2c72489e2/mpicbg_/src/main/java/SIFT_Align.java)
        # - https://github.com/axtimwalde/mpicbg/blob/2f411b380cffb580e35410b6517ffeb2c72489e2/mpicbg/src/main/java/mpicbg/ij/SIFT.java
        print('Running plugin: Linear Stack Aligment with SIFT')
        IJ.run("Linear Stack Alignment with SIFT", "initial_gaussian_blur=1.6 steps_per_scale_octave=3 minimum_image_size=128 maximum_image_size=1024 feature_descriptor_size=8 feature_descriptor_orientation_bins=8 closest/next_closest_ratio=0.92 maximal_alignment_error=50 inlier_ratio=0.05 expected_transformation=Rigid interpolate show_transformation_matrix")
    elif method == 'StackReg':
        print('Running plugin: StackReg')
        IJ.run("StackReg ", "transformation=[Rigid Body]")
    else:
        print('ERROR: Unsupported registration method: {}'.format(method))

    # Save the aligned stack
    aligned_stack = IJ.getImage()  # The plugin only created one new image, the aligned stack, and it is now active
    output_filename = '{}_aligned_stack.tif'.format(method)
    IJ.save(aligned_stack, os.path.join(dstdir, output_filename))

# Do the registration
print('Performing image registration')
registration()
