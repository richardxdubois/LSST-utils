import numpy as np
import itertools
import pickle
from copy import deepcopy
import yaml
import argparse
from tornado.ioloop import IOLoop
try:
    import lsst.daf.butler as daf_butler
    import lsst.eo.pipe as eo_pipe
    DM_stack = True
except ImportError:
    DM_stack = False

from bokeh.models.widgets import DataTable, TableColumn, Div, NumberFormatter
from bokeh.models.formatters import DatetimeTickFormatter
from bokeh.models import (RangeSlider, Rect, HoverTool, ColorBar, LinearColorMapper, ColumnDataSource, Select, Button,
                          TextInput, TapTool, RadioButtonGroup, Range1d)
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
try:
    do_CR = data["do_CR"]
except KeyError:
    do_CR = False

title_run_base = data["in_file_name"]

serial_numbers_pkl = data_dir + data["serial_numbers_pkl"]

message_log = []


def clip_limits(test, threshold):

    """
    mask = ~np.isnan(test)
    median = np.median(test[mask])
    std = np.std(test[mask])

    lower = max(min(test), median - threshold * std)
    upper = min(max(test), median + threshold * std)

    """

    # Calculate Q1 (25th percentile) and Q3 (75th percentile)
    Q1 = np.percentile(test, 25)
    Q3 = np.percentile(test, 75)

    # Calculate the IQR
    IQR = Q3 - Q1

    # Define outlier bounds
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR

    lower = max(min(test), lower)
    upper = min(max(test), upper)

    return lower, upper


def re_histogram(cds, width_name, test, lower, upper):

    t_hist, t_edges = np.histogram(test, bins=100, range=(lower, upper))
    width = t_edges[1] - t_edges[0]
    t_vbar_width = np.ones_like(t_hist) * width
    cds.data = {"top": t_hist, "x": t_edges[:-1], width_name: t_vbar_width}


def generate_log_message(log_div, message):
    message_log.append(message)

    if len(message_log) > 5:
        message_log.pop(0)

    log_div.text = "Log: <br>" + "<br>".join(message_log)
    curdoc().add_next_tick_callback(lambda: None)


p = None

with open(in_file, 'rb') as f:
    p = pickle.load(f)

tests = list(p.keys())
test_name = tests[11]
second_test_name = test_name

with open(serial_numbers_pkl, 'rb') as sn:
    serial_numbers = pickle.load(sn)

clip_threshold = 5.
t2_lower = 0
t2_upper = 0

test_run = None

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

current_raft = None

raft_border = 0.2
ccd_border = 0.05

fp = figure(height=1000, width=1000, title="Focal plane", tools="pan,wheel_zoom,box_zoom,lasso_select,reset,save,hover")

# placeholder figures
fp2 = figure(height=320, width=640, title="2nd test", tools="pan,wheel_zoom,box_zoom,reset,save,hover")
fp2.visible = False

fp2s = figure(height=320, width=640, title="2nd test scatter", tools="pan,wheel_zoom,box_zoom,reset,save,hover")
fp2s.visible = False

# set up the grid of amps

x = np.arange(segments) * amp_width
y = np.arange(amps) * amp_length/2.
xg, yg = np.meshgrid(x, y)
xr, yr = np.meshgrid(y, x)

x_flat = xg.flatten()
y_flat = yg.flatten()
xr_flat = xr.flatten()
yr_flat = yr.flatten()


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

start_raft = {}
x_0 = raft_border
y_0 = raft_border

for rg in raft_groups:
    for r in rg:
        start_raft[r] = [x_0, y_0]
        x_0 += 3 * amp_length + raft_border
    y_0 += 3 * amp_length + raft_border
    x_0 = raft_border

start_ccd = {}
x_0 = ccd_border
y_0 = ccd_border

