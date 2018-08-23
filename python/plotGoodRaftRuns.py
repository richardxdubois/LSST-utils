from get_EO_analysis_results import get_EO_analysis_results
from bokeh.plotting import figure, output_file, show, save
from bokeh.layouts import gridplot, layout
from bokeh.models import ColumnDataSource
from bokeh.layouts import widgetbox
from bokeh.models.widgets import Panel, Tabs, PreText, DataTable, TableColumn, HTMLTemplateFormatter
from  eTraveler.clientAPI.connection import Connection
import argparse

class plotGoodRaftRuns():

    def __init__(self, db='Prod', server='Prod', base_dir=None):

        self.traveler_name = {}
        self.test_type = "fe55_raft_analysis"
        self.traveler_name['I&T-Raft'] = 'INT-SR-EOT-01'
        self.traveler_name['BNL-Raft'] = 'SR-RTM-EOT-03'
        self.base_dir = base_dir
        self.db = db
        self.server = server

        if server == 'Prod':
            pS = True
        else:
            pS = False
        self.connect = Connection(operator='richard', db=db, exp='LSST-CAMERA', prodServer=pS)


    def find_runs(self,site_type=None, runs=None):

         #data = self.connect.getResultsJH(htype="LCA-11021_RTM",
         #                                stepName=self.test_type,
         #                                travelerName=self.traveler_name)

        if runs is not None:
            runs = runs

        return runs

    def make_run_pages(self, site_type=None, runs=None):

        run_list = self.find_runs(site_type=site_type, runs=runs)
        raft_list = []

        for run in run_list:
            data = self.connect.getRunResults(run=run)
            raft = data["experimentSN"]
            raft_list.append(raft)
            self.write_run_plot(run=run, site_type=site_type, raft=raft)

        return run_list, raft_list



    def write_run_plot(self, run=None, site_type=None, raft=None):

        g = get_EO_analysis_results(db=self.db, server=self.server)

        raft_list, data = g.get_tests(site_type=site_type, test_type="gain", run=run)
        res = g.get_results(test_type="gain", data=data, device=raft)

        raft_list_ptc, data_ptc = g.get_tests(site_type=site_type, test_type="ptc_gain", run=run)
        res_ptc_gain = g.get_results(test_type='ptc_gain', data=data_ptc, device=raft)

        raft_list_psf, data_psf = g.get_tests(site_type=site_type, test_type="psf_sigma", run=run)
        res_psf = g.get_results(test_type='psf_sigma', data=data_psf, device=raft)

        raft_list_rn, data_rn = g.get_tests(site_type=site_type, test_type="read_noise", run=run)
        res_rn = g.get_results(test_type='read_noise', data=data_rn, device=raft)

        raft_list_cti_low_serial, data_cls = g.get_tests(site_type=site_type, test_type="cti_low_serial",
                                                        run=run)
        res_cls = g.get_results(test_type='cti_low_serial', data=data_cls, device=raft)
        raft_list_cti_high_serial, data_chs = g.get_tests(site_type=site_type,
                                                          test_type="cti_high_serial",
                                                        run=run)
        res_chs = g.get_results(test_type='cti_high_serial', data=data_chs, device=raft)

        raft_list_cti_low_parallel, data_clp = g.get_tests(site_type=site_type,
                                                           test_type="cti_low_parallel",
                                                        run=run)
        res_clp = g.get_results(test_type='cti_low_parallel', data=data_clp, device=raft)

        raft_list_cti_high_parallel, data_chp = g.get_tests(site_type=site_type,
                                                            test_type="cti_high_parallel",
                                                        run=run)
        res_chp = g.get_results(test_type='cti_high_parallel', data=data_chp, device=raft)

        raft_list_dark_pixels, data_dp = g.get_tests(site_type=site_type, test_type="dark_pixels",
                                                        run=run)
        res_dp = g.get_results(test_type='dark_pixels', data=data_dp, device=raft)

        raft_list_dark_columns, data_dc = g.get_tests(site_type=site_type, test_type="dark_columns",
                                                        run=run)
        res_dc = g.get_results(test_type='dark_columns', data=data_dc, device=raft)

        raft_list_bright_pixels, data_bp = g.get_tests(site_type=site_type, test_type="bright_pixels",
                                                        run=run)
        res_bp = g.get_results(test_type='bright_pixels', data=data_bp, device=raft)

        raft_list_bright_columns, data_bc = g.get_tests(site_type=site_type, test_type="bright_columns",
                                                        run=run)
        res_bc = g.get_results(test_type='bright_columns', data=data_bc, device=raft)

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
        p.circle('x', 'gain', source=source, legend="Gain: Run " + str(run), line_width=2)
        ptc.circle('x','ptc', source=source, legend="ptc Gain: Run " + str(run), line_width=2)
        psf.circle('x','psf', source=source, legend="PSF: Run " + str(run), line_width=2)
        rn.circle('x','rn', source=source, legend="Read Noise: Run " + str(run), line_width=2)

        cls.circle('x','cls', source=source, legend="CTI low serial: Run " + str(run), line_width=2)
        chs.circle('x','chs', source=source, legend="CTI high serial: Run " + str(run), line_width=2)
        clp.circle('x','clp', source=source, legend="CTI low parallel: Run " + str(run), line_width=2)
        chp.circle('x','chp', source=source, legend="CTI high parallel: Run " + str(run), line_width=2)

        bp.circle('x','bp', source=source, legend="Bright Pixels: Run " + str(run), line_width=2)
        bc.circle('x','bc', source=source, legend="Bright Columns: Run " + str(run), line_width=2)
        dp.circle('x','dp', source=source, legend="Dark Pixels: Run " + str(run), line_width=2)
        dc.circle('x','dc', source=source, legend="Dark Columns: Run " + str(run), line_width=2)


        # NEW: put the subplots in a gridplot
        grid = gridplot([[p, ptc], [psf, rn]])
        grid_cti = gridplot([[cls, chs], [clp, chp]])
        grid_def = gridplot([[bp, bc], [dp, dc]])

        raft_text = "Plots for I&T Raft run " + str(run) + " " + raft

        pre = PreText(text=raft_text, width=500, height=100)

        tab1 = Panel(child=grid, title="Gains, PSF, Noise")
        tab2 = Panel(child=grid_cti, title="CTI")
        tab3 = Panel(child=grid_def, title="Defects")

        tabs = Tabs(tabs=[ tab1, tab2, tab3 ])

        l= layout([widgetbox(pre), tabs])

        o_file = self.base_dir + raft + "-" + str(run) + ".html"
        output_file(o_file)
        save(l)


    def write_table(self, run_list=None, raft_list=None):

        data = dict(
                rafts=raft_list,
                runs=run_list
                )
        dashboard = ColumnDataSource(data)

        columns = [
            TableColumn(field="rafts", title="Raft"),
            TableColumn(field="runs", title="Run", formatter=
                HTMLTemplateFormatter(template=
                "<a href= \
                'http://slac.stanford.edu/~richard/LSST/<%= rafts %>-<%= runs %>.html' \
                ><%= runs %></a>"))
        ]
        data_table = DataTable(source=dashboard, columns=columns, width=400, height=280)

        return data_table

