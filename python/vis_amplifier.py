import numpy as np
from astropy.io import fits
import argparse
from findCCD import findCCD
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt

class vis_amplifier():

    def __init__(self, testName=None, CCDType=None, sensorId=None, XtraOpts = 'IMGTYPE=="FLAT"', run= None,
                 amp=None, mirror='BNL-Prod'):

       self.testName = testName
       self.CCDType = CCDType
       self.sensorId =sensorId
       self.run = run
       self.amp = amp
       self.XtraOpts = XtraOpts
       self.mirror = mirror

    def make_plt(self):
        
       fCCD= findCCD(FType='fits', testName=self.testName, sensorId=self.sensorId, run= self.run,
                     XtraOpts=self.XtraOpts, appSuffix='',prodServer='Prod',mirrorName=mirror)

       files = fCCD.find()


       # see LSSTTD-437 for treatment of bias using bias files, not (only) the overscan region.


       file = files[0]
       print file
#       file = '/Users/richard/LSST/Data/RTM-005/E2V-CCD250-220_sflat_500_flat_H011_20171213042022.fits'
#       file = '/Users/richard/LSST/Data/RTM-005/E2V-CCD250-252_sflat_500_flat_H001_20170523024234.fits'
       hdulist = fits.open(file)

       amp = int(self.amp)
       datasec=hdulist[amp].header['DATASEC'][1:-1].replace(':',',').split(',')

       biassec =  ['513', '562', '1', '2000']

       pixeldata = hdulist[amp].data
       bias = np.array(pixeldata[100:1900,520:550])

       # seeing a change in mean bias moving across the overscan region

       pedestal = np.mean(bias.flatten())
#       bias_sub = pixeldata[0:2047,0:511] - pedestal
       bias_sub = pixeldata[600:750,0:50] - pedestal


       return bias_sub

if __name__ == "__main__":

    ## Command line arguments
    parser = argparse.ArgumentParser(description='Plot image for CCD/amp/run.')

    ##   The following are 'convenience options' which could also be specified in the filter string
    parser.add_argument('-s','--sensorID', default=None,help="(metadata) Sensor ID (default=%(default)s)")
    parser.add_argument('-a','--amplifier', default=1,help="amplifier number (default=%(default)s)")
    parser.add_argument('-t','--type', default='dark',help="file kind (default=%(default)s)")
    parser.add_argument('-r','--run', default=None,help="run number (default=%(default)s)")
    parser.add_argument('-m','--mirror', default='BNL-Prod',help="DC mirror ")
    parser.add_argument('-o','--output', default='amplifier.pdf',help="output pdf file ")
    args = parser.parse_args()

    

    vA = vis_amplifier(testName=args.type, sensorId=args.sensorID, run=args.run, amp=args.amplifier, mirror=args.mirror)

    bias_sub = vA.make_plt()

    with PdfPages(args.output) as pdf:

        plt.imshow(bias_sub, cmap='hot', origin='lower')
        plt.colorbar()
        plt.suptitle(' Image region - flat')
        pdf.savefig()
        plt.close()
