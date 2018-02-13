from exploreRaft import exploreRaft
from  eTraveler.clientAPI.connection import Connection
from connector import connector

import argparse

## Command line arguments
parser = argparse.ArgumentParser(
    description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('--run', default=None, help="(raft run number (default=%(default)s)")
parser.add_argument('-s', '--schema', default=None, help="(metadata) schema (default=%(default)s)")
parser.add_argument('-X', '--XtraOpts', default=None,
                    help="any extra 'datacat find' options (default=%(default)s)")
parser.add_argument('-d', '--db', default='Prod', help="eT database (default=%(default)s)")
parser.add_argument('-e', '--eTserver', default='Prod', help="eTraveler server (default=%(default)s)")
parser.add_argument('--appSuffix', '--appSuffix', default='jrb',
                    help="eTraveler server (default=%(default)s)")
args = parser.parse_args()

schema = args.schema
if args.eTserver == 'Prod':
    pS = True
else:
    pS = False

run_list = args.run.split(',')

eR = exploreRaft(db=args.db, prodServer=args.eTserver)
connector = connector(prodServer=pS)

# set up a prod connection for the vendor and TS3 searches
connectProd = connector.run_selector('1234')

rsp = connectProd.getRunSummary(run=run_list[0])
raft = rsp['experimentSN']

print 'Searching ', raft, ' for ', schema

ccd_list = eR.raftContents(raft)
runs_used = [-99] * (2 + len(run_list))
print ccd_list

result_name = 'dark_pixels'

for row in ccd_list:
    ccdProd = row[0].split('-Dev')[0]
    ccd = str(row[0])

    test_table = {}
    htype = 'ITL-CCD'
    if 'E2V' in ccd: htype = 'e2v-CCD'

    returnDataVendor = connectProd.getResultsJH(htype=htype, stepName='dark_defects_offline',
                                                travelerName='SR-EOT-02', experimentSN=ccdProd)

    expDict = returnDataVendor[ccdProd]
    runs_used[0] = expDict['runNumber']
    stepDict = expDict['steps']['dark_defects_offline']

    schemaList = stepDict['dark_defects']
    for d in schemaList:
        if d['schemaInstance'] == 0: continue
        test_table[d['amp']] = [d[result_name], -99., -99., -99., -99.]

    try:
        returnDataTS3 = connectProd.getResultsJH(htype=htype, stepName='dark_defects',
                                                 travelerName='SR-EOT-1',
                                                 experimentSN=ccdProd)

        expDict = returnDataTS3[ccdProd]
        runs_used[1] = expDict['runNumber']

        stepDict = expDict['steps']['dark_defects']
        schemaList = stepDict['dark_defects']
        for d in schemaList:
            if d['schemaInstance'] == 0: continue
            test_table[d['amp']][1] = d[result_name]

    except:
        pass

    raft_run = 1
    for run in run_list:
        raft_run += 1
        raft_connect = connector.run_selector(run)
        ccd_name = ccd
        if 'D' in run:
            ccd_name += '-Dev'
        returnDataTS8 = raft_connect.getRunResults(run=run, itemFilter=('sensor_id', ccd_name))
        runs_used[raft_run] = run

        stepDict = returnDataTS8['steps']['dark_defects_raft']

        schemaList = stepDict['dark_defects_raft']
        for d in schemaList:
            if d['schemaInstance'] == 0: continue
            test_table[d['amp']][raft_run] = d[result_name]

    print "run #'s used: Vendor, TS3, Raft ", runs_used
    print row
    print 'Amplifier           Vendor EOT-02         TS3 EOT-1            TS8          I&T'

    for amp in test_table:
        print "%8i              %6.2f              %6.2f             %6.2f        %6.2f         %6.2f" \
              % (amp, test_table[amp][0],
                 test_table[amp][1],
                 test_table[amp][2],
                 test_table[amp][3],
                 test_table[amp][4]
                 )
