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
from bokeh.models.formatters import PrintfTickFormatter, BasicTickFormatter
from bokeh.models import (RangeSlider, Rect, HoverTool, ColorBar, LinearColorMapper, ColumnDataSource, Select, Button,
                          TextInput, TapTool, RadioButtonGroup, Range1d, CDSView, BooleanFilter, CustomJSTickFormatter)
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

data_dir = data["data_dir"]
in_file = data_dir + data["in_file_name"]
guard_value = data["guard_value"]

try:
    do_CR = data["do_CR"]
except KeyError:
    do_CR = False

title_run_base = data["in_file_name"]

serial_numbers_pkl = data_dir + data["serial_numbers_pkl"]

message_log = []

log_div = Div(text="Log:<br>", width=400, height=150)


def generate_log_message(log_div, message):
    message_log.append(message)

    if len(message_log) > 5:
        message_log.pop(0)

    log_div.text = "Log: <br>" + "<br>".join(message_log)
    curdoc().add_next_tick_callback(lambda: None)


type_dropdown = Select(title="Pick type", value="all", options=["all", "E2V", "ITL"])


def clip_limits(name, test, threshold):

    mask = (~np.isnan(test)) & (test != guard_value)
    median = np.median(test[mask])
    std = np.std(test[mask])

    lower = max(min(test), median - threshold * std)
    upper = min(max(test), median + threshold * std)

    generate_log_message(log_div, f"{name} Clipping median {median:.2f} std + {std:.2f} thrsh {clip_threshold:.2f}")

    return lower, upper


def do_test_stuff(t_source, h_source, t_test_name, use_slider=True, mask_in=None):

    z_u = np.array(source_static[t_test_name])
    raft_type = np.array(source.data["raft_type"])

    if use_slider:
        lower, upper = slider.value
    else:
        lower, upper = clip_limits(t_test_name, z_u, clip_threshold)

    if mask_in is None:
        # mask is channels failing cuts. Set them to a guard value.
        if type_dropdown.value != "all":
            mask = ((z_u < lower) | (z_u > upper) | np.isnan(z_u)) | (raft_type != type_dropdown.value)
        else:
            mask = (z_u < lower) | (z_u > upper) | np.isnan(z_u)
    else:
        # take mask from main test (probably)
        mask = mask_in

    z_u[mask] = guard_value
    t_source.data[t_test_name] = z_u

    t_mask = (lower <= z_u) & (z_u <= upper)

    if t_test_name == "test2":
        width_name = "t2_vbar_width"
    else:
        width_name = "vbar_width"

    re_histogram(h_source, width_name, z_u[t_mask], lower, upper)

    return lower, upper, mask


def slider_format(lower, upper):
    if slider.format == BasicTickFormatter and abs(lower) > 0.01:
        return

    if lower < 0.01:

        t_lower = np.log(lower)
        t_upper = np.log(upper)
        step = t_upper - t_lower

        try:
            slider.remove_on_change('value_throttled', update)
        except:
            pass

        slider.start, slider.end = (t_lower, t_upper)
        slider.value = (slider.start, slider.end)
        try:
            slider.on_change('value_throttled', update)
        except:
            pass

        slider.format = CustomJSTickFormatter(code="return Math.exp(tick).toFixed(2)")
        slider.step = step
        r_lower = np.exp(t_lower)
        r_upper = np.exp(t_upper)
    else:
        t_lower = lower
        t_upper = upper
        step = t_upper - t_lower

        slider.remove_on_change('value_throttled', update)
        slider.start, slider.end = (t_lower, t_upper)
        slider.value = (slider.start, slider.end)
        slider.on_change('value_throttled', update)
        slider.format = BasicTickFormatter()
        slider.step = step
        r_lower = t_lower
        r_upper = t_upper

    return r_lower, r_upper


