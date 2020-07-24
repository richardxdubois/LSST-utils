import argparse
import numpy as np
import math
import pandas
from bokeh.plotting import curdoc, output_file, save, reset_output, figure
from bokeh.layouts import row, column, layout
from bokeh.models import ColumnDataSource, DataTable, TableColumn, NumberFormatter, HTMLTemplateFormatter


def dir_signs(target, combo, standard):

    # current is current raft/sensor name: Rab_Scd - it is one of the combo name pairs
    # combo is the measurement pair

    #  target sensor is Rij_Skl. The originating sensor is Rmn_Sop

    # cross raft boundaries

    # ij != mn
    #      j==n: i<m - -y ; i>m +y
    #      i==m: j<n - -x ; j>n +x

    # inside a raft

    #       k==o: l>p - +x; l<p - -x
    #       l==p: k>o - +y; k<o - -y

    cur_name = target.split("_")
    cur_r = cur_name[0][-2:]
    cur_s = cur_name[1][-2:]

    r = [0]*2
    s = [0]*2

    c_name = combo.split("_")
    r[0] = c_name[0][-2:]
    s[0] = c_name[1][-2:]

    r[1] = c_name[2][-2:]
    s[1] = c_name[3][-2:]

    c_tgt = 0
    c_oth = 1
    if cur_r == r[1] and cur_s == s[1]:
        c_tgt = 1
        c_oth = 0

    x_sign = 1.
    y_sign = 1.

    std_sign = 1.  # account for direction between standard and target
    if target != standard:
        std_sign = -1.

    # now run through the options

    # cross-raft

    if cur_r != r[c_oth]:
        if int(cur_r[1]) == int(r[c_oth][1]) and int(cur_r[0]) < int(r[c_oth][0]):
            y_sign = -1.
            x_sign = std_sign
        elif int(cur_r[0]) == int(r[c_oth][0]) and int(cur_r[0]) < int(r[c_oth][0]):
            x_sign = -1.
            y_sign = std_sign
    else:
        if int(cur_s[0]) == int(s[c_oth][0]) and int(cur_s[1]) < int(s[c_oth][1]):
            x_sign = -1.
            y_sign = std_sign
        elif int(cur_s[1]) == int(s[c_oth][1]) and int(cur_s[0]) < int(s[c_oth][0]):
            y_sign = -1.
            x_sign = std_sign

    x_sign = std_sign
    y_sign = std_sign

    return x_sign, y_sign, std_sign


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
    ftheta.append(c_row["dtheta_fit"])

print("Found ", len(names), " good filesets")

TOOLS = "pan, wheel_zoom, box_zoom, reset, save"

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

sensors = ["R30_S10", "R30_S00", "R20_S20", "R20_S10", "R20_S00", "R20_S01", "R20_S02",
           "R20_S12", "R20_S22", "R30_S02", "R30_S12", "R30_S22", "R30_S21", "R30_S20"]

start_x = 0.
start_y = 0.

running_x = start_x
running_y = start_y

print(sensors[-1], 0., 0.)
rot_angle = 0
cur_sensor = sensors[-1]  # assumes this is a loop with the starting point == ending point

# find the proper connecting measurement given the current sensor and standard
for tgt_sensor in sensors:
    idl = 0
    # find the connecting measurement for target and current sensor. idl is index into arrays.
    for ic, c in enumerate(names):
        if tgt_sensor in c:
            if cur_sensor in c:
                idl = ic

    #x_sign, y_sign, std_sign = dir_signs(target=tgt_sensor, combo=names[idl], standard=st_name[idl])

    x_sign = 1.
    y_sign = 1.

    std_sign = 1.  # account for direction between standard and target
    if tgt_sensor != st_name[idl]:
        std_sign = -1.
        x_sign = std_sign
        y_sign = std_sign

    dx0 = -x[idl] * x_sign
    dy0 = -y[idl] * y_sign

    # apply running rotation to the deltas, but only after the first connection and invert since going backwards
    rot_angle -= std_sign*sdiff[idl]
    rot_angle = 0.

    if idl == 0:
        dx = dx0
        dy = dy0
    else:
        dx = dx0 * math.cos(rot_angle) - dy0 * math.sin(rot_angle)
        dy = dx0 * math.sin(rot_angle) + dy0 * math.cos(rot_angle)

    running_x += dx
    running_y += dy

    print(tgt_sensor, names[idl], running_x, running_y, "      ",
          st_name[idl], std_sign, sdiff[idl], rot_angle, dx, x_sign, dx0, dy, y_sign, dy0)

    cur_sensor = tgt_sensor

out_lay = layout(focal_plane)

output_file(args.output + "CCD_locations.html")
save(out_lay, title="CCD grid locations")
