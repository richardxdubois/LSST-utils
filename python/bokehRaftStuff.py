from exploreRaft import exploreRaft
from get_EO_analysis_results import get_EO_analysis_results
from bokeh.plotting import figure, output_file, show, save
from bokeh.layouts import gridplot, layout
from bokeh.models import ColumnDataSource
from bokeh.layouts import widgetbox
from bokeh.models.widgets import Panel, Tabs, PreText, DataTable, TableColumn, HTMLTemplateFormatter
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

raft_list_dark_pixels, data_dp = g.get_tests(site_type=args.site_type, test_type="dark_pixels",
                                                run=args.run)
res_dp = g.get_results(test_type='dark_pixels', data=data_dp, device=raft_list)

raft_list_dark_columns, data_dc = g.get_tests(site_type=args.site_type, test_type="dark_columns",
                                                run=args.run)
res_dc = g.get_results(test_type='dark_columns', data=data_dc, device=raft_list)

raft_list_bright_pixels, data_bp = g.get_tests(site_type=args.site_type, test_type="bright_pixels",
                                                run=args.run)
res_bp = g.get_results(test_type='bright_pixels', data=data_bp, device=raft_list)

raft_list_bright_columns, data_bc = g.get_tests(site_type=args.site_type, test_type="bright_columns",
                                                run=args.run)
res_bc = g.get_results(test_type='bright_columns', data=data_bc, device=raft_list)

test_list = []
test_list_ptc = []
test_list_psf = []
test_list_rn = []

test_list_cls = []
test_list_chs = []
test_list_clp = []
test_list_chp = []

test_list_dp = []
test_list_dc = []
test_list_bp = []
test_list_bc = []

for ccd in res:
    test_list.extend(res[ccd])
    test_list_ptc.extend(res_ptc_gain[ccd])
    test_list_psf.extend(res_psf[ccd])
    test_list_rn.extend(res_rn[ccd])

    test_list_cls.extend(res_cls[ccd])
    test_list_chs.extend(res_chs[ccd])
    test_list_clp.extend(res_clp[ccd])
    test_list_chp.extend(res_chp[ccd])

    test_list_bp.extend(res_bp[ccd])
    test_list_bc.extend(res_bc[ccd])
    test_list_dp.extend(res_dp[ccd])
    test_list_dc.extend(res_dc[ccd])



# NEW: create a column data source for the plots to share
source = ColumnDataSource(data=dict(x=range(0,len(test_list)), gain=test_list, ptc=test_list_ptc,
                        psf=test_list_psf, rn=test_list_rn, cls=test_list_cls,
                        chs=test_list_chs, clp=test_list_clp, chp=test_list_chp,
                        bp=test_list_bp, bc=test_list_bc, dp=test_list_dp, dc=test_list_dc))

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

bp = figure(tools=TOOLS, title="Bright Pixels", x_axis_label='amp', y_axis_label='Bright Pixels')
bc = figure(tools=TOOLS, title="Bright Columns", x_axis_label='amp', y_axis_label='Bright Columns')
dp = figure(tools=TOOLS, title="Dark Pixels", x_axis_label='amp', y_axis_label='Dark Pixels')
dc = figure(tools=TOOLS, title="Dark Columns", x_axis_label='amp', y_axis_label='Dark Columns')


# add a line renderer with legend and line thickness
p.circle('x', 'gain', source=source, legend="Gain: Run " + run_num, line_width=2)
ptc.circle('x','ptc', source=source, legend="ptc Gain: Run " + run_num, line_width=2)
psf.circle('x','psf', source=source, legend="PSF: Run " + run_num, line_width=2)
rn.circle('x','rn', source=source, legend="Read Noise: Run " + run_num, line_width=2)

cls.circle('x','cls', source=source, legend="CTI low serial: Run " + run_num, line_width=2)
chs.circle('x','chs', source=source, legend="CTI high serial: Run " + run_num, line_width=2)
clp.circle('x','clp', source=source, legend="CTI low parallel: Run " + run_num, line_width=2)
chp.circle('x','chp', source=source, legend="CTI high parallel: Run " + run_num, line_width=2)

bp.circle('x','bp', source=source, legend="Bright Pixels: Run " + run_num, line_width=2)
bc.circle('x','bc', source=source, legend="Bright Columns: Run " + run_num, line_width=2)
dp.circle('x','dp', source=source, legend="Dark Pixels: Run " + run_num, line_width=2)
dc.circle('x','dc', source=source, legend="Dark Columns: Run " + run_num, line_width=2)


# NEW: put the subplots in a gridplot
grid = gridplot([[p, ptc], [psf, rn]])
grid_cti = gridplot([[cls, chs], [clp, chp]])
grid_def = gridplot([[bp, bc], [dp, dc]])

raft_text = "Plots for I&T Raft run " + run_num + " " + raft_list

pre = PreText(text=raft_text, width=500, height=100)

tab1 = Panel(child=grid, title="Gains, PSF, Noise")
tab2 = Panel(child=grid_cti, title="CTI")
tab3 = Panel(child=grid_def, title="Defects")

tabs = Tabs(tabs=[ tab1, tab2, tab3 ])

l= layout([widgetbox(pre), tabs])

output_file('bokehRaftStuff.html')
save(l)

data = dict(
        rafts=['LCA-11021_RTM-010-Dev', 'LCA-11021_RTM-003_ETU2' ],
        runs=['<a href="http://slac.stanford.edu/~richard/LSST/bokehRaftStuff-6006D-RTM-010.html">6006D</a>',
              '<a href="http://slac.stanford.edu/~richard/LSST/bokehRaftStuff-5731-ETU2.html">5731</a>']
    )
dashboard = ColumnDataSource(data)

columns = [
        TableColumn(field="rafts", title="Raft"),
        TableColumn(field="runs", title="Run", formatter=HTMLTemplateFormatter())
    ]
data_table = DataTable(source=dashboard, columns=columns, width=400, height=280)

output_file('bokehDashboard.html')
show(data_table)