for cg in ccd_groups:
    for c in cg:
        start_ccd[c] = [x_0, y_0]
        x_0 += amp_length + ccd_border
    y_0 += amp_length + ccd_border
    x_0 = ccd_border

CR_layout = {
    "R00": {
        "SG0": ["S21", 0.],
        "SG1": ["S12", 0.],
        "SW": ["S22", 0.]
    },
    "R04": {
        "SG0": ["S21", 0.],
        "SG1": ["S10", 0.],
        "SW": ["S20", np.pi/2.]
    },
    "R40": {
        "SG0": ["S01", 0.],
        "SG1": ["S12", 0.],
        "SW": ["S02", np.pi/2.]
    },
    "R44": {
        "SG0": ["S10", 0.],
        "SG1": ["S01", 0.],
        "SW": ["S00", 0.]
    }
}


def CR_grid(raft):

    # composed of 4 sensors, 2 SW (each with 8 channels) and 2 SG with 16. The layout is rotated counterclockwise
    # use R00 as the template, starting with SG1

    CR_x = np.empty(0)
    CR_y = np.empty(0)
    CR_ccd = np.empty(0)
    CR_angle = np.empty(0)

    x_SG1 = x_flat + start_ccd[CR_layout[raft]["SG1"][0]][0]
    CR_x = np.append(CR_x, x_SG1)
    y_SG1 = y_flat + start_ccd[CR_layout[raft]["SG1"][0]][1]
    CR_y = np.append(CR_y, y_SG1)
    CR_ccd = np.append(CR_ccd, np.full(16, "SG1"))
    CR_angle = np.append(CR_angle, np.full(16, CR_layout[raft]["SG1"][1]))

    if raft == "R00" or raft == "R44":
        x_SW = x_flat + start_ccd[CR_layout[raft]["SW"][0]][0]
        y_SW = y_flat + start_ccd[CR_layout[raft]["SW"][0]][1]
    else:
        x_SW = xr_flat + start_ccd[CR_layout[raft]["SW"][0]][0] + (amp_width + ccd_border)
        y_SW = yr_flat + start_ccd[CR_layout[raft]["SW"][0]][1] - (amp_width + ccd_border)

    CR_x = np.append(CR_x, x_SW)
    CR_y = np.append(CR_y, y_SW)

    CR_ccd = np.append(CR_ccd, np.full(8, "SW1"))
    CR_ccd = np.append(CR_ccd, np.full(8, "SW0"))
    CR_angle = np.append(CR_angle, np.full(16, CR_layout[raft]["SW"][1]))

    x_SG = x_flat + start_ccd[CR_layout[raft]["SG0"][0]][0]
    y_SG = y_flat + start_ccd[CR_layout[raft]["SG0"][0]][1]

    CR_x = np.append(CR_x, x_SG)
    CR_y = np.append(CR_y, y_SG)

    CR_ccd = np.append(CR_ccd, np.full(16, "SG0"))
    CR_angle = np.append(CR_angle, np.full(16, CR_layout[raft]["SG0"][1]))

    CR_x += start_raft[raft][0]
    CR_y += start_raft[raft][1]

    CR_raft = np.full(len(CR_x), raft)
    CR_raft_type = np.full(len(CR_x), serial_numbers[raft]["type"])

    return CR_x, CR_y, CR_ccd, CR_raft, CR_angle, CR_raft_type


