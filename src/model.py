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
    _KEY_SIFT_IMAGES_PIXELS_PER_MM = 'sift_images_pixels_per_mm'
    _KEY_FIJI_PATH = 'fiji_path'
    _KEY_ODEMIS_CLI = 'odemis_cli'
    _KEY_SIFT_REGISTRATION_SCRIPT = 'sift_registration_script'
    _KEY_LM_IMAGES_PREFIX = 'lm_images_prefix'
    _KEY_EM_IMAGES_PREFIX = 'em_images_prefix'
    _KEY_SIFT_INPUT_FOLDER = 'sift_input_folder'
    _KEY_SIFT_OUTPUT_FOLDER = 'sift_output_folder'
    _KEY_TEMPLATE_SLICE_PATH = 'template_slice_path'
    _KEY_PREPROCESSED_OVERVIEW_IMAGE_PATH = 'preprocessed_overview_image_path'

    def __init__(self):
        # User defined model parameters (will be made persistent)
        self.overview_image_path = None  # path to the overview image; it shows an overview of the section ribbons; typically obtained by stitching many LM image tiles together
        self.slice_polygons_path = None
        self.ribbons_mask_path = None
        self.lm_images_output_folder = None
        self.em_images_output_folder = None
        self.original_point_of_interest = None
        self.lm_stabilization_time_secs = 0.0  # time in seconds that we wait for the immersion oil droplet and stage etc. to stabilize before acquiring 100x LM images
        self.delay_between_LM_image_acquisition_secs = 0.0  # time in seconds to pause between successive microscope commands to acquire an LM image (maybe 1 or 2 secs in reality)
        self.delay_between_EM_image_acquisition_secs = 0.0  # time in seconds to pause between successive microscope commands to acquire an EM image (maybe 1 or 2 secs in reality)
        self.overview_image_pixels_per_mm = 0.0  # of the e.g. x20 lens overview image
        self.sift_images_pixels_per_mm = 0.0  # of the e.g. x100 lens LM images that will be acquired and used for SIFT registration
        self.fiji_path = None  # path to the Fiji executable; a headless Fiji is called in the background to perform LM image registration using one of the Fiji plugins
        self.odemis_cli = None  # path to the Odemis CLI (command line interface) tool
        self.sift_registration_script = None
        self.lm_images_prefix = None  # prefix of x100 image filenames
        self.em_images_prefix = None  # prefix of EM image filenames
        self.sift_input_folder = None
        self.sift_output_folder = None
        self.template_slice_path = None
        self.preprocessed_overview_image_path = None  # the path of the most recently loaded preprocessed overview image

        # Calculated model parameters (not persistent)
        self.slice_polygons = []
        self.all_points_of_interest = None
        self.slice_offsets_microns = None  # stage movements to move from the point-of-interest in slice to to slice i+1, based only on mapping the slice outline quadrilaterals
        self.combined_offsets_microns = None  # refined stage movement (combining slice outline mapping + SIFT registration of x100 images)
        self.overview_image_to_stage_coord_trf = None  # a numpy 3 x 3 homogeneous transformation matrix from overview image (pixel) coordinates to stage position coordinates (in mm); the third row of the matrix is [0 0 1], and it transforms a column matrix [xi; yi; 1]

        self.lm_use_focus_map = True  # Flag deciding whether or not to use the focus map (self.focus_map) created with the low magnification lens (e.g. 20x) to set the (rough) focus during LM image acquisition with the 100x lens. The 100x lens has a smaller depth of field than the 20x, so focus set this way may not be very good, but it could be a decent initial focus guess for autofocus.
        self.focus_map = None  # The actual focus map. It can be built and saved for use in the tiled overview image acquisition plugin for Odemis, and optionally used lateron during 100x LM image acquisition as well. Note: we need an overview image aligned with the stage before we can build a focus map (because we need to know the extent of the sample grid)
        self.image_size = (2048, 2048)  # (width, height) of the LM images in pixels; this is the size of the images that Odemis acquires; it is assumed to be constant.

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
        self.sift_input_folder                       = self._config.Read(TomoModel._KEY_SIFT_INPUT_FOLDER, r'/home/secom/development/tomo/data/output/LM')
        self.sift_output_folder                      = self._config.Read(TomoModel._KEY_SIFT_OUTPUT_FOLDER, r'/home/secom/development/tomo/data/output/LM')
        self.sift_images_pixels_per_mm               = self._config.ReadFloat(TomoModel._KEY_SIFT_IMAGES_PIXELS_PER_MM, 15398.49624)
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
        self._config.Write(TomoModel._KEY_SIFT_INPUT_FOLDER, self.sift_input_folder)
        self._config.Write(TomoModel._KEY_SIFT_OUTPUT_FOLDER, self.sift_output_folder)
        self._config.WriteFloat(TomoModel._KEY_SIFT_IMAGES_PIXELS_PER_MM, self.sift_images_pixels_per_mm)
        self._config.Write(TomoModel._KEY_TEMPLATE_SLICE_PATH, self.template_slice_path)
        self._config.Write(TomoModel._KEY_PREPROCESSED_OVERVIEW_IMAGE_PATH, self.preprocessed_overview_image_path)
        self._config.Flush()

    # Note
    #
    # On our SECOM we have the following image resolutions:
    # +------+-------------+
    # | lens | pixels/mm   |
    # +------+-------------+
    # |  10x |  1538.46154 |
    # |  20x |  3077.38542 |  WARNING: NOT VERY ACCURATE!
    # | 100x | 15398.49624 |
    # +------+-------------+
