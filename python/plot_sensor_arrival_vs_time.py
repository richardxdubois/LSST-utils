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
parser.add_argument('-t', '--htype', default=None, help="hardware type (default=%(default)s)")
parser.add_argument('-d', '--db', default='Prod', help="eT database (default=%(default)s)")
parser.add_argument('-e', '--eTserver', default='Dev', help="eTraveler server (default=%(default)s)")
parser.add_argument('--appSuffix', '--appSuffix', default='jrb',
                    help="eTraveler server (default=%(default)s)")
parser.add_argument('-o', '--output', default='sensor_arrivals.pdf',
                    help="output plot file (default=%(default)s)")
parser.add_argument('-p', '--plan', default='',
                    help="input csv file with planned deliveries (default=%(default)s)")

args = parser.parse_args()

plan = collections.OrderedDict()

with open(args.plan, 'rU') as f:
    reader = csv.reader(f)
    for row in reader:
        if args.htype == 'ITL-CCD':
            deliver_date = row[3]
            count = row[6]
        else:
            deliver_date = row[23]
            count = row[24]

        deliver = datetime.datetime.strptime(deliver_date, '%m/%d/%y').date()
        plan[deliver] = count

if args.eTserver == 'Prod':
    pS = True
else:
    pS = False
connect = Connection(operator='richard', db=args.db, exp='LSST-CAMERA', prodServer=pS,
                     appSuffix='-' + args.appSuffix)

hardwareLabels = ['SR_Grade:', 'SR_Contract:']

# returnData = connect.getFilepathsJH(htype=args.htype, stepName="Scan-and-Ingest-Vendor-Data", travelerName='SR-GEN-RCV-02', hardwareLabels=hardwareLabels)
returnData = connect.getHardwareInstances(htype=args.htype, hardwareLabels=hardwareLabels)

print len(returnData), args.htype, ' labelled ccds found'

ccd_list = {}
gradeLabels = []
t_diff = []
count_ccd = 0

for inst in returnData:

    found = False

    ccd = inst['experimentSN']
    count_ccd += 1

    label = inst['hardwareLabels']
    (grp1, grade1) = label[0].split(':')
    if grade1 not in gradeLabels:
        gradeLabels.append(grade1)

    grp2 = ''
    grade2 = ''
    if len(label) == 2:
        (grp2, grade2) = label[1].split(':')

    # Some sensors were received with SR-RCV-2 and then later it changed to SR-GEN-RCV-02

    beginTime = ''

    try:
        runListOld = connect.getComponentRuns(experimentSN=ccd, htype=args.htype, travelerName='SR-RCV-2')
        for rcv_run in sorted(runListOld):
            travRun = runListOld[rcv_run]
            beginTime = travRun['begin']
            if beginTime == '':
                continue
            found = True
            break
    except Exception, msg:
        try:
            runListGen = connect.getComponentRuns(experimentSN=ccd, htype=args.htype,
                                                  travelerName='SR-GEN-RCV-02')
            for rcv_run in sorted(runListGen):
                travRun = runListGen[rcv_run]
                beginTime = travRun['begin']
                if beginTime == '':
                    continue
                found = True
                break
        except Exception, msg:
            # these are all REJECTED status
            print 'No receive traveler found for ', ccd, ' ', grade1

    if found:

        try:
            begin = datetime.datetime.strptime(beginTime, '%Y-%m-%dT%H:%M:%S.%f')
            ccd_list[begin] = [ccd, grade1, grade2]
        except:
            print ' could not convert time for ', ccd
        print count_ccd, ccd, begin, grade1

        # get the time difference between vendor data arrival and receipt of the sensor at BNL

        try:
            runListCCD = connect.getComponentRuns(experimentSN=ccd, htype=args.htype,
                                                  travelerName='SR-RCV-01')

            for rcv_run in sorted(runListCCD):
                travRun = runListCCD[rcv_run]
                rcv_begin = travRun['begin']
                td_rcv = datetime.datetime.strptime(rcv_begin, '%Y-%m-%dT%H:%M:%S.%f')
                t_diff.append((begin - td_rcv).days)
                break
        except:
            print 'no SR-RCV-01 traveler for ', ccd, ' ', grade1
            pass

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
        if g == 'SR_SEN_Science':
            ax.fill_between(p.keys(), p.values(), label=g)
        else:
            ax.plot(p.keys(), p.values(), label=g)

    ax.plot(plan.keys(), plan.values(), label='Plan', color='k')
    plt.xticks(rotation=30)
    plt.legend(loc='upper left')
    plt.suptitle(args.htype)
    plt.tight_layout()

    pdf.savefig()
    plt.close()

    plt.hist(t_diff, bins=100)
    plt.xlabel('Time Difference (days)')
    plt.suptitle('Time between Vendor Data and Receipt at BNL')
    pdf.savefig()
    plt.close()