def get_CR_test(raft):

    new_test = np.empty(0)
    amp_names = np.empty(0)

    raft_ccd = raft + "_SG1"
    try:
        results = np.array(list(test_data[raft_ccd].values()))[::-1]
    except:
        results = np.ones(16) * -1000.

    signal = np.zeros((2, 8))
    signal[1, :] = results[8:16][::-1]
    signal[0, :] = results[0:8]
    z_flat = signal.flatten()
    new_test = np.append(new_test, z_flat)

    try:
        amp_n = np.array(list(test_data[raft_ccd].keys()))[::-1]
    except:
        amp_n = np.full(16, "SG1")

    amp_n_shaped = np.empty((2, 8), dtype=object)
    amp_n_shaped[1, :] = amp_n[8:16][::-1]
    amp_n_shaped[0, :] = amp_n[0:8]
    amp_n_flat = amp_n_shaped.flatten()
    amp_names = np.append(amp_names, amp_n_flat)

    signal = np.zeros((2, 8))
    SW1 = raft + "_SW1"
    results = np.array(list(test_data[SW1].values()))[::-1]
    signal[0, :] = results[::-1]
    SW0 = raft + "_SW0"
    results = np.array(list(test_data[SW0].values()))
    signal[1, :] = results
    z_flat = signal.flatten()
    new_test = np.append(new_test, z_flat)

    try:
        amp_n0 = np.array(list(test_data[SW1].keys()))[::-1]
        amp_n1 = np.array(list(test_data[SW0].keys()))[::-1]
    except:
        amp_n1 = np.full(8, "SW1")
        amp_n0 = np.full(8, "SW0")

    amp_n_shaped = np.empty((2, 8), dtype=object)
    amp_n_shaped[1, :] = amp_n1[::-1]
    amp_n_shaped[0, :] = amp_n0
    amp_n_flat = amp_n_shaped.flatten()
    amp_names = np.append(amp_names, amp_n_flat)

    raft_ccd = raft + "_SG0"
    try:
        results = np.array(list(test_data[raft_ccd].values()))[::-1]
    except:
        results = np.ones(16) * -1000.

    signal = np.zeros((2, 8))
    signal[1, :] = results[8:16][::-1]
    signal[0, :] = results[0:8]
    z_flat = signal.flatten()
    new_test = np.append(new_test, z_flat)

    try:
        amp_n = np.array(list(test_data[raft_ccd].keys()))[::-1]
    except:
        amp_n = np.full(16, "SG0")

    amp_n_shaped = np.empty((2, 8), dtype=object)
    amp_n_shaped[1, :] = amp_n[8:16][::-1]
    amp_n_shaped[0, :] = amp_n[0:8]
    amp_n_flat = amp_n_shaped.flatten()

    amp_names = np.append(amp_names, amp_n_flat)

    return new_test, amp_names

"""
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
"""


def get_new_test(test_name, single_raft=None):
    t_name = test_name

    if "HIGH" in test_name or "LOW" in test_name:
        t_name_split = test_name.split("_")
        t_name = (t_name_split[0], t_name_split[1])

    test_data = p[t_name]

    new_test = np.empty(0)

    for rg in raft_groups:
        for r in rg:
            if single_raft is not None and r != single_raft:
                continue

            if r in list(CR_layout.keys()):
                if do_CR:
                    R00_test, _ = get_CR_test(r)
                    new_test = np.append(new_test, R00_test)
                continue
            """
            if "R40" in r:
               continue
            if "R04" in r:
                continue
            if "R44" in r:
                continue
            """

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


def get_new_run(run_name):
    generate_log_message(log_div, "Entered get_new_run " + run_name)
    repo = "/repo/main"
    butler = daf_butler.Butler(repo)

    acq_run = run_name  # form is run-id_<weekly>, eg E2233_d_2025_01_27

    pattern = f"u/lsstccs/eo_*_{acq_run}"
    collections = butler.registry.queryCollections(pattern)

    amp_data = eo_pipe.get_amp_data(repo, collections)
    generate_log_message(log_div, "new amp data acquired")

    return amp_data


# Add a color bar

color_mapper = LinearColorMapper(palette="Inferno256", low=min_z, high=max_z)

color_bar = ColorBar(color_mapper=color_mapper, location=(0, 0))
fp.add_layout(color_bar, 'right')

raft_offset_x = 0
raft_offset_y = 0

y_scale = 3
x_scale = 3

