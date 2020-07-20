import argparse
import numpy as np
import pandas
from bokeh.plotting import curdoc, output_file, save, reset_output, figure
from bokeh.layouts import row, column, layout
from bokeh.models import ColumnDataSource, DataTable, TableColumn, NumberFormatter, HTMLTemplateFormatter

print("in main")

parser = argparse.ArgumentParser(
    description='Examine CCD spot images to look at spacing')

# The following are 'convenience options' which could also be specified in
# the filter string

parser.add_argument('-o', '--output', default='/Users/richard/LSST/Code/misc/CCD_grids/',
                    help="output directory path")
parser.add_argument('--in_params', default='CCD_grids_params.csv',
                    help="output params file spec")
parser.add_argument('-u', '--url_base', default='http://slac.stanford.edu/~richard/LSST/CCD_grids/',
                    help="base html path")

args = parser.parse_args()

csv_assign = pandas.read_csv(args.in_params, header=0, skipinitialspace=True)
print("csv read in: ", args.in_params)
combos_frame = csv_assign.set_index('name', drop=False)
id_col = combos_frame["name"]

names = []
orient = []
x = []      # for the table
y = []      # for the table
sdiff = []
fx = []
fy = []
ftheta = []
st_name = []

# load up the parameters

for index, c_row in csv_assign.iterrows():
    names.append(c_row["name"])
    orient.append(c_row["orientation"])
    x.append(c_row["dx_line"])
    y.append(c_row["dy_line"])
    sdiff.append(c_row["dtheta_line"])
    st_name.append(c_row["ref_CCD"])
    fx.append(c_row["dx_fit"])
    fy.append(c_row["dy_fit"])
    ftheta.append(c_row["dtheta_fit "])  # beware the extra blank!

print("Found ", len(names), " good filesets")

TOOLS = "pan, wheel_zoom, box_zoom, reset, save"

sd, bins = np.histogram(np.array(sdiff), bins=10)
w = bins[1] - bins[0]
sd_hist = figure(tools=TOOLS, title="rotations (rad)", x_axis_label='rotation (rad)',
                y_axis_label='counts', height=300, width=600)
sd_hist.vbar(top=sd, x=bins[:-1], width=bins[1] - bins[0], fill_color='red', fill_alpha=0.2)

out_lay = layout(sd_hist)

output_file(args.output + "CCD_locations.html")
save(out_lay, title="CCD grid locations")
