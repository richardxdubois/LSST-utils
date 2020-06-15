import argparse
import numpy as np
from ccd_spacing import ccd_spacing
from bokeh.plotting import curdoc, output_file, save, reset_output, figure
from bokeh.layouts import row, column
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
parser.add_argument('-o', '--output', default='/Users/richard/LSST/Code/misc/CCD_grids/',
                    help="output directory path")
parser.add_argument('-u', '--url_base', default='http://slac.stanford.edu/~richard/LSST/CCD_grids/',
                    help="base html path")

args = parser.parse_args()
print(args.dir)
cS = ccd_spacing(dir_index=args.dir, combo_name=args.combo)

cS.line_fitting = True
cS.use_offsets = True
cS.overlay_ccd = True

# loop over file sets
out_lines = []
problems = 0
successes = 0
names = []
orient = []
x = []
x_o = []
y = []
y_o = []
urls = []

for combos in cS.file_paths:
    try:
        rc = cS.get_data(combo_name=combos)
    except ValueError:
        problems += 1
        continue
    successes += 1
    out_str = combos + " " + str(cS.ccd_relative_orientation) + " " + str(cS.center_to_center) + "\n"
    out_lines.append(out_str)

    rc = cS.make_plots()
    line_layout = cS.make_line_plots()

    names.append(combos)
    orient.append(cS.ccd_relative_orientation)

    c2c = cS.center_to_center
    x.append(str(c2c[0]))
    y.append(str(c2c[1]))

    if cS.ccd_relative_orientation == "horizontal":
        a = -c2c[0]
        c2c[0] = -c2c[1]
        c2c[1] = a

    x_o.append(c2c[0])
    y_o.append(c2c[1])

    o_name = combos + "_plots.html"
    url_link = args.url_base + o_name
    urls.append(url_link)

    output_file(args.output + o_name)
    save(line_layout, title=combos + " grid plots")
    reset_output()

print("Found ", successes, " good filesets and", problems, " problem filesets")

results_source = ColumnDataSource(dict(names=names, x=x, y=y, o=orient, url=urls))

results_columns = [
    TableColumn(field="names", title="Raft-sensors", width=50),
    TableColumn(field="o", title="Sensor Orientation", width=50),
    TableColumn(field="x", title="x offset (px)", width=50, formatter=NumberFormatter(format='0.00')),
    TableColumn(field="y", title="y offset (px)", width=50, formatter=NumberFormatter(format='0.00')),
    TableColumn(field="url", title="Links to plots",
                formatter=HTMLTemplateFormatter(template="<a href='<%= url %>' target='_blank'>plots</a>"),
                width=50)
]

results_table = DataTable(source=results_source, columns=results_columns, width=700, height=650)

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

out_lay = row(results_table, column(x_hist, y_hist))

output_file(args.output + "CCD_grids.html")
save(out_lay, title="CCD grid plots")