source_dict_fp = {"x":[], "y":[], "z":[], "ccd":[], "raft":[], "amp":[], "test2":[], "angle":[], "raft_type":[]}

for rg in raft_groups:
    for r in rg:
        if r in CR_layout.keys():
            raft_offset_x = x_scale * amp_length
            raft_offset_y = 0
            if do_CR:
                CR_x, CR_y, CR_ccd, CR_raft, CR_angle, CR_raft_type = CR_grid(r)
                R00_test, CR_amp = get_CR_test(r)

                source_dict_fp["x"].extend(CR_x)
                source_dict_fp["y"].extend(CR_y)
                source_dict_fp["z"].extend(R00_test)
                source_dict_fp["ccd"].extend(CR_ccd)
                source_dict_fp["raft"].extend(CR_raft)
                source_dict_fp["amp"].extend(CR_amp)
                source_dict_fp["angle"].extend(CR_angle)
                source_dict_fp["raft_type"].extend(CR_raft_type)

            continue
        """
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
        """

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
                angle = np.zeros(len(z_flat))
                raft_type = np.full(len(z_flat), serial_numbers[r]["type"])

                #x_offset = ccd_offset_x + raft_offset_x
                #y_offset = ccd_offset_y + raft_offset_y

                x_offset = start_raft[r][0] + start_ccd[c][0]
                y_offset = start_raft[r][1] + start_ccd[c][1]
                #source, g = make_ccd(x_offset=x_offset, y_offset=y_offset, raft_id=r, ccd_id=c,
                #                     test_results=results)
                #g.fill_color = {'field': 'z', 'transform': color_mapper}
                #fp.add_glyph(source, g)

                x_new = x_flat + x_offset
                y_new = y_flat + y_offset

                source_dict_fp["x"].extend(x_new)
                source_dict_fp["y"].extend(y_new)
                source_dict_fp["z"].extend(z_flat)
                source_dict_fp["ccd"].extend(ccd)
                source_dict_fp["raft"].extend(raft)
                source_dict_fp["amp"].extend(amp_names_flat)
                source_dict_fp["angle"].extend(angle)
                source_dict_fp["raft_type"].extend(raft_type)

                ccd_offset_x += amp_length
            ccd_offset_y += amp_length
            ccd_offset_x = 0

        raft_offset_x += y_scale * amp_length

    raft_offset_x = 0
    raft_offset_y += y_scale * amp_length

source_dict_fp["test2"] = source_dict_fp["z"]

source_dict_raft = {"x":[], "y":[], "z":[], "ccd":[], "raft":[], "amp":[], "test2":[], "angle":[], "raft_type":[]}

r = "R01"
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
        angle = np.zeros(len(z_flat))
        raft_type = np.full(len(z_flat), serial_numbers[r]["type"])

        x_offset = start_raft[r][0] + start_ccd[c][0]
        y_offset = start_raft[r][1] + start_ccd[c][1]

        x_new = x_flat + x_offset
        y_new = y_flat + y_offset

        source_dict_raft["x"].extend(x_new)
        source_dict_raft["y"].extend(y_new)
        source_dict_raft["z"].extend(z_flat)
        source_dict_raft["ccd"].extend(ccd)
        source_dict_raft["raft"].extend(raft)
        source_dict_raft["amp"].extend(amp_names_flat)
        source_dict_raft["angle"].extend(angle)
        source_dict_raft["raft_type"].extend(raft_type)

source_dict_raft["test2"] = source_dict_raft["z"]

if do_CR:
    r = "R00"
    source_dict_CR = {"x":[], "y":[], "z":[], "ccd":[], "raft":[], "amp":[], "test2":[], "angle":[], "raft_type":[]}

    CR_x, CR_y, CR_ccd, CR_raft, CR_angle, CR_raft_type = CR_grid(r)
    R00_test, CR_amp = get_CR_test(r)

    source_dict_CR["x"].extend(CR_x)
    source_dict_CR["y"].extend(CR_y)
    source_dict_CR["z"].extend(R00_test)
    source_dict_CR["ccd"].extend(CR_ccd)
    source_dict_CR["raft"].extend(CR_raft)
    source_dict_CR["amp"].extend(CR_amp)
    source_dict_CR["angle"].extend(CR_angle)
    source_dict_CR["raft_type"].extend(CR_raft_type)

    source_dict_CR["test2"] = source_dict_CR["z"]

