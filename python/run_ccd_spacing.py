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
parser.add_argument('--out_params', default='CCD_grids_params.csv',
                    help="output params file spec")
parser.add_argument('-u', '--url_base', default='http://slac.stanford.edu/~richard/LSST/CCD_grids/',
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

# loop over file sets

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
st_name = []

for combos in cS.file_paths:
    try:
        rc = cS.get_data(combo_name=combos)
    except ValueError:
        print("run_ccd_spacing - problem with ", combos)
        problems += 1
        continue
    successes += 1

    if args.dofit == "yes":
        cS.use_fit = True
        rc = cS.match()
        fx.append(cS.dy0)
        fy.append(cS.dx0)
        ftheta.append(cS.dtheta0)

    rc = cS.make_plots()
    line_layout = cS.make_line_plots()

    names.append(combos)
    orient.append(cS.ccd_relative_orientation)

    c2c = cS.center_to_center

    x.append(str(c2c[0]))
    y.append(str(c2c[1]))

    if abs(c2c[0]) < 2000:  # "short" direction
        x_o.append(c2c[0])
        y_o.append(c2c[1])
    else:  # "long" direction
        x_o.append(c2c[1])
        y_o.append(c2c[0])

    sdiff.append(cS.mean_slope_diff)
    st_name.append(cS.names_ccd[cS.ccd_standard])

    o_name = combos + "_plots.html"
    url_link = args.url_base + o_name
    urls.append(url_link)

    output_file(args.output + o_name)
    save(line_layout, title=combos + " grid plots")
    reset_output()

print("Found ", successes, " good filesets and", problems, " problem filesets")

if args.dofit:
    results_source = ColumnDataSource(dict(names=names, x=x, y=y, o=orient, fx=fx, fy=fy, ftheta=ftheta,
                                           sdiff=sdiff, st_name=st_name, url=urls))
else:
    results_source = ColumnDataSource(dict(names=names, x=x, y=y, o=orient, sdiff=sdiff, st_name=st_name, url=urls))

results_columns = [
    TableColumn(field="names", title="Raft-sensors", width=75),
    TableColumn(field="o", title="Sensor Orientation", width=50),
    TableColumn(field="st_name", title="Ref CCD", width=30),
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


results_table = DataTable(source=results_source, columns=results_columns, width=1000, height=1200)

x_off, bins = np.histogram(np.array(x_o), bins=10)
w = bins[1] - bins[0]
x_hist = figure(tools=cS.TOOLS, title="short offsets", x_axis_label='offsets (px)',
                y_axis_label='counts', height=300, width=600)
x_hist.vbar(top=x_off, x=bins[:-1], width=bins[1] - bins[0], fill_color='red', fill_alpha=0.2)

y_off, bins = np.histogram(np.array(y_o), bins=10)
w = bins[1] - bins[0]
y_hist = figure(tools=cS.TOOLS, title="long offsets", x_axis_label='offsets (px)',
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

    sd, bins = np.histogram(np.array(sdiff), bins=10)
    w = bins[1] - bins[0]
    sd_hist = figure(tools=cS.TOOLS, title="rotations (rad)", x_axis_label='rotation (rad)',
                y_axis_label='counts', height=300, width=600)
    sd_hist.vbar(top=sd, x=bins[:-1], width=bins[1] - bins[0], fill_color='red', fill_alpha=0.2)

    out_lay = layout(row(results_table, column(x_hist, y_hist, sd_hist)), row(dx_hist, dy_hist))

output_file(args.output + "CCD_grids.html")
save(out_lay, title="CCD grid plots")

# write out results to csv file

f = open(args.out_params, "w+")

header_line = "name, orientation, ref_CCD, dx_line, dy_line, dtheta_line, dx_fit, dy_fit, dtheta_fit\n"
f.write(header_line)

for idn, name in enumerate(names):

    line_out = str(name) + ", " + str(orient[idn]) + ", " + str(st_name[idn]) + ", " + str(x[idn]) + ", ", \
               str(y[idn]) + \
               ", " + str(sdiff[idn]) + ", " + str(fx[idn]) + ", " + str(fy[idn]) + ", " + str(ftheta[idn]) + " \n"

    f.write("".join(line_out))

f.close()
