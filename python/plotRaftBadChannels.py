from exploreRaft import exploreRaft
from  eTraveler.clientAPI.connection import Connection
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import datetime
import collections

import argparse


## Command line arguments
parser = argparse.ArgumentParser(description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('-r','--raftID', default=None,help="(metadata) Raft ID (default=%(default)s)")
parser.add_argument('--run', default=None,help="(raft run number (default=%(default)s)")
parser.add_argument('-d','--db',default='Prod',help="database to use (default=%(default)s)")
parser.add_argument('-e','--eTserver',default='Dev',help="eTraveler server (default=%(default)s)")
parser.add_argument('--appSuffix','--appSuffix',default='jrb',help="eTraveler server (default=%(default)s)")
parser.add_argument('-o','--output',default='bad_channels.pdf',help="output plot file (default=%(default)s)")

args = parser.parse_args()

bad_channel_ramp = collections.OrderedDict()


if args.eTserver == 'Prod': pS = True
else: pS = False

eR = exploreRaft(db=args.db, prodServer=args.eTserver)
connect = Connection(operator='richard', db=args.db, exp='LSST-CAMERA', prodServer=pS,
                     appSuffix='-' + args.appSuffix)
bad_channels = 0
total = 0

returnData = connect.getResultsJH(htype='LCA-11021_RTM', travelerName='SR-RTM-EOT-03', stepName='bright_defects_raft')

# sort data on ascending time of eTraveler run

sortedkeys = sorted(returnData, cmp=lambda x, y: cmp(returnData[x]['begin'], returnData[y]['begin']))

for r in sortedkeys:

    print 'Operating on raft ', r

    raftDict = returnData[r]
    stepDict = raftDict['steps']
    beginTime = returnData[r]['begin']
    bad_channels = 0

    begin = datetime.datetime.strptime(beginTime, '%Y-%m-%dT%H:%M:%S.%f')
    bad_channel_ramp[begin] = total

    for d in stepDict['bright_defects_raft']:
        if d == 'job_info':
            continue
        defects = stepDict[d]['bright_defects_raft']
        for s in defects:
            if s['schemaInstance'] == 0: continue
            bright_pixel_count = s['bright_pixels']
            bad_channel_ramp[begin] += bright_pixel_count
            bad_channels += bright_pixel_count
            print s['sensor_id'], bright_pixel_count
        break

    print r, ' bad channels ', bad_channels
    total += bad_channels

print 'Total bad channels ', total

with PdfPages(args.output) as pdf:

    fig, ax = plt.subplots()

    ax.plot(bad_channel_ramp.keys(), bad_channel_ramp.values(), label='Total', color='k')
    plt.xticks(rotation=30)
    plt.legend(loc='upper left')
    plt.suptitle('LCA-11021_RTM Bad Channels')
    plt.tight_layout()

    pdf.savefig()
    plt.close()

    

