from getResults import getResults

import argparse


## Command line arguments
parser = argparse.ArgumentParser(description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('-r', '--run', default=None,help="(raft run number (default=%(default)s)")
parser.add_argument('--db', default='db_connect.txt',help="db connect file for getResults ")
args = parser.parse_args()

print 'Discover step and schema names for run ', args.run

eT = getResults( dbConnectFile=args.db)

eT.connectDB()

returnData  = eT.getRunResults(args.run)
    
for step in returnData['steps']:
        stepDict = returnData['steps'][step]
        print '\n Step ', step, '\n'

        for schemaList in stepDict:
            print schemaList




    

