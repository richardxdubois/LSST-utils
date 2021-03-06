from __future__ import print_function

from eTraveler.clientAPI.connection import Connection
import numpy as np
from findCCD import findCCD
from exploreRaft import exploreRaft
import astropy.io.fits as fits
from sklearn.cluster import DBSCAN
from sklearn import metrics
from sklearn.datasets.samples_generator import make_blobs
from sklearn.preprocessing import StandardScaler
from scipy import sparse

import argparse
import matplotlib
matplotlib.use('agg')

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


class compare_raft_defects():
    def __init__(self, run1=None, run2=None, defect_list='bright_defects_raft', debug = False,  db='Prod',
                 single_ccd=None, prodServer='Prod', appSuffix='', mirror='prod'):

        self.run1 = run1
        self.run2 = run2
        self.current_defect = ''
        self.single_ccd = single_ccd
        self.current_ccd = ''
        self.current_slot = ""
        self.defect_list = defect_list
        self.mirror = mirror
        self.amp = -1
        self.clusters1 = {}
        self.clusters2 = {}

        self.db = db
        self.prodServer = prodServer
        self.debug = debug
        self.printit = True
        self.ccd_stats = {}

        pS = True
        if self.prodServer == 'Dev':
            pS = False

        self.connect = Connection(operator='richard', db=self.db, exp='LSST-CAMERA', prodServer=pS)

        self.fCCD = findCCD(FType='fits', testName='bright_defects_raft', run=-1, sensorId='E2V',
                            mirrorName=self.mirror,prodServer=self.prodServer,appSuffix=appSuffix)

        self.eR = exploreRaft(prodServer=self.prodServer,appSuffix=appSuffix)

        if self.debug is True:
            self.run1 = 9537
            self.run2 = 10317

        returnData = self.connect.getRunSummary(run=self.run2)
        self.raft = returnData['experimentSN']
        self.ccd_list = self.eR.raftContents(raftName=self.raft, run=self.run2)

        # check whether the two runs have the same CCD content (unless a single CCD is requested)
        self.ccd_list_chk = self.eR.raftContents(raftName=self.raft, run=self.run1)
        if self.ccd_list != self.ccd_list_chk and self.single_ccd is None:
            raise Exception("CCD lists don't match")

        if self.debug is True:
            self.ccd_list = [('ITL-3800C-325', 0, 0)]

        self.r1_files = self.get_files_run(run=self.run1, defect_name=self.defect_list[0])
        self.r2_files = self.get_files_run(run=self.run2, defect_name=self.defect_list[0])

    def comp_defects(self, hdu1, hdu2):

        if self.amp == 1:
            print('Raft ', self.raft, ' Defect ', self.current_defect, ' ccd ', self.current_ccd,
                  ' Slot ', self.current_slot, ' Run 1 ', self.run1, ' Run 2', self.run2, ' \n')
            print(' Amp  Tot(', self.run1, ')  Tot(', self.run2, ') # Diff Px   # Clus 1    # Clus 2')

        tot1 = tot2 = tot_diff = 0

        badc = {}
        defect_1 = 0
        defect_2 = 0
        sum_run1 = 0
        sum_run2 = 0

        amp_stats = self.ccd_stats.setdefault(self.current_ccd, [])

        for amp in range(1, 17):
            if self.amp != -1 and amp != self.amp:
                continue

            pixeldata_run1 = np.array(hdu1[amp].data)
            pixeldata_run2 = np.array(hdu2[amp].data)
            sum_run1 = np.sum(pixeldata_run1)
            sum_run2 = np.sum(pixeldata_run2)
            diff_pix = pixeldata_run1 - pixeldata_run2

            badc = np.where(diff_pix != 0)
            defect_1 = np.where(pixeldata_run1 != 0)
            defect_2 = np.where(pixeldata_run2 != 0)
            diff_pix_count = len(badc[0])

            amp_defects = np.array([sum_run1, sum_run2, diff_pix_count])
            self.ccd_stats[self.current_ccd].append(amp_defects)

            # find clusters

            n_clus1 = n_clus2 = 0

            if len(defect_1[0]) != 0:
                cl1 = self.clusters1.setdefault(ccd, {})
                n_clus1, clusters1 = self.find_clusters(defect_1)
                self.clusters1[ccd][amp] = clusters1
            if len(defect_2[0]) != 0:
                cl2 = self.clusters2.setdefault(ccd, {})
                n_clus2, clusters2 = self.find_clusters(defect_2)
                self.clusters2[ccd][amp] = clusters2

            print("%2i     %5i        %5i       %5i      %5i       %5i" % (amp, sum_run1, sum_run2,
                                    diff_pix_count, n_clus1, n_clus2 ))

            if self.amp == 16:
                tot1 = tot2 = tot_diff = 0
                for i in range(0,16):
                    tot1 += self.ccd_stats[self.current_ccd][i][0]
                    tot2 += self.ccd_stats[self.current_ccd][i][1]
                    tot_diff += self.ccd_stats[self.current_ccd][i][2]

                print('\n Totals')
                print("       %5i        %5i       %5i" % (tot1, tot2, tot_diff))

        return (badc, defect_1, defect_2)

    def find_clusters(self, defect_list=None):

        X = []
        for i_d, d in enumerate(defect_list[0]):
            X.append((d, defect_list[1][i_d]))

        db = DBSCAN(eps=1., min_samples=3).fit(X)
        core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
        core_samples_mask[db.core_sample_indices_] = True
        labels = db.labels_

        # Number of clusters in labels, ignoring noise if present.
        n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise_ = list(labels).count(-1)
        unique_labels = set(labels)

        cluster_dict = {}
        for k in unique_labels:
            if k == -1:
                continue
            class_member_mask = (labels == k)
            xy = []
            for i_d, d in enumerate(X):
                if class_member_mask[i_d]:
                    xy.append(d)
            cluster_dict[k] = xy

        return n_clusters_, cluster_dict

    def get_files_run(self, run, defect_name):

        file_list = {}
        returnData = self.connect.getRunSummary(run=run)
        subsystem = returnData['subsystem']
        mirror = 'BNL'
        if subsystem == 'Integration and Test':
            mirror = 'INT'
        mirror = mirror + '-' + self.mirror

        if self.debug is False:
            for ccd_tup in self.ccd_list:
                ccd = ccd_tup[0]

                f = self.fCCD.find(sensorId=ccd, run=run, testName=defect_name, mirrorName=mirror)
                for g in f:
                    if 'mask' in g and ccd in g:
                        file_list[ccd] = g

        if self.debug is True:
            if run == 9537:
                file_list = {
                    'ITL-3800C-325': "/Users/richard/LSST/Data/ITL-3800C-325/"
                                     "ITL-3800C-325_dark_pixel_mask-9537.fits"}
            else:
                file_list = {
                    'ITL-3800C-325':  "/Users/richard/LSST/Data/ITL-3800C-325/"
                                      "ITL-3800C-325_dark_pixel_mask-10317.fits"}

        return file_list

    def tabulate_defects(self):

        for d in self.defect_list:

            self.current_defect = d

            r1_files = self.get_files_run(run=self.run1, defect_name=d)
            r2_files = self.get_files_run(run=self.run2, defect_name=d)

            for ccd_tup in self.ccd_list:
                ccd = ccd_tup[0]
                self.current_ccd = ccd
                self.current_slot = ccd_tup[1]
                f1 = r1_files[ccd]
                hdu1 = fits.open(f1)
                f2 = r2_files[ccd]
                hdu2 = fits.open(f2)

                print('\n ', f1, '\n', f2)
                comp = self.comp_defects(hdu1=hdu1, hdu2=hdu2)

    def examine_defects(self, ccd, amp):

        self.current_ccd = ccd
        self.amp = amp

        self.current_defect = self.defect_list[0]

        f1 = self.r1_files[ccd]
        hdu1 = fits.open(f1)
        f2 = self.r2_files[ccd]
        hdu2 = fits.open(f2)

        comp = self.comp_defects(hdu1=hdu1, hdu2=hdu2)
        return comp