source_dict = deepcopy(source_dict_fp)
source = ColumnDataSource(source_dict)

g = Rect(x='x', y='y', width=amp_width, height=amp_length / 2., angle='angle', line_color="black")
g.fill_color = {'field': 'z', 'transform': color_mapper}
fp.add_glyph(source, g)

# Step 5: Add tooltips
hover = fp.select(dict(type=HoverTool))
hover.tooltips = [("type", "@raft_type"), ("test", "@z"), ("ccd", "@ccd"), ("raft", "@raft"),
                  ("amp", "@amp")]

fp.title.text = title_run_base + " Full focal plane: " + test_name
#  Suppress Axes
fp.xaxis.visible = False  # Hide x-axis
fp.yaxis.visible = False  # Hide y-axis

#  Suppress Grid Lines
fp.xgrid.grid_line_color = None  # Remove x-grid lines
fp.ygrid.grid_line_color = None  # Remove y-grid lines

mask = ~np.isnan(source_dict["z"])
z_u = np.array(source_dict["z"])[mask]
lower, upper = clip_limits(z_u, clip_threshold)

res_h, res_edges = np.histogram(z_u, bins=100, range=(lower, upper))
vbar_width = np.ones_like(res_h) * (res_edges[1] - res_edges[0])

hist_source = ColumnDataSource(data=dict(top=res_h, x=res_edges[:-1], vbar_width=vbar_width))
source_static = deepcopy(source_dict)

p1 = figure(width=640, height=640, title=test_name)
p1.vbar(top="top", x="x", width="vbar_width", alpha=0.3, fill_color="red", source=hist_source,)

step = (upper - lower) / 20.
slider = RangeSlider(start=lower, end=upper, value=(lower, upper), step=step, title="test value range")

color_mapper.low = lower * 0.8 if lower > 0 else lower * 1.2
color_mapper.high = upper * 1.1

# set up the second test histogram

test2_u = np.array(source_dict["test2"])[mask]
lower, upper = clip_limits(test2_u, clip_threshold)

t2_res_h, t2_res_edges = np.histogram(test2_u, bins=100, range=(lower, upper))
t2_vbar_width = np.ones_like(t2_res_h) * (t2_res_edges[1] - t2_res_edges[0])

t2_hist_source = ColumnDataSource(data=dict(top=t2_res_h, x=t2_res_edges[:-1], t2_vbar_width=vbar_width))
fp2.vbar(top="top", x="x", width="t2_vbar_width", alpha=0.3, fill_color="red", source=t2_hist_source)

fp2s.scatter(x="z", y="test2", source=source)

# Create a new list with tuple elements replaced by joined strings - some test names are tuples
name_list = []

for elem in tests:
    if isinstance(elem, tuple) and len(elem) == 2:
        name_list.append(f"{elem[0]}_{elem[1]}")
    else:
        name_list.append(elem)

name_dropdown = Select(title="Pick test", value=test_name, options=name_list)
second_dropdown = Select(title="Pick second test", value=second_test_name, options=name_list)
second_dropdown.visible = False

type_dropdown = Select(title="Pick type", value="all", options=["all", "E2V", "ITL"])

log_div = Div(text="Log:<br>", width=400, height=150)

run_text_box = TextInput(title="Pick run", value="None")
if not DM_stack:
    run_text_box.visible = False
    generate_log_message(log_div, "No DM stack or EO - run selection disabled")

clip_select = TextInput(title="Set clip sigma", value=str(clip_threshold), width=75)

