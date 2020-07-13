import argparse
import numpy as np
from ccd_spacing import ccd_spacing
from bokeh.plotting import curdoc, output_file, save, reset_output, figure
from bokeh.layouts import row, column, layout
from bokeh.models import ColumnDataSource, DataTable, TableColumn, NumberFormatter, HTMLTemplateFormatter

print("in main")

parser = argparse.ArgumentParser(
    description='Examine CCD spot images to look at spacing')

# The following are 'convenience options' which could also be specified in
# the filter string
parser.add_argument('-d', '--dir',
                    default='/Users/richard/LSST/Data/GridSpacing/',
                    help="default directory to use")
parser.add_argument('-c', '--combo', default='R22_S10_S11', help="raft, sensor combo name")
parser.add_argument('-f', '--dofit', default='yes', help="do full fit yes/no")
parser.add_argument('-o', '--output', default='/Users/richard/LSST/Code/misc/CCD_grids/',
                    help="output directory path")
parser.add_argument('-u', '--url_base', default='http://slac.stanford.edu/~richard/LSST/CCD_grids/sims/',
                    help="base html path")
parser.add_argument('-g', '--grid', default=
                    '/Users/richard/LSST/Code/misc/CCD_grids/optical_distortion_grid.fits',
                    help="grid distortions file")

args = parser.parse_args()
print(args.dir)
cS = ccd_spacing(dir_index=args.dir, combo_name=args.combo, distort_file=args.grid)

cS.line_fitting = True
cS.use_offsets = True
cS.overlay_ccd = True

cS.sim_distort = True
cS.sim_doit = True

# loop over file sets
out_lines = []
problems = 0
successes = 0
names = []
orient = []
x = []      # for the table
x_o = []    # for the offsets plot
y = []      # for the table
y_o = []    # for the offsets plot
sdiff = []
urls = []
fx = []
fy = []
ftheta = []

config = {}
# configs are: distort on/off; offset; rotation; orientation
config[0] = [False, 0., 0., "vertical"]
config[1] = [True, 0., 0., "vertical"]
config[2] = [True, 0., 0.002, "vertical"]
config[3] = [True, 0., 0.004, "vertical"]
config[4] = [True, 5., 0., "vertical"]
config[5] = [True, 5., 0.002, "vertical"]
config[6] = [True, 5., 0.004, "vertical"]
config[7] = [True, 10., 0., "vertical"]
config[8] = [True, 10., 0.002, "vertical"]
config[9] = [True, 10., 0.004, "vertical"]

config[10] = [False, 0., 0., "horizontal"]
config[11] = [True, 0., 0., "horizontal"]
config[12] = [True, 0., 0.002, "horizontal"]
config[13] = [True, 0., 0.004, "horizontal"]
config[14] = [True, 5., 0., "horizontal"]
config[15] = [True, 5., 0.002, "horizontal"]
config[16] = [True, 5., 0.004, "horizontal"]
config[17] = [True, 10., 0., "horizontal"]
config[18] = [True, 10., 0.002, "horizontal"]
config[19] = [True, 10., 0.004, "horizontal"]

for combos in config:
    cS.sim_distort = config[combos][0]
    cS.sim_offset = config[combos][1]
    cS.sim_rotate = config[combos][2]
    cS.ccd_relative_orientation = config[combos][3]

    try:
        rc = cS.get_data()
    except ValueError:
        problems += 1
        continue
    successes += 1
    c_name = str(config[combos][0]) + " " + str(config[combos][1]) + " " + str(config[combos][2]) + " " + \
        config[combos][3]

    print("Doing, ", c_name)
    out_str = c_name + " " + str(cS.ccd_relative_orientation) + " " + str(cS.center_to_center) + "\n"
    out_lines.append(out_str)

    if args.dofit == "yes":
        cS.use_fit = True
        rc = cS.match()
        if cS.ccd_relative_orientation == "vertical":
            fx.append(cS.dy0)
            fy.append(cS.dx0)
            ftheta.append(cS.dtheta0)
        else:
            fx.append(-cS.dx0)
            fy.append(-cS.dy0)
            ftheta.append(-cS.dtheta0)

    rc = cS.make_plots()
    line_layout = cS.make_line_plots()

    names.append(c_name)
    orient.append(cS.ccd_relative_orientation)

    c2c = cS.center_to_center

    if cS.ccd_relative_orientation == "horizontal":
        x.append(str(-c2c[0]))
        y.append(str(-c2c[1]))
        a = -c2c[0]
        c2c[0] = c2c[1]
        c2c[1] = a
        sdiff.append(-cS.mean_slope_diff)
    else:
        x.append(str(c2c[0]))
        y.append(str(c2c[1]))
        sdiff.append(cS.mean_slope_diff)

    x_o.append(c2c[0])
    y_o.append(c2c[1])

    o_name = str(combos) + "_plots.html"
    url_link = args.url_base + o_name
    urls.append(url_link)

    output_file(args.output + o_name)
    save(line_layout, title=str(combos) + " grid plots")
    reset_output()