def extract_signal_data(test_data, raft_ccd, angle, raft_ccd2=None):
    r, c = raft_ccd.split("_")

    try:
        results = np.array(list(test_data[raft_ccd].values()))[::-1]
        if raft_ccd2 is not None:
            results = np.append(results, np.array(list(test_data[raft_ccd2].values()))[::-1])
    except:
        results = np.ones(16) * guard_value

    if angle == 0.:
        signal = np.zeros((2, 8))
        signal[1, :] = results[8:16][::-1]
        signal[0, :] = results[0:8]
    else:
        signal = np.zeros((8, 2))
        signal[:, 1] = results[8:16][::-1]
        signal[:, 0] = results[0:8]

    return signal.flatten()


def extract_amp_names(test_data, raft_ccd, angle, raft_ccd2=None):
    r, c = raft_ccd.split("_")

    try:
        results = np.array(list(test_data[raft_ccd].keys()))[::-1]
        if raft_ccd2 is not None:
            results = np.append(results, np.array(list(test_data[raft_ccd2].keys()))[::-1])
    except:
        results = np.full(16, c)

    if angle == 0.:
        amps = np.empty((2, 8), dtype=object)
        amps[1, :] = results[8:16][::-1]
        amps[0, :] = results[0:8]
    else:
        amps = np.empty((8, 2), dtype=object)
        amps[:, 1] = results[8:16][::-1]
        amps[:, 0] = results[0:8]

    return amps.flatten()


def re_histogram(cds, width_name, test, lower, upper):

    t_hist, t_edges = np.histogram(test, bins=100, range=(lower, upper))
    width = t_edges[1] - t_edges[0]
    t_vbar_width = np.ones_like(t_hist) * width
    cds.data = {"top": t_hist, "x": t_edges[:-1], width_name: t_vbar_width}


p = None

# get the cached pickle file of amp results

with open(in_file, 'rb') as f:
    p = pickle.load(f)

tests = list(p.keys())
test_name = tests[11]
second_test_name = test_name

# get the radt, CCD serial number etc (from Seth Digel).

with open(serial_numbers_pkl, 'rb') as sn:
    serial_numbers = pickle.load(sn)

clip_threshold = 5.
t2_lower = 0
t2_upper = 0

test_run = None

print(tests)

# start with ptc_gains to get going

test_data = p[test_name]
gains = np.array(list(itertools.chain.from_iterable(amplifier.values()
                                                    for amplifier in test_data.values())))
filtered_gains = gains[~np.isnan(gains)]
min_z = min(filtered_gains)
max_z = max(filtered_gains)

# get the list of amp names
amp_names_flat = extract_amp_names(test_data, raft_ccd="R01_S00", angle=0., raft_ccd2=None)

# CCD defined as 1 unit. 8 amps per half, so each is 1/8=0.125 wide and 0.5 high.
# rafts are 3 CCDs wide and tall, hence 3 units.

amp_width = 0.125
amp_length = 1.
segments = 8
amps = 2

current_raft = None

# define whitespace around the rafts and CCDs

raft_border = 0.2
ccd_border = 0.05

# placeholder figures

fp = figure(height=1000, width=1000, title="Focal plane", tools="pan,wheel_zoom,box_zoom,lasso_select,reset,save,hover")

