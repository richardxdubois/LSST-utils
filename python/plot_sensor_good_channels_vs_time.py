from  eTraveler.clientAPI.connection import Connection
import datetime
import argparse
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import collections
import csv

## Command line arguments
parser = argparse.ArgumentParser(
    description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('-t', '--htype', default='ITL-CCD', help="hardware type (default=%(default)s)")
parser.add_argument('-d', '--db', default='Prod', help="eT database (default=%(default)s)")
parser.add_argument('-e', '--eTserver', default='Dev', help="eTraveler server (default=%(default)s)")
parser.add_argument('--appSuffix', '--appSuffix', default='jrb',
                    help="eTraveler server (default=%(default)s)")
parser.add_argument('-o', '--output', default='sensor_good_channels.pdf',
                    help="output plot file (default=%(default)s)")

args = parser.parse_args()

if args.eTserver == 'Prod':
    pS = True
else:
    pS = False
connect = Connection(operator='richard', db=args.db, exp='LSST-CAMERA', prodServer=pS,
                     appSuffix='-' + args.appSuffix)

#hardwareLabels = ['SR_Grade:SCIENCE']
hardwareLabels = ['SR_Grade:SR_SEN_Science', 'SR_Grade:SR_SEN_Reserve']

#returnData = connect.getHardwareInstances(htype=args.htype)
returnData = connect.getHardwareInstances(htype=args.htype, hardwareLabels=hardwareLabels)

print len(returnData), args.htype, ' labelled ccds found'

ccd_list = {}
count_ccd = 0

for inst in returnData:

    found = False

    ccd = inst['experimentSN']
    count_ccd += 1

    label = inst['hardwareLabels']
    grp1, grade1 = label[0].split(':')

    try:
        runListEOT2 = connect.getComponentRuns(experimentSN=ccd, htype=args.htype, travelerName='SR-EOT-02')
        # sort data on ascending eTraveler run
        sortedkeys = sorted(runListEOT2, cmp=lambda x, y: cmp(data[x]['runNumber'], data[y]['runNumber']))

        for r in sortedkeys:
            run = runListEOT2[r]['runNumber']
            runEOT2 = connect.getRunResults(run=run)
            for step in runEOT2:
                continue
            break

        ccd_list[ccd] = grade1
    except:
        print 'No EOT02 for ', ccd
        continue

print 'Found ', len(ccd_list), ' ', args.htype
