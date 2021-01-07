import subprocess
import gdal
import os

from tkinter.filedialog import askdirectory
from tkinter import Tk
from glob import glob
from tqdm import tqdm


def PROJECTIONS():
    """
    Return constant PROJECTIONS.

    :return: A dictionary of projections and EPSG codes.
    """
    projections = {
        'utm08': 3155, 'utm8': 3155, 'utm09': 3156, 'utm9': 3156,
        'utm10': 3157, 'utm11': 2955, 'bcalb': 3005
    }

    return projections


class CloudOptimizedGeotiff:

    """
    Create Cloud Optimized Geotiffs.

    Converts ASCII and USGS DEM raster elevation data
    to Cloud Optimized Geotiffs.
    """

    def __init__(self):
        
        # Define creation option values.
        self.predictor = 3 
        self.epsg = None
        self.compress_method = 'DEFLATE'
        self.compress_level = 6  
        self.overview_levels = [2, 4]
        self.resampling = 'cubic'
        self.blockxsize = 512
        self.blockysize = 512

        # set global GDAL configuration options
        gdal.SetConfigOption(
            ('GDAL_TIFF_OVR_BLOCKSIZE', f'{self.blockxsize}'),
            ('COMPRESS_OVERVIEW', f'{self.compress_method}')
        )

        # make use of python exceptions
        gdal.UseExceptions()

    def set_jpeg_quality(self, jpeg_quality=75):

        """
        Append jpeg quality to gdal command string.

        Argument jpeg_quality set to 75 by default.

        :param jpeg_quality: int between 1 and 100.
        """

        self.compress_method += f' -co JPEG_QUALITY={jpeg_quality}'

    def batch_compress_and_tile(self, list_of_files: list, out_dir: str):

        """
        Compress and internally tile a list of files.


        :param list_of_files:   A list of usgs or ascii dems.
        :param out_dir:         Directory
        :return:
        """

        # change directory to output location
        os.chdir(out_dir)
        
        # loop through files and convert, compress, and internally tile new tif files
        for file in tqdm(list_of_files):

            # define output name
            out_name = f'{os.path.splitext(os.path.basename(file))[0]}.tif'

            # move on to next file if file exists
            if os.path.exists(out_name):
                continue

            # get the epsg code
            self.epsg_from_filename(file)

            # create translate options object
            translate_options = self.create_translate_options()

            # perform compression and tiling
            try:
                gdal.Translate(out_name, file, options=translate_options)

            # log any errors encountered
            except Exception as e:
                with open(os.path.join(out_dir, 'compression_and_tiling_errors.txt'), 'a+') as err_file:
                    err_file.write(f'{file}\t{e}\n')

    def create_translate_options(self):

        """
        Create translate options object.

        :return: gdal_translate options.
        """

        # amend gdal command string for jpeg
        if self.compress_method == 'JPEG':
            self.set_jpeg_quality()

        # Create gdal_translate command options
        trans_str = (
            f'-of GTiff -a_srs EPSG:{str(self.epsg)} '
            f'-co PREDICTOR={str(self.predictor)} -q '
            f'-co TILED=YES -co NUM_THREADS=ALL_CPUS '
            f'-co COMPRESS={self.compress_method} '
            f'-co ZLEVEL={str(self.compress_level)}'
        )
        # pass parsed string to TranslateOptions object
        return gdal.TranslateOptions(gdal.ParseCommandLine(trans_str))

    def epsg_from_filename(self, filename):

        """
        Get epsg code from filename.

        Created for GeoBC. Will only work with GeoBC naming conventions.

        :param filename:    GeoBC approved filename.
        """

        # try to get projection from filename, if no projection in the filename, filename is wrong.
        for index, string in enumerate(os.path.splitext(os.path.basename(filename))[0].split('_')):
            if 'utm' in string or 'bcalb' in string:  # check for proj in filename
                # use index value as key to get value from dictionary
                self.epsg = PROJECTIONS()[string]
                break

    """Method to create overviews using GDAL's python api"""
    def batch_create_overviews(self, list_of_files):

        """
        Create overviews for list of files.

        :param list_of_files: A list of tif files.
        :return:
        """

        # loop through files, create overviews
        for f in tqdm(list_of_files):
            im = gdal.Open(f)
            im.BuildOverviews('CUBIC', self.overview_levels)  # create overviews
            im = None  # close the datasource

    def batch_create_cog(self, list_of_files, out_dir):

        """
        Create cloud optimized geotiffs.

        :param list_of_files:   A list of input files.
        :param out_dir:         Output location.
        """

        # create gdal_translate command string
        trans_str = (
            f'-co TILED=YES '
            f'-co COPY_SRC_OVERVIEWS=YES '
            f'-co COMPRESS={self.compress_method} '
            f'-co NUM_THREADS=ALL_CPUS '
            f'-co BLOCKXSIZE={str(self.blockxsize)} '
            f'-co BLOCKYSIZE={str(self.blockysize)}'
        )

        # parse command line syntax to be passed to translate options
        tp = gdal.ParseCommandLine(trans_str)

        # pass parsed string to TranslateOptions object
        trans_opt = gdal.TranslateOptions(tp)

        # define output path for cloud optimized geotiffs
        out = os.path.join(out_dir, 'COG')
        os.mkdir(out)  # make the dir
        os.chdir(out)  # navigate to dir

        # loop the files and convert
        for file in tqdm(list_of_files):
            out_name = f'{os.path.splitext(os.path.basename(file))[0]}.tif'
            # if file already exists, pass
            if os.path.exists(out_name):
                continue

            # make COGS
            try:
                gdal.Translate(out_name, file, options=trans_opt)  # pass translate options to gdal.Translate()

            # log any errors encountered
            except Exception as e:
                with open(os.path.join(out, 'COG_creation_errors.txt'), 'a+') as err_file:
                    err_file.write(f'{file}\t{e}\n')

    @staticmethod
    def remove_intermediate_tif(in_dir):

        """Remove intermediate tif files created."""

        # Remove intermediate files
        [os.remove(f) for f in glob(os.path.join(in_dir, '*.tif'))]

    def run_cog_conversion(self):

        """Run full conversion process."""

        # Close empty tkinter window
        Tk().withdraw()
        # Specify input and output directory
        idir = askdirectory(title='Select input directory')
        odir = askdirectory(title='Select output directory')

        # create list of files
        flist = []
        for e in ('*.asc', '*.dem', '*.tif'):
            flist.extend(glob(os.path.join(idir, e), recursive=True))

        # run the gdal.Translate function
        self.batch_compress_and_tile(flist, odir)
        # generate overviews
        self.batch_create_overviews(odir)
        # generate cogs from new tif files
        self.batch_create_cog(glob(os.path.join(odir, '*.tif')), odir)
        # remove intermediate files
        self.remove_intermediate_tif(odir)


def main():

    """Drive the program."""

    CloudOptimizedGeotiff().run_cog_conversion()


if __name__ == '__main__':
    main()
