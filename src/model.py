# Frank Vernaillen
# (c) Vlaams Instituut voor Biotechnologie (VIB)
# 2018-2019

import wx
from pubsub import pub

MSG_SLICE_POLYGON_CHANGED = 'msg_slice_polygon_changed'

class TomoModel:
    _KEY_OVERVIEW_IMAGE_PATH = 'overview_image_path'
    _KEY_SLICE_POLYGONS_PATH = 'slice_polygons_path'
    _KEY_RIBBONS_MASK_PATH = 'ribbons_mask_path'
    _KEY_LM_IMAGES_OUTPUT_FOLDER = 'lm_images_output_folder'
    _KEY_EM_IMAGES_OUTPUT_FOLDER = 'em_images_output_folder'
    _KEY_LM_STABILIZATION_TIME_SECS = 'lm_stabilization_time_secs'
    _KEY_LM_ACQUISITION_DELAY = 'lm_acquisition_delay'
    _KEY_EM_ACQUISITION_DELAY = 'em_acquisition_delay'
    _KEY_LM_DO_AUTOFOCUS = 'lm_do_autofocus'
    _KEY_LM_MAX_AUTOFOCUS_CHANGE_NANOMETERS = 'lm_max_autofocus_change_nanometers'
    _KEY_OVERVIEW_IMAGE_PIXELS_PER_MM = 'overview_image_pixels_per_mm'
    _KEY_LM_SIFT_IMAGES_PIXELS_PER_MM = 'lm_sift_images_pixels_per_mm'
    _KEY_FIJI_PATH = 'fiji_path'
    _KEY_ODEMIS_CLI = 'odemis_cli'
    _KEY_SIFT_REGISTRATION_SCRIPT = 'sift_registration_script'
    _KEY_LM_IMAGES_PREFIX = 'lm_images_prefix'
    _KEY_EM_IMAGES_PREFIX = 'em_images_prefix'
    _KEY_LM_SIFT_OUTPUT_FOLDER = 'lm_sift_output_folder'
    _KEY_EM_SIFT_OUTPUT_FOLDER = 'em_sift_output_folder'
    _KEY_TEMPLATE_SLICE_PATH = 'template_slice_path'
    _KEY_PREPROCESSED_OVERVIEW_IMAGE_PATH = 'preprocessed_overview_image_path'

    def __init__(self):
        # Data stored in persistent storage, e.g. user defined model parameters
        self.overview_image_path = None  # path to the overview image; it shows an overview of the section ribbons; typically obtained by stitching many LM image tiles together
        self.slice_polygons_path = None
        self.ribbons_mask_path = None
        self.lm_images_output_folder = None
        self.em_images_output_folder = None
        self.original_point_of_interest = None  # in overview image coordinates
        self.lm_stabilization_time_secs = 0.0  # time in seconds that we wait for the immersion oil droplet and stage etc. to stabilize before acquiring 100x LM images
        self.delay_between_LM_image_acquisition_secs = 0.0  # time in seconds to pause between successive microscope commands to acquire an LM image (maybe 1 or 2 secs in reality)
        self.delay_between_EM_image_acquisition_secs = 0.0  # time in seconds to pause between successive microscope commands to acquire an EM image (maybe 1 or 2 secs in reality)
        self.overview_image_pixels_per_mm = 0.0  # of the e.g. x20 lens overview image
        self.lm_sift_images_pixels_per_mm = 0.0  # of the e.g. x100 lens LM images that will be acquired and used for SIFT registration
        self.fiji_path = None  # path to the Fiji executable; a headless Fiji is called in the background to perform LM image registration using one of the Fiji plugins
        self.odemis_cli = None  # path to the Odemis CLI (command line interface) tool
        self.sift_registration_script = None  # full path of the Python image registration script that will be run from a headless Fiji that will be started from Tomo
        self.lm_images_prefix = None  # prefix of x100 image filenames
        self.em_images_prefix = None  # prefix of EM image filenames
        self.lm_sift_output_folder = None
        self.em_sift_output_folder = None
        self.template_slice_path = None
        self.preprocessed_overview_image_path = None  # the path of the most recently loaded preprocessed overview image

        # Data not stored in persistent storage, e.g. derived parameters or data unlikely to remain the same for multiple experiments
        self.slice_polygons = []
        self.all_points_of_interest = None  # in overview image coordinates (pixels), first point is user selected POI in first section, all others are predicted POIs in subsequent sections
        self.slice_offsets_microns = None  # stage movements to move from the point-of-interest in slice to to slice i+1, based only on mapping the slice outline quadrilaterals
        self.combined_offsets_microns = None  # refined stage movement (combining slice outline mapping + SIFT registration of x100 images)
        self.all_offsets_microns = []  # All poi offsets (slice mapping + LM SIFT offsets + EM sift offsets + ???): e.g. [{'name':'slice mapping', 'parameters':{}, 'offsets':[(dx1,dy1),(dx2,dy2)]}, {'name':'LM SIFT Registration', 'parameters':{}, 'offsets':[(dx1,dy1), (dx2,dy2),...]}, ('name': 'EM SIFT Registration', 'parameters': {'magnification':5000, etc}, 'offsets': [(dx1,dy1),(dx2, dy2),...]})]; the sum of all these offsets is the same as combined_offsets_microns
                                       # Currently used only as an informative history of the different offset corrections.
        self.overview_image_to_stage_coord_trf = None  # a numpy 3 x 3 homogeneous transformation matrix from overview image (pixel) coordinates to stage position coordinates (in mm); the third row of the matrix is [0 0 1], and it transforms a column matrix [xi; yi; 1]

        self.lm_use_focus_map = True  # Flag deciding whether or not to use the focus map (self.focus_map) created with the low magnification lens (e.g. 20x) to set the (rough) focus during LM image acquisition with the 100x lens. The 100x lens has a smaller depth of field than the 20x, so focus set this way may not be very good, but it could be a decent initial focus guess for autofocus.
        self.focus_map = None  # The actual focus map (for LM only). It can be built and saved for use in the tiled overview image acquisition plugin for Odemis, and optionally used lateron during 100x LM image acquisition as well. Note: we need an overview image aligned with the stage before we can build a focus map (because we need to know the extent of the sample grid)

        self.lm_registration_params = {'crop': False, 'roi': [0, 0, 2048, 2048], 'enhance_contrast': False, 'invert': False}  # roi=[top left x, top left y, width, height] in pixels (integer values); invert=invert stack images (yields more intuitive images in EM mode so always used there, not used for LM)
        self.em_registration_params = {'crop': False, 'roi': [0, 0, 2048, 2048], 'enhance_contrast': True, 'invert': True}  # same meaning as lm_registration_params

        self.em_scale = 1  # scale for EM image acquisition (an integer: 1, 2, 4, 8 or 16); for example 4 corresponds to the Odemis scale string '4,4'
        self.em_dwell_time_microseconds = 50  # dwell time for EM image acquisition (in microseconds)
        self.em_magnification = 5000  # magnification factor for EM image acquisition

        # Constants
        self.lm_image_size = (2048, 2048)  # (width, height) of the LM images in pixels; this is the size of the images that Odemis acquires; it is assumed to be constant.
        self.max_em_image_size = (5120, 3840)  # (width, height) of the EM images in pixels *only* for an em_scale=1. For a scale s the actual EM images are 5120/s, 3840/s pixels large.

        # Persistent storage
        self._config = wx.Config('be.vib.bits.tomo')
        self.read_parameters()

    def set_slice_polygon(self, i, polygon):
        self.slice_polygons[i] = polygon
        pub.sendMessage(MSG_SLICE_POLYGON_CHANGED, index=i, polygon=polygon)

    def read_parameters(self):
        self.overview_image_path                     = self._config.Read(TomoModel._KEY_OVERVIEW_IMAGE_PATH, r'/home/secom/development/tomo/data/bisstitched-0.tif')
        self.slice_polygons_path                     = self._config.Read(TomoModel._KEY_SLICE_POLYGONS_PATH, r'/home/secom/development/tomo/data/bisstitched-0.points.json')
        self.ribbons_mask_path                       = self._config.Read(TomoModel._KEY_RIBBONS_MASK_PATH, r'/home/secom/development/tomo/data/bisstitched-0-ribbonsmask.tif')
        self.lm_images_output_folder                 = self._config.Read(TomoModel._KEY_LM_IMAGES_OUTPUT_FOLDER, r'/home/secom/development/tomo/data/output/LM')
        self.em_images_output_folder                 = self._config.Read(TomoModel._KEY_EM_IMAGES_OUTPUT_FOLDER, r'/home/secom/development/tomo/data/output/EM')
        self.lm_stabilization_time_secs              = self._config.ReadFloat(TomoModel._KEY_LM_STABILIZATION_TIME_SECS, 5.0)
        self.delay_between_LM_image_acquisition_secs = self._config.ReadFloat(TomoModel._KEY_LM_ACQUISITION_DELAY, 2.0)
        self.delay_between_EM_image_acquisition_secs = self._config.ReadFloat(TomoModel._KEY_EM_ACQUISITION_DELAY, 2.0)
        self.overview_image_pixels_per_mm            = self._config.ReadFloat(TomoModel._KEY_OVERVIEW_IMAGE_PIXELS_PER_MM, 3077.38542)
        self.fiji_path                               = self._config.Read(TomoModel._KEY_FIJI_PATH, r'/home/secom/Downloads/Fiji.app/ImageJ-linux64')
        self.odemis_cli                              = self._config.Read(TomoModel._KEY_ODEMIS_CLI, r'/usr/bin/odemis-cli')
        self.sift_registration_script                = self._config.Read(TomoModel._KEY_SIFT_REGISTRATION_SCRIPT, r'/home/secom/development/tomo/sift_registration.py')
        self.lm_images_prefix                        = self._config.Read(TomoModel._KEY_LM_IMAGES_PREFIX, 'lmsection')
        self.em_images_prefix                        = self._config.Read(TomoModel._KEY_EM_IMAGES_PREFIX, 'emsection')
        self.lm_sift_output_folder                   = self._config.Read(TomoModel._KEY_LM_SIFT_OUTPUT_FOLDER, r'/home/secom/')
        self.em_sift_output_folder                   = self._config.Read(TomoModel._KEY_EM_SIFT_OUTPUT_FOLDER, r'/home/secom/')
        self.lm_sift_images_pixels_per_mm            = self._config.ReadFloat(TomoModel._KEY_LM_SIFT_IMAGES_PIXELS_PER_MM, 0.0)
        self.template_slice_path                     = self._config.Read(TomoModel._KEY_TEMPLATE_SLICE_PATH, r'/home/secom/some/folder/template_slice_contour.json')
        self.preprocessed_overview_image_path        = self._config.Read(TomoModel._KEY_PREPROCESSED_OVERVIEW_IMAGE_PATH, r'/home/secom/development/tomo/data/preprocessed_overview_image.tif')

    def write_parameters(self):
        self._config.Write(TomoModel._KEY_OVERVIEW_IMAGE_PATH, self.overview_image_path)
        self._config.Write(TomoModel._KEY_SLICE_POLYGONS_PATH, self.slice_polygons_path)
        self._config.Write(TomoModel._KEY_RIBBONS_MASK_PATH, self.ribbons_mask_path)
        self._config.Write(TomoModel._KEY_LM_IMAGES_OUTPUT_FOLDER, self.lm_images_output_folder)
        self._config.Write(TomoModel._KEY_EM_IMAGES_OUTPUT_FOLDER, self.em_images_output_folder)
        self._config.WriteFloat(TomoModel._KEY_LM_STABILIZATION_TIME_SECS, self.lm_stabilization_time_secs)
        self._config.WriteFloat(TomoModel._KEY_LM_ACQUISITION_DELAY, self.delay_between_LM_image_acquisition_secs)
        self._config.WriteFloat(TomoModel._KEY_EM_ACQUISITION_DELAY, self.delay_between_EM_image_acquisition_secs)
        self._config.WriteFloat(TomoModel._KEY_OVERVIEW_IMAGE_PIXELS_PER_MM, self.overview_image_pixels_per_mm)
        self._config.Write(TomoModel._KEY_FIJI_PATH, self.fiji_path)
        self._config.Write(TomoModel._KEY_ODEMIS_CLI, self.odemis_cli)
        self._config.Write(TomoModel._KEY_SIFT_REGISTRATION_SCRIPT, self.sift_registration_script)
        self._config.Write(TomoModel._KEY_LM_IMAGES_PREFIX, self.lm_images_prefix)
        self._config.Write(TomoModel._KEY_EM_IMAGES_PREFIX, self.em_images_prefix)
        self._config.Write(TomoModel._KEY_LM_SIFT_OUTPUT_FOLDER, self.lm_sift_output_folder)
        self._config.Write(TomoModel._KEY_EM_SIFT_OUTPUT_FOLDER, self.em_sift_output_folder)
        self._config.WriteFloat(TomoModel._KEY_LM_SIFT_IMAGES_PIXELS_PER_MM, self.lm_sift_images_pixels_per_mm)
        self._config.Write(TomoModel._KEY_TEMPLATE_SLICE_PATH, self.template_slice_path)
        self._config.Write(TomoModel._KEY_PREPROCESSED_OVERVIEW_IMAGE_PATH, self.preprocessed_overview_image_path)
        self._config.Flush()

    ###############################
    #  EM   # EM image dimensions #
    # Scale #   width   height    #
    ###############################
    #  1,1  #   5120     3840     #
    #  2,2  #   2560     1920     #
    #  4,4  #   1280      960     #
    #  8,8  #    640      480     #
    # 16,16 #    320      240     #
    ###############################
    #  s,s  #   5120/s   3840/s   #
    ###############################

    # About EM image pixel size:
    # One example image:
    #   magnification=1000
    #   scale=4,4 (= 1280x960 pixels)
    #   has physical FOV 119 x 89.25 micrometers (as seen in Fiji)
    #   => pixels/micrometer = 1280/119 = 960/89.25 = 10.756302521
    #   If scale changes, the same physical FOV is still imaged, so the pixels become accordingly larger or smaller.
    #   If magnification becomes m times larger, the physical FOV becomes m times smaller.

    def get_em_image_size_in_pixels(self):
        # returns (width, height) of EM image in pixels
        width_pixels = self.max_em_image_size[0] / self.em_scale
        height_pixels = self.max_em_image_size[1] / self.em_scale
        return width_pixels, height_pixels

    def get_em_image_size_in_microns(self):
        # Note: the magical values 119 and 89.25 micrometer were obtained from the metadata of an EM image acquired with the microscope.
        # I don't know where they come from...
        width_microns = 119 * (1000.0 / self.em_magnification)
        height_microns = 89.25 * (1000.0 / self.em_magnification)
        return width_microns, height_microns

    def get_em_pixels_per_micrometer(self):
        width_pixels, height_pixels = self.get_em_image_size_in_pixels()
        width_microns, height_microns = self.get_em_image_size_in_microns()
        pixels_per_micrometer_x = width_pixels / width_microns
        pixels_per_micrometer_y = height_pixels / height_microns
        assert abs(pixels_per_micrometer_x - pixels_per_micrometer_y) < 1e-3
        return pixels_per_micrometer_x

    def set_em_scale_string(self, scale_string):
        """
        :param scale_string, always of the format 'n,n' (n a power of 2) e.g. '16,16'
        :return: the scale value as an integer e.g. 16
        """
        scales = scale_string.split(',')
        assert len(scales) == 2
        assert int(scales[0]) == int(scales[1])
        self.em_scale = int(scales[0])

    def get_em_scale_string(self):
        """
        :return: an EM scale string as expected by some Odemis calls e.g. '4,4' for a factor 4 (down) scale
        """
        return '{},{}'.format(self.em_scale, self.em_scale)

    # Note
    #
    # On our SECOM we have the following approximate image resolutions:
    # +------+-------------+
    # | lens | pixels/mm   |
    # +------+-------------+
    # |  10x |  1538.46154 |
    # |  20x |  3077.38542 |  WARNING: NOT VERY ACCURATE!
    # | 100x | 15398.49624 |
    # +------+-------------+
