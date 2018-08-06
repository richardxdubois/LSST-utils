"""Script to collect information about defects and CTI for individual ITL
sensors and use a metric to assign a score to sensors and rank them."""

from  eTraveler.clientAPI.connection import Connection
from exploreRaft import exploreRaft
import matplotlib.pyplot as plt
from get_EO_analysis_results import get_EO_analysis_results
import numpy as np


import argparse


if __name__ == "__main__":

    ## Command line arguments
    parser = argparse.ArgumentParser(
        description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

    ##   The following are 'convenience options' which could also be specified in the filter string
    #parser.add_argument('-t', '--htype', default=None, help="hardware type (default=%(default)s)") #ITL-CCD
    parser.add_argument('-d', '--db', default='Prod', help="eT database (default=%(default)s)")
    parser.add_argument('-e', '--eTserver', default='Dev', help="eTraveler server (default=%(default)s)")
    parser.add_argument('--appSuffix', '--appSuffix', default='jrb',
                        help="eTraveler server (default=%(default)s)")
    args = parser.parse_args()

    g = get_EO_analysis_results()
    raft_list, data = g.get_tests(site_type="BNL-Raft", test_type="gain")

    eR = exploreRaft()

    all_gains = []
    all_gains_ITL = []
    all_gains_e2v = []
    all_gains_ETU2 = []
    itl_sub_list = []

    for raft in raft_list:
        bnl_gains = g.get_results(test_type='gain', device=raft, data=data)
        for ccd in bnl_gains:
            gains=bnl_gains[ccd]
            if 'ETU1' in raft:
                continue
            if 'ETU2' in raft:
                all_gains_ETU2 += gains
                continue
            all_gains += gains
            if eR.raft_type(raft=raft) == 'ITL':
                all_gains_ITL += gains
                aspic0 = np.median(np.array(gains[0:8]))
                aspic1 = np.median(np.array(gains[8:16]))
                aspic0_list = [x - aspic0 for x in gains[0:8]]
                aspic1_list = [x - aspic1 for x in gains[8:16]]
                itl_sub_list += aspic0_list
                itl_sub_list += aspic1_list
                print raft, ccd, aspic0, aspic1
            else:
                all_gains_e2v += gains

    f, ax = plt.subplots(nrows=2,ncols=2, sharex=True)
    plt.xlabel('Gains')
    plt.xlim(0.5,1.2)
    plt.title('Gains - BNL Raft tests')
    ax[0,0].hist(all_gains,50)
    ax[0,0].set_title("All")
    ax[0,1].hist(all_gains_ETU2,50)
    ax[0,1].set_title("ETU2 - ITL")
    ax[1,0].set_title("e2v")
    ax[1,0].hist(all_gains_e2v,50)
    ax[1,1].set_title("ITL")
    ax[1,1].hist(all_gains_ITL,50)
    plt.close()

    plt.hist(itl_sub_list, 200)
    plt.xlabel('Median Subtracted Gains')
    plt.xlim(-0.15,0.15)
    plt.title('ITL ASPIC Gains - BNL Raft tests')
    plt.close()


    raft_list_INT, data_int = g.get_tests(site_type="I&T-Raft", test_type="gain")

    gains_ratio_list = []
    gains_int_list = []
    gains_bnl_list = []

    for raft in raft_list_INT:
        if eR.raft_type(raft=raft) == 'ITL':
            continue

        if 'ETU' in raft:
            continue

        int_gains = g.get_results(test_type='gain', device=raft, data=data_int)
        bnl_gains = g.get_results(test_type='gain', device=raft, data=data)

        for ccd in int_gains:
            gains_int = int_gains[ccd]
            gains_int_list += gains_int
            gains_bnl = bnl_gains[ccd]
            gains_bnl_list += gains_bnl

    gains_ratio = np.array(gains_int_list)/np.array(gains_bnl_list)



    plt.hist(gains_ratio)
    plt.xlabel('Gain Ratio')
    plt.title('Gain Ratio - I&T/BNL Gains')
    plt.close()


