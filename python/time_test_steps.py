from  eTraveler.clientAPI.connection import Connection
import datetime
import argparse
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


## Command line arguments
parser = argparse.ArgumentParser(description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('-t','--htype', default="ITL-CCD",help="hardware type (default=%(default)s)")
parser.add_argument('-d','--db',default='Prod',help="eT database (default=%(default)s)")
parser.add_argument('-e','--eTserver',default='Dev',help="eTraveler server (default=%(default)s)")
parser.add_argument('--appSuffix','--appSuffix',default='jrb',help="eTraveler server (default=%(default)s)")
args = parser.parse_args()


if args.eTserver == 'Prod': pS = True
else: pS = False
connect = Connection(operator='richard', db=args.db, exp='LSST-CAMERA', prodServer=pS, appSuffix='-'+args.appSuffix)

# get the list of CCDs we've received vendor data for of this type

returnData  = connect.getResultsJH(htype=args.htype, stepName = 'vendorIngest', travelerName='SR-RCV-01')

ccd_list_all = []
ccd_list = []
step_times = {}

for ccd in returnData:
    ccd_list_all.append(ccd)
    
    try:
        returnDataTS3  = connect.getResultsJH(htype=args.htype, stepName = 'test_report', travelerName='SR-EOT-1', experimentSN=ccd)

        expDict = returnDataTS3[ccd]
        
        try:
            stepDict = expDict['steps']['test_report']
        except:
            continue
    except:
        continue
            
    run = expDict["runNumber"]
    rsp = connect.getRunActivities(run=run)

    for step in rsp:
        if step['status'] != 'success': continue
        step_name = step['stepName']
        if step_name not in step_times: step_times[step_name] = []
        begin = datetime.datetime.strptime(step['begin'],'%Y-%m-%dT%H:%M:%S.%f')
        end = datetime.datetime.strptime(step['end'],'%Y-%m-%dT%H:%M:%S.%f')
        dT = end-begin
        step_times[step_name].append(dT.seconds)

with PdfPages('SR-EOT-1-acq.pdf') as pdf:

    numplot = 0
    for step in step_times:
        if 'acq' in step:
            numplot += 1

            fig2 = plt.figure(numplot)
            plt.hist(step_times[step],bins=50)
            fig2.suptitle(step)
            pdf.savefig()
            plt.close()

        
    
        




    

