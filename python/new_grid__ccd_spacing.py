import argparse
import numpy as np
import pickle
import math
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
parser.add_argument('-o', '--output', default=None, help="output directory path")
parser.add_argument('--pickle', default=None, help="output directory for pickle of cS.sensor")
parser.add_argument('-g', '--grid', default=None, help="grid distortions file")
parser.add_argument('-c', '--combo', default="R22_S10_R22_S21", help="raft/sensor combo")

args = parser.parse_args()


out_files = " --output " + args.output

s_p = args.pickle + args.combo + ".p"
pickle_file = open(s_p, "rb")
pickle_obj = pickle.load(pickle_file)
pickle_file.close()

sensor = pickle_obj[1]
x = [0.]*2401
y = [0.]*2401
idx = [0]*2401

num_lines = len(sensor.lines)

for lines in range(num_lines):
    num_spots = len(sensor.lines[lines])
    for sp, spot in enumerate(sensor.lines[lines]):
        gi = sensor.grid_index[lines][sp]
        x[gi] = spot[0]
        y[gi] = spot[1]
        idx[gi] = gi

theta = -sensor.grid_fit_results.params["theta"].value
x_center = x[1200]
y_center = y[1200]
x_cen = x - x_center
y_cen = y - y_center

x_rot = x_cen * math.cos(theta) - y_cen * math.sin(theta)
y_rot = x_cen * math.sin(theta) + y_cen * math.cos(theta)

print("x min, max = ", min(x_rot), max(x_rot))
print("y min, max = ", min(y_rot), max(y_rot))

pickle.dump([x_rot, y_rot], open(args.output + "grid.p", "wb"))

TOOLS = "pan, wheel_zoom, box_zoom, reset, save, box_select, lasso_select, tap"

orig_cds = ColumnDataSource(dict(x=x, y=y, gi=idx))
grid_orig = figure(title="Spots Grid: original grid from   " + args.combo, x_axis_label='x',
                  y_axis_label='y', tools=TOOLS, tooltips=[
                      ("x", "@x"), ("y", "@y"), ("gi", "@gi")])
grid_orig.circle(x="x", y="y", source=orig_cds, color="gray", size=10)

rot_cds = ColumnDataSource(dict(x=x_rot, y=y_rot, gi=idx))
grid_rot = figure(title="Spots Grid: rotated grid from   " + args.combo, x_axis_label='x',
                  y_axis_label='y', tools=TOOLS, tooltips=[
                      ("x", "@x"), ("y", "@y"), ("gi", "@gi")])
grid_rot.circle(x="x", y="y", source=rot_cds, color="gray", size=10)

out_lay = layout(grid_orig, grid_rot)

output_file(args.output + "CCD_grid_replacement.html")
save(out_lay, title="CCD grid replacement")
print("done")
