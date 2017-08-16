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
parser.add_argument('-t', '--htype', default='LCA-13574', help="hardware type (default=%(default)s)")
parser.add_argument('-d', '--db', default='Prod', help="eT database (default=%(default)s)")
parser.add_argument('-e', '--eTserver', default='Dev', help="eTraveler server (default=%(default)s)")
parser.add_argument('--appSuffix', '--appSuffix', default='jrb',
                    help="eTraveler server (default=%(default)s)")
parser.add_argument('-o','--output',default='reb_arrivals.pdf',help="output plot file (default=%(default)s)")

args = parser.parse_args()

if args.eTserver == 'Prod':
    pS = True
else:
    pS = False


connect = Connection(operator='richard', db=args.db, exp='LSST-CAMERA', prodServer=pS,
                     appSuffix='-' + args.appSuffix)

returnData = connect.getHardwareInstances(htype=args.htype)

reb_list = {}
all_rebs = {}

for inst in returnData:

    reb = inst['experimentSN']
    found = False
    beginTime = ' '

    try:
        runListREB = connect.getComponentRuns(experimentSN=reb, htype=args.htype, travelerName='SR-GEN-RCV-02')
        for rcv_run in sorted(runListREB):
            travRun = runListREB[rcv_run]
            beginTime = travRun['begin']
            if beginTime == '':
                continue
            found = True
            break

    except Exception, msg:
        try:
            runListOld = connect.getComponentRuns(experimentSN=reb, htype=args.htype,
                                                  travelerName='SR-RCV-2')
            for rcv_run in sorted(runListOld):
                travRun = runListOld[rcv_run]
                beginTime = travRun['begin']
                if beginTime == '':
                    continue
                found = True
                break
        except Exception, msg:
            # these are all REJECTED status
            print 'No receive traveler found for ', reb
    if found:
        begin = datetime.datetime.strptime(beginTime, '%Y-%m-%dT%H:%M:%S.%f')
        reb_list[begin] = [reb]

print 'Found ', len(reb_list), ' ', args.htype

running = collections.OrderedDict()
running_sum = 0

for d in sorted(reb_list):

    running_sum += 1
    dstring = d.date()
    running[dstring] = running_sum
    print d, reb_list[d][0]


with PdfPages(args.output) as pdf:

    fig, ax = plt.subplots()


    ax.fill_between(running.keys(), running.values())

    plt.xticks(rotation=30)
    plt.suptitle(args.htype)
    plt.tight_layout()

    pdf.savefig()
    plt.close()
