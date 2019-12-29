from __future__ import print_function
from get_EO_analysis_results import get_EO_analysis_results
from exploreRaft import exploreRaft
from scipy import stats
from scipy.interpolate import interp1d
from scipy import optimize
import numpy as np
import pandas as pd
import argparse
from statistics import median

from bokeh.models import ColumnDataSource
from bokeh.plotting import figure, output_file, reset_output, show, save, curdoc
from bokeh.layouts import row, layout
from bokeh.models import Span, Label
from bokeh.models.widgets import DataTable, TableColumn, NumberFormatter
parser = argparse.ArgumentParser(
    description='Create heatmap of Camera EO test data quantities.')

parser.add_argument('-t', '--test', default="read_noise", help="test quantity to display")
parser.add_argument('-m', '--max', default=1.e10, help="max test value to use")
parser.add_argument('-n', '--min', default=0., help="min test value to use")
parser.add_argument('-r', '--run', default=None, help="run number")
parser.add_argument('--obj', default=9., help="Objective  value")
parser.add_argument('--thr', default=13., help="Threshold value")
parser.add_argument('-d', '--db', default="Prod", help="eT database")
parser.add_argument('-o', '--output', default="cumulative.html", help="output html filespec")

args = parser.parse_args()

g = get_EO_analysis_results(db=args.db)
r = exploreRaft()

TOOLS = "pan,wheel_zoom,box_zoom,reset,save,box_select,lasso_select"

test_list = []
bad_pixels = []
weights = []
pix_count = 0
pix_count_corr = 0

ITL_test_list = []
e2v_test_list = []

raft_name = []
raft_type = []
raft_run = []
raft_median_test = []
raft_min_test = []
raft_max_test = []
raft_bad = []

raft_weight = []

pix_amp_ITL = 2000. * 509. * 1.e-9
pix_amp_e2v = 2002. * 512. * 1.e-9

if args.run is not None:

    raft_list, data = g.get_tests(test_type=args.test, run=args.run)
    res = g.get_results(test_type=args.test, data=data, device=raft_list)

    for raft in res[args.test]:
        print("Processing raft ", raft)
        for ccd in res[args.test][raft]:
            amp_tests = res[args.test][raft][ccd]
            test_list.extend(amp_tests)
            pix_count += len(amp_tests)

else:

#    runs_list = [10517, 10861]

    runs_list = [10517, 10861, 10669, 10928, 11063, 10722, 11351, 11415, 10982, 11903, 11166, 12027,
                11808, 11852, 11746, 12008, 11952, 11671, 12086, 12130, 12139, "6611D", 10909, 11128, 11260]

    g = get_EO_analysis_results(db=args.db)

    for run in runs_list:

        raft_list, data = g.get_tests(run=run)
        res = g.get_all_results(data=data, device=raft_list)

        pix_per_amp = pix_amp_e2v

        r_type = r.raft_type(raft=raft_list)
        e2v = True
        if "CRTM" in raft_list or r_type == "ITL":
            pix_per_amp = pix_amp_ITL
            e2v = False

        print("Processing raft ", raft_list)

        raft_test_list = []
        raft_bad_pixels = []

        for ccd in res[args.test]:
            amp_tests = res[args.test][ccd]
            raft_test_list.extend(amp_tests)
            pix_count += len(amp_tests) * pix_per_amp

            # get bad pixel counts

            dkp = res["dark_pixels"][ccd]
            dkpc = np.array(res["dark_columns"][ccd])*2000.
            brp = res["bright_pixels"][ccd]
            brpc = np.array(res["bright_columns"][ccd])*2000.
            raft_bad_pixels.extend(dkp + dkpc + brp + brpc)

        bad_pixels.extend(raft_bad_pixels)
        test_list.extend(raft_test_list)
        pix_count_corr = pix_count - sum(raft_bad_pixels)

        # gather up per raft info
        raft_name.append(raft_list)
        raft_run.append(run)
        raft_bad.append(sum(raft_bad_pixels))
        raft_median_test.append(median(raft_test_list))
        raft_min_test.append(min(raft_test_list))
        raft_max_test.append(max(raft_test_list))

        raft_weight = (1.-np.array(raft_bad_pixels)*1.e-9/pix_per_amp)
        weights.extend(raft_weight)

        if e2v:
            e2v_test_list.extend(raft_test_list)
            raft_type.append("e2v")
        else:
            ITL_test_list.extend(raft_test_list)
            raft_type.append("ITL")

num_bad = sum(bad_pixels)*1.e-9
final_pix_count = pix_count - num_bad

print("len(test_list) = ", len(test_list), " for ", pix_count, " Gpixels and ", num_bad, " bad Gpixels" )
numbins = 50
min_t = max(float(args.min), min(test_list))
max_t = min(max(test_list), float(args.max))

# pixels per amp: for e2v it is 2002x512 and for ITL it is 2000x509
# So 4004x4096 for e2v and 4000x4072 for ITL, for the entire CCD

cumul = stats.cumfreq(np.array(test_list), numbins=numbins, weights=weights, defaultreallimits=(min_t, max_t))
norm_cum = cumul.cumcount/cumul.cumcount[-1]*final_pix_count

bins = [cumul.lowerlimit + i*cumul.binsize for i in range(numbins+1)]
bins_interp = bins[:-1] + cumul.binsize/2.

obj = np.digitize(float(args.obj), bins)
obj_val = norm_cum[obj]

thr = np.digitize(float(args.thr), bins)
thr_val = norm_cum[thr]

full_pixels = pix_count
half_pixels = full_pixels*0.5
pixels_95 = full_pixels*0.95
pixels_75 = full_pixels*0.75



f2 = interp1d(bins_interp, norm_cum, kind='cubic')
f2_inv_half = lambda x: f2(x) - half_pixels
half = optimize.newton(f2_inv_half, 5.)

f2_inv_75 = lambda x: f2(x) - pixels_75
obj_interp = optimize.newton(f2_inv_75, 5.5)

f2_inv_95 = lambda x: f2(x) - pixels_95
thr_interp = optimize.newton(f2_inv_95, 6.5)

print("binned obj, thr ", f'{obj_val:6.2f}', f'{thr_val:6.2f}',
      " interp obj, thr ", f'{obj_interp:6.2f}',
      f'{thr_interp:6.2f}')
print("noise = ", f'{half:6.2f}', " for ", f'{half_pixels:6.2f}', " Gpixels")

histsource = ColumnDataSource(pd.DataFrame(dict(top=norm_cum, left=bins[:-1], right=bins[1:])))
# Using numpy to get the index of the bins to which the value is assigned
h = figure(title=args.test, tools=TOOLS, toolbar_location="below")
h.quad(source=histsource, top='top', bottom=0, left='left', right='right', fill_color='blue',
       fill_alpha=0.2)

h.line(x=bins_interp, y=f2(bins_interp), line_color="black")

thr_line = Span(location=float(pixels_95), dimension="width", line_color="blue")
h.add_layout(thr_line)
thr_label = Label(x=0, y=float(pixels_95), text='Thrsh (95%)', text_color="blue")
h.add_layout(thr_label)

obj_line = Span(location=float(pixels_75), dimension="width", line_color="red")
h.add_layout(obj_line)
obj_label = Label(x=0, y=float(pixels_75), text='Obj (75%)', text_color="red")
h.add_layout(obj_label)

# Low is 1/2 nominal pixel count
low_line = Span(location=half_pixels, dimension="width", line_color="green")
h.add_layout(low_line)
low_label = Label(x=0, y=half_pixels, text='Low (50%)', text_color="green")
h.add_layout(low_label)

h.xaxis.axis_label = args.test
h.yaxis.axis_label = "pixels (GPx)"

# histograms: all, ITL, e2v

np_array = np.array(test_list)
selected_q = [q for q in np_array if float(args.min) <= q < float(args.max)]
h_q, bins = np.histogram(selected_q, bins=50)
histsource = ColumnDataSource(pd.DataFrame(dict(top=h_q, left=bins[:-1], right=bins[1:])))
# Using numpy to get the index of the bins to which the value is assigned
h_hist = figure(title="Read Noise", tools=TOOLS, toolbar_location="below")
h_hist.quad(source=histsource, top='top', bottom=0, left='left', right='right', fill_color='blue',
       fill_alpha=0.2)

ITL_array = np.array(ITL_test_list)
ITL_selected_q = [q for q in ITL_array if float(args.min) <= q < float(args.max)]
ITL_h_q, ITL_bins = np.histogram(ITL_selected_q, bins=50)
ITL_histsource = ColumnDataSource(pd.DataFrame(dict(top=ITL_h_q, left=ITL_bins[:-1], right=ITL_bins[1:])))
# Using numpy to get the index of the bins to which the value is assigned
ITL_h_hist = figure(title="ITL Read Noise", tools=TOOLS, toolbar_location="below")
ITL_h_hist.quad(source=ITL_histsource, top='top', bottom=0, left='left', right='right', fill_color='blue',
       fill_alpha=0.2)

e2v_array = np.array(e2v_test_list)
e2v_selected_q = [q for q in e2v_array if float(args.min) <= q < float(args.max)]
e2v_h_q, e2v_bins = np.histogram(e2v_selected_q, bins=ITL_bins)
e2v_histsource = ColumnDataSource(pd.DataFrame(dict(top=e2v_h_q, left=e2v_bins[:-1], right=e2v_bins[1:])))
# Using numpy to get the index of the bins to which the value is assigned
e2v_h_hist = figure(title="e2v Read Noise", tools=TOOLS, toolbar_location="below")
e2v_h_hist.quad(source=e2v_histsource, top='top', bottom=0, left='left', right='right', fill_color='blue',
       fill_alpha=0.2)

# tabulate different thresholds

descr = ["Threshold KPP (95%)", "Objective KPP (75%)", "Low bin (50%)"]
threshs = [pixels_95, pixels_75, half_pixels]
vals = [thr_interp, obj_interp, half]

columns = [
    TableColumn(field="descr", title="Threshold type"),
    TableColumn(field="threshs", title="threshold (GPx)", formatter=NumberFormatter(format='0.00')),
    TableColumn(field="vals", title="Read Noise (e-)", formatter=NumberFormatter(format='0.00'))
]
threshold_dict = dict(descr=descr, threshs=threshs, vals=vals)

thr_table = ColumnDataSource(threshold_dict)
thr_dt = DataTable(source=thr_table, columns=columns, width=900, height=150)

# tabulate per raft info

raft_columns = [
    TableColumn(field="name", title="Raft", width=350),
    TableColumn(field="type", title="Raft type"),
    TableColumn(field="run", title="Ref run"),
    TableColumn(field="badp", title="Bad Pixels"),
    TableColumn(field="median", title="Median noise", formatter=NumberFormatter(format='0.00')),
    TableColumn(field="min", title="min noise", formatter=NumberFormatter(format='0.00')),
    TableColumn(field="max", title="max noise", formatter=NumberFormatter(format='0.00'))
    ]

raft_props_dict = dict(name=raft_name, type=raft_type, run=raft_run, badp=raft_bad, median=raft_median_test,
                       min=raft_min_test, max=raft_max_test)
raft_props_table = ColumnDataSource(raft_props_dict)
raft_props_dt = DataTable(source=raft_props_table, columns=raft_columns, height=750, width=900)

plot_layout = layout(row(h, h_hist), thr_dt, raft_props_dt, row(e2v_h_hist, ITL_h_hist))

output_file(args.output)

if args.run is None:
    title_txt = "TS8 Good Runs " + args.test + " Cumulative Distribution"
else:
    title_txt = "Run " + args.run + " " + args.test + " Cumulative Distribution"

save(plot_layout, title=title_txt)
