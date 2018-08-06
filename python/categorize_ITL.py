from  eTraveler.clientAPI.connection import Connection
from exploreRaft import exploreRaft
import argparse


## Command line arguments
parser = argparse.ArgumentParser(description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('-t','--htype', default=None,help="hardware type (default=%(default)s)")
parser.add_argument('-d','--db',default='Prod',help="eT database (default=%(default)s)")
parser.add_argument('-e','--eTserver',default='Prod',help="eTraveler server (default=%(default)s)")
parser.add_argument('--appSuffix','--appSuffix',default='jrb',help="eTraveler server (default=%(default)s)")
args = parser.parse_args()


if args.eTserver == 'Prod': pS = True
else: pS = False
connect = Connection(operator='richard', db=args.db, exp='LSST-CAMERA', prodServer=pS)

eR = exploreRaft()

htype = 'ITL-CCD'
hw_labels = ['SR_Grade:']
hw_list = connect.getHardwareInstances(htype='ITL-CCD', hardwareLabels=hw_labels)

ccd_list_all = {}

for item in hw_list:

    ccd = item['experimentSN']
    parent = eR.CCD_parent(CCD_name=ccd)
    if parent == '':
        parent = 'orphan'

    labels = item['hardwareLabels']
    if 'SR_Grade:SR_SEN_Engineering' in labels[:]:
        continue
    if 'SR_Grade:SR_SEN_Rejected' in labels[:]:
        continue
    run_TS3 = -1
    run_EOT05 = -1

    try:
        returnDataEOT05  = connect.getResultsJH(htype=htype, stepName='SR-CCD-EOT-05_Preflight-Check',
                                                travelerName='SR-CCD-EOT-05', experimentSN=ccd)

        expDict = returnDataEOT05[ccd]
        run_EOT05 = expDict['runNumber']
    except:
        pass


    try:
        returnDataTS3  = connect.getResultsJH(htype=htype, stepName = 'test_report', travelerName='SR-EOT-1',
                                              experimentSN=ccd)

        expDict = returnDataTS3[ccd]
        run_TS3 = expDict['runNumber']
    except:
        pass



    properties = [parent, labels[0].split(':')[-1], run_TS3, run_EOT05]
    ccd_list_all[ccd] = properties

print   len(ccd_list_all), ccd_list_all
    
        




    