if __name__ == "__main__":

    ## Command line arguments
    parser = argparse.ArgumentParser(
        description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

    ##   The following are 'convenience options' which could also be specified in the filter string
    parser.add_argument('--run', default=None, help="(raft run number (default=%(default)s)")
    parser.add_argument('-d', '--db', default='Prod', help="database to use (default=%(default)s)")
    parser.add_argument('-e', '--eTserver', default='Dev', help="eTraveler server (default=%(default)s)")
    parser.add_argument('-s', '--site_type', default=None,
                        help="site type (default=%((default)s)"                                                                     "default)s)")
    parser.add_argument('-o', '--output', default='/Users/richard/LSST/Data/bokeh/',
                        help="output base directory (default=%(default)s)")

    args = parser.parse_args()

    pG = plotGoodRaftRuns(db='Prod', server='Prod', base_dir=args.output)

    runs_bnl = [4418, 5761, 6147, 7660]
    run_list, raft_list = pG.make_run_pages(site_type="BNL-Raft", runs=runs_bnl)

    data_table_bnl = pG.write_table(run_list=run_list, raft_list=raft_list)

    runs_int = [5582, 5730, 5731, 6259, 7046, 7086 ]
    run_list, raft_list = pG.make_run_pages(site_type="I&T-Raft", runs=runs_int)

    data_table_int = pG.write_table(run_list=run_list, raft_list=raft_list)

    pG_dev = plotGoodRaftRuns(db='Dev', server='Prod', base_dir=args.output)

    runs_int_dev = [5708, 5715, 5867, 5899, 5923, 5941, 5943, 6006 ]
    run_list, raft_list = pG_dev.make_run_pages(site_type="I&T-Raft", runs=runs_int_dev)

    data_table_int_dev = pG_dev.write_table(run_list=run_list, raft_list=raft_list)

    dash_file = args.output + 'bokehDashboard.html'
    output_file(dash_file)

    intro_text = "EO Test Results for Good Raft Runs"
    pre_intro = PreText(text=intro_text, width=500, height=10)


    type_text = "BNL-Raft"
    pre = PreText(text=type_text, width=500, height=10)
    l = layout(pre_intro, pre, data_table_bnl)

    type_int = "I&T-Raft (Prod)"
    pre_int = PreText(text=type_int, width=500, height=10)
    l_int= layout(pre_int, data_table_int)

    type_int_dev = "I&T-Raft (Dev)"
    pre_int_dev = PreText(text=type_int_dev, width=500, height=10)
    l_int_dev= layout(pre_int_dev, data_table_int_dev)

    p = layout(l, [l_int, l_int_dev])

    save(p)