# Create a Button to exit the server
exit_button = Button(label="Exit", button_type="danger")

# Create RadioGroup to handle second histogram mode
second_toggle = RadioButtonGroup(labels=["On", "Off"], active=1)
st_div = Div(text="Second histos")


# Define a function to stop the server
def stop_server():
    generate_log_message(log_div, ("Server is shutting down..."))
    print("Server is shutting down...")
    IOLoop.current().stop()

# Attach the stop function to the button click event

exit_button.on_click(stop_server)

# Add TapTool
taptool = TapTool()
fp.add_tools(taptool)


# Define a callback function for TapTool
def tap_callback(event):
    global source
    selected = source.selected
    try:
        selected_index = source.selected.indices[0]
    except IndexError:
        generate_log_message(log_div, "Hit whitespace! Try again")
        return

    selected_data = source.data
    raft_value = selected_data['raft'][selected_index]
    ccd_value = selected_data['ccd'][selected_index]
    amp_value = selected_data['amp'][selected_index]
    # Unselect at the end of the callback
    source.selected.indices = []
    generate_log_message(log_div, f"Selected raft: {raft_value}, ccd: {ccd_value}, amp: {amp_value}")

    global current_raft
    global source_static

    if current_raft is None:
        current_raft = raft_value
        if do_CR and current_raft in list(CR_layout.keys()):
            source.data = dict(x=source_dict_CR["x"], y=source_dict_CR["y"], z=source_dict_CR["z"],
                               ccd=source_dict_CR["ccd"], raft=source_dict_CR["raft"], amp=source_dict_CR["amp"],
                               angle=source_dict_CR["angle"], raft_type=source_dict_CR["raft_type"])
            source_static = deepcopy(source_dict_CR)
        else:
            source.data = dict(x=source_dict_raft["x"], y=source_dict_raft["y"], z=source_dict_raft["z"],
                               ccd=source_dict_raft["ccd"], raft=source_dict_raft["raft"], amp=source_dict_raft["amp"],
                               angle=source_dict_raft["angle"], raft_type=source_dict_raft["raft_type"])

            source_static = deepcopy(source_dict_raft)

        new_test_data = get_new_test(test_name, single_raft=current_raft)
        source.data["z"] = list(new_test_data)
        source_static["z"] = list(new_test_data)
        t2_new_test_data = get_new_test(second_test_name, single_raft=current_raft)
        source.data["test2"] = list(t2_new_test_data)
        source_static["test2"] = list(t2_new_test_data)
        fp.title.text = title_run_base + " " + current_raft + ": " + test_name
        generate_log_message(log_div, "Switched to single raft mode: " + current_raft)
    else:
        current_raft = None
        source.data = dict(x=source_dict_fp["x"], y=source_dict_fp["y"], z=source_dict_fp["z"],
                           ccd=source_dict_fp["ccd"], raft=source_dict_fp["raft"], amp=source_dict_fp["amp"],
                           angle=source_dict_fp["angle"], raft_type=source_dict_fp["raft_type"])

        source_static = deepcopy(source_dict_fp)
        new_test_data = get_new_test(test_name)
        source.data["z"] = list(new_test_data)
        source_static["z"] = list(new_test_data)
        t2_new_test_data = get_new_test(second_test_name)
        source.data["test2"] = list(t2_new_test_data)
        source_static["test2"] = list(t2_new_test_data)
        fp.title.text = title_run_base + " Full focal plane: " + test_name

        generate_log_message(log_div, "Switched to full fp mode")

    lower, upper = slider.value

    z_u = np.array(source.data["z"])
    raft_type = np.array(source.data["raft_type"])

    mask = ~np.isnan(z_u)

    new_test_noNan = z_u[mask]

    c_lower, c_upper = clip_limits(new_test_noNan, clip_threshold)

    slider.remove_on_change('value_throttled', update)
    slider.start = c_lower
    slider.end = c_upper
    slider.value = (c_lower, c_upper)
    slider.on_change('value_throttled', update)

    re_histogram(hist_source, "vbar_width", new_test_noNan, c_lower, c_upper)

    """
    hist, edges = np.histogram(new_test_data[mask], bins=100, range=(lower, upper))
    width = edges[1] - edges[0]
    vbar_width = np.ones_like(hist) * width
    hist_source.data = dict(top=hist, x=edges[:-1], vbar_width=vbar_width)
    """

    p1.title.text = test_name

    # re histogram 2nd test
    t2z = np.array(source.data["test2"])
    t2_mask = ~np.isnan(t2z)
    t2_new_noNaN = t2z[t2_mask]

    t2_lower, t2_upper = clip_limits(t2_new_noNaN, clip_threshold)

    re_histogram(t2_hist_source, "t2_vbar_width", t2z, t2_lower, t2_upper)

    fp2s.y_range = Range1d(start=t2_lower, end=t2_upper)
    fp2s.x_range = Range1d(start=c_lower, end=c_upper)

    """
    t2_hist, t2_edges = np.histogram(t2_new_noNaN, bins=100, range=(t2_lower, t2_upper))
    width = t2_edges[1] - t2_edges[0]
    t2_vbar_width = np.ones_like(t2_hist) * width
    t2_hist_source.data = dict(top=t2_hist, x=t2_edges[:-1], t2_vbar_width=t2_vbar_width)
    """

    generate_log_message(log_div, "Ready")