if __name__ == "__main__":
    ## Command line arguments
    parser = argparse.ArgumentParser(
        description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

    ##   The following are 'convenience options' which could also be specified in the filter string
    parser.add_argument('--run1', default=None, help="(first raft run number (default=%(default)s)")
    parser.add_argument('--run2', default=None, help="(second raft run number (default=%(default)s)")
    parser.add_argument('--defects', default='bright_defects_raft', help="(comma delimited list of defect types (default=%(default)s)")
    parser.add_argument('-m', '--mirror', default='prod', help="mirror BNL-prod, INT-prod ")
    parser.add_argument('--db', default='Prod', help="Prod or Dev eT db ")
    parser.add_argument('--debug', default='no', help="debug flag(default=%(default)s)")
    parser.add_argument('-e', '--eTserver', default='Prod', help="eTraveler server (default=%(default)s)")
    parser.add_argument('--appSuffix', '--appSuffix', default='',
                        help="eTraveler server (default=%(default)s)")
    parser.add_argument('-o', '--output', default='raft_defects.pdf',
                        help="output plot file (default=%(default)s)")
    parser.add_argument('-i', '--infile', default="",
                        help="input file name for list of runs, temps (default=%(default)s)")
    parser.add_argument('-a', '--amp', default=-1, help="optional amp to examine ")
    parser.add_argument('-c', '--ccd', default=None, help="optional CCD to examine ")

    args = parser.parse_args()

    dl = args.defects
    defect_list = dl.split(',')
    if args.debug == 'yes':
        debug = True
    else:
        debug = False

    defects = compare_raft_defects(run1=args.run1, run2=args.run2, defect_list=defect_list, debug=debug,
                                   single_ccd=args.ccd,
                                  mirror=args.mirror, prodServer=args.eTserver, appSuffix=args.appSuffix)

#    tab_defects = defects.tabulate_defects()

    amp_req = int(args.amp)

    with PdfPages(args.output) as pdf:
        for ccd_t in defects.ccd_list:
            if args.ccd is not None and ccd_t[0] != args.ccd:
                continue

            for amp in range(1, 17):
                if amp_req != -1 and amp != amp_req:
                    continue

                ccd = ccd_t[0]

                view_defects = defects.examine_defects(amp=amp,ccd=ccd)
                badc_diff = view_defects[0]
                badc_run1 = view_defects[1]
                badc_run2 = view_defects[2]
    #                print(badc_diff)

                plt.scatter(badc_diff[1],badc_diff[0])
                plt.title('Defect Differences: ' + ccd + ' amp ' + str(amp))
                plt.xlabel('column')
                plt.ylabel('row')
                pdf.savefig()
                plt.close()

                plt.scatter(badc_run1[1], badc_run1[0])
                plt.title('Defect Run ' + args.run1 +  ': ' + ccd + ' amp ' + str(amp))
                plt.xlabel('column')
                plt.ylabel('row')
                pdf.savefig()
                plt.close()

                plt.scatter(badc_run2[1], badc_run2[0])
                plt.title('Defect Run ' + args.run2 + ': ' + ccd + ' amp ' + str(amp))
                plt.xlabel('column')
                plt.ylabel('row')
                pdf.savefig()
                plt.close()

                try:
                    defects.clusters1[ccd][amp]
                    for clus in defects.clusters1[ccd][amp]:
                        pixels = defects.clusters1[ccd][amp][clus]
                        plt.scatter([p[1] for p in pixels], [p[0] for p in pixels])
                        plt.title('Defect Run ' + args.run1 + ': ' + ccd + ' amp ' + str(amp) + " cls " +
                                  str(clus))
                        plt.xlabel('column')
                        plt.ylabel('row')
                        pdf.savefig()
                        plt.close()
                except KeyError:
                    pass

                try:
                    defects.clusters2[ccd][amp]
                    for clus in defects.clusters2[ccd][amp]:
                        pixels = defects.clusters2[ccd][amp][clus]
                        plt.scatter([p[1] for p in pixels], [p[0] for p in pixels])
                        plt.title('Defect Run ' + args.run2 + ': ' + ccd + ' amp ' + str(amp) + " cls " +
                                  str(clus))
                        plt.xlabel('column')
                        plt.ylabel('row')
                        pdf.savefig()
                        plt.close()
                except KeyError:
                    pass
