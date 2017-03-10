from getResults import getResults
from exploreRaft import exploreRaft

import argparse


## Command line arguments
parser = argparse.ArgumentParser(description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('-r','--raftID', default=None,help="(metadata) Raft ID (default=%(default)s)")
parser.add_argument('-s','--schema', default=None,help="(metadata) schema (default=%(default)s)")
args = parser.parse_args()


raft = args.raftID
schema = args.schema

print 'Searching ', raft, ' for ', schema

eR = exploreRaft(db='Dev')
eT = getResults( dbConnectFile='db_connect.txt')

eT.connectDB()

ccd_list = eR.raftContents(raft)

for row in ccd_list:
    ccd = row[0].split('-Dev')[0]
    print ccd
    print 'Amplifier           Vendor EOT-02         TS3 EOT-1'
    
    test_table = {}
    
    returnDataVendor  = eT.getResultsJH(schemaName=schema, htype='ITL-CCD', travelerName='SR-EOT-02', experimentSN=ccd)

    expDict = returnDataVendor[ccd]

    for d in returnDataVendor[ccd]['instances']:
        if d['schemaInstance'] == 0: continue
        test_table[d['amp']] = [d['read_noise'], -99.]

    try:
        returnDataTS3  = eT.getResultsJH(schemaName=schema, htype='ITL-CCD', travelerName='SR-EOT-1', experimentSN=ccd)
        for d in returnDataTS3[ccd]['instances']:
            if d['schemaInstance'] == 0: continue
            test_table[d['amp']][1] = d['read_noise']

    except:
        pass
        
    for amp in test_table:
        print "%8i              %6.2f              %6.2f" % (amp, test_table[amp][0], test_table[amp][1])
        




    

