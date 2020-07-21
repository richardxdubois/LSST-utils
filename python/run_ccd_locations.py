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

# now build the sensor/raft grid

focal_plane = figure(tools=TOOLS, title="Focal plane grid", x_axis_label='pixels',
                y_axis_label='pixels', height=1000, width=1000)
d_raft = 127000.  # 127 mm between raft centers - per LCA-13381
d_sensor = 42250.  # 42.25 mm between sensor centers

for rh in range(0, 5):
    for rv in range(0, 5):
        # suppress the corners
        if (rh == 0 and rv == 0) or (rh == 4 and rv == 0) or (rh == 0 and rv == 4) or (rh == 4 and rv == 4):
            continue

        cx_r = (rh-2)*d_raft
        cy_r = (rv-2)*d_raft

        focal_plane.rect(x=cx_r, y=cy_r, width=d_raft, height=d_raft, fill_alpha=0.0, line_width=2)
        for sh in range(0, 3):
            for sv in range(0, 3):
                cx_s = cx_r + (sh-1)*d_sensor
                cy_s = cy_r + (sv-1)*d_sensor
                focal_plane.rect(x=cx_s, y=cy_s, width=d_sensor, height=d_sensor, fill_color="red",
                                 fill_alpha=0.20)

for n in names:
    c_name = n.split("_")
    r0 = c_name[0][-2:]
    s0 = c_name[1][-2:]

    cy_0 = -2.5*d_raft + (float(r0[0])+0.5)*d_raft + (float(s0[0]) - 1.)*d_sensor
    cx_0 = -2.5*d_raft + (float(r0[1])+0.5)*d_raft + (float(s0[1]) - 1.)*d_sensor

    r1 = c_name[2][-2:]
    s1 = c_name[3][-2:]
    cy_1 = -2.5*d_raft + (float(r1[0])+0.5)*d_raft + (float(s1[0]) - 1.)*d_sensor
    cx_1 = -2.5*d_raft + (float(r1[1])+0.5)*d_raft + (float(s1[1]) - 1.)*d_sensor

    focal_plane.line([cx_0, cx_1], [cy_0, cy_1], line_color="black", line_width=2)

focal_plane.circle(x=0., y=0., color="green", size=8)

linked = ["R30_S10_R30_S20", "R30_S00_R30_S10", "R20_S20_R30_S00", "R20_S10_R20_S20", "R20_S20_R20_S21",
          "R20_S21_R30_S01", "R30_S01_R30_S11", "R30_S11_R30_S21", "R30_S20_R30_S21"]

start_x = 0.
start_y = 0.

running_x = start_x
running_y = start_y

for m in linked[1:]:
    idl = names.index(m)
    s_ref = st_name[idl]
    dirn = -1.
    if s_ref == m[0:7]:
        dirn = 1.

    dx = x[idl] * dirn
    dy = y[idl] * dirn

    running_x += dy
    running_y += dx

    print(m, s_ref, running_x, running_y)


out_lay = layout(sd_hist, focal_plane)

output_file(args.output + "CCD_locations.html")
save(out_lay, title="CCD grid locations")
