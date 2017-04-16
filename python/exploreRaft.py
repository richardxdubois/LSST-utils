#import commands
#import connection
from  eTraveler.clientAPI.connection import Connection

class exploreRaft():

    def __init__(self, db='Prod', prodServer='Prod'):

        if prodServer == 'Prod': pS = True
        else: pS = False

        self.connect = Connection(operator='richard', db=db, exp='LSST-CAMERA', prodServer=pS)

    def raftContents(self, raftName=None):
        kwds = {'experimentSN':raftName, 'htype':'LCA-11021_RTM', 'noBatched':'true'}

        response = self.connect.getHardwareHierarchy(**kwds)

# LCA-13574 is the RSA.

        reb_list = []
        for row in response:
            kid = row['child_experimentSN']
            if '13574' in kid:
                reb_list.append((kid,row['slotName']))
        
# match up the CCD to the REB via REB and slot numbering. The CCD in slot Sxy is on REBx. Note that the CCD is actually
# assembled onto the RSA.

        ccd_list = []
        for child in response:
#            print child['parent_experimentSN'], child['relationshipTypeName'],  child['child_experimentSN'], child['slotName']

            kid = child['child_experimentSN']
            if 'ITL' in kid or 'e2v' in kid:
                slotName = child['slotName']
                rebNumber = slotName[1]
                for reb in reb_list:
                    rebLoc = reb[1][3]
                    if rebLoc == rebNumber:
                        rebId = reb[0]
                        break
                ccd_list.append((kid, slotName, rebId))

        return ccd_list

    def CCD_parent(self, CCD_name=None, htype='ITL-CCD'):
    
# now find raft for a CCD

        kwds = {'experimentSN': CCD_name, 'htype':htype, 'noBatched':'true'}

#connect = connection.Connection('richard', db='Dev', exp='LSST-CAMERA', prodServer=True)

        response = self.connect.getContainingHardware(**kwds)

        for child in response:
            if 'RTM' in child['parent_experimentSN']:
                parentRTM = child['parent_experimentSN']
                break

        return parentRTM

    def REB_parent(self, REB_name=None):
    
# now find raft for a REB

        kwds = {'experimentSN': REB_name, 'htype':'LCA-13574', 'noBatched':'true'}   # need to fix REB htype!

        response = self.connect.getContainingHardware(**kwds)

        for child in response:
            if 'RTM' in child['parent_experimentSN']:
                parentRTM = child['parent_experimentSN']
                break

        return parentRTM

    def REB_CCD(self, REB_name=None):

        raft = self.REB_parent(REB_name)
        ccd_list = self.raftContents(raft)

        ccd_in_reb = []
        for ccd in ccd_list:
            if REB_name == ccd[2]: ccd_in_reb.append(ccd[0])

        return ccd_in_reb

    
if __name__ == "__main__":

    raftName = 'LCA-11021_RTM-004_ETU2-Dev'

    eR = exploreRaft(db='Dev')

    ccd_list = eR.raftContents(raftName)

    print ccd_list

    CCD_name = 'ITL-3800C-103-Dev'

    parentRaft = eR.CCD_parent(CCD_name,'ITL-CCD')

    print CCD_name, "'s parent raft = ", parentRaft

    reb_parent = eR.REB_parent('LCA-13574-003')
    print 'parent raft of LCA-13574-003 is ', reb_parent

    reb_ccds = eR.REB_CCD('LCA-13574-003')
    print 'CCDs on REB LCA-13574-003 are ', reb_ccds

