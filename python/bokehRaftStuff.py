from exploreRaft import exploreRaft
from  get_EO_analysis_results import get_EO_analysis_results
from bokeh.plotting import figure, output_file, show
from bokeh.layouts import gridplot, layout
from bokeh.models import ColumnDataSource
from bokeh.layouts import widgetbox
from bokeh.models.widgets import Panel, Tabs, PreText
import argparse


## Command line arguments
parser = argparse.ArgumentParser(description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

##   The following are 'convenience options' which could also be specified in the filter string
parser.add_argument('--run', default=None,help="(raft run number (default=%(default)s)")
parser.add_argument('-d','--db',default='Prod',help="database to use (default=%(default)s)")
parser.add_argument('-e','--eTserver',default='Dev',help="eTraveler server (default=%(default)s)")
parser.add_argument('-t','--test_type',default=None,help="test type (default=%((default)s)"                                                                     "default)s)")
parser.add_argument('-s','--site_type',default=None,help="site type (default=%((default)s)"                                                                     "default)s)")
parser.add_argument('-o','--output',default='raft_stuff.html',help="output html file (default=%(default)s)")

args = parser.parse_args()

eR = exploreRaft(db=args.db, prodServer=args.eTserver)
run_num = args.run

g = get_EO_analysis_results(db=args.db, server=args.eTserver)

raft_list, data = g.get_tests(site_type=args.site_type, test_type=args.test_type, run=args.run)
res = g.get_results(test_type=args.test_type, data=data, device=raft_list)

raft_list_ptc, data_ptc = g.get_tests(site_type=args.site_type, test_type="ptc_gain", run=args.run)
res_ptc_gain = g.get_results(test_type='ptc_gain', data=data_ptc, device=raft_list)

raft_list_psf, data_psf = g.get_tests(site_type=args.site_type, test_type="psf_sigma", run=args.run)
res_psf = g.get_results(test_type='psf_sigma', data=data_psf, device=raft_list)

raft_list_rn, data_rn = g.get_tests(site_type=args.site_type, test_type="read_noise", run=args.run)
res_rn = g.get_results(test_type='read_noise', data=data_rn, device=raft_list)

raft_list_cti_low_serial, data_cls = g.get_tests(site_type=args.site_type, test_type="cti_low_serial",
                                                run=args.run)
res_cls = g.get_results(test_type='cti_low_serial', data=data_cls, device=raft_list)
raft_list_cti_high_serial, data_chs = g.get_tests(site_type=args.site_type, test_type="cti_high_serial",
                                                run=args.run)
res_chs = g.get_results(test_type='cti_high_serial', data=data_chs, device=raft_list)

raft_list_cti_low_parallel, data_clp = g.get_tests(site_type=args.site_type, test_type="cti_low_parallel",
                                                run=args.run)
res_clp = g.get_results(test_type='cti_low_parallel', data=data_clp, device=raft_list)

raft_list_cti_high_parallel, data_chp = g.get_tests(site_type=args.site_type, test_type="cti_high_parallel",
                                                run=args.run)
res_chp = g.get_results(test_type='cti_high_parallel', data=data_chp, device=raft_list)

test_list = []
test_list_ptc = []
test_list_psf = []
test_list_rn = []
test_list_cls = []
test_list_chs = []
test_list_clp = []
test_list_chp = []

for ccd in res:
    test_list.extend(res[ccd])
    test_list_ptc.extend(res_ptc_gain[ccd])
    test_list_psf.extend(res_psf[ccd])
    test_list_rn.extend(res_rn[ccd])
    test_list_cls.extend(res_cls[ccd])
    test_list_chs.extend(res_chs[ccd])
    test_list_clp.extend(res_clp[ccd])
    test_list_chp.extend(res_chp[ccd])

# NEW: create a column data source for the plots to share
source = ColumnDataSource(data=dict(x=range(0,len(test_list)), gain=test_list, ptc=test_list_ptc,
                                    psf=test_list_psf, rn=test_list_rn))

TOOLS = "pan,wheel_zoom,box_zoom,reset,save,box_select,lasso_select"

# create a new plot with a title and axis labels
p = figure(tools=TOOLS, title="gains", x_axis_label='amp', y_axis_label='gain')
ptc = figure(tools=TOOLS, title="ptc gains", x_axis_label='amp', y_axis_label='gain')
psf = figure(tools=TOOLS, title="psf", x_axis_label='amp', y_axis_label='psf')
rn = figure(tools=TOOLS, title="Read noise", x_axis_label='amp', y_axis_label='Noise')
cls = figure(tools=TOOLS, title="CTI low serial", x_axis_label='amp', y_axis_label='CTI')
chs = figure(tools=TOOLS, title="CTI high serial", x_axis_label='amp', y_axis_label='CTI')
clp = figure(tools=TOOLS, title="CTI low parallel", x_axis_label='amp', y_axis_label='CTI')
chp = figure(tools=TOOLS, title="CTI high parallel", x_axis_label='amp', y_axis_label='CTI')

# add a line renderer with legend and line thickness
p.circle('x', 'gain', source=source, legend="Gain: Run " + run_num, line_width=2)
ptc.circle('x','ptc', source=source, legend="ptc Gain: Run " + run_num, line_width=2)
psf.circle('x','psf', source=source, legend="PSF: Run " + run_num, line_width=2)
rn.circle('x','rn', source=source, legend="Read Noise: Run " + run_num, line_width=2)

cls.circle('x','rn', source=source, legend="CTI low serial: Run " + run_num, line_width=2)
chs.circle('x','rn', source=source, legend="CTI high serial: Run " + run_num, line_width=2)
clp.circle('x','rn', source=source, legend="CTI low parallel: Run " + run_num, line_width=2)
chp.circle('x','rn', source=source, legend="CTI high parallel: Run " + run_num, line_width=2)

# NEW: put the subplots in a gridplot
grid = gridplot([[p, ptc], [psf, rn]])
grid_cti = gridplot([[cls, chs], [clp, chp]])

raft_text = "Plots for I&T Raft run " + run_num + " " + raft_list

pre = PreText(text=raft_text, width=500, height=100)

tab1 = Panel(child=grid, title="Gains, PSF, Noise")
tab2 = Panel(child=grid_cti, title="CTI")

tabs = Tabs(tabs=[ tab1, tab2 ])

l= layout([widgetbox(pre), tabs])
show(l)