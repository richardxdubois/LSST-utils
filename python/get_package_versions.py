from getResults import getResults
import argparse


## Command line arguments
parser = argparse.ArgumentParser(description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('-r','--run', default=None,help="(raft run number (default=%(default)s)")
parser.add_argument('-d','--db', default="db_connect.txt",help="(database connect file to use (default=%(default)s)")
parser.add_argument('-s','--schema', default="package_versions",help="(schema name for versions (default=%(default)s)")
parser.add_argument('--key1', default="package",help="(first key - usually package (default=%(default)s)")
parser.add_argument('--key2', default="version",help="(second key - usually version (default=%(default)s)")
args = parser.parse_args()


eT = getResults( dbConnectFile=args.db)

eT.connectDB()

# specify run number

print 'Finding package versions for run number: ', args.run, args.schema

runData = eT.getRunResults(args.run, schemaName=args.schema )

versions = []
for s in runData['steps']:
    schdict = runData['steps'][s]
    for p in schdict:
        for instance in schdict[p]:
            if instance[args.key1] == 'string': continue
            versions.append([instance[args.key1], instance[args.key2]])
    break

#print 'package versions \n\n', versions
for packages in versions:
    print "%35s              %s" % (packages[0], packages[1])


