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

hardwareLabels = ['SR_Grade:SR_SEN_Prototype', 'SR_Grade:SR_SEN_Engineering', 'SR_Grade:SR_SEN_Mechanical', 'SR_Grade:SR_SEN_Rejected', 'SR_Grade:SR_SEN_Reserve', 'SR_Grade:SR_SEN_Science',
                  'SR_Contract:SR_SEN_Fall_Out-Option_2', 'SR_Contract:SR_SEN_First_Article', 'SR_Contract:SR_SEN_M12', 'SR_Contract:SR_SEN_Off_Contract',
                  'SR_Contract:SR_SEN_Option_1', 'SR_Contract:SR_SEN_Phase_A', 'SR_Contract:SR_SEN_Phase_B', 'SR_Contract:SR_SEN_Prototype']

returnData = connect.getFilepathsJH(htype=args.htype, stepName="Scan-and-Ingest-Vendor-Data", travelerName='SR-GEN-RCV-02', hardwareLabels=hardwareLabels)

ccd_list = {}
gradeLabels = []

for ccd in returnData:

    expDict = returnData[ccd]

    run = expDict["runNumber"]

    label = expDict["hardwareLabels"]
    (grp1, grade1) = label[0].split(':')
    if grade1 not in gradeLabels:
        gradeLabels.append(grade1)

    grp2 = ''
    grade2 = ''
    if len(label) == 2:
        (grp2, grade2) = label[1].split(':')

    beginTime = expDict['begin']
    begin = datetime.datetime.strptime(beginTime, '%Y-%m-%d %H:%M:%S.%f')
    ccd_list[begin] = [ccd, grade1, grade2]

print 'Found ', len(ccd_list), ' ', args.htype

running = collections.OrderedDict()
running_sum = 0
grade_plots = collections.OrderedDict()

for grades in gradeLabels:

    running.clear()
    running_sum = 0

    for d in sorted(ccd_list):
        grade = ccd_list[d][1]

        if grades <> grade:
            continue

        running_sum += 1
        dstring = d.date()
        running[dstring] = running_sum
        print d, ccd_list[d][0], ' ', grade, ' ', ccd_list[d][2]

    grade_plots[grades] = running.copy()

with PdfPages(args.output) as pdf:

    fig, ax = plt.subplots()

    for g in gradeLabels:
        p = grade_plots[g]
        print g, len(p.keys())
        ax.fill_between(p.keys(), p.values(), label=g)
    plt.xticks(rotation=30)
    plt.legend(loc='upper left')
    plt.suptitle(args.htype)
    plt.tight_layout()

    pdf.savefig()
    plt.close()
