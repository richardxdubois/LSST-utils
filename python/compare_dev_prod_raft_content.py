from  eTraveler.clientAPI.connection import Connection
from exploreRaft import exploreRaft
import argparse
import collections

"""
Purpose: compare CCD and REB content of rafts defined in Prod and Dev. For comparison, it is assumed the 
prod raft name is contained in the dev one (eg dev has -Dev appended). Ditto for CCDs. In fact, 
a match just requires that the prod name be a substring of the dev one for raft, CCD and REB.

A count is kept matching slot by slot, so a perfect match is 9 CCDs and 9 REBs.
"""

## Command line arguments
parser = argparse.ArgumentParser(
    description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('-t', '--htype', default='LCA-11021_RTM', help="hardware type (default=%(default)s)")
parser.add_argument('-d', '--db', default='Prod', help="eT database (default=%(default)s)")
parser.add_argument('-e', '--eTserver', default='Prod', help="eTraveler server (default=%(default)s)")
parser.add_argument('-o', '--output', default='unlabeled_sensors.pdf',
                    help="output plot file (default=%(default)s)")

args = parser.parse_args()

if args.eTserver == 'Prod':
    pS = True
else:
    pS = False
connect_prod = Connection(operator='richard', db='Prod', exp='LSST-CAMERA', prodServer=pS)
connect_dev = Connection(operator='richard', db='Dev', exp='LSST-CAMERA', prodServer=pS)

eR_prod = exploreRaft(db='Prod')
eR_dev = exploreRaft(db='Dev')

returnData_prod = connect_prod.getHardwareInstances(htype=args.htype)
returnData_dev = connect_dev.getHardwareInstances(htype=args.htype)

print len(returnData_prod), args.htype, ' rafts found in prod'

raft_list = collections.OrderedDict()
raft_list_dev = collections.OrderedDict()

for inst in returnData_prod:

    raft = inst['experimentSN']
    # ignore strange names
    if 'MTR' in raft:
        continue

    content_prod = eR_prod.raftContents(raftName=raft)
    if len(content_prod) == 0:
        continue
    raft_list[raft] = content_prod

for inst in returnData_dev:

    raft = inst['experimentSN']
    # ignore strange names
    if 'MTR' in raft or 'test' in raft or '002_ETU1' in raft:
        continue

    content_dev = eR_dev.raftContents(raftName=raft)
    raft_list_dev[raft] = content_dev


print raft_list

for raft in raft_list:
    print 'Matching raft: ', raft
    for raft_dev in raft_list_dev:
        ccd_type = eR_prod.raft_type(raft=raft) + "-CCD"
        nc = 0
        nc_sn = 0
        nr = 0
        nr_sn = 0

        if raft in raft_dev:
            if len(raft_list_dev[raft_dev]) == 0:
                print 'Dev raft ', raft_dev, ' has no content'
                continue
            for idx in range(0,9):
                c = raft_list[raft][idx]
                c_dev = raft_list_dev[raft_dev][idx]
                if c[0] in c_dev[0]:
                    nc += 1
                    returnCCD_dev = connect_dev.getHardwareInstances(htype=ccd_type, experimentSN=c_dev[0])
                    try:
                        ccd_manu_l = returnCCD_dev[0]
                        ccd_manu = ccd_manu_l['manufacturerId']
                        nc_sn += 1
                    except KeyError:
                        pass
                if c[2] in c_dev[2]:
                    nr += 1
                    returnREB_dev = connect_dev.getHardwareInstances(htype='LCA-13574', experimentSN=c_dev[2])
                    try:
                        reb_manu = returnREB_dev[0]['manufacturerId']
                        nr_sn += 1
                    except KeyError:
                        pass
            print raft, raft_dev, nc, nc_sn, nr, nr_sn