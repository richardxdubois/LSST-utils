import numpy as np
from astropy.io import fits
import argparse
from  eTraveler.clientAPI.connection import Connection

## Command line arguments
parser = argparse.ArgumentParser(description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('-p','--prefix', default="/Users/richard/lsst_archive/farm/g/lsst/u5/",help="run number (default=%("
                                                                            "default)s)")
parser.add_argument('-r','--run', default=None,help="run number (default=%(default)s)")
parser.add_argument('-t','--test', default="SR-CCD-EOT-05_Preflight-Check",help="test/step name (default=%("
                                                                                "default)s)")
parser.add_argument('--db', default='Prod',help="db connect file for getResults ")
args = parser.parse_args()

connect = Connection(operator='richard', db=args.db, exp='LSST-CAMERA')

filePaths = connect.getRunFilepaths(run=args.run, stepName=args.test)
run_sum = connect.getRunSummary(run=args.run)

ccd = run_sum['experimentSN']
# see LSSTTD-437 for treatment of bias using bias files, not (only) the overscan region.

vpath = filePaths[args.test][3]['virtualPath'].strip('LSST/')

file = args.prefix + vpath
file = file.replace("SR-CCD-EOT-05_Preflight-Check", "preflight_acq")
print 'Operating on ', file
hdulist = fits.open(file)
expTime = hdulist[0].header['EXPTIME']

for ampHdu in range(1,17):
    datasec = hdulist[ampHdu].header['DATASEC'][1:-1].replace(':', ',').split(',')
    biassec = hdulist[ampHdu].header['BIASSEC'][1:-1].replace(':', ',').split(',')

    pixeldata = hdulist[ampHdu].data
    bias_restricted = np.array(pixeldata[1500:1900,520:550])
    bias_full = np.array(pixeldata[int(biassec[2]):int(biassec[3]), int(biassec[0]):
                                                                    int(biassec[1])])

    # seeing a change in mean bias moving across the overscan region

    bias_full_median = np.mean(bias_full.flatten())
    bias_full_restricted = np.mean(bias_restricted.flatten())

    print 'ccd = ', ccd, ' amp = ', ampHdu, ' bias_full_median = ', bias_full_median, \
                                    ' bias_restricted_median = ', bias_full_restricted


