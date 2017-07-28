from  eTraveler.clientAPI.connection import Connection
import datetime
import argparse
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import collections

## Command line arguments
parser = argparse.ArgumentParser(
    description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('-t', '--htype', default=None, help="hardware type (default=%(default)s)")
parser.add_argument('-d', '--db', default='Prod', help="eT database (default=%(default)s)")
parser.add_argument('-e', '--eTserver', default='Dev', help="eTraveler server (default=%(default)s)")
parser.add_argument('--appSuffix', '--appSuffix', default='jrb',
                    help="eTraveler server (default=%(default)s)")
parser.add_argument('-o','--output',default='sensor_arrivals.pdf',help="output plot file (default=%(default)s)")
args = parser.parse_args()

if args.eTserver == 'Prod':
    pS = True
else:
    pS = False
connect = Connection(operator='richard', db=args.db, exp='LSST-CAMERA', prodServer=pS,
                     appSuffix='-' + args.appSuffix)

returnData = connect.getFilepathsJH(htype=args.htype, stepName="Scan-and-Ingest-Vendor-Data", travelerName='SR-GEN-RCV-02')

ccd_list = {}
for ccd in returnData:

    expDict = returnData[ccd]

    run = expDict["runNumber"]
    rsp = connect.getRunActivities(run=run)

    for step in rsp:
        if step['status'] <> 'success': continue
        step_name = step['stepName']
        begin = datetime.datetime.strptime(step['begin'], '%Y-%m-%dT%H:%M:%S.%f')
        ccd_list[begin] = ccd
        break

print 'Found ', len(ccd_list), ' ', args.htype

running = collections.OrderedDict()
running_sum = 0

for d in sorted(ccd_list):
    running_sum += 1
    dstring = d.date()
    running[dstring] = running_sum
    print d, ccd_list[d]

with PdfPages(args.output) as pdf:

    plt.plot(running.keys(), running.values())
    plt.xticks(rotation=30)
    plt.tight_layout()

    pdf.savefig()
    plt.close()
