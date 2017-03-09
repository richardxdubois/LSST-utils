import numpy as np
import matplotlib.pyplot as plt
import astropy as ast
import astropy.stats
from astropy.io import fits
import scipy as sc
import scipy.signal
import textwrap
import os
from query_eT import query_eT
from findCCD import findCCD
import statsmodels.api as smapi
from statsmodels.formula.api import ols
from matplotlib.backends.backend_pdf import PdfPages
import argparse


## Command line arguments
parser = argparse.ArgumentParser(description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('-s','--sensorID', default=None,help="(metadata) Sensor ID (default=%(default)s)")
parser.add_argument('-c','--CCDType', default="ITL-3800C",help="(metadata) CCD vendor type (default=%(default)s)")
parser.add_argument('-a','--amplifier', default=1,help="amplifier number (default=%(default)s)")
parser.add_argument('-t','--type', default='dark',help="file kind (default=%(default)s)")
args = parser.parse_args()


ccdType = args.CCDType
dataTypeFiles = 'SR-RCV-01'
device = args.sensorID
ampHdu = int(args.amplifier)

# fCCD= findCCD(mirrorName='vendorCopy-prod',FType='fits', XtraOpts='IMGTYPE="DARK"&&TESTTYPE="DARK"', testName='vendorIngest', CCDType=ccdType,sensorId=device, dataType=dataTypeFiles)

#files_test = fCCD.find()
#print files_test

print ' Working on amp #', ampHdu

gainName = ['fe55_analysis', 'gain']
darkName = ['dark_current','dark_current_95CL']
dataType = 'SR-EOT-02'

eT = query_eT(schemaName=gainName[0], valueName=gainName[1], ccdType=ccdType, dataType=dataType, device=device)

engine = eT.connectDB()

gainEOT1  = eT.queryResultsDB(engine)

eT.setParams(schemaName=darkName[0], valueName=darkName[1])

darkEOT1  = eT.queryResultsDB(engine)

# TS-3
#files = ["/Users/richard/LSST/Data/ITL-3800C-034/EOT-1/ITL-3800C-034_dark_bias_000_20170104200232.fits"]


#files = ["/Users/richard/LSST/Data/ITL-3800C-034/EOT-1/ITL-3800C-034_dark_dark_1_20170104201952.fits"]
#           "/Users/richard/LSST/Data/ITL-3800C-034/EOT-1/ITL-3800C-034_dark_dark_2_20170104202929.fits",
#           "/Users/richard/LSST/Data/ITL-3800C-034/EOT-1/ITL-3800C-034_dark_dark_3_20170104203908.fits",
#           "/Users/richard/LSST/Data/ITL-3800C-034/EOT-1/ITL-3800C-034_dark_dark_4_20170104204843.fits",
#            "/Users/richard/LSST/Data/ITL-3800C-034/EOT-1/ITL-3800C-034_dark_dark_5_20170104205822.fits" ]

#files = ["/Users/richard/LSST/Data/ITL-3800C-034/EOT-02/ITL-3800C-034_dark_dark_001_20160913074701.fits"]
#             "/Users/richard/LSST/Data/ITL-3800C-034/EOT-02/ITL-3800C-034_dark_dark_003_20160913074701.fits",
#             "/Users/richard/LSST/Data/ITL-3800C-034/EOT-02/ITL-3800C-034_dark_dark_005_20160913074701.fits",
#             "/Users/richard/LSST/Data/ITL-3800C-034/EOT-02/ITL-3800C-034_dark_dark_007_20160913074701.fits",
#             "/Users/richard/LSST/Data/ITL-3800C-034/EOT-02/ITL-3800C-034_dark_dark_009_20160913074701.fits"
#             ]

#files = ["/Users/richard/LSST/Data/ITL-3800C-068/EOT-02/ITL-3800C-068_dark_dark_001_20161219091450.fits",
#             "/Users/richard/LSST/Data/ITL-3800C-068/EOT-02/ITL-3800C-068_dark_dark_003_20161219091450.fits",
#             "/Users/richard/LSST/Data/ITL-3800C-068/EOT-02/ITL-3800C-068_dark_dark_005_20161219091450.fits",
#             "/Users/richard/LSST/Data/ITL-3800C-068/EOT-02/ITL-3800C-068_dark_dark_007_20161219091450.fits",
#             "/Users/richard/LSST/Data/ITL-3800C-068/EOT-02/ITL-3800C-068_dark_dark_009_20161219091450.fits"
#             ]

#files = ["/Users/richard/LSST/Data/ITL-3800C-068/EOT-02/ITL-3800C-068_fe55_bias_000_20161219091441.fits"]   
  
#files = ["/Users/richard/LSST/Data/ETU2/ITL-3800C-041-Dev_dark_dark_000_4642D_20170219224445.fits"]   

#files = ["/Users/richard/LSST/Data/ITL-3800C-145/ETU2/ITL-3800C-145-Dev_fe55_bias_000_4689D_20170302045344.fits"]

files = ["/Users/richard/LSST/Data/ITL-3800C-145/ETU2/ITL-3800C-145-Dev_fe55_bias_000_4689D_20170302045344.fits"]

#files = ["/Users/richard/LSST/Data/ITL-3800C-145/ETU2/ITL-3800C-145-Dev_fe55_bias_000_4701D_20170307003226.fits"]

imagesList = []
biasPedsX = []
biasPedsY = []

# see LSSTTD-437 for treatment of bias using bias files, not (only) the overscan region.

for file in files:
    print 'Operating on ', file
    hdulist = fits.open(file)
    expTime = hdulist[0].header['EXPTIME']
    print textwrap.fill(str(hdulist[ampHdu].header),80)
#    print textwrap.fill(str(hdulist[2].header),80)

    datasec=hdulist[ampHdu].header['DATASEC'][1:-1].replace(':',',').split(',')
#    pixels = hdulist[1].data[4:512,1:2000]
    pixeldata = hdulist[ampHdu].data
#    pixels = pixeldata[int(datasec[0]):int(datasec[1]),int(datasec[2]):int(datasec[3])]
    pixels = pixeldata[int(datasec[2]):int(datasec[3]),int(datasec[0]):int(datasec[1])]
    print 'pixels shape = ', pixels.shape
    print "pixels first 50 columns in row 1000", pixels[1000,0:50]
    
#    biassec=hdulist[ampHdu].header['BIASSEC'][1:-1].replace(':',',').split(',')
# hardwwire biassec for rafts for now

    biassec =  ['513', '562', '1', '2000']
    print 'biassec = ', biassec
    
    bias = np.array(pixeldata[int(biassec[2]):int(biassec[3]),int(biassec[0]):int(biassec[1])])

# seeing a change in mean bias moving across the overscan region
    
#    bias = pixeldata[20:1999,0:49]
    print 'bias shape = ', bias.shape
    pedestal = np.mean(bias.flatten())
    print 'pedestal = ', pedestal

    pedRows = np.array([0.]*1999)
    for rows in range(0,1999):
        pedRows[rows]= np.mean(bias[rows,:])

    pixCols = np.array([0.]*508)
    for cols in range(0,508):
        pixCols[cols] = np.mean(pixels[:,cols])

    print 'First 20 pedRows = ', pedRows[0:20]
    print 'pedRows shape = ', pedRows.shape

    mod = ols('data ~ x',dict(x=range(len(pedRows)), data=pedRows))
    regression = mod.fit()
    print dir(regression)
    print regression.summary()
    testFit = regression.outlier_test()
    outliers = ((i,pedRows[i]) for i, t in enumerate(testFit.icol(2)) if t < 0.5)
    print ' Outliers = ', list(outliers)
    print 'Fit parameters = ', regression.params

    pedRowsFixed = pedRows
    for rows in outliers:
        pedRowsFixed[rows0] = rows[1]

# biasPedsY is column means for groups of columns 10 wide moving across the overscan
        
    for b in range(5):
        biasPedsY.append(np.mean(pixeldata[int(biassec[2]):int(biassec[3]),(b)*10:(b+1)*10].flatten()))

# biasPedsX is row means for groups of rows 200 wide moving up the overscan

for b in range(10):
    biasPedsX.append(np.mean(pixeldata[b*200:(b+1)*200,int(biassec[0]):int(biassec[1])].flatten()))

        #    pixel_range = sigma_clipped_pixels.min(), sigma_clipped_pixels.max()
#    plt.hist(pixels.flatten(),bins=50,range=pixel_range)
    segmentGain = gainEOT1[device][ampHdu-1][0]
    print 'segmentGain = ', segmentGain

    if expTime == 0.:
        print "bias zero exposure - setting gain, expTime to 1"
        expTime = 1.
        segmentGain = 1.

    current = segmentGain*(pixels-pedRowsFixed[:,None])/expTime
    print 'current shape = ', current.shape
    
    imagesList.append(current)

print 'biasPedsY = ', biasPedsY
print 'biasPedsX = ', biasPedsX
    
# take median per pixel of all darks to reduce cosmics
    
asImages = np.array(imagesList)
medianCurrent = np.median(asImages, axis=0)
print medianCurrent.shape


with PdfPages(args.type + '_' + device + '_amp_' + str(ampHdu) + '.pdf') as pdf:

    fig1=plt.figure(1)
    plt.imshow(medianCurrent,cmap='hot',vmin=-0.1, vmax=0.1, origin='lower')
    plt.colorbar()
    plt.suptitle(' Image region - currents')
    pdf.savefig()
    plt.close()

    fig1=plt.figure(8)
    plt.imshow(pixels[0:100,300:500],cmap='hot', origin='lower', extent=[300,500, 0,100])
    plt.colorbar()
    plt.suptitle(' Image region zoomed - ADU')
    pdf.savefig()
    plt.close()

    fig9=plt.figure(9)
    plt.imshow(pixels,cmap='hot', origin='lower')
    plt.colorbar()
    plt.suptitle(' Image region - ADU')
    pdf.savefig()
    plt.close()

    fig6=plt.figure(6)
    plt.imshow(bias[0:200,0:49]-pedRowsFixed[0:200,None],cmap='hot', vmin=-20, vmax=20, origin='lower')
    plt.colorbar()
    plt.suptitle(' Bias region subtracted - [0:200,0:49] - ADUs')
    pdf.savefig()
    plt.close()

    fig2 = plt.figure(2)
    range = [-0.1,0.1]
    if expTime == 1.: range = [-200,100]
    plt.hist(medianCurrent.flatten(),bins=50, range=range)
    fig2.suptitle(' current - pixel values')
    pdf.savefig()
    plt.close()

    fig10=plt.figure(10)
    plt.plot(pixCols)
    fig10.suptitle(' Column means by column - ADU')
    pdf.savefig()
    plt.close()


    
    fig4=plt.figure(4)
    plt.plot(medianCurrent[0:1999,200],'r')
    plt.xlabel('row number')
    plt.suptitle(' Image current medians for column 200' )
    pdf.savefig()
    plt.close()

    fig7=plt.figure(7)
    plt.plot(pedRowsFixed[1:100])
    plt.xlabel('row number')
    plt.suptitle(' Bias row means by row [1:100] ')
    pdf.savefig()
    plt.close()

    fig5=plt.figure(5)
    plt.plot(biasPedsY)
    plt.xlabel('columns means bias by overscan for groups of 10 columns wide ')
    pdf.savefig()
    plt.close()
    
    fig5=plt.figure(6)
    plt.plot(biasPedsX)
    plt.xlabel('row means bias by overscan  for groups of rows 200 wide')
    pdf.savefig()
    plt.close()

#    sorted = np.sort(np.absolute(medianCurrent.flatten()))
sorted = np.sort(medianCurrent.flatten())
index95 = int(len(sorted)*0.95)
print 'num pixels = ', len(sorted), ' 95 = ', index95
subset=sorted[index95-10:index95+30]
print(subset)
darkcurr95 = sorted[index95]
segmentDark = darkEOT1[device][ampHdu-1][0]

print 'darkcurr95 = ', darkcurr95, 'EO dark95 = ', segmentDark

for nxtValue in range(index95,len(sorted)):
    if sorted[nxtValue] != darkcurr95:
        print 'Next dark value at ', nxtValue, float(nxtValue)/float(len(sorted)), sorted[nxtValue]
        break


    

