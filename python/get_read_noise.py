import numpy as np
from astropy.io import fits
import scipy as sc
import os
import argparse
from findCCD_v2 import findCCD_v2


class get_read_noise():

    def __init__(self, testName=None, CCDType=None,sensorId=None,  XtraOpts = None, run= None, db_connect='db_connect.txt'):

       self.testName = testName
       self.CCDType = CCDType
       self.sensorId =sensorId
       self.run = run
       self.XtraOpts = XtraOpts
       self.db_connect = db_connect
       

    def get_noise(self):
        
       fCCD= findCCD_v2(FType='fits', testName=self.testName, CCDType=self.CCDType,sensorId=self.sensorId, dataType='SR-RTM-EOT-03', run= self.run, db_connect=self.db_connect, XtraOpts=self.XtraOpts)

       files = fCCD.find()

#       files = ["/Users/richard/LSST/Data/ITL-3800C-145/ETU2/ITL-3800C-145-Dev_fe55_bias_000_4714D_20170309232824.fits"]

       # see LSSTTD-437 for treatment of bias using bias files, not (only) the overscan region.

       noise_list = []

       for file in files:
           hdulist = fits.open(file)

           for amp in range(1,17):
               datasec=hdulist[amp].header['DATASEC'][1:-1].replace(':',',').split(',')

               biassec =  ['513', '562', '1', '2000']

               pixeldata = hdulist[amp].data
               bias = np.array(pixeldata[1500:1900,520:550])

               # seeing a change in mean bias moving across the overscan region

               pedestal = np.mean(bias.flatten())
               bias_sub = bias.flatten()-pedestal

               sigma = np.std(bias_sub)

               noise_list.append([amp, pedestal, sigma])

           break   # just do one file

       return noise_list

if __name__ == "__main__":

    ## Command line arguments
    parser = argparse.ArgumentParser(description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

    ##   The following are 'convenience options' which could also be specified in the filter string
    parser.add_argument('-s','--sensorID', default=None,help="(metadata) Sensor ID (default=%(default)s)")
    parser.add_argument('-c','--CCDType', default="ITL-3800C",help="(metadata) CCD vendor type (default=%(default)s)")
    parser.add_argument('-a','--amplifier', default=1,help="amplifier number (default=%(default)s)")
    parser.add_argument('-t','--type', default='dark',help="file kind (default=%(default)s)")
    parser.add_argument('-r','--run', default=None,help="run number (default=%(default)s)")
    parser.add_argument('--db', default='devdb_connect.txt',help="db connect file for getResults ")
    args = parser.parse_args()

    gN = get_read_noise(testName=args.type, CCDType=args.CCDType, sensorId=args.sensorID, run=args.run, db_connect=args.db)

    noise_list = gN.get_noise()
    print noise_list

