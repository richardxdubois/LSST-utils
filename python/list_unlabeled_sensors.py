from  eTraveler.clientAPI.connection import Connection
import datetime
import argparse
import collections

## Command line arguments
parser = argparse.ArgumentParser(
    description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('-t', '--htype', default='ITL-CCD', help="hardware type (default=%(default)s)")
parser.add_argument('-d', '--db', default='Prod', help="eT database (default=%(default)s)")
parser.add_argument('-e', '--eTserver', default='Dev', help="eTraveler server (default=%(default)s)")
parser.add_argument('--appSuffix', '--appSuffix', default='jrb',
                    help="eTraveler server (default=%(default)s)")
parser.add_argument('-o', '--output', default='unlabeled_sensors.pdf',
                    help="output plot file (default=%(default)s)")

args = parser.parse_args()

if args.eTserver == 'Prod':
    pS = True
else:
    pS = False
connect = Connection(operator='richard', db=args.db, exp='LSST-CAMERA', prodServer=pS,
                     appSuffix='-' + args.appSuffix)

hardwareLabels = ['SR_Grade:']
#hardwareLabels = ['SR_Grade:SR_SEN_Science', 'SR_Grade:SR_SEN_Reserve']

#returnData = connect.getHardwareInstances(htype=args.htype)
returnData = connect.getHardwareInstances(htype=args.htype)
returnDataLabeled = connect.getHardwareInstances(htype=args.htype, hardwareLabels=hardwareLabels)

print len(returnData), args.htype, ' ccds found'

ccd_list = collections.OrderedDict()
count_ccd = 0
unlabeled = 0

for inst in returnData:

    found = False

    ccd = inst['experimentSN']
    when = datetime.datetime.strptime(inst['locationSetTS'], '%Y-%m-%dT%H:%M:%S.%f')
    t_cut = datetime.datetime.strptime('2017-05-01', '%Y-%m-%d')
    where, dummy = inst['location'].split(':')

    if when < t_cut or where <> 'BNL':
        continue

    label = 'No Label'
    for il in returnDataLabeled:
        clab = il['experimentSN']
        if clab == ccd:
            label = il['hardwareLabels']
            break

    if label == 'No Label':
        unlabeled += 1


    count_ccd += 1
    ccd_list[ccd] = [when, where, label]

print 'Found ', len(ccd_list), ' ', args.htype, ' with ', unlabeled, ' not yet labeled'

for c in ccd_list:
    print c, ' ', ccd_list[c][0], ' ', ccd_list[c][1], ' ', ccd_list[c][2]
