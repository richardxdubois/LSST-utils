from  eTraveler.clientAPI.connection import Connection
from findCCD import findCCD
import argparse
from exploreRaft import exploreRaft
from raft_observation import raft_observation

class find_CCD_image_files():

    def __init__(self, db = None, server = None, appSuffix = None):

        self.sensorID = None
        self.CCDType = None
        self.testName = None
        self.db = db
        self.server = server
        self.appSuffix = appSuffix

        if server == 'Prod':
            pS = True
        else:
            pS = False

        self.connect = Connection(operator='richard', db=db, exp='LSST-CAMERA', prodServer=pS, appSuffix='-'+appSuffix)

        self.testInfo = {}
        self.testInfo['vendor'] = ['SR-RCV-01', 'vendorIngest','vendorCopy']
        self.testInfo['TS3'] = ['SR-EOT-1', 'dark_acq', 'slac.lca.archive']


    def get_single(self, testName =  None):

        ccd = self.sensorID
        stepName = self.testInfo[testName][1]
        travName = self.testInfo[testName][0]
        fCCDName = self.testInfo[testName][1]
        mirrorName = self.testInfo[testName][2]

        files = []

        try:
            returnData = self.connect.getResultsJH(htype=self.CCDType, experimentSN=ccd, stepName=stepName,
                                                   travelerName=travName)
            expDict = returnData[ccd]
            stepDict = expDict['steps'][stepName]
            run = expDict['runNumber']
            fCCD = findCCD(FType='fits', testName=fCCDName, sensorId=ccd, run=run, mirrorName=mirrorName, XtraOpts='IMGTYPE=="DARK"')
            files = fCCD.find()

        except:
            pass

        return files


    def get_raft(self):

        eR = exploreRaft(db=self.db, prodServer=self.server)

        raft = eR.CCD_parent(CCD_name=self.sensorID, htype=self.CCDType)

        stepName = 'fe55_raft_acq'
        files = []

        returnData  = self.connect.getResultsJH(htype='LCA-11021_RTM', experimentSN = raft, stepName = stepName, travelerName='SR-RTM-EOT-03')

        try:
            expDict = returnData[raft]
            run = expDict['runNumber']

            rO = raft_observation(run=run, step=stepName,imgtype='BIAS')
            obs_dict = rO.find()


            for t in obs_dict:
                fl = obs_dict[t]
                for f in fl:
                    if self.sensorID in f:
                        files.append(f)
        except:
            pass

        return files


    def get_files(self, sensorID=None):

        self.sensorID = sensorID

        if 'ITL' in self.sensorID:
            self.CCDType = "ITL-CCD"
        if 'E2V' in self.sensorID:
            self.CCDType = "e2v-CCD"


        all_the_files = {}

        all_the_files['vendor'] = self.get_single(testName = 'vendor')
        all_the_files['TS3'] = self.get_single(testName='TS3')
        all_the_files['raft'] = self.get_raft()

        return all_the_files

if __name__ == "__main__":

    ## Command line arguments
    parser = argparse.ArgumentParser(
        description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

    ##   The following are 'convenience options' which could also be specified in the filter string
    parser.add_argument('-s', '--sensorID', default=None, help="sensor name (default=%(default)s)")
    parser.add_argument('-d', '--db', default='Prod', help="eT database (default=%(default)s)")
    parser.add_argument('-e', '--eTserver', default='Dev', help="eTraveler server (default=%(default)s)")
    parser.add_argument('--appSuffix', '--appSuffix', default='jrb',
                        help="eTraveler server (default=%(default)s)")
    args = parser.parse_args()

    f = find_CCD_image_files(db = args.db, server= args.eTserver, appSuffix = args.appSuffix)

    files = f.get_files(args.sensorID)

    print 'Sensor ', '\n \n', files
    
        




    

