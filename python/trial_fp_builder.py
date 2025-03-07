import numpy as np
import itertools
import pickle
from copy import deepcopy
import yaml
import argparse
from tornado.ioloop import IOLoop

from bokeh.models.widgets import DataTable, TableColumn, Div, NumberFormatter
from bokeh.models.formatters import DatetimeTickFormatter
from bokeh.models import RangeSlider, Rect, HoverTool, ColorBar, LinearColorMapper, ColumnDataSource, Select, Button
from bokeh.plotting import figure, output_file, reset_output, show, save, curdoc
from bokeh.layouts import row, layout, column
from bokeh.transform import transform

parser = argparse.ArgumentParser()

parser.add_argument('--app_config',
                    default="process_exposure_config.yaml",
                    help="overall app config file")
args = parser.parse_args()

with open(args.app_config, "r") as f:
    data = yaml.safe_load(f)

#data_dir = "/Volumes/Data/Rubin/camera/"
#in_file = data_dir + "E2233_amps_data.npy"

data_dir = data["data_dir"]
in_file = data_dir + data["in_file_name"]

p = None

with open(in_file, 'rb') as f:
    p = pickle.load(f)

tests = list(p.keys())
test_name = tests[11]
print(tests)

test_data = p[test_name]
gains = np.array(list(itertools.chain.from_iterable(amplifier.values()
                                           for amplifier in test_data.values())))
filtered_gains = gains[~np.isnan(gains)]

amp_names = np.array(list(test_data["R01_S00"].keys()))[::-1]
amp_names_shaped = np.empty((2,8), dtype=object)
amp_names_shaped[1, :] = amp_names[8:16][::-1]
amp_names_shaped[0, :] = amp_names[0:8]
amp_names_flat = amp_names_shaped.flatten()

# CCD defined as 1 unit. 8 amps per half, so each is 1/8=0.125 wide and 0.5 high.
# rafts are 3 CCDs wide and tall, hence 3 units.

amp_width = 0.125
amp_length = 1.
segments = 8
amps = 2

fp = figure(height=1000, width=1000, title="Focal plane", tools="pan,wheel_zoom,box_zoom,lasso_select,reset,save,hover")

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

    signal = np.zeros((2, 8))
    signal[1, :] = test_results[8:16][::-1]
    signal[0, :] = test_results[0:8]
    z_flat = signal.flatten()
    raft = np.full(len(z_flat), raft_id)
    ccd = np.full(len(z_flat), ccd_id)

    source = ColumnDataSource(data=dict(x=x_flat+x_offset, y=y_flat+y_offset, z=z_flat, ccd=ccd,
                                        raft=raft, amp=amp_names_flat))
    g = Rect(x='x', y='y', width=amp_width, height=amp_length/2., line_color="black")

    # Step 5: Add tooltips
    hover = fp.select(dict(type=HoverTool))
    hover.tooltips = [(test_name, "@z"), ("ccd", "@ccd"), ("raft", "@raft"),
                      ("amp", "@amp")]

    return source, g


def get_new_test(test_name):
    test_data = p[test_name]

    new_test = np.empty(0)

    for rg in raft_groups:
        for r in rg:
            if "R00" in r:
                continue
            if "R40" in r:
               continue
            if "R04" in r:
                continue
            if "R44" in r:
                continue
           # print(r, raft_offset_x, raft_offset_y)
            for cd in ccd_groups:
                for c in cd:
                    raft_ccd = r + "_" + c
                    results = np.array(list(test_data[raft_ccd].values()))[::-1]
                    signal = np.zeros((2, 8))
                    signal[1, :] = results[8:16][::-1]
                    signal[0, :] = results[0:8]
                    z_flat = signal.flatten()

                    new_test = np.append(new_test, z_flat)

    return new_test

# Add a color bar
color_mapper = LinearColorMapper(palette="Viridis256", low=min_z, high=max_z)

color_bar = ColorBar(color_mapper=color_mapper, location=(0, 0))
fp.add_layout(color_bar, 'right')

raft_offset_x = 0
raft_offset_y = 0

y_scale = 3
x_scale = 3

