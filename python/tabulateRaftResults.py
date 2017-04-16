from getResults import getResults
from exploreRaft import exploreRaft
from  eTraveler.clientAPI.connection import Connection

import argparse


## Command line arguments
parser = argparse.ArgumentParser(description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('-r','--raftID', default=None,help="(metadata) Raft ID (default=%(default)s)")
parser.add_argument('--run', default=None,help="(raft run number (default=%(default)s)")
parser.add_argument('-s','--schema', default=None,help="(metadata) schema (default=%(default)s)")
parser.add_argument('-X','--XtraOpts',default=None,help="any extra 'datacat find' options (default=%(default)s)")
parser.add_argument('-d','--db',default='Prod',help="eT database (default=%(default)s)")
parser.add_argument('-e','--eTserver',default='Prod',help="eTraveler server (default=%(default)s)")
args = parser.parse_args()


raft = args.raftID
schema = args.schema
if args.eTserver == 'Prod': pS = True
else: pS = False

print 'Searching ', raft, ' for ', schema

eR = exploreRaft(db=args.db, prodServer=args.eTserver)
connect = Connection(operator='richard', db=args.db, exp='LSST-CAMERA', prodServer=pS)

ccd_list = eR.raftContents(raft)
runs_used = [-99]*3

for row in ccd_list:
#    ccd = row[0].split('-Dev')[0]
    ccd = str(row[0])
    
    test_table = {}
    htype = 'ITL-CCD'
    if 'E2V' in ccd: htype = 'e2v-CCD'
    
    returnDataVendor  = connect.getResultsJH(htype=htype, stepName = 'read_noise_offline', travelerName='SR-EOT-02', experimentSN=ccd)
    
    expDict = returnDataVendor[ccd]
    runs_used[0] = expDict['runNumber']
    stepDict = expDict['steps']['read_noise_offline']

    schemaList = stepDict[schema]
    for d in schemaList:
        if d['schemaInstance'] == 0: continue
        test_table[d['amp']] = [d['read_noise'], -99., -99.]

    try:
        returnDataTS3  = connect.getResultsJH(htype=htype, stepName = 'read_noise_offline', travelerName='SR-EOT-1', experimentSN=ccd)

        expDict = returnDataTS3[ccd]
        runs_used[1] = expDict['runNumber']

        stepDict = expDict['steps']['read_noise_offline']
        schemaList = stepDict[schema]
        for d in schemaList:
            if d['schemaInstance'] == 0: continue
            test_table[d['amp']][1] = d['read_noise']

    except:
        pass


    returnDataTS8  = connect.getRunResults(run=args.run,itemFilter=('sensor_id', ccd))
    runs_used[2] = args.run
    
    for step in returnDataTS8['steps']:
        stepDict = returnDataTS8['steps'][step]

        for schemaList in stepDict:
            if schemaList == 'read_noise_raft':
                for d in stepDict[schemaList]:
                    if d['schemaInstance'] == 0: continue
                    test_table[d['amp']][2] = d['read_noise']

    print "run #'s used: Vendor, TS3, TS8 ", runs_used
    print row
    print 'Amplifier           Vendor EOT-02         TS3 EOT-1            TS8'

    for amp in test_table:
        print "%8i              %6.2f              %6.2f             %6.2f" % (amp, test_table[amp][0], test_table[amp][1], test_table[amp][2])
        




    

