from getResults import getResults
from exploreRaft import exploreRaft

import argparse


## Command line arguments
parser = argparse.ArgumentParser(description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('-r','--raftID', default=None,help="(metadata) Raft ID (default=%(default)s)")
parser.add_argument('--run', default=None,help="(raft run number (default=%(default)s)")
parser.add_argument('-s','--schema', default=None,help="(metadata) schema (default=%(default)s)")
parser.add_argument('-X','--XtraOpts',default=None,help="any extra 'datacat find' options (default=%(default)s)")
parser.add_argument('-d','--db',default='db_connect.txt',help="database connect file (default=%(default)s)")
parser.add_argument('-e','--eTdb',default='Prod',help="eTraveler database (default=%(default)s)")
args = parser.parse_args()


raft = args.raftID
schema = args.schema

print 'Searching ', raft, ' for ', schema

eR = exploreRaft(db=args.eTdb)
eT = getResults( dbConnectFile=args.db)

eT.connectDB()

ccd_list = eR.raftContents(raft)


for row in ccd_list:
    ccd = str(row[0])
    print ccd
    print row
    print 'Amplifier           TS8 Fe55 Gain         TS8 PTC Gain'
    
    test_table = {}
    returnData  = eT.getRunResults(args.run,itemFilter=('sensor_id', ccd))
    
    for step in returnData['steps']:
        stepDict = returnData['steps'][step]

        for schemaList in stepDict:
            if schemaList == 'fe55_raft_analysis':
                for d in stepDict[schemaList]:
                    if d['schemaInstance'] == 0: continue
                    test_table[d['amp']] = [d['gain'], -99.]
            if schemaList == 'ptc_raft':
                for d in stepDict[schemaList]:
                    if d['schemaInstance'] == 0: continue
                    test_table[d['amp']][1] = d['ptc_gain']

    
    for amp in test_table:
        print "%8i              %6.2f              %6.2f" % (amp, test_table[amp][0], test_table[amp][1])
        




    

