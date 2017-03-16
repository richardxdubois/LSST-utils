from getResults import getResults
import argparse


## Command line arguments
parser = argparse.ArgumentParser(description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('-r','--run', default=None,help="(raft run number (default=%(default)s)")
parser.add_argument('-d','--db', default="db_connect.txt",help="(database connect file to use (default=%(default)s)")
args = parser.parse_args()


eT = getResults( dbConnectFile='devdb_connect.txt')

eT.connectDB()

# specify run number

print 'Finding data via run number'

runData = eT.getRunResults(args.run, schemaName='package_versions' )


versions = []
for s in runData['schemas']:
    pdict = runData['schemas'][s]
    for p in pdict:
        for instance in pdict[p]:
            if instance['package'] == 'string': continue
            versions.append([instance['package'], instance['version']])
    break

#print 'package versions \n\n', versions
for packages in versions:
    print "%35s              %s" % (packages[0], packages[1])