# Attach the callback to the TapTool's event
fp.on_event('tap', tap_callback)


# Define a callback to toggle the visibility of the plot
def second_callback(attr, old, new):
    if second_toggle.active == 0:  # "On"
        fp2.visible = True
        fp2s.visible = True
        second_dropdown.visible = True
        p1.height = 320
    else:  # "Off"
        fp2.visible = False
        fp2s.visible = False
        second_dropdown.visible = False
        p1.height = 640


second_toggle.on_change("active", second_callback)


# Define callback to update the data
def update(attr, old, new):
    # Get the new range from the slider
    lower, upper = slider.value
    selected_name = name_dropdown.value
    second_name = second_dropdown.value
    selected_run = run_text_box.value
    global source_static
    global test_name
    global second_test_name
    global test_run
    global p
    global t2_upper
    global t2_lower
    global title_run_base
    global clip_threshold

    if clip_threshold != float(clip_select.value):
        clip_threshold = float(clip_select.value)
        generate_log_message(log_div, "Clipping threshold set to " + str(clip_threshold))

    # who triggered this?
    w = new == run_text_box.value
    d = new == name_dropdown.value
    s = new == second_dropdown.value

    new_run = False
    if selected_run != test_run and w:
        if DM_stack:
            generate_log_message(log_div, "run_text_box selected: " + selected_run)
            p = get_new_run(selected_run)
            generate_log_message(log_div, selected_run + " loaded")
            test_run = selected_run
            title_run_base = test_run
            new_run = True
        else:
            generate_log_message(log_div, "DM stack or EO code unavailble. Request ignored: " + selected_run)
            return

    if (d and selected_name != test_name) or new_run:
        generate_log_message(log_div,"getting new test data: " + selected_name)
        new_test_data = get_new_test(selected_name, current_raft)
        source_static["z"] = list(new_test_data)

        if not new_run:
            test_name = selected_name
        generate_log_message(log_div,"updating sliders for : " + selected_name)

        slider.remove_on_change('value_throttled', update)
        slider.start, slider.end = clip_limits(new_test_data, clip_threshold)
        slider.value = (slider.start, slider.end)
        slider.on_change('value_throttled', update)

        lower = slider.start
        upper = slider.end
        color_mapper.low = lower * 0.8 if lower > 0 else lower * 1.2
        color_mapper.high = upper * 1.1

    if (s and second_test_name != second_name) or new_run:
        generate_log_message(log_div, "getting new second test data: " + second_name)
        t2_new_test_data = get_new_test(second_name, current_raft)
        source_static["test2"] = list(t2_new_test_data)

        if not new_run:
            second_test_name = second_name

    x_u = np.array(source_static["x"])
    y_u = np.array(source_static["y"])
    z_u = np.array(source_static["z"])
    raft_type = np.array(source_static["raft_type"])
    r_u = np.array(source_static["raft"])
    c_u = np.array(source_static["ccd"])
    amp_u = np.array(source_static["amp"])
    test2 = np.array(source_static["test2"])

    # Filter the data source based on the range and selected name
    if type_dropdown.value != "all":
        pos_mask = (z_u >= lower) & (z_u <= upper) & (~np.isnan(z_u)) & (raft_type == type_dropdown.value)
        mask = ((z_u < lower) | (z_u > upper) | np.isnan(z_u)) | (raft_type != type_dropdown.value)
    else:
        pos_mask = (z_u >= lower) & (z_u <= upper) & (~np.isnan(z_u))
        mask = (z_u < lower) | (z_u > upper) | np.isnan(z_u)

    z_u[mask] = lower / 10.
    source.data["z"] = z_u
    source.data["test2"] = source_static["test2"]
    #source.data = new_data


    # Update the histogram
    #new_zu = np.array(new_data["z"])
    generate_log_message(log_div, "about to remake histogram")

    new_zu = np.array(source.data["z"])
    re_histogram(hist_source, "vbar_width", new_zu, lower, upper)
    """
    hist, edges = np.histogram(new_zu, bins=100, range=(lower, upper))
    width = edges[1] - edges[0]
    vbar_width = np.ones_like(hist) * width
    hist_source.data = dict(top=hist, x=edges[:-1], vbar_width=vbar_width)
    """

    p1.title.text = test_name

    # re histogram 2nd test

    t2_new_zu = np.array(source.data["test2"])[pos_mask]
    t2_mask = ~np.isnan(t2_new_zu)
    #hist, edges = np.histogram(new_zu, bins=100)

    mean = np.mean(t2_new_zu[t2_mask])
    std = np.std(t2_new_zu[t2_mask])

    t2_lower, t2_upper = clip_limits(t2_new_zu[t2_mask], clip_threshold)

    # Create a mask for elements within the threshold
    mask = (t2_new_zu > t2_lower) & (t2_new_zu < t2_upper)

    # Filter the data
    clipped_data = t2_new_zu[mask]

    re_histogram(t2_hist_source, "t2_vbar_width", clipped_data, t2_lower, t2_upper)

    fp2.title.text = second_test_name
    fp2s.yaxis.axis_label = second_name
    fp2s.xaxis.axis_label = test_name
    fp2s.y_range = Range1d(start=t2_lower, end=t2_upper)
    fp2s.x_range = Range1d(start=lower, end=upper)

    if current_raft is None:
        fp.title.text = title_run_base + " Full focal plane: " + test_name
    else:
        fp.title.text = title_run_base + " " + current_raft + " " + test_name

    generate_log_message(log_div, "Ready")

# Attach the callback to the slider and dropdown
slider.on_change('value_throttled', update)
name_dropdown.on_change('value', update)
second_dropdown.on_change('value', update)
run_text_box.on_change('value', update)
clip_select.on_change('value', update)
type_dropdown.on_change('value', update)

#output_file("/Volumes/Data/Rubin/camera/trial_fp_builder.html")
l = layout(exit_button, row( type_dropdown, column(run_text_box, clip_select), name_dropdown, slider,
                             column(st_div, second_toggle),
                             second_dropdown, log_div),
           row(fp, column(p1, fp2s, fp2)))
#save(l, title="trial focal plane")

# Add the layout to the current document
curdoc().add_root(l)
