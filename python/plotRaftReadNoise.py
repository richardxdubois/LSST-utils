from exploreRaft import exploreRaft
from  eTraveler.clientAPI.connection import Connection
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


import argparse


## Command line arguments
parser = argparse.ArgumentParser(description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('-r','--raftID', default=None,help="(metadata) Raft ID (default=%(default)s)")
parser.add_argument('--run', default=None,help="(raft run number (default=%(default)s)")
parser.add_argument('-d','--db',default='Prod',help="database to use (default=%(default)s)")
parser.add_argument('-e','--eTserver',default='Dev',help="eTraveler server (default=%(default)s)")
parser.add_argument('--appSuffix','--appSuffix',default='jrb',help="eTraveler server (default=%(default)s)")
parser.add_argument('-o','--output',default='read_noise.pdf',help="output plot file (default=%(default)s)")
parser.add_argument('-i', '--infile', default="", help="input file name for list of wav files (default=%(default)s)")

args = parser.parse_args()
raft_list = {}

if args.infile <> "":
    with open(args.infile) as f:
        for line in f:
            (raft, run) = line.split()
            raft_list[raft] = run
else:
    raft_list[args.raftID] = args.run


if args.eTserver == 'Prod': pS = True
else: pS = False

eR = exploreRaft(db=args.db, prodServer=args.eTserver)
connect = Connection(operator='richard', db=args.db, exp='LSST-CAMERA', prodServer=pS,
                     appSuffix='-' + args.appSuffix)
noise = []

for r in raft_list:

    print 'Searching ', r, ' for ', raft_list[r] , 'database and server is ', args.eTserver


    ccd_list = eR.raftContents(r)

    for row in ccd_list:
        ccd = str(row[0])

        test_table = {}
        returnData = connect.getRunResults(run=raft_list[r], itemFilter=('sensor_id',ccd))
        run = returnData['run']

        for step in returnData['steps']:
            stepDict = returnData['steps'][step]

            for schemaList in stepDict:
                if schemaList == 'read_noise_raft':
                    for d in stepDict[schemaList]:
                        if d['schemaInstance'] == 0: continue
                        noise.append(d['read_noise'])

with PdfPages(args.output) as pdf:

    plt.hist(noise)

    pdf.savefig()
    plt.close()

    

