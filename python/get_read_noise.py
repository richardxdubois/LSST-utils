import numpy as np
from astropy.io import fits
import scipy as sc
import os
import argparse
from findCCD import findCCD
from exploreRaft import exploreRaft


class get_read_noise():

    def __init__(self, testName=None, CCDType=None,sensorId=None,  XtraOpts = None, run= None):

       self.testName = testName
       self.CCDType = CCDType
       self.sensorId =sensorId
       self.run = run
       self.XtraOpts = XtraOpts       

    def get_noise(self):
        
       fCCD= findCCD(FType='fits', testName=self.testName, sensorId=self.sensorId, dataType='SR-RTM-EOT-03', run= self.run, XtraOpts=self.XtraOpts)

       files = fCCD.find()


       # see LSSTTD-437 for treatment of bias using bias files, not (only) the overscan region.

       noise_list = []

       file = files[0]
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
    parser.add_argument('-R','--raft', default=None,help="run number (default=%(default)s)")
    parser.add_argument('--db', default='devdb_connect.txt',help="db connect file for getResults ")
    args = parser.parse_args()

    
    eR = exploreRaft(prodServer='Dev',appSuffix='-jrb')

    ccd_list = eR.raftContents(args.raft)


    for ccd_tuple in ccd_list:
        
        ccd = ccd_tuple[0]
        print ccd
        
        gN = get_read_noise(testName=args.type, CCDType=args.CCDType, sensorId=ccd, run=args.run)

        noise_list = gN.get_noise()
        print noise_list, '\n'

