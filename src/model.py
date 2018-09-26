# Frank Vernaillen
# September 2018
# (c) Vlaams Instituut voor Biotechnologie (VIB)

import numpy as np
import wx

class TomoModel:
    _KEY_OVERVIEW_IMAGE_PATH = 'overview_image_path'
    _KEY_SLICE_POLYGONS_PATH = 'slice_polygons_path'
    _KEY_LM_IMAGES_OUTPUT_FOLDER = 'lm_images_output_folder'
    _KEY_EM_IMAGES_OUTPUT_FOLDER = 'em_images_output_folder'
    _KEY_ORIGINAL_POI_X = 'original_poi_x'
    _KEY_ORIGINAL_POI_Y = 'original_poi_y'
    _KEY_LM_ACQUISITION_DELAY = 'lm_acquisition_delay'
    _KEY_EM_ACQUISITION_DELAY = 'em_acquisition_delay'
    _KEY_OVERVIEW_IMAGE_MM_PER_PIXEL = 'overview_image_mm_per_pixel'
    _KEY_SIFT_IMAGES_MM_PER_PIXEL = 'sift_images_mm_per_pixel'
    _KEY_FIJI_PATH = 'fiji_path'
    _KEY_ODEMIS_CLI = 'odemis_cli'
    _KEY_SIFT_REGISTRATION_SCRIPT = 'sift_registration_script'
    _KEY_LM_IMAGES_PREFIX = 'lm_images_prefix'
    _KEY_EM_IMAGES_PREFIX = 'em_images_prefix'
    _KEY_SIFT_INPUT_FOLDER = 'sift_input_folder'
    _KEY_SIFT_OUTPUT_FOLDER = 'sift_output_folder'

    # Persistent storage
    _config = None

    # User defined model parameters (will be made persistent)
    overview_image_path = None
    slice_polygons_path = None
    lm_images_output_folder = None
    em_images_output_folder = None
    original_point_of_interest = np.array([0, 0])
    delay_between_LM_image_acquisition_secs = 0.0  # time in seconds to pause between successive microscope commands to acquire an LM image (maybe 1 or 2 secs in reality)
    delay_between_EM_image_acquisition_secs = 0.0  # time in seconds to pause between successive microscope commands to acquire an EM image (maybe 1 or 2 secs in reality)
    overview_image_mm_per_pixel = 0.0  # of the e.g. x20 lens overview image
    sift_images_mm_per_pixel = 0.0 # of the e.g. x100 lens LM images that will be acquired and used for SIFT registration
    fiji_path = None
    odemis_cli = None
    sift_registration_script = None
    lm_images_prefix = None  # prefix of x100 image filenames
    em_images_prefix = None  # prefix of EM image filenames
    sift_input_folder = None
    sift_output_folder = None

    # Calculated model parameters (not persistent)
    slice_polygons = None
    all_points_of_interest = None
    slice_offsets_microns = None  # stage movements to move from the point-of-interest in slice to to slice i+1, based only on mapping the slice outline quadrilaterals
    combined_offsets_microns = None  # refined stage movement (combining slice outline mapping + SIFT registration of x100 images)

    def __init__(self):
        self._config = wx.Config('be.vib.bits.tomo')
        self.read_parameters()

    def read_parameters(self):
        self.overview_image_path                     = self._config.Read(TomoModel._KEY_OVERVIEW_IMAGE_PATH, r'/home/secom/development/tomo/data/bisstitched-0.tif')
        self.slice_polygons_path                     = self._config.Read(TomoModel._KEY_SLICE_POLYGONS_PATH, r'/home/secom/development/tomo/data/bisstitched-0.points.json')
        self.lm_images_output_folder                 = self._config.Read(TomoModel._KEY_LM_IMAGES_OUTPUT_FOLDER, r'/home/secom/development/tomo/data/output/LM')
        self.em_images_output_folder                 = self._config.Read(TomoModel._KEY_EM_IMAGES_OUTPUT_FOLDER, r'/home/secom/development/tomo/data/output/EM')
        self.original_point_of_interest[0]           = self._config.ReadInt(TomoModel._KEY_ORIGINAL_POI_X, 2417)
        self.original_point_of_interest[1]           = self._config.ReadInt(TomoModel._KEY_ORIGINAL_POI_Y, 1066)
        self.delay_between_LM_image_acquisition_secs = self._config.ReadFloat(TomoModel._KEY_LM_ACQUISITION_DELAY, 2.0)
        self.delay_between_EM_image_acquisition_secs = self._config.ReadFloat(TomoModel._KEY_EM_ACQUISITION_DELAY, 2.0)
        self.overview_image_mm_per_pixel             = self._config.ReadFloat(TomoModel._KEY_OVERVIEW_IMAGE_MM_PER_PIXEL, 3077.38542)
        self.fiji_path                               = self._config.Read(TomoModel._KEY_FIJI_PATH, r'/home/secom/Downloads/Fiji.app/ImageJ-linux64')
        self.odemis_cli                              = self._config.Read(TomoModel._KEY_ODEMIS_CLI, r'/usr/bin/odemis-cli')
        self.sift_registration_script                = self._config.Read(TomoModel._KEY_SIFT_REGISTRATION_SCRIPT, r'/home/secom/development/tomo/sift_registration.py')
        self.lm_images_prefix                        = self._config.Read(TomoModel._KEY_LM_IMAGES_PREFIX, 'lmsection')
        self.em_images_prefix                        = self._config.Read(TomoModel._KEY_EM_IMAGES_PREFIX, 'emsection')
        self.sift_input_folder                       = self._config.Read(TomoModel._KEY_SIFT_INPUT_FOLDER, r'/home/secom/development/tomo/data/output/LM')
        self.sift_output_folder                      = self._config.Read(TomoModel._KEY_SIFT_OUTPUT_FOLDER, r'/home/secom/development/tomo/data/output/LM')
        self.sift_images_mm_per_pixel                = self._config.ReadFloat(TomoModel._KEY_SIFT_IMAGES_MM_PER_PIXEL, 1000.0)  # just a random value, probably not typical

    def write_parameters(self):
        self._config.Write(TomoModel._KEY_OVERVIEW_IMAGE_PATH, self.overview_image_path)
        self._config.Write(TomoModel._KEY_SLICE_POLYGONS_PATH, self.slice_polygons_path)
        self._config.Write(TomoModel._KEY_LM_IMAGES_OUTPUT_FOLDER, self.lm_images_output_folder)
        self._config.Write(TomoModel._KEY_EM_IMAGES_OUTPUT_FOLDER, self.em_images_output_folder)
        self._config.WriteInt(TomoModel._KEY_ORIGINAL_POI_X, self.original_point_of_interest[0])
        self._config.WriteInt(TomoModel._KEY_ORIGINAL_POI_Y, self.original_point_of_interest[1])
        self._config.WriteFloat(TomoModel._KEY_LM_ACQUISITION_DELAY, self.delay_between_LM_image_acquisition_secs)
        self._config.WriteFloat(TomoModel._KEY_EM_ACQUISITION_DELAY, self.delay_between_EM_image_acquisition_secs)
        self._config.WriteFloat(TomoModel._KEY_OVERVIEW_IMAGE_MM_PER_PIXEL, self.overview_image_mm_per_pixel)
        self._config.Write(TomoModel._KEY_FIJI_PATH, self.fiji_path)
        self._config.Write(TomoModel._KEY_ODEMIS_CLI, self.odemis_cli)
        self._config.Write(TomoModel._KEY_SIFT_REGISTRATION_SCRIPT, self.sift_registration_script)
        self._config.Write(TomoModel._KEY_LM_IMAGES_PREFIX, self.lm_images_prefix)
        self._config.Write(TomoModel._KEY_EM_IMAGES_PREFIX, self.em_images_prefix)
        self._config.Write(TomoModel._KEY_SIFT_INPUT_FOLDER, self.sift_input_folder)
        self._config.Write(TomoModel._KEY_SIFT_OUTPUT_FOLDER, self.sift_output_folder)
        self._config.WriteFloat(TomoModel._KEY_SIFT_IMAGES_MM_PER_PIXEL, self.sift_images_mm_per_pixel)
        self._config.Flush()

    # # Input parameters # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
    # Frank Windows
    # overview_image_path = r'F:\Secom\sergio_x20_LM_objective_overview_image\bisstitched-0.tif'
    # slice_polygons_path = r'E:\git\bits\bioimaging\Secom\tomo\data\bisstitched-0.points.json'
    # lm_images_output_folder = r'E:\git\bits\bioimaging\Secom\tomo\data\output\LM'
    # original_point_of_interest = np.array([2417, 1066]) #[1205, 996])
    # delay_between_LM_image_acquisition_secs = 0.1  # time in seconds to pause between successive microscope commands to acquire an LM image (maybe 1 or 2 secs in reality)
    # mm_per_pixel = 3077.38542  # of the x20 lens overview image
    # fiji = r'e:\Fiji.app\ImageJ-win64.exe'
    # odemis_cli = r'E:\git\bits\bioimaging\Secom\tomo\odemis-cli.bat'
    # sift_registration_script = r'E:\git\bits\bioimaging\Secom\tomo\sift_registration.py'
    # lm_images_prefix = 'section'                      # prefix = 'lm_slice_'   # prefix of x100 image filenames
    # sift_input_folder = r'F:\Secom\cell1'
    # sift_output_folder = r'F:\Secom\cell1\frank'      # os.path.join(lm_images_output_folder, 'xxxxx')
    #
    # Frank Ubuntu
    # overview_image_path = r'/media/frank/FRANK EXTERNAL/Manual Backups/tomo/data/bisstitched-0.tif'
    # slice_polygons_path = r'/media/frank/FRANK EXTERNAL/Manual Backups/tomo/data/bisstitched-0.points.json'
    # sift_registration_script = r'/media/frank/FRANK EXTERNAL/sift_registration.py'
    # sift_input_folder = r'/media/frank/FRANK EXTERNAL/Secom/cell1'
    # sift_output_folder = r'/media/frank/FRANK EXTERNAL/Secom/cell1/frank'
    # fiji = r'/home/frank/Fiji.app/ImageJ-linux64'
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #