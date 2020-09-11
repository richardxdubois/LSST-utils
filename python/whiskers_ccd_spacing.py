import argparse
import numpy as np
from scipy import stats
from ccd_spacing import ccd_spacing

from bokeh.plotting import figure, curdoc, output_file, save
from bokeh.palettes import Viridis256 as palette #@UnresolvedImport
from bokeh.layouts import row, column, layout, gridplot
from bokeh.models.widgets import TextInput, Dropdown, Button, Slider, FileInput
from bokeh.models import CustomJS, ColumnDataSource, Legend, LinearColorMapper, ColorBar, LogColorMapper, Arrow, \
    NormalHead, TickFormatter


print("in main")

parser = argparse.ArgumentParser(
    description='Examine CCD spot images to look at spacing')

# The following are 'convenience options' which could also be specified in
# the filter string
parser.add_argument('-d', '--dir',
                    default=None, help="default directory to use")
parser.add_argument('-o', '--output', default=None, help="output directory path")
parser.add_argument('-e', '--executable', default="../bin/", help="path to shell script")
parser.add_argument('-m', '--mode', default="vertical", help="horizontal or vertical")
parser.add_argument('--out_params', default=None,
                    help="output params directory spec")
parser.add_argument('--pickle', default=None, help="output directory for pickle of cS.sensor")
parser.add_argument('--logs', default=None, help="output directory for batch logs")
parser.add_argument('-g', '--grid', default=None, help="grid distortions file")
parser.add_argument('-s', '--single', default="no", help="run first combo")

args = parser.parse_args()
print(args.dir)
cS = ccd_spacing(dir_index=args.dir, distort_file=args.grid, pickles_dir=args.pickle)

distort_file = " -g " + args.grid
spot_files = " -d " + args.dir
out_files = " --output " + args.output

distances = {}
where_x = {}
where_y = {}

for combos in cS.file_paths:
    if combos == "R30_S00_R30_S10" or combos == "R30_S00_R30_S01":
        continue

    cS.raft_ccd_combo = combos
    rc = cS.get_pickle_file()

    if cS.ccd_relative_orientation != args.mode:
        continue

    for s in range(2):
        c = distances.setdefault(combos, {})
        sd = c.setdefault(s, [])
        c[s] = cS.sensor[s].grid_distances

        wx = where_x.setdefault(combos, {})
        wxd = wx.setdefault(s, [])
        wx[s] = cS.sensor[s].grid_x
        wy = where_y.setdefault(combos, {})
        wyd = wy.setdefault(s, [])
        wy[s] = cS.sensor[s].grid_y

    if args.single == "yes":
        break

dist_mean = [None]*2
dist_std = [None]*2

for s in range(2):
    dist_sums = []
    f = True
    for co in distances:
        if f:
            dist_sums = np.array(distances[co][s])
            f = False
        else:
            dist_sums = np.vstack([dist_sums, distances[co][s]])

    dist_mean[s] = np.mean(stats.sigmaclip(dist_sums, low=10., high=10.), axis=0) # in case a row is very wrong
    dist_std[s] = np.std(dist_sums, axis=0)

c_color_mapper_res = LinearColorMapper(palette=palette, low=-0.5, high=0.5)
c_color_bar_res = ColorBar(color_mapper=c_color_mapper_res, label_standoff=8, width=500, height=20,
                           border_line_color=None, location=(0, 0), orientation='horizontal',
                           )
TOOLS = "pan, wheel_zoom, box_zoom, reset, save, box_select, lasso_select, tap"

r_plots = {}
x_s = {}
y_s = {}
res_s = {}
r_cds = {}

plot_layout = []

for co in where_x:
    rp = r_plots.setdefault(co, {})
    xp = x_s.setdefault(co, {})
    yp = y_s.setdefault(co, {})
    rp = res_s.setdefault(co, {})
    rc = r_cds.setdefault(co, {})

    name = co.split("_")

    for s in range(2):
        rps = rp.setdefault(s, [])
        xps = xp.setdefault(s, [])
        yps = yp.setdefault(s, [])
        rps = rp.setdefault(s, [])
        for ig, x in enumerate(where_x[co][s]):
            if distances[co][s][ig] == 0.:
                continue
            y = where_y[co][s][ig]
            resid = distances[co][s][ig] - dist_mean[s][ig]
            xps.append(x)
            yps.append(y)
            rps.append(resid)
            sensor_name = name[2*s] + "_" + name[2*s+1]

        r_cds[co][s] = ColumnDataSource(dict(x=x_s[co][s], y=y_s[co][s], res=res_s[co][s]))

        r_plots[co][s] = figure(title="Spots Grid: residuals  " + sensor_name, x_axis_label='x',
                              y_axis_label='y', tools=TOOLS, height=1000, width=1000,
                              tooltips=[
                                  ("x", "@x"), ("y", "@y"), ("distance", "@res")]
                              )
        r_plots[co][s].circle(x="x", y="y", source=r_cds[co][s], color="gray", size=10,
                            fill_color={'field': 'res', 'transform': c_color_mapper_res})
        r_plots[co][s].add_layout(c_color_bar_res, 'below')

    plot_layout.append(row(r_plots[co][0], r_plots[co][1]))

out_lay = layout(plot_layout)

output_file(args.output + "CCD_grid_distortions_" + args.mode + ".html")
save(out_lay, title="CCD grid distortions: " + args.mode)
print("done")
