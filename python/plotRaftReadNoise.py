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
args = parser.parse_args()


raft = args.raftID
if args.eTserver == 'Prod': pS = True
else: pS = False

print 'Searching ', raft, ' for ', args.db , 'database and server is ', args.eTserver

eR = exploreRaft(db=args.db, prodServer=args.eTserver)

connect = Connection(operator='richard', db=args.db, exp='LSST-CAMERA', prodServer=pS, appSuffix='-'+args.appSuffix)
kwds = {'run':args.run}

ccd_list = eR.raftContents(raft)

noise = []

for row in ccd_list:
    ccd = str(row[0])
    
    test_table = {}
    kwds["itemFilter"]=('sensor_id', ccd)
    returnData = connect.getRunResults(**kwds)
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

    

