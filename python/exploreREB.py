from  eTraveler.clientAPI.connection import Connection

class exploreREB():

    def __init__(self, db='Prod', prodServer='Prod'):

        if prodServer == 'Prod': pS = True
        else: pS = False

        self.connect = Connection(operator='richard', db=db, exp='LSST-CAMERA', prodServer=pS)

    def REBContents(self, REBName=None):
        kwds = {'experimentSN':REBName, 'htype':'LCA-13574', 'noBatched':'true'}

        response = self.connect.getHardwareHierarchy(**kwds)

# LCA-11721 is the ASPIC.

        aspic_list = []
        for row in response:
            kid = row['child_experimentSN']
            if '11721' in kid:
                aspic_list.append((kid,row['slotName']))
        
        return aspic_list

    def ASPIC_parent(self, ASPIC_name=None, htype='LCA-11721'):
    
# now find ASPIC for a REB

        kwds = {'experimentSN': ASPIC_name, 'htype':htype, 'noBatched':'true'}

        response = self.connect.getContainingHardware(**kwds)

        for child in response:
            if '13574' in child['parent_experimentSN']:
                parentREB = child['parent_experimentSN']
                break

        return parentREB

    
if __name__ == "__main__":

    REBName = 'LCA-13574-017'

    eR = exploreREB()

    aspic_list = eR.REBContents(REBName)

    print aspic_list

    aspic_name = 'LCA-11721-ASPIC-0453'

    parentREB = eR.ASPIC_parent(aspic_name,'LCA-11721')

    print aspic_name, "'s parent REB = ", parentREB
