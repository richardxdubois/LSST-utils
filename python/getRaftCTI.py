from  eTraveler.clientAPI.connection import Connection
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import datetime
import collections
import numpy as np
from findCCD import findCCD

import argparse


def get_results(data=None, step=None, item=None, multiplier=1., org='amp'):
    raft = data['experimentSN']
    run = data['run']
    out = collections.OrderedDict()

    stepDict = data['steps']

    print 'Operating on raft ', raft, ' run', run, ' for step ', item

    for d in stepDict[step]:
        if d <> step:
            continue
        step_info = stepDict[d][step]
        for s in step_info:
            if s['schemaInstance'] == 0: continue
            thing = s[item] * multiplier
            sensor = s['sensor_id']
            ccd = out.setdefault(sensor, {})
            amp = s[org]
            ccd[amp] = thing
        break

    return out


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

run_list = collections.OrderedDict()
run_ccd_files = collections.OrderedDict()

if args.infile <> "":
    with open(args.infile) as f:
        for line in f:
            run, temp = line.split()
            run_list[run] = temp
else:
    run_list[args.run] = str(args.temp)

if args.eTserver == 'Prod':
    pS = True
else:
    pS = False

connect = Connection(operator='richard', db=args.db, exp='LSST-CAMERA', prodServer=pS,
                     appSuffix='-' + args.appSuffix)

fCCD = findCCD(FType='fits', testName='fe55_raft_analysis', run=-1, sensorId='E2V')

for r in run_list:

    returnData = connect.getRunResults(run=r, stepName='cte_raft')
    cti = get_results(data=returnData, step='cte_raft', item='cti_low_serial')


    for ccd in cti:

        bad = False
        for a in cti[ccd]:
            cti_val = cti[ccd][a]
            if cti_val > 5e-6:
                bad = True
                print 'ccd ', ccd, ' amp ', a, ' fails CTI low serial with ', cti_val
        if bad:
            f= fCCD.find(sensorId=ccd,run=r)