source_dict = {"x":[], "y":[], "z":[], "ccd":[], "raft":[], "amp":[]}

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

        #print(r, raft_offset_x, raft_offset_y)
        for cd in ccd_groups:
            for c in cd:
                raft_ccd = r + "_" + c
                results = np.array(list(test_data[raft_ccd].values()))[::-1]
                signal = np.zeros((2, 8))
                signal[1, :] = results[8:16][::-1]
                signal[0, :] = results[0:8]
                z_flat = signal.flatten()
                raft = np.full(len(z_flat), r)
                ccd = np.full(len(z_flat), c)

                x_offset = ccd_offset_x + raft_offset_x
                y_offset = ccd_offset_y + raft_offset_y
                #source, g = make_ccd(x_offset=x_offset, y_offset=y_offset, raft_id=r, ccd_id=c,
                #                     test_results=results)
                #g.fill_color = {'field': 'z', 'transform': color_mapper}
                #fp.add_glyph(source, g)

                x_new = x_flat + x_offset
                y_new = y_flat + y_offset

                source_dict["x"].extend(x_new)
                source_dict["y"].extend(y_new)
                source_dict["z"].extend(z_flat)
                source_dict["ccd"].extend(ccd)
                source_dict["raft"].extend(raft)
                source_dict["amp"].extend(amp_names_flat)

                ccd_offset_x += amp_length
            ccd_offset_y += amp_length
            ccd_offset_x = 0

        raft_offset_x += y_scale * amp_length

    raft_offset_x = 0
    raft_offset_y += y_scale * amp_length

source = ColumnDataSource(source_dict)

g = Rect(x='x', y='y', width=amp_width, height=amp_length / 2., line_color="black")
g.fill_color = {'field': 'z', 'transform': color_mapper}
fp.add_glyph(source, g)

# Step 5: Add tooltips
hover = fp.select(dict(type=HoverTool))
hover.tooltips = [("test", "@z"), ("ccd", "@ccd"), ("raft", "@raft"),
                  ("amp", "@amp")]

fp.title.text = "Full focal plane: " + test_name
#  Suppress Axes
fp.xaxis.visible = False  # Hide x-axis
fp.yaxis.visible = False  # Hide y-axis

#  Suppress Grid Lines
fp.xgrid.grid_line_color = None  # Remove x-grid lines
fp.ygrid.grid_line_color = None  # Remove y-grid lines

mask = ~np.isnan(source_dict["z"])
z_u = np.array(source_dict["z"])
res_h, res_edges = np.histogram(z_u[mask], bins=100)
hist_source = ColumnDataSource(data=dict(top=res_h, x=res_edges[:-1]))
source_static = deepcopy(source_dict)

width = res_edges[1] - res_edges[0]
p1 = figure(width=640, height=640, title=test_name)
p1.vbar(top="top", x="x", width=width, alpha=0.3, fill_color="red", source=hist_source,)

step = (max_z - min_z) / 20.
slider = RangeSlider(start=min_z, end=max_z, value=(min_z, max_z), step=step, title="test value range")

name_list = tests  # Unique names sorted
dropdown = Select(title="Pick test", value=name_list[0], options=name_list)

# Create a Button to exit the server
exit_button = Button(label="Exit", button_type="danger")


# Define a function to stop the server
def stop_server():
    print("Server is shutting down...")
    IOLoop.current().stop()

# Attach the stop function to the button click event
exit_button.on_click(stop_server)


# Define callback to update the data
def update(attr, old, new):
    # Get the new range from the slider
    lower, upper = slider.value
    selected_name = dropdown.value
    global source_static
    global test_name

    if selected_name != test_name:
        new_test_data = get_new_test(selected_name)
        source_static["z"] = list(new_test_data)
        test_name = selected_name
        slider.remove_on_change('value', update)
        slider.start = min(new_test_data)
        slider.end = max(new_test_data)
        slider.value = (slider.start, slider.end)
        slider.on_change('value', update)
        lower = slider.start
        upper = slider.end
        color_mapper.low = lower
        color_mapper.high = upper

    x_u = np.array(source_static["x"])
    y_u = np.array(source_static["y"])
    z_u = np.array(source_static["z"])
    r_u = np.array(source_static["raft"])
    c_u = np.array(source_static["ccd"])
    amp_u = np.array(source_static["amp"])

    # Filter the data source based on the range and selected name
    mask = (z_u >= lower) & (z_u <= upper) & (~np.isnan(z_u))
    new_data = dict(x=x_u[mask], y=y_u[mask],
                    z=z_u[mask], raft=r_u[mask],
                    ccd=c_u[mask], amp=amp_u[mask])
    source.data = new_data

    # Update the histogram
    new_zu = np.array(new_data["z"])
    #print("about to remake histogram", len(new_zu))

    hist, edges = np.histogram(new_zu, bins=100)
    hist_source.data = dict(top=hist, x=edges[:-1])


# Attach the callback to the slider and dropdown
slider.on_change('value', update)
dropdown.on_change('value', update)

#output_file("/Volumes/Data/Rubin/camera/trial_fp_builder.html")
l = layout(exit_button, row(dropdown, slider), row(fp, p1))
#save(l, title="trial focal plane")

# Add the layout to the current document
curdoc().add_root(l)
