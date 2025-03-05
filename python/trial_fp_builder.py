import numpy as np
import itertools
import pickle

from bokeh.models.widgets import DataTable, TableColumn, Div, NumberFormatter
from bokeh.models.formatters import DatetimeTickFormatter
from bokeh.models import Label, Rect, HoverTool, ColorBar, LinearColorMapper, ColumnDataSource
from bokeh.plotting import figure, output_file, reset_output, show, save
from bokeh.layouts import row, layout, column
from bokeh.transform import transform

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

ptc_h, ptc_edges = np.histogram(filtered_gains, bins=100)

width = ptc_edges[1] - ptc_edges[0]
p1 = figure(plot_width=640, plot_height=640, title="ptc gains")
p1.vbar(top=ptc_h, x=ptc_edges[1:], width=width, alpha=0.3, fill_color="red")

amp_names = np.array(list(ptc_gain["R01_S00"].keys()))
amp_names_shaped = np.empty((2,8), dtype=object)
amp_names_shaped[0,:] = amp_names[8:15]
amp_names_shaped[1,:] = amp_names[0:7]
amp_names_flat = amp_names_shaped.flatten()

# CCD defined as 1 unit. 8 amps per half, so each is 1/8=0.125 wide and 0.5 high.
# rafts are 3 CCDs wide and tall, hence 3 units.

amp_width = 0.125
amp_length = 1.
segments = 8
amps = 2

fp = figure(height=1000, width=1000, title="Focal plane", tools="hover")

x = np.arange(segments) * amp_width
y = np.arange(amps) * amp_length/2.
x, y = np.meshgrid(x, y)

x_flat = x.flatten()
y_flat = y.flatten()

min_z = min(filtered_gains)
max_z = max(filtered_gains)

raft_groups = [["R00", "R01", "R02", "R03", "R04"],
              ["R10", "R11", "R12", "R13", "R14"],
              ["R20", "R21", "R22", "R23", "R24"],
              ["R30", "R31", "R32", "R33", "R34"],
              ["R40", "R41", "R42", "R43", "R44"]]

ccd_groups = [["S00", "S01", "S02"],
             ["S10", "S11", "S12"],
             ["S20", "S21", "S22"]]


def make_ccd(x_offset, y_offset, raft_id, ccd_id, test_results):
    #signal = np.array(test_results)[::-1].reshape((2, 8))
    signal = np.zeros((2, 8))
    signal[0, :] = test_results[8:]
    signal[1, :] = test_results[:8]
    z_flat = signal.flatten()
    raft = np.full(len(z_flat), raft_id)
    ccd = np.full(len(z_flat), ccd_id)

    source = ColumnDataSource(data=dict(x=x_flat+x_offset, y=y_flat+y_offset, z=z_flat, ccd=ccd,
                                        raft=raft, amp=amp_names_flat))
    g = Rect(x='x', y='y', width=amp_width, height=amp_length/2., line_color="black")

    # Step 5: Add tooltips
    hover = fp.select(dict(type=HoverTool))
    hover.tooltips = [("ptc_gain", "@z"), ("ccd", "@ccd"), ("raft", "@raft"),
                      ("amp", "@amp")]

    return source, g


# Add a color bar
color_mapper = LinearColorMapper(palette="Viridis256", low=min_z, high=max_z)

color_bar = ColorBar(color_mapper=color_mapper, location=(0, 0))
fp.add_layout(color_bar, 'right')

"""
raft_ccd = "R01_S00"
ptc_results = np.array(list(ptc_gain[raft_ccd].values()))

source, g = make_ccd(x_offset=0, y_offset=0, raft_id="R01", ccd_id="S00", test_results=ptc_results)
g.fill_color = {'field': 'z', 'transform': color_mapper}
fp.add_glyph(source, g)

raft_ccd = "R01_S10"
ptc_results = np.array(list(ptc_gain[raft_ccd].values()))
source_1, g_1 = make_ccd(x_offset=0, y_offset=2, raft_id="R01", ccd_id="S10", test_results=ptc_results)
g_1.fill_color = {'field': 'z', 'transform': color_mapper}
fp.add_glyph(source_1, g_1)
"""

raft_offset_x = 0
raft_offset_y = 0

y_scale = 3
x_scale = 3

for rg in raft_groups:
    for r in rg:
        if "R00" in r:
            raft_offset_x = x_scale * amp_length
            raft_offset_y = 0
            continue
        if "R40" in r:
            raft_offset_x = x_scale * amp_length
            #raft_offset_y += y_scale * amp_length
            continue
        if "R04" in r:
            raft_offset_x = 0
            #raft_offset_y = y_scale * amp_length
            continue
        if "R44" in r:
            continue

        ccd_offset_x = 0
        ccd_offset_y = 0

        print(r, raft_offset_x, raft_offset_y)
        for cd in ccd_groups:
            for c in cd:
                raft_ccd = r + "_" + c
                ptc_results = np.array(list(ptc_gain[raft_ccd].values()))

                x_offset = ccd_offset_x + raft_offset_x
                y_offset = ccd_offset_y + raft_offset_y
                source, g = make_ccd(x_offset=x_offset, y_offset=y_offset, raft_id=r, ccd_id=c,
                                     test_results=ptc_results)
                g.fill_color = {'field': 'z', 'transform': color_mapper}
                fp.add_glyph(source, g)

                ccd_offset_x += amp_length
            ccd_offset_y += amp_length
            ccd_offset_x = 0

        raft_offset_x += y_scale * amp_length

    raft_offset_x = 0
    raft_offset_y += y_scale * amp_length


fp.title.text = "Full focal plane: ptc_gains"

output_file("/Volumes/Data/Rubin/camera/trial_fp_builder.html")
l = layout(row(fp, p1))
save(l, title="trial focal plane")
