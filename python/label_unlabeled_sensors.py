from eTraveler.clientAPI.connection import Connection
import datetime
import argparse
import collections
import pandas

"""
label_unlabeled_sensors:

Read an excel spreadsheet containing Project endorsed grades for e2v and ITL sensors. Already-labeled 
sensors are not affected.
"""


## Command line arguments
parser = argparse.ArgumentParser(
    description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('-t', '--htype', default='ITL', help="hardware type (default=%(default)s)")
parser.add_argument('-d', '--db', default='Prod', help="eT database (default=%(default)s)")
parser.add_argument('-e', '--eTserver', default='Dev', help="eTraveler server (default=%(default)s)")
parser.add_argument('--doit', default='no', help="actualy do the labeling")
parser.add_argument('--do_one', default='no', help="do only the first ccd as a test")
parser.add_argument('--account', default='richard', help="account to use")
parser.add_argument('--appSuffix', '--appSuffix', default='jrb',
                    help="eTraveler server (default=%(default)s)")
parser.add_argument('-i', '--input',
                    default='/Users/richard/LSST/Data/Sensor_Plots_for_Watchlist-20180709.xlsx',
                    help="output plot file (default=%(default)s)")
parser.add_argument('-o', '--output', default='unlabeled_sensors.pdf',
                    help="output plot file (default=%(default)s)")
parser.add_argument('-p', '--plan', default='',
                    help="input csv file with planned deliveries (default=%(default)s)")

args = parser.parse_args()

if args.eTserver == 'Prod':
    pS = True
else:
    pS = False


connect = Connection(operator=args.account, db=args.db, exp='LSST-CAMERA', prodServer=pS)

ccd_params = {}
ccd_params['ITL'] = ['ITL-CCD', '3800C']
ccd_params['e2v'] = ['e2v-CCD', 'CCD250']

excel_assign = pandas.read_excel(io=args.input,
                                 sheet_name=args.htype.upper(), header=0)
sensor_frame = excel_assign.set_index('Sensor ID', drop=False)

hardwareLabels = ['SR_Grade:']

returnData = connect.getHardwareInstances(htype=ccd_params[args.htype][0], model=ccd_params[args.htype][1])
returnDataLabeled = connect.getHardwareInstances(htype=ccd_params[args.htype][0],
                                                 model=ccd_params[args.htype][1],
                                                 hardwareLabels = hardwareLabels)

print len(returnData), args.htype, ' ccds found'

ccd_list = collections.OrderedDict()
count_ccd = 0
unlabeled = 0

for inst in returnData:
    found = False

    ccd = inst['experimentSN']

    label = 'No Label'
    for il in returnDataLabeled:
        clab = il['experimentSN']
        if clab == ccd:
            label = il['hardwareLabels']
            break

    if label == 'No Label':
        unlabeled += 1
        try:
            grade = "SR_SEN_" + sensor_frame.loc[ccd, "Grade"]
            if 'Forecasted' in grade:
                print ccd, ' set to ', grade, ' ignoring'
                continue
        except KeyError:
            print ccd, ' not in spreadsheet - ignoring'
            continue

        ccd_list[ccd] = grade

        if args.doit == 'yes':
            rc = connect.modifyHardwareLabel(experimentSN=ccd, htype=ccd_params[args.htype][0], label=grade,
                group='SR_Grade', adding='true', reason='match Vincent Riot spreadsheet 2018-07-29')
            print "Updated ", ccd, " as grade ", grade
            if args.do_one == 'yes':
                break

    count_ccd += 1

print 'Found ', len(ccd_list), ' ', args.htype, ' with ', unlabeled, ' not yet labeled'

for c in ccd_list:
    print c, ' ', ccd_list[c]
