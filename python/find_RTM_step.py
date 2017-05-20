from  eTraveler.clientAPI.connection import Connection
import datetime
import argparse
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


## Command line arguments
parser = argparse.ArgumentParser(description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('-t','--htype', default=None,help="hardware type (default=%(default)s)")
parser.add_argument('-r','--raft', default=None,help="raft name (default=%(default)s)")
parser.add_argument('-d','--db',default='Prod',help="eT database (default=%(default)s)")
parser.add_argument('-e','--eTserver',default='Dev',help="eTraveler server (default=%(default)s)")
parser.add_argument('--appSuffix','--appSuffix',default='jrb',help="eTraveler server (default=%(default)s)")
args = parser.parse_args()


if args.eTserver == 'Prod': pS = True
else: pS = False
connect = Connection(operator='richard', db=args.db, exp='LSST-CAMERA', prodServer=pS, appSuffix='-'+args.appSuffix)

for run in range(4963,5010):
    runInfo  = connect.getRunSummary(run=run)
    if runInfo["experimentSN"] == args.raft:
        print args.raft, run
        act = connect.getRunActivities(run=run)

        for step in act:
            step_name = step['stepName']
            print step_name, step['status']
            
        
    
        




    

