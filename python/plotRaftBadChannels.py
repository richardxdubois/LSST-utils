from  eTraveler.clientAPI.connection import Connection
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import datetime
import collections
import numpy as np

import argparse


def get_bad(data=None,step=None,item=None, multiplier=1.):

    time_ramp = collections.OrderedDict()
    items_ramp = collections.OrderedDict()

    # sort data on ascending time of eTraveler run
    sortedkeys = sorted(data, cmp=lambda x, y: cmp(data[x]['begin'], data[y]['begin']))

    for r in sortedkeys:
        # skip RTM-004 - data entry issues?
        if 'RTM-004' in r:
            continue

        raftDict = data[r]
        stepDict = raftDict['steps']
        beginTime = data[r]['begin']
        items_list = []

        bad_channels = 0
        print 'Operating on raft ', r, ' ', beginTime, ' ', item


        begin = datetime.datetime.strptime(beginTime, '%Y-%m-%dT%H:%M:%S.%f')
        time_ramp[begin] = total

        for d in stepDict[step]:
            if d == 'job_info':
                continue
            defects = stepDict[d][step]
            for s in defects:
                if s['schemaInstance'] == 0: continue
                thing = s[item]*multiplier
                time_ramp[begin] += thing
                bad_channels += thing
                items_list.append(thing)
                print s['sensor_id'], thing
            break

        items_ramp[begin] = items_list

    return time_ramp, items_ramp


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

bad_channel_ramp_total = collections.OrderedDict()


if args.eTserver == 'Prod': pS = True
else: pS = False

connect = Connection(operator='richard', db=args.db, exp='LSST-CAMERA', prodServer=pS,
                     appSuffix='-' + args.appSuffix)
bad_channels = 0
total = 0

returnData = connect.getResultsJH(htype='LCA-11021_RTM', travelerName='SR-RTM-EOT-03', stepName='bright_defects_raft')
brights, bl = get_bad(data=returnData,step='bright_defects_raft',item='bright_pixels')
bright_cols, blc = get_bad(data=returnData,step='bright_defects_raft',item='bright_columns',multiplier=2002.)

returnData = connect.getResultsJH(htype='LCA-11021_RTM', travelerName='SR-RTM-EOT-03', stepName='dark_defects_raft')
darks, dl = get_bad(data=returnData,step='dark_defects_raft',item='dark_pixels')
dark_cols, dlc = get_bad(data=returnData,step='dark_defects_raft',item='dark_columns',multiplier=2002.)

returnData = connect.getResultsJH(htype='LCA-11021_RTM', travelerName='SR-RTM-EOT-03', stepName='read_noise_raft')
read_noise, read_noise_c = get_bad(data=returnData,step='read_noise_raft',item='read_noise')

read_noise_ramp = collections.OrderedDict()

for t in brights:

    read_noise_list = np.array(read_noise_c[t])
    bad_read_noise = 4004.*sum(read_noise_list > 9.)
    read_noise_ramp[t] = bad_read_noise

    bad_channels = brights[t] + darks[t] + bright_cols[t] + dark_cols[t] + bad_read_noise
    bad_channel_ramp_total[t] = bad_channels + total

    print ' bad channels ', bad_channels
    total += bad_channels

print 'Total bad channels ', total

with PdfPages(args.output) as pdf:

    fig, ax = plt.subplots()

    ax.plot(bad_channel_ramp_total.keys(), bad_channel_ramp_total.values(), label='Running Total', color='k')
    ax.plot(brights.keys(), brights.values(), label='Bright Pixels')
    ax.plot(bright_cols.keys(), bright_cols.values(), label='Bright ColumnPixels')
    ax.plot(darks.keys(), darks.values(), label='Dark Pixels')
    ax.plot(dark_cols.keys(), dark_cols.values(), label='Dark ColumnPixels')
    ax.plot(read_noise_ramp.keys(), read_noise_ramp.values(), label='Read Noise AmpPixels')
    ax.axhspan(2.6e9*0.02, 3.2e9*0.02, color='lightgray')
    ax.set_yscale('log')
    plt.xticks(rotation=30)
    plt.legend(loc='upper left')
    plt.suptitle('LCA-11021_RTM Bad Channels')
    plt.tight_layout()

    pdf.savefig()
    plt.close()

    

