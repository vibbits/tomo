#@String srcdir
#@String dstdir
#@String prefix
#@Integer numimages

# Prototype script for registering a set of images with ImageJ's SIFT registration plugin.
# This script is to be executed by a headless Fiji.
#
# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

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
    # Collect the filenames of the images we will load and save as a single stack
    print('Scanning source directory {} for images'.format(srcdir))
    images = []
    for filename in os.listdir(srcdir):
        if filename.startswith(prefix):
            full_filename = os.path.join(srcdir, filename)
            if os.path.isfile(full_filename):
                images.append(filename)

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

    # Display the unaligned stack (for debugging, not possible in headless mode)
    # stackImp.show()  # Not allowed when running Fiji in headless mode. Will throw a java.awt.HeadlessException

    # Some plugins, like the SIFT Image registration plugin we want to use,
    # use WindowManager.getCurrentImage() as their input image. However, if Fiji is running in headless mode
    # we cannot display images and getCurrentImage() is null. Fortunately, as a workaround, we can use setTempCurrentImage()
    # on the WindowManager which will then return it when getCurrentImage() is called.
    print('Make the unaligned stack the current image for the SIFT registration plugin')
    WindowManager.setTempCurrentImage(stackImp)   # WindowManager.getCurrentImage() will now return stackImp

    # Align the stack with SIFT. For now we run the ImageJ SIFT plugin,
    # but maybe we ought to use the SIFT class directly?
    # Here are some pointers.
    # Scripting SIFT:
    # - http://imagej.net/Scripting_toolbox#Scripting_SIFT
    # SIFT plugin source code:
    # - https://github.com/axtimwalde/mpicbg/blob/2f411b380cffb580e35410b6517ffeb2c72489e2/mpicbg_/src/main/java/SIFT_Align.java)
    # - https://github.com/axtimwalde/mpicbg/blob/2f411b380cffb580e35410b6517ffeb2c72489e2/mpicbg/src/main/java/mpicbg/ij/SIFT.java
#   IJ.run("Linear Stack Alignment with SIFT", "initial_gaussian_blur=1.60 steps_per_scale_octave=3 minimum_image_size=64 maximum_image_size=1024 feature_descriptor_size=4 feature_descriptor_orientation_bins=8 closest/next_closest_ratio=0.92 maximal_alignment_error=25 inlier_ratio=0.05 expected_transformation=Rigid interpolate");
    IJ.run("Linear Stack Alignment with SIFT", "initial_gaussian_blur=1.8 steps_per_scale_octave=3 minimum_image_size=128 maximum_image_size=1024 feature_descriptor_size=8 feature_descriptor_orientation_bins=8 closest/next_closest_ratio=0.92 maximal_alignment_error=25 inlier_ratio=0.05 expected_transformation=Translation interpolate");

    # Save the aligned stack
    aligned_stack = IJ.getImage()  # The SIFT plugin only created one new image, the aligned stack, it is now active
    IJ.save(aligned_stack, os.path.join(dstdir, "sift_aligned_stack.tif"))

# Do the registration
print('SIFT registration srcdir=' + srcdir + " dstdir=" + dstdir + " prefix=" + prefix)
registration()
