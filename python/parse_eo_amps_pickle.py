import itertools
import numpy as np
import pickle

from bokeh.models.widgets import DataTable, TableColumn, Div, NumberFormatter
from bokeh.models.formatters import DatetimeTickFormatter
from bokeh.models import Label, Span, LinearAxis, Range1d, Whisker, ColumnDataSource
from bokeh.plotting import figure, output_file, reset_output, show, save
from bokeh.layouts import row, layout, column

data_dir = "/Volumes/Data/Rubin/camera/"
in_file = data_dir + "E2233_amps_data.npy"

p = None

with open(in_file, 'rb') as f:
    p = pickle.load(f)

tests = list(p.keys())

print(tests)

ptc_gain = p["ptc_gain"]

gains = np.array(list(itertools.chain.from_iterable(amplifier.values()
                                           for amplifier in ptc_gain.values())))
filtered_gains = gains[~np.isnan(gains)]
#print(len(gains))
print("min, max gains", np.min(filtered_gains), np.max(filtered_gains) )

sw_guiders = list(filter(lambda element: "SW" in element, ptc_gain.keys()))
num_sw_guiders = len(sw_guiders)

print(" number of SW guide CCDs", num_sw_guiders)

ptc_h, ptc_edges = np.histogram(filtered_gains, bins=100)

width = ptc_edges[1] - ptc_edges[0]
p1 = figure(plot_width=640, plot_height=640, title="ptc gains")
p1.vbar(top=ptc_h, x=ptc_edges[1:], width=width, alpha=0.3, fill_color="red")

output_file(data_dir + "ptc_gains.html", title="PTC Gains")
l = layout(p1)
save(l)
