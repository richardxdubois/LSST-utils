import commands
import connection

class exploreRaft():

    def __init__(self):

        self.connect = connection.Connection('richard', db='Dev', exp='LSST-CAMERA', prodServer=True)

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

if __name__ == "__main__":

    raftName = 'LCA-11021_RTM-004_ETU2-Dev'

    eR = exploreRaft()

    ccd_list = eR.raftContents(raftName)

    print ccd_list

    CCD_name = 'ITL-3800C-103-Dev'

    parentRaft = eR.CCD_parent(CCD_name,'ITL-CCD')

    print CCD_name, "'s parent raft = ", parentRaft