print("Found ", successes, " good filesets and", problems, " problem filesets")

if args.dofit:
    results_source = ColumnDataSource(dict(names=names, x=x, y=y, o=orient, fx=fx, fy=fy, ftheta=ftheta,
                                           sdiff=sdiff, url=urls))
else:
    results_source = ColumnDataSource(dict(names=names, x=x, y=y, o=orient, sdiff=sdiff, url=urls))

results_columns = [
    TableColumn(field="names", title="Raft-sensors", width=50),
    TableColumn(field="o", title="Sensor Orientation", width=50),
    TableColumn(field="x", title="x offset (px)", width=50, formatter=NumberFormatter(format='0.00')),
    TableColumn(field="y", title="y offset (px)", width=50, formatter=NumberFormatter(format='0.00')),
    TableColumn(field="sdiff", title="slopes diff (rad)", width=50, formatter=NumberFormatter(format='0.0000'))
]
if args.dofit:
    results_columns.append(TableColumn(field="fx", title="fit x offset (px)", width=50,
                                       formatter=NumberFormatter(format='0.00')))
    results_columns.append(TableColumn(field="fy", title="fit y offset (px)", width=50,
                                       formatter=NumberFormatter(format='0.00')))
    results_columns.append(TableColumn(field="ftheta", title="fit theta diff (rad)", width=50,
                                       formatter=NumberFormatter(format='0.0000')))

results_columns.append(TableColumn(field="url", title="Links to plots",
                formatter=HTMLTemplateFormatter(template="<a href='<%= url %>' target='_blank'>plots</a>"),
                width=50))


results_table = DataTable(source=results_source, columns=results_columns, width=900, height=650)

x_off, bins = np.histogram(np.array(x_o), bins=10)
w = bins[1] - bins[0]
x_hist = figure(tools=cS.TOOLS, title="x offsets", x_axis_label='offsets (px)',
                y_axis_label='counts', height=300, width=600)
x_hist.vbar(top=x_off, x=bins[:-1], width=bins[1] - bins[0], fill_color='red', fill_alpha=0.2)

y_off, bins = np.histogram(np.array(y_o), bins=10)
w = bins[1] - bins[0]
y_hist = figure(tools=cS.TOOLS, title="y offsets", x_axis_label='offsets (px)',
                y_axis_label='counts', height=300, width=600)
y_hist.step(y=y_off, x=bins[:-1] + w / 2.)
y_hist.vbar(top=y_off, x=bins[:-1], width=bins[1] - bins[0], fill_color='red', fill_alpha=0.2)

d_x = np.array([float(xi) for xi in x]) - np.array(fx)
d_y = np.array([float(yi) for yi in y]) - np.array(fy)

out_lay = row(results_table, column(x_hist, y_hist))

if args.dofit:
    dx_off, bins = np.histogram(np.array(d_x), bins=10)
    w = bins[1] - bins[0]
    dx_hist = figure(tools=cS.TOOLS, title="x offset diff", x_axis_label='offsets (px)',
                    y_axis_label='counts', height=300, width=600)
    dx_hist.vbar(top=dx_off, x=bins[:-1], width=bins[1] - bins[0], fill_color='red', fill_alpha=0.2)

    dy_off, bins = np.histogram(np.array(d_y), bins=10)
    w = bins[1] - bins[0]
    dy_hist = figure(tools=cS.TOOLS, title="y offset diff", x_axis_label='offsets (px)',
                    y_axis_label='counts', height=300, width=600)
    dy_hist.vbar(top=dy_off, x=bins[:-1], width=bins[1] - bins[0], fill_color='red', fill_alpha=0.2)

    out_lay = layout(row(results_table, column(x_hist, y_hist)), row(dx_hist, dy_hist))


output_file(args.output + "CCD_grids_sims.html")
save(out_lay, title="CCD sims grid plots")
