from  eTraveler.clientAPI.connection import Connection
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import datetime
import collections
import numpy as np
from findCCD import findCCD

import argparse


## Command line arguments
parser = argparse.ArgumentParser(
    description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('--run', default=None, help="(raft run number (default=%(default)s)")
parser.add_argument('--temp', default="-85.", help="(temperature (default=%(default)s)")
parser.add_argument('-d', '--db', default='Prod', help="database to use (default=%(default)s)")
parser.add_argument('-e', '--eTserver', default='Dev', help="eTraveler server (default=%(default)s)")
parser.add_argument('--appSuffix', '--appSuffix', default='jrb',
                    help="eTraveler server (default=%(default)s)")
parser.add_argument('-o', '--output', default='raft_temp_dependence.pdf',
                    help="output plot file (default=%(default)s)")
parser.add_argument('-i', '--infile', default="",
                    help="input file name for list of runs, temps (default=%(default)s)")

args = parser.parse_args()

if args.eTserver == 'Prod':
    pS = True
else:
    pS = False

connect = Connection(operator='richard', db=args.db, exp='LSST-CAMERA', prodServer=pS,
                     appSuffix='-' + args.appSuffix)

rsp = {}
##htype='e2v-CCD'
htype = 'LCA-10307'
traveler = 'NCR'
step = 'NCR_Interim_Plans'
#step = 'NCR_Approval'

print 'Invoking getMissingSignatures with no arguments '
# print 'htype=',htype, ' travelerName=',traveler, ' stepName=',step
# ,' experimentSN=',eSN
try:
#    rsp = connect.getMissingSignatures(travelerName=traveler,stepName=step)
    rsp = connect.getMissingSignatures()

    print 'Data returned for ', len(rsp), ' components'

    for esn in rsp:
        print ('For component %s \n' % (esn))
        esnData = rsp[esn]
        for r in esnData:
            print 'For run number=', r

        runData = esnData[r]
        for k in runData:
            if k != 'steps':
                print k, ' : ', runData[k]
        steps = runData['steps']
        for s in steps:
            print ('For stepName %s \n' % (s))
            steprecords = steps[s]  # array of dicts
            for rec in steprecords:
                # sreq is
                for field in rec:
                    print field, ':', rec[field]
                    if rec['signerValue'] == "":
                        print 'Missing signature for group ', rec['signerRequest']

except Exception,msg:
    print 'Operation failed with exception: '
    print  msg