p1 = figure(width=640, height=640, title=test_name)

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
        "SG0": ["S12", np.pi/2.],
        "SG1": ["S21", 0.],
        "SW": ["S22", 0.]
    },
    "R04": {
        "SG0": ["S21", 0.],
        "SG1": ["S10", np.pi/2.],
        "SW": ["S20", np.pi/2.]
    },
    "R40": {
        "SG0": ["S01", 0.],
        "SG1": ["S12", 3.*np.pi/2.],
        "SW": ["S02", np.pi/2.]
    },
    "R44": {
        "SG0": ["S10", np.pi/2.],
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

    # SG1

    if raft == "R00" or raft == "R44":
        x_SG1 = x_flat + start_ccd[CR_layout[raft]["SG1"][0]][0]
        y_SG1 = y_flat + start_ccd[CR_layout[raft]["SG1"][0]][1]
    else:
        x_SG1 = xr_flat + start_ccd[CR_layout[raft]["SG1"][0]][0] + (amp_width + ccd_border)
        y_SG1 = yr_flat + start_ccd[CR_layout[raft]["SG1"][0]][1] - (amp_width + ccd_border)

    """
    x_SG1 = x_flat + start_ccd[CR_layout[raft]["SG1"][0]][0]
    y_SG1 = y_flat + start_ccd[CR_layout[raft]["SG1"][0]][1]
    """

    CR_y = np.append(CR_y, y_SG1)
    CR_x = np.append(CR_x, x_SG1)

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

    # Kludge for R44 - not understood
    if raft != "R44":
        CR_ccd = np.append(CR_ccd, np.full(8, "SW1"))
        CR_ccd = np.append(CR_ccd, np.full(8, "SW0"))
    else:
        CR_ccd = np.append(CR_ccd, np.full(8, "SW0"))
        CR_ccd = np.append(CR_ccd, np.full(8, "SW1"))

    CR_angle = np.append(CR_angle, np.full(16, CR_layout[raft]["SW"][1]))

    # SG0

    if raft == "R40" or raft == "R04":
        x_SG0 = x_flat + start_ccd[CR_layout[raft]["SG0"][0]][0]
        y_SG0 = y_flat + start_ccd[CR_layout[raft]["SG0"][0]][1]
    else:
        x_SG0 = xr_flat + start_ccd[CR_layout[raft]["SG0"][0]][0] + (amp_width + ccd_border)
        y_SG0 = yr_flat + start_ccd[CR_layout[raft]["SG0"][0]][1] - (amp_width + ccd_border)

    """
    x_SG0 = x_flat + start_ccd[CR_layout[raft]["SG0"][0]][0]
    y_SG0 = y_flat + start_ccd[CR_layout[raft]["SG0"][0]][1]
    """

    CR_x = np.append(CR_x, x_SG0)
    CR_y = np.append(CR_y, y_SG0)

    CR_ccd = np.append(CR_ccd, np.full(16, "SG0"))
    CR_angle = np.append(CR_angle, np.full(16, CR_layout[raft]["SG0"][1]))

    CR_x += start_raft[raft][0]
    CR_y += start_raft[raft][1]

    CR_raft = np.full(len(CR_x), raft)
    CR_raft_type = np.full(len(CR_x), serial_numbers[raft]["type"])

    return CR_x, CR_y, CR_ccd, CR_raft, CR_angle, CR_raft_type


def get_CR_test(raft, test_data):

    new_test = np.empty(0)
    amp_names = np.empty(0)

    # SG1

    raft_ccd = raft + "_SG1"

    z_flat = extract_signal_data(test_data, raft_ccd, CR_layout[raft]["SG1"][1])

    new_test = np.append(new_test, z_flat)

    amp_names_flat = extract_amp_names(test_data, raft_ccd, CR_layout[raft]["SG1"][1])
    amp_names = np.append(amp_names, amp_names_flat)

    # SW0 + SW1

    SW1 = raft + "_SW1"
    SW0 = raft + "_SW0"

    """
    signal = np.zeros((2, 8))
    results = np.array(list(test_data[SW1].values()))[::-1]
    signal[0, :] = results[::-1]
    results = np.array(list(test_data[SW0].values()))
    signal[1, :] = results
    z_flat = signal.flatten()
    new_test = np.append(new_test, z_flat)
    """
    # Kludge for R44 (don't understand why it is needed
    if raft != "R44":
        z_flat = extract_signal_data(test_data, SW1, CR_layout[raft]["SW"][1], SW0)
    else:
        z_flat = extract_signal_data(test_data, SW0, CR_layout[raft]["SW"][1], SW1)

    new_test = np.append(new_test, z_flat)

    """
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
    """
    # Kludge for R44 (don't understand why it is needed
    if raft != "R44":
        amp_n_flat = extract_amp_names(test_data, SW1, CR_layout[raft]["SW"][1], SW0)
    else:
        amp_n_flat = extract_amp_names(test_data, SW0, CR_layout[raft]["SW"][1], SW1)

    amp_names = np.append(amp_names, amp_n_flat)

    # SG0

    raft_ccd = raft + "_SG0"

    """
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
    """
    z_flat = extract_signal_data(test_data, raft_ccd, CR_layout[raft]["SG0"][1])
    new_test = np.append(new_test, z_flat)

    amp_n_flat = extract_amp_names(test_data, raft_ccd, CR_layout[raft]["SG0"][1])
    amp_names = np.append(amp_names, amp_n_flat)

    return new_test, amp_names


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
                    R00_test, _ = get_CR_test(r, test_data)
                    new_test = np.append(new_test, R00_test)
                continue

            for cd in ccd_groups:
                for c in cd:
                    raft_ccd = r + "_" + c
                    z_flat = extract_signal_data(test_data, raft_ccd, 0., raft_ccd2=None)

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


def make_ccd_grid(r, dict_choice):
    for cd in ccd_groups:
        for c in cd:
            raft_ccd = r + "_" + c

            z_flat = extract_signal_data(test_data, raft_ccd, 0.)

            raft = np.full(len(z_flat), r)
            ccd = np.full(len(z_flat), c)
            angle = np.zeros(len(z_flat))
            raft_type = np.full(len(z_flat), serial_numbers[r]["type"])

            x_offset = start_raft[r][0] + start_ccd[c][0]
            y_offset = start_raft[r][1] + start_ccd[c][1]

            x_new = x_flat + x_offset
            y_new = y_flat + y_offset

            dict_choice["x"].extend(x_new)
            dict_choice["y"].extend(y_new)
            dict_choice["z"].extend(z_flat)
            dict_choice["ccd"].extend(ccd)
            dict_choice["raft"].extend(raft)
            dict_choice["amp"].extend(amp_names_flat)
            dict_choice["angle"].extend(angle)
            dict_choice["raft_type"].extend(raft_type)


# Add a color bar

color_mapper = LinearColorMapper(palette="Inferno256", low=min_z, high=max_z)

color_bar = ColorBar(color_mapper=color_mapper, location=(0, 0))
fp.add_layout(color_bar, 'right')

raft_offset_x = 0
raft_offset_y = 0

y_scale = 3
x_scale = 3

# set up full focal plane

source_dict_fp = {"x":[], "y":[], "z":[], "ccd":[], "raft":[], "amp":[], "test2":[], "angle":[], "raft_type":[]}

for rg in raft_groups:
    for r in rg:
        if r in CR_layout.keys():
            raft_offset_x = x_scale * amp_length
            raft_offset_y = 0
            if do_CR:
                CR_x, CR_y, CR_ccd, CR_raft, CR_angle, CR_raft_type = CR_grid(r)
                R00_test, CR_amp = get_CR_test(r, test_data)

                source_dict_fp["x"].extend(CR_x)
                source_dict_fp["y"].extend(CR_y)
                source_dict_fp["z"].extend(R00_test)
                source_dict_fp["ccd"].extend(CR_ccd)
                source_dict_fp["raft"].extend(CR_raft)
                source_dict_fp["amp"].extend(CR_amp)
                source_dict_fp["angle"].extend(CR_angle)
                source_dict_fp["raft_type"].extend(CR_raft_type)

            continue

        rc = make_ccd_grid(r, source_dict_fp)

source_dict_fp["test2"] = source_dict_fp["z"]

# set up main focal plane single raft

source_dict_raft = {"x":[], "y":[], "z":[], "ccd":[], "raft":[], "amp":[], "test2":[], "angle":[], "raft_type":[]}

rc = make_ccd_grid("R01", source_dict_raft)

source_dict_raft["test2"] = source_dict_raft["z"]

if do_CR:
    # set up single corner raft

    r = "R00"
    source_dict_CR = {"x":[], "y":[], "z":[], "ccd":[], "raft":[], "amp":[], "test2":[], "angle":[], "raft_type":[]}

    CR_x, CR_y, CR_ccd, CR_raft, CR_angle, CR_raft_type = CR_grid(r)
    #R00_test, CR_amp = get_CR_test(r, test_data)

    source_dict_CR["x"].extend(CR_x)
    source_dict_CR["y"].extend(CR_y)
    source_dict_CR["z"].extend(np.ones_like(CR_x))
    source_dict_CR["ccd"].extend(CR_ccd)
    source_dict_CR["raft"].extend(CR_raft)
    source_dict_CR["amp"].extend(np.ones_like(CR_x))
    source_dict_CR["angle"].extend(CR_angle)
    source_dict_CR["raft_type"].extend(CR_raft_type)

    source_dict_CR["test2"] = source_dict_CR["z"]

source_dict = deepcopy(source_dict_fp)
source_static = deepcopy(source_dict)

source = ColumnDataSource(source_dict)

# set up glyph to represent the raft grid. It is used for all states by changing the ColumnDataSource contents
# (source.data)

g = Rect(x='x', y='y', width=amp_width, height=amp_length / 2., angle='angle', line_color="black")
g.fill_color = {'field': 'z', 'transform': color_mapper}
fp.add_glyph(source, g)

#  Add tooltips
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

# primary test heatmaps and histogram content

hist_source = ColumnDataSource(data=dict(top=[], x=[], vbar_width=[]))

lower, upper, mask = do_test_stuff(t_source=source, h_source=hist_source, t_test_name="z", use_slider=False,
                                   mask_in=None)
# seems to be a chicken and egg timing situation for the slider with changing values and defining the callback
# so this is not using slider_format.

step = (upper - lower) / 20.
slider = RangeSlider(start=lower, end=upper, value=(lower, upper), step=step,
                     format=BasicTickFormatter(), title="test value range")

color_mapper.low = lower * 0.8 if lower > 0 else lower * 1.2
color_mapper.high = upper * 1.1

p1.vbar(top="top", x="x", width="vbar_width", alpha=0.3, fill_color="red", source=hist_source)

# secondary test heatmaps and histogram content

t2_hist_source = ColumnDataSource(data=dict(top=[], x=[], t2_vbar_width=[]))

t_lower, t_upper, _ = do_test_stuff(t_source=source, h_source=t2_hist_source, t_test_name="test2", use_slider=False,
                                    mask_in=mask)

fp2.vbar(top="top", x="x", width="t2_vbar_width", alpha=0.3, fill_color="red", source=t2_hist_source)

raft_type = np.array(source_dict["raft_type"])
view_ITL = CDSView(filter=BooleanFilter([True if t == "ITL" else False for t in raft_type]))
view_E2V = CDSView(filter=BooleanFilter([True if t == "E2V" else False for t in raft_type]))


fp2s.scatter(x="z", y="test2", source=source, view=view_ITL, color="blue", legend_label="ITL")
fp2s.scatter(x="z", y="test2", source=source, view=view_E2V, color="red", legend_label="E2V")

fp2s.y_range = Range1d(start=t2_lower, end=t2_upper)
fp2s.x_range = Range1d(start=lower, end=upper)

hover_s = fp2s.select(dict(type=HoverTool))
hover_s.tooltips = [("type", "@raft_type"), ("test", "@z"), ("test2", "@test2"),
                    ("ccd", "@ccd"), ("raft", "@raft"), ("amp", "@amp")]

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


def update_slider(lower, upper):
    try:
        slider.remove_on_change('value_throttled', update)
    except:
        pass

    slider.start = lower
    slider.end = upper
    slider.value = (lower, upper)
    slider.step = (upper - lower) / 20.

    try:
        slider.on_change('value_throttled', update)
    except:
        pass
    if abs(slider.start) < 0.1:
        slider.format = PrintfTickFormatter(format="%1.2e")
    else:
        slider.format = BasicTickFormatter()

    color_mapper.low = lower * 0.8 if lower > 0 else lower * 1.2
    color_mapper.high = upper * 1.1


# Define a callback function for TapTool
def tap_callback(event):
    # used for selecting a single raft to view; then toggle back
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

    # reset sensor type selection

    type_dropdown.value = "all"

    if current_raft is None:
        # switch from fp to either CR or main fp raft
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

        kwargs = {"test_name": test_name, "single_raft": current_raft}
        kwargs2 = {"test_name": second_test_name, "single_raft": current_raft}

        fp.title.text = title_run_base + " " + current_raft + ": " + test_name
        generate_log_message(log_div, "Switched to single raft mode: " + current_raft)
    else:
        # switch from single raft to full fp
        current_raft = None
        source.data = dict(x=source_dict_fp["x"], y=source_dict_fp["y"], z=source_dict_fp["z"],
                           ccd=source_dict_fp["ccd"], raft=source_dict_fp["raft"], amp=source_dict_fp["amp"],
                           angle=source_dict_fp["angle"], raft_type=source_dict_fp["raft_type"])

        source_static = deepcopy(source_dict_fp)

        kwargs = {"test_name": test_name, "single_raft": current_raft}
        kwargs2 = {"test_name": second_test_name, "single_raft": current_raft}

        fp.title.text = title_run_base + " Full focal plane: " + test_name

        generate_log_message(log_div, "Switched to full fp mode")

    new_test_data = get_new_test(**kwargs)
    source.data["z"] = list(new_test_data)
    source_static["z"] = list(new_test_data)
    t2_new_test_data = get_new_test(**kwargs2)
    source.data["test2"] = list(t2_new_test_data)
    source_static["test2"] = list(t2_new_test_data)

    lower, upper, mask = do_test_stuff(t_source=source, h_source=hist_source, t_test_name="z", use_slider=False)
    rc = update_slider(lower, upper)

    p1.title.text = test_name

    # re histogram 2nd test

    t2_lower, t2_upper, _ = do_test_stuff(t_source=source, h_source=t2_hist_source, t_test_name="test2",
                                          use_slider=False,
                                          mask_in=mask
                                          )

    fp2s.y_range = Range1d(start=t2_lower, end=t2_upper)
    fp2s.x_range = Range1d(start=lower, end=upper)

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
    clip = new == clip_select.value

    new_run = False
    if selected_run != test_run and w:
        # new run selected - replace dict of measurements - p
        if DM_stack:
            generate_log_message(log_div, "run_text_box selected: " + selected_run)
            p = get_new_run(selected_run)
            generate_log_message(log_div, selected_run + " loaded")
            test_run = selected_run
            title_run_base = test_run
            new_run = True
        else:
            generate_log_message(log_div, "DM stack or EO code unavailable. Request ignored: " + selected_run)
            return

    if (d and selected_name != test_name) or new_run or clip:
        # new test name selected. Replace "z" in source_static and source.data
        # clip the data and set the sliders to the clipped lower and upper
        generate_log_message(log_div,"getting new test data: " + selected_name)
        new_test_data = get_new_test(selected_name, current_raft)
        source_static["z"] = list(new_test_data)
        source.data["z"] = list(new_test_data)

        if not new_run:
            test_name = selected_name
        generate_log_message(log_div, "updating sliders for : " + selected_name)

        t_lower, t_upper = clip_limits(test_name, new_test_data, clip_threshold)
        mask = (new_test_data > t_lower) & (new_test_data < t_upper)
        new_masked = new_test_data[mask]
        lower, upper = clip_limits(test_name, new_masked, clip_threshold)

        rc = update_slider(lower, upper)

    if (s and second_test_name != second_name) or new_run:
        # select 2nd test. Replace "test2" in source_static and source.data
        generate_log_message(log_div, "getting new second test data: " + second_name)
        t2_new_test_data = get_new_test(second_name, current_raft)
        source_static["test2"] = list(t2_new_test_data)
        source.data["test2"] = source_static["test2"]

        if not new_run:
            second_test_name = second_name

    # stuff done for all entries to update - histograms are remade every time

    # fetch the test data array - "z". Sliders either were determined when the test was updated or
    # via manual adjustment. Get the data from the original test from source_static.

    lower, upper, mask = do_test_stuff(t_source=source, h_source=hist_source, t_test_name="z", use_slider=True,
                                       mask_in=None)

    p1.title.text = test_name

    # re histogram 2nd test

    t2_lower, t2_upper, _ = do_test_stuff(t_source=source, h_source=t2_hist_source, t_test_name="test2",
                                          use_slider=False,
                                          mask_in=mask)

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

l = layout(exit_button, row( type_dropdown, column(run_text_box, clip_select), name_dropdown, slider,
                             column(st_div, second_toggle),
                             second_dropdown, log_div),
           row(fp, column(p1, fp2s, fp2)))

# Add the layout to the current document
curdoc().add_root(l)
curdoc().title = "LSSTCam focal plane EO viewer"
