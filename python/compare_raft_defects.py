from  eTraveler.clientAPI.connection import Connection
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import datetime
import collections
import numpy as np
from findCCD import findCCD
from exploreRaft import exploreRaft
import astropy.io.fits as fits

import argparse


class compare_raft_defects():
    def __init__(self, run1=None, run2=None, defect_list='bright_defects_raft', debug = False,  db='Prod',
                 prodServer='Dev', appSuffix='-jrb', mirror='prod'):

        self.run1 = run1
        self.run2 = run2
        self.current_defect = ''
        self.current_ccd = ''
        self.defect_list = defect_list
        self.mirror = mirror

        self.db = db
        self.prodServer = prodServer
        self.debug = debug

        pS = True
        if self.prodServer == 'Dev':
            pS = False

        self.connect = Connection(operator='richard', db=args.db, exp='LSST-CAMERA', prodServer=pS,
                                  appSuffix=appSuffix)

        self.fCCD = findCCD(FType='fits', testName='bright_defects_raft', run=-1, sensorId='E2V',
                            mirrorName=self.mirror)

        self.eR = exploreRaft()

        returnData = self.connect.getRunSummary(run=run1)
        self.raft = returnData['experimentSN']

        self.ccd_list = self.eR.raftContents(self.raft)
        if self.debug == True:
            self.ccd_list = [('ITL-3800C-022', 0, 0)]

    def comp_defects(self, hdu1, hdu2):

        print 'Raft ', self.raft, ' Defect ', self.current_defect, ' ccd ', self.current_ccd, ' Run 1 ', self.run1,\
            ' Run 2', self.run2, ' \n'
        print ' Amp  Tot(', self.run1, ')  Tot(', self.run2, ') # Diff Px'

        tot1 = tot2 = tot_diff = 0

        for amp in range(1, 17):
            pixeldata_run1 = np.array(hdu1[amp].data)
            pixeldata_run2 = np.array(hdu2[amp].data)
            sum_run1 = np.sum(pixeldata_run1)
            sum_run2 = np.sum(pixeldata_run2)
            diff_pix = pixeldata_run1 - pixeldata_run2

            badc = np.where(diff_pix != 0)
            diff_pix = len(badc[0])
            print "%2i     %5i        %5i       %5i" % (amp, sum_run1, sum_run2, diff_pix)

            tot1 += sum_run1
            tot2 += sum_run2
            tot_diff += diff_pix

        print '\n Totals'
        print "       %5i        %5i       %5i" % (tot1, tot2, tot_diff)

    def get_files_run(self, run, defect_name):

        file_list = {}
        returnData = self.connect.getRunSummary(run=run)
        subsystem = returnData['subsystem']
        mirror = 'BNL'
        if subsystem == 'Integration and Test':
            mirror = 'INT'
        mirror = mirror + '-' + self.mirror


        if self.debug == False:
            for ccd_tup in self.ccd_list:
                ccd = ccd_tup[0]

                f = self.fCCD.find(sensorId=ccd, run=run, testName=defect_name, mirrorName=mirror)
                for g in f:
                    if 'mask' in g and ccd in g:
                        file_list[ccd] = g

        if self.debug == True:
            if run == '5730':
                file_list = {
                    'ITL-3800C-022': '/Users/richard/LSST/Data/ETU2/ITL-3800C-022_bright_pixel_mask-5730.fits'}
            else:
                file_list = {
                    'ITL-3800C-022': '/Users/richard/LSST/Data/ETU2/ITL-3800C-022_bright_pixel_mask-5731.fits'}

        return file_list

    def tabulate_defects(self):


        for d in self.defect_list:

            self.current_defect = d

            r1_files = self.get_files_run(run=self.run1, defect_name=d)
            r2_files = self.get_files_run(run=self.run2, defect_name=d)

            for ccd_tup in self.ccd_list:
                ccd = ccd_tup[0]
                self.current_ccd = ccd
                f1 = r1_files[ccd]
                hdu1 = fits.open(f1)
                f2 = r2_files[ccd]
                hdu2 = fits.open(f2)

                print '\n ', f1, '\n', f2
                comp = self.comp_defects(hdu1=hdu1, hdu2=hdu2)


if __name__ == "__main__":
    ## Command line arguments
    parser = argparse.ArgumentParser(
        description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

    ##   The following are 'convenience options' which could also be specified in the filter string
    parser.add_argument('--run1', default=None, help="(first raft run number (default=%(default)s)")
    parser.add_argument('--run2', default=None, help="(second raft run number (default=%(default)s)")
    parser.add_argument('--defects', default='bright_defects_raft', help="(comma delimited list of defect types (default=%(default)s)")
    parser.add_argument('-m','--mirror', default='prod', help="mirror BNL-prod, INT-prod ")
    parser.add_argument('--db', default='Prod', help="Prod or Dev eT db ")
    parser.add_argument('--debug', default='no', help="debug flag(default=%(default)s)")
    parser.add_argument('-e', '--eTserver', default='Dev', help="eTraveler server (default=%(default)s)")
    parser.add_argument('--appSuffix', '--appSuffix', default='jrb',
                        help="eTraveler server (default=%(default)s)")
    parser.add_argument('-o', '--output', default='raft_temp_dependence.pdf',
                        help="output plot file (default=%(default)s)")
    parser.add_argument('-i', '--infile', default="",
                        help="input file name for list of runs, temps (default=%(default)s)")

    args = parser.parse_args()

    dl = args.defects
    defect_list = dl.split(',')
    if args.debug == 'yes':
        debug = True
    else:
        debug = False

    defects = compare_raft_defects(run1=args.run1, run2=args.run2, defect_list = defect_list, debug=debug,
                                   mirror=args.mirror)

    tab_defects = defects.tabulate_defects()
