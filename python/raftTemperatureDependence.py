from  eTraveler.clientAPI.connection import Connection
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import datetime
import collections
import numpy as np

import argparse


def get_results(data=None, step=None, item=None, multiplier=1., org='amp'):
    raft = data['experimentSN']
    run = data['run']
    out = collections.OrderedDict()

    stepDict = data['steps']

    print 'Operating on raft ', raft, ' run', run, ' for step ', item

    for d in stepDict[step]:
        if d <> step:
            continue
        step_info = stepDict[d][step]
        for s in step_info:
            if s['schemaInstance'] == 0: continue
            thing = s[item] * multiplier
            sensor = s['sensor_id']
            ccd = out.setdefault(sensor, {})
            amp = s[org]
            ccd[amp] = thing
        break

    return out


## Command line arguments
parser = argparse.ArgumentParser(
    description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('--run', default=None, help="(raft run number (default=%(default)s)")
parser.add_argument('--temp', default=-85., help="(temperature (default=%(default)s)")
parser.add_argument('-d', '--db', default='Prod', help="database to use (default=%(default)s)")
parser.add_argument('-e', '--eTserver', default='Dev', help="eTraveler server (default=%(default)s)")
parser.add_argument('--appSuffix', '--appSuffix', default='jrb',
                    help="eTraveler server (default=%(default)s)")
parser.add_argument('-o', '--output', default='raft_temp_dependence.pdf',
                    help="output plot file (default=%(default)s)")
parser.add_argument('-i', '--infile', default="",
                    help="input file name for list of wav files (default=%(default)s)")

args = parser.parse_args()

run_list = collections.OrderedDict()
bright_temp = collections.OrderedDict()
bright_cols_temp = collections.OrderedDict()
dark_temp = collections.OrderedDict()
dark_cols_temp = collections.OrderedDict()

if args.infile <> "":
    with open(args.infile) as f:
        for line in f:
            run, temp = line.split()
            run_list[run] = temp
else:
    run_list[args.run] = args.temp

if args.eTserver == 'Prod':
    pS = True
else:
    pS = False

connect = Connection(operator='richard', db=args.db, exp='LSST-CAMERA', prodServer=pS,
                     appSuffix='-' + args.appSuffix)

for r in run_list:

    temp = run_list[r]
    returnData = connect.getRunResults(run=r, stepName='bright_defects_raft')
    brights = get_results(data=returnData, step='bright_defects_raft', item='bright_pixels')
    bright_cols = get_results(data=returnData, step='bright_defects_raft', item='bright_columns',
                              multiplier=2002.)

    returnData = connect.getRunResults(run=r, stepName='dark_defects_raft')
    darks = get_results(data=returnData, step='dark_defects_raft', item='dark_pixels')
    dark_cols = get_results(data=returnData, step='dark_defects_raft', item='dark_columns', multiplier=2002.)

    returnData = connect.getRunResults(run=r, stepName='fe55_raft_analysis')
    gains = get_results(data=returnData, step='fe55_raft_analysis', item='gain')
    psf = get_results(data=returnData, step='fe55_raft_analysis', item='psf_sigma')

    returnData = connect.getRunResults(run=r, stepName='qe_raft_analysis')
    qe = get_results(data=returnData, step='qe_raft_analysis', item='QE', org='band')

    brights_total = 0
    bright_cols_total = 0
    darks_total = 0
    dark_cols_total = 0

    for ccd in brights:
        brights_total += sum(brights[ccd].values())
        bright_cols_total += sum(bright_cols[ccd].values())
        darks_total += sum(darks[ccd].values())
        dark_cols_total += sum(dark_cols[ccd].values())

    bright_temp[temp] = brights_total
    bright_cols_temp[temp] = bright_cols_total
    dark_temp[temp] = darks_total
    dark_cols_temp[temp] = dark_cols_total
    print 'Run ', r, '- Total defects(px): bright pixels ', brights_total, ' bright cols: ', bright_cols_total, ' dark pixels: ', darks_total, ' dark cols: ', dark_cols_total

with PdfPages(args.output) as pdf:
    fig, ax = plt.subplots()

    ax.plot(bright_temp.keys(), np.array(bright_temp.values())/bright_temp['-85.'], label='Bright Pixels')
    ax.plot(bright_cols_temp.keys(), np.array(bright_cols_temp.values()) / bright_cols_temp['-85.'], label='Bright Columns')
    ax.plot(dark_temp.keys(), np.array(dark_temp.values()) / dark_temp['-85.'], label='Dark Pixels')
    ax.plot(dark_cols_temp.keys(), np.array(dark_cols_temp.values()) / dark_cols_temp['-85.'], label='Dark Columns')
    plt.legend(loc='upper left')
    plt.xlabel('Temperature (C)')
    plt.ylabel('Normalize to -85C')
    plt.tight_layout()

    pdf.savefig()
    plt.close()
