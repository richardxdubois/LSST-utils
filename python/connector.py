from  eTraveler.clientAPI.connection import Connection

class connector():
    def __init__(self, prodServer = True):

        self.prod_connect = Connection(operator='richard', db='Prod', exp='LSST-CAMERA', prodServer=prodServer)
        self.dev_connect = Connection(operator='richard', db='Dev', exp='LSST-CAMERA', prodServer=prodServer)

    def run_selector(self,run):

        conn = self.prod_connect
        if 'D' in run:
            conn = self.dev_connect

        return conn