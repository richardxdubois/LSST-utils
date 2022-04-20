from bokeh.plotting import figure, output_file, reset_output, show, save, curdoc
from bokeh.layouts import row, layout, column
from bokeh.models import GeoJSONDataSource, LinearColorMapper, ColorBar, LogColorMapper, Range1d
from bokeh.models.widgets import Tabs, Panel, DataTable, TableColumn, DateFormatter, \
    NumberFormatter, Div
from bokeh.models import ColumnDataSource, Span, Label, HoverTool, DatetimeTickFormatter
import numpy as np
import argparse
import math
import pandas

ncsa = "/Users/richarddubois/Code/LSST/misc/QUOTA_FOR_SRP.csv"

uhome = []
jhome = []
project = []
scratch = []
repo = []

f = open(ncsa)

header = True
for lines in f:
    strp_line = lines.strip("\n").strip()
    fields = strp_line.split(",")
    if fields[1] == "user":
        continue

    if fields[1] == "home":
        uhome.append(int(fields[2]))
    elif fields[1] == "jhome":
        jhome.append(int(fields[2]))
    elif fields[1] == "project":
        project.append(int(fields[2]))
    elif fields[1] == "scratch":
        scratch.append(int(fields[2]))
    elif fields[1] == "repo":
        repo.append(int(fields[2]))


hist, edges = np.histogram(uhome, bins=15, range=(0.1,100))

p_hist = figure(title="Home directory usage (GB)",
                x_axis_label='GB', y_axis_label='counts',
                width=600)

p_hist.vbar(top=hist, x=edges[:-1], fill_color='red', fill_alpha=0.2)

jhist, j_edges = np.histogram(jhome, bins=15, range=(0.1, 100))

j_hist = figure(title="JHome directory usage (GB)",
                x_axis_label='GB', y_axis_label='counts',
                width=600)

j_hist.vbar(top=jhist, x=j_edges[:-1], fill_color='red', fill_alpha=0.2)

shist, j_edges = np.histogram(scratch, bins=15, range=(0.1, 100))

s_hist = figure(title="Scratch directory usage (GB)",
                x_axis_label='GB', y_axis_label='counts',
                width=600)

s_hist.vbar(top=shist, x=j_edges[:-1], fill_color='red', fill_alpha=0.2)

prhist, j_edges = np.histogram(project, bins=15, range=(0.1, 100))

pr_hist = figure(title="Project directory usage (GB)",
                x_axis_label='GB', y_axis_label='counts',
                width=600)

pr_hist.vbar(top=prhist, x=j_edges[:-1], fill_color='red', fill_alpha=0.2)

rhist, j_edges = np.histogram(repo, bins=15, range=(0.1, 100))

r_hist = figure(title="Repo directory usage (GB)",
                x_axis_label='GB', y_axis_label='counts',
                width=600)

r_hist.vbar(top=rhist, x=j_edges[:-1], fill_color='red', fill_alpha=0.2)


m = layout(row(p_hist, j_hist), row(s_hist, pr_hist), r_hist)

output_file("/Users/richarddubois/Code/LSST/misc/ncsa_usage.html")
save(m, title="NCSA Disk usage")
