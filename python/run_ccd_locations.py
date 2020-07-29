import argparse
import numpy as np
import math
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
parser.add_argument('-i', '--invert', default='no',
                    help="invert sensor order")
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
    ftheta.append(c_row["dtheta_fit"])

print("Found ", len(names), " good filesets")

TOOLS = "pan, wheel_zoom, box_zoom, reset, save"

# now build the sensor/raft grid

focal_plane = figure(tools=TOOLS, title="Focal plane grid", x_axis_label='pixels',
                y_axis_label='pixels', height=1000, width=1000)
d_raft = 12700.  # pixels - 127 mm between raft centers - per LCA-13381
d_sensor = 4225.  # pixels - 42.25 mm between sensor centers

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
cx_m = []
cy_m = []
dx_m = []
dy_m = []

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

    focal_plane.line([cx_0, cx_1], [cy_0, cy_1], line_color="black", line_width=8)

focal_plane.circle(x=0., y=0., color="green", size=8)

sensors = ["R30_S10", "R30_S00", "R20_S20", "R20_S10", "R20_S00", "R20_S01", "R20_S02",
           "R20_S12", "R20_S22", "R30_S02", "R30_S12", "R30_S22", "R30_S21", "R30_S20"]

#sensors = ["R30_S10", "R30_S20"]

#sensors = ["R30_S10", "R30_S00", "R30_S10", "R30_S20"]

#sensors = ["R30_S10", "R30_S00", "R20_S20", "R20_S10", "R20_S00", "R20_S10", "R20_S20", "R30_S00",
#           "R30_S10", "R30_S20"]

#sensors = ["R30_S10", "R30_S00", "R20_S20", "R20_S10", "R20_S00", "R20_S01",
#           "R20_S11", "R20_S21", "R30_S01", "R30_S11", "R30_S21", "R30_S20"]

#sensors = ["R30_S11", "R30_S01", "R20_S21", "R20_S20", "R30_S00", "R30_S10", "R30_S20", "R30_S21"]
#sensors = ["R30_S11",  "R30_S10", "R30_S20", "R30_S21"]

#sensors = ["R30_S21", "R30_S22", "R30_S21"]

if args.invert == "yes":
    sensors.reverse()

start_x = 0.
start_y = 0.

running_x = start_x
running_y = start_y

print(sensors[-1], 0., 0.)
rot_angle = 0
cur_sensor = sensors[-1]  # assumes this is a loop with the starting point == ending point

r0 = cur_sensor[0:3]
s0 = cur_sensor[4:7]

cy_0 = -2.5 * d_raft + (float(r0[1]) + 0.5) * d_raft + (float(s0[1]) - 1.) * d_sensor
cx_0 = -2.5 * d_raft + (float(r0[2]) + 0.5) * d_raft + (float(s0[2]) - 1.) * d_sensor

orientation = ""

# find the proper connecting measurement given the current sensor and standard
for ids, tgt_sensor in enumerate(sensors):
    idl = 0
    # find the connecting measurement for target and current sensor. idl is index into arrays.
    for ic, c in enumerate(names):
        if tgt_sensor in c:
            if cur_sensor in c:
                idl = ic
                break

    std_sign = 1.  # account for direction between standard and target
    if tgt_sensor != st_name[idl]:
        std_sign = -1.

    dx0 = -x[idl] * std_sign
    dy0 = -y[idl] * std_sign

    dx = dx0 * math.cos(rot_angle) - dy0 * math.sin(rot_angle)
    dy = dx0 * math.sin(rot_angle) + dy0 * math.cos(rot_angle)

    # apply rotation to the deltas, but only after the first connection

    rot_angle -= std_sign*sdiff[idl]

    r0 = tgt_sensor[0:3]
    s0 = tgt_sensor[4:7]

    cy_m.append(-2.5 * d_raft + (float(r0[1]) + 0.5) * d_raft + (float(s0[1]) - 1.) * d_sensor)
    cx_m.append(-2.5 * d_raft + (float(r0[2]) + 0.5) * d_raft + (float(s0[2]) - 1.) * d_sensor)

    focal_plane.line([cx_0, dx + cx_0],
                     [cy_0, dy + cy_0],
                     line_color="red", line_width=2)

    cx_0 += dx
    cy_0 += dy

    running_x += dx
    running_y += dy

    dx_m.append(cx_0 - cx_m[ids])
    dy_m.append(cy_0 - cy_m[ids])
    dist_m = math.hypot(cx_0 - cx_m[ids], cy_0 - cy_m[ids])

    print(tgt_sensor, names[idl], running_x, running_y, "      ",
          st_name[idl], std_sign, sdiff[idl], rot_angle, orient[idl], dx, dx0, dy, dy0, dx_m[ids], dy_m[ids], dist_m)

    cur_sensor = tgt_sensor

fx = figure(tools=TOOLS, title="x diffs to centers", x_axis_label='sensor count',
                y_axis_label='pixels')
fy = figure(tools=TOOLS, title="y diffs to centers", x_axis_label='sensor count',
                y_axis_label='pixels')

fx.vbar(top=dx_m, x=range(len(dx_m)), width=1, fill_color='red', fill_alpha=0.2)
fy.vbar(top=dy_m, x=range(len(dy_m)), width=1, fill_color='red', fill_alpha=0.2)

out_lay = layout(focal_plane, row(fx, fy))

output_file(args.output + "CCD_locations.html")
save(out_lay, title="CCD grid locations")
