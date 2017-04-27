from  eTraveler.clientAPI.connection import Connection

import argparse


## Command line arguments
parser = argparse.ArgumentParser(description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('-t','--htype', default=None,help="hardware type (default=%(default)s)")
parser.add_argument('-d','--db',default='Prod',help="eT database (default=%(default)s)")
parser.add_argument('-e','--eTserver',default='Dev',help="eTraveler server (default=%(default)s)")
parser.add_argument('--appSuffix','--appSuffix',default='jrb',help="eTraveler server (default=%(default)s)")
args = parser.parse_args()


if args.eTserver == 'Prod': pS = True
else: pS = False
connect = Connection(operator='richard', db=args.db, exp='LSST-CAMERA', prodServer=pS, appSuffix='-'+args.appSuffix)

   
returnData  = connect.getResultsJH(htype=args.htype, stepName = 'vendorIngest', travelerName='SR-RCV-01')

ccd_list_all = []
ccd_list = []
for ccd in returnData:
    ccd_list_all.append(ccd)
    
    try:
        returnDataTS3  = connect.getResultsJH(htype=args.htype, stepName = 'test_report', travelerName='SR-EOT-1', experimentSN=ccd)

        expDict = returnDataTS3[ccd]
        
        try:
            stepDict = expDict['steps']['test_report']
            ccd_list.append(ccd)
        except:
            pass
    except:
        pass

print 'Type ', args.htype,  len(ccd_list_all), 'total. Found ', len(ccd_list), 'with SR-EOT-1', '\n \n', ccd_list
    
        




    

