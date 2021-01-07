import gdal
import sys
import os
import glob2
import csv
import time
start_time = time.time()
# this allows GDAL to throw Python Exceptions
gdal.UseExceptions()

# Script will recursively go through subdirectories and report information about each tif image. If there is
# a corrupt image it will add an entry to a csv. place script in parent folder and run.

lst = glob2.glob('**\*.jpg')

for file in lst:

    try:
        jpg = gdal.Open(file)
        # print gtif.GetMetadata()
        statinfo = os.stat(file)
        size = statinfo.st_size / 1e6
        cols = jpg.RasterXSize
        rows = jpg.RasterYSize

        print(file,' -- ', size, 'Mb')
        # print size, "Mb"

        print("     bands", jpg.RasterCount, ' -- ', cols, "cols x ", rows, " rows")
        # print cols, " cols x ", rows, " rows"

        jpg = None


    except (RuntimeError, e):
        print('Unable to open '+file)
        print(e)
        x = file, e
        # print x
        # sys.exit(1)
        with open('image_errors.csv', 'ab') as csvfile:
            wr = csv.writer(csvfile, delimiter=',')
            wr.writerow(x)

print("--- %s seconds ---" % (time.time() - start_time))
print(len(lst), 'files')








