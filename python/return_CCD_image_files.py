from  eTraveler.clientAPI.connection import Connection
from findCCD import findCCD
import argparse
from exploreRaft import exploreRaft
from raft_observation import raft_observation

class return_CCD_image_files():

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



    def get_raft(self, runList=None, sensorID=None):

        self.sensorID = sensorID
        if 'ITL' in self.sensorID:
            self.CCDType = "ITL-CCD"
        if 'E2V' in self.sensorID:
            self.CCDType = "e2v-CCD"

        eR = exploreRaft(db=self.db, prodServer=self.server)

        raft = eR.CCD_parent(CCD_name=self.sensorID, htype=self.CCDType)

        stepName = ['fe55_raft_acq', 'dark_raft_acq','flat_pair_raft_acq', 'sflat_raft_acq']

        files = []

        for run in runList:

            for stp in stepName:

                try:

                    rO = raft_observation(run=run, step=stp,imgtype='BIAS', db=self.db)
                    obs_dict = rO.find()

                    for t in obs_dict:
                        fl = obs_dict[t]
                        for f in fl:
                            if self.sensorID in f:
                                files.append(f)
                except:
                    pass

        return files

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

    f = return_CCD_image_files(db = args.db, server= args.eTserver, appSuffix = args.appSuffix)

    runList = ['4834', '4864', '4865', '4866']

    files = f.get_raft(sensorID=args.sensorID, runList=runList)

    print 'Sensor ', '\n \n'

    for fl in files:
        print fl
    
        




    

