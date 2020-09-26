import argparse
import numpy as np
import pickle
from astropy import stats
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
parser.add_argument('-w', '--whiskers', default="./", help="whisker files directory")

args = parser.parse_args()
print(args.dir)
cS = ccd_spacing(dir_index=args.dir, distort_file=args.grid,
                 pickles_dir=args.pickle, whiskers=args.whiskers)

distort_file = " -g " + args.grid
spot_files = " -d " + args.dir
out_files = " --output " + args.output

distances = {}
where_x = {}
where_y = {}
g = {}

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
        gw = g.setdefault(combos, {})
        g[combos][s] = cS.sensor[s].grid_whiskers

        wx = where_x.setdefault(combos, {})
        wxd = wx.setdefault(s, [])
        wx[s] = cS.sensor[s].grid_x
        wy = where_y.setdefault(combos, {})
        wyd = wy.setdefault(s, [])
        wy[s] = cS.sensor[s].grid_y

    if args.single == "yes":
        break

dist_mean = [None]
dist_std = [None]
whx_mean = [None]
why_mean = [None]

dist_sums = [0.]*2401
wh_x = [0.]*2401
wh_y = [0.]*2401

f = True
for co in distances:
    wh_xt = [0.] * 2401
    wh_yt = [0.] * 2401
    for s in range(2):
        dist_sums = np.array(distances[co][s])
        whisks = g[co][s]
        for iw in range(len(whisks)):
            try:
                wh_xt[iw] = g[co][s][iw][0]
                wh_yt[iw] = g[co][s][iw][1]
            except TypeError:  # float, not a list of 2. Should be zero.
                pass

    if f:
        wh_x = wh_xt
        wh_y = wh_yt
        f = False
    else:
        dist_sums = np.vstack([dist_sums, distances[co][s]])
        wh_x = np.vstack([wh_x, wh_xt])
        wh_y = np.vstack([wh_y, wh_yt])

clipped = stats.sigma_clip(dist_sums, sigma=3., axis=0)
dist_mean = np.mean(clipped, axis=0) # in case a row is very wrong
dist_std = np.std(dist_sums, axis=0)
whx_clipped = stats.sigma_clip(wh_x, sigma=3., axis=0)
whx_mean = np.mean(whx_clipped, axis=0) # in case a row is very wrong
why_clipped = stats.sigma_clip(wh_y, sigma=3., axis=0)
why_mean = np.mean(why_clipped, axis=0) # in case a row is very wrong

# write out pickle file of whiskers

pickle.dump([whx_mean, why_mean], open("whiskers_" + args.mode + ".p", "wb"))
exit()

c_color_mapper_res = LinearColorMapper(palette=palette, low=-0.5, high=0.5)
c_color_bar_res = ColorBar(color_mapper=c_color_mapper_res, label_standoff=8, width=500, height=20,
                           border_line_color=None, location=(0, 0), orientation='horizontal',
                           )
TOOLS = "pan, wheel_zoom, box_zoom, reset, save, box_select, lasso_select, tap"

r_plots = {}
d_plots = {}
dist_plots = {}
x_s = {}
y_s = {}
res_s = {}
dist_s = {}
r_cds = {}

plot_layout = []

for co in where_x:
    rp = r_plots.setdefault(co, {})
    dp = d_plots.setdefault(co, {})
    dip = dist_plots.setdefault(co, {})

    xp = x_s.setdefault(co, {})
    yp = y_s.setdefault(co, {})
    rsp = res_s.setdefault(co, {})
    ds = dist_s.setdefault(co, {})

    rc = r_cds.setdefault(co, {})

    name = co.split("_")

    for s in range(2):
        rps = rp.setdefault(s, [])
        xps = xp.setdefault(s, [])
        yps = yp.setdefault(s, [])
        rsps = rsp.setdefault(s, [])
        dps = dp.setdefault(s, [])
        dsp = ds.setdefault(s, [])
        dips = dip.setdefault(s, [])

        for ig, x in enumerate(where_x[co][s]):
            if distances[co][s][ig] == 0.:
                continue
            y = where_y[co][s][ig]
            resid = distances[co][s][ig] - dist_mean[s][ig]
            xps.append(x)
            yps.append(y)
            rsps.append(resid)
            dsp.append(distances[co][s][ig])
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

        d_plots[co][s] = figure(title="subtracted distances  " + sensor_name, x_axis_label='distances (px)',
                           y_axis_label='count', tools=TOOLS, height=450)

        h0, b0 = np.histogram(res_s[co][s], bins=50)
        w = b0[1] - b0[0]
        d_plots[co][s].step(y=h0, x=b0[:-1] + w / 2.)

        dist_plots[co][s] = figure(title="original distances  " + sensor_name, x_axis_label='distances (px)',
                           y_axis_label='count', tools=TOOLS, height=450)

        h1, b1 = np.histogram(dist_s[co][s], bins=50)
        w = b1[1] - b1[0]
        dist_plots[co][s].step(y=h1, x=b1[:-1] + w / 2.)


    plot_layout.append(row(r_plots[co][0], column(dist_plots[co][0], d_plots[co][0]),
                           r_plots[co][1], column(dist_plots[co][1], d_plots[co][1])))

out_lay = layout(plot_layout)

output_file(args.output + "CCD_grid_distortions_" + args.mode + ".html")
save(out_lay, title="CCD grid distortions: " + args.mode)
print("done")
