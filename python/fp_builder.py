import numpy as np
import itertools
import pickle
from copy import deepcopy
import yaml
import argparse
import re
from pathlib import Path
import time

from tornado.ioloop import IOLoop
from tornado import gen

from bokeh.models.widgets import DataTable, TableColumn, Div, NumberFormatter
from bokeh.models.formatters import PrintfTickFormatter, BasicTickFormatter
from bokeh.models import (RangeSlider, Rect, HoverTool, ColorBar, LinearColorMapper, ColumnDataSource, Select, Button,
                          TextInput, TapTool, RadioButtonGroup, Range1d, CDSView, BooleanFilter, CheckboxButtonGroup)
from bokeh.plotting import figure, output_file, reset_output, show, save, curdoc
from bokeh.layouts import row, layout, column
from bokeh.transform import transform

try:
    import lsst.daf.butler as daf_butler
    import lsst.eo.pipe as eo_pipe

    DM_stack = True
except ImportError:
    DM_stack = False
    print("Could not load DM or EO code")


class fp_builder():
    def __init__(self):

        self.DM_stack = DM_stack

        # in case the DM stack and EO pipe code is unavailable. In that case, only pickle files can be used.

        parser = argparse.ArgumentParser()

        parser.add_argument('--app_config',
                            default="process_exposure_config.yaml",
                            help="overall app config file")
        args = parser.parse_args()

        with open(args.app_config, "r") as f:
            data = yaml.safe_load(f)

        self.data_dir = data["data_dir"]
        self.in_file = self.data_dir + data["in_file_name"]

        self.guard_value = data["guard_value"]

        self.do_CR = data["do_CR"]

        self.title_run_base = data["in_file_name"]

        self.serial_numbers_pkl = self.data_dir + data["serial_numbers_pkl"]

        self.message_log = []

        # flag to update colour map ranges after each slider change or not (default not)

        self.cm_refresh = True

        self.source_dict_raft = None
        self.source_dict_fp = None

        # map of test results: map of tests; map of rafts; map of sensors; map of segments; test value

        self.amp_results = None

        self.raft_groups = None
        self.ccd_groups = None

        self.current_raft = None

        # primary and secondary test names

        self.test_name = None
        self.second_test_name = None

        # initial copy after each new run or test fetch. Used to start from scratch after slider changes etc
        self.source_static = None

        # source updates are reflected in updates to figures
        self.source = ColumnDataSource()

        # define the CR layout - location of sensor, direction of readout and order of 0:7, 8-15 segments

        self.CR_layout = {
            "R00": {
                "SG0": ["S12", np.pi / 2., 1, 1],
                "SG1": ["S21", 0., -1, 1],
                "SW": ["S22", 0., -1, 1]
            },
            "R04": {
                "SG0": ["S21", 0., 1, 1],
                "SG1": ["S10", np.pi / 2., -1, 0],
                "SW": ["S20", np.pi / 2., -1, 0]
            },
            "R40": {
                "SG0": ["S01", 0., -1, 0],
                "SG1": ["S12", 3. * np.pi / 2., 1, 1],
                "SW": ["S02", np.pi / 2., 1, 1]
            },
            "R44": {
                "SG0": ["S10", np.pi / 2., -1, 0],
                "SG1": ["S01", 0., 1, 0],
                "SW": ["S00", 0., 1, 0]
            }
        }

        # get the cached pickle file of amp results and pick an initial test to set up on

        with open(self.in_file, 'rb') as f:
            self.amp_results = pickle.load(f)

        self.tests = list(self.amp_results.keys())
        self.test_name = self.tests[11]
        self.second_test_name = self.test_name

        # define the figures

        # main heatmap figure
        self.fp = figure(height=1000, width=1100, title="Focal plane",
                         tools="pan,wheel_zoom,box_zoom,lasso_select,reset,save,hover")

        # histogram of primary test
        self.histo1 = figure(width=640, height=640, title=self.test_name)

        # histogram of secondary test
        self.histo2 = figure(height=320, width=640, title="2nd test", tools="pan,wheel_zoom,box_zoom,reset,save,hover")
        self.histo2.visible = False

        # scatter plot of primary vs secondary
        self.scatter12 = figure(height=320, width=640, title="2nd test scatter",
                           tools="pan,wheel_zoom,box_zoom,reset,save,hover")
        self.scatter12.visible = False

        # get the raft, CCD serial number etc (from Seth Digel).

        with open(self.serial_numbers_pkl, 'rb') as sn:
            self.serial_numbers = pickle.load(sn)

        # n_sigma clip threshold displays
        self.clip_threshold = 5.

        self.t2_lower = 0
        self.t2_upper = 0

        # for querying runs from the butler
        self.test_run = None

        self.good_runs_list = data['good_runs_file']
        gr = self.data_dir + self.good_runs_list
        with open(gr, "r") as f:
            self.good_runs = yaml.safe_load(f)

        self.good_runs_versions = [(t + "_" + self.good_runs[t]) for t in self.good_runs]

        if self.DM_stack:

            repo = "/repo/main"
            butler = daf_butler.Butler(repo)

            # query for full list of DM versions vs run
            pattern_version = f"u/lsstccs/eo_*_*"

            collections_v = butler.registry.queryCollections(pattern_version)

            # Define the regular expression pattern

            #  .*?_E(\d+)_(.+)$:
            #  .*?_ matches any characters up to the first _E.
            #  E(\d+): Matches E followed by one or more digits, capturing the digits as the first group.
            #  _(.+)$: Matches an underscore followed by any characters until the end of the string, capturing this part as the second group.

            pattern = r".*?_E(\d+)_(.+)$"

            self.runs_versions = {}
            for r in collections_v:

                # Search for the pattern in the input string
                match = re.search(pattern, r)

                if match:
                    E_code = f"E{match.group(1)}"  # Extract run
                    w_code = f"w_{match.group(2)}"  # Extract DM version

                    self.runs_versions.setdefault(E_code, [])
                    if w_code not in self.runs_versions[E_code]:
                        self.runs_versions[E_code].append(w_code)

        self.pickled_runs = []
        rc = self.find_run_pickles()
        self.new_pickle = False

        print(self.tests)

        # start with ptc_gains to get going

        self.test_data = self.amp_results[self.test_name]
        self.gains = np.array(list(itertools.chain.from_iterable(amplifier.values()
                                                                 for amplifier in self.test_data.values())))
        filtered_gains = self.gains[~np.isnan(self.gains)]
        self.min_z = min(filtered_gains)
        self.max_z = max(filtered_gains)

        self.name_list = []

        for elem in self.tests:
            if isinstance(elem, tuple) and len(elem) == 2:
                self.name_list.append(f"{elem[0]}_{elem[1]}")
            else:
                self.name_list.append(elem)

        # get the list of amp names (never change for focal plane)

        self.fp_amp_names_flat, _ = self.extract_amp_names(self.test_data, raft_ccd="R01_S00", angle=0., raft_ccd2=None)

        # set up all the widgets and their callbacks
        rc = self.create_widgets()
        rc = self.set_callbacks()

        # CCD defined as 1 unit. 8 amps per half, so each is 1/8=0.125 wide and 0.5 high.
        # rafts are 3 CCDs wide and tall, hence 3 units.

        self.amp_width = 0.125
        self.amp_length = 1.
        self.segments = 8
        self.amps = 2

        # define whitespace around the rafts and CCDs

        self.raft_border = 0.2
        self.ccd_border = 0.05

        self.start_raft = {}
        self.start_ccd = {}

        # set up the basic amp grid and then full grids for full fp, single raft and CR
        rc = self.amp_grid()

        rc = self.setup_full_fp()
        rc = self.setup_raft()

        if self.do_CR:
            rc = self.setup_CR()

        # start with full fp, choosing it to set source_dict
        self.source_dict = deepcopy(self.source_dict_fp)
        self.source_static = deepcopy(self.source_dict)

        self.source = ColumnDataSource(self.source_dict)

        # set up glyph to represent the raft grid. It is used for all states by changing the ColumnDataSource contents
        # (source.data)

        g = Rect(x='x', y='y', width=self.amp_width, height=self.amp_length / 2., angle='angle', line_color="black")
        g.fill_color = {'field': 'z', 'transform': self.color_mapper}
        self.fp.add_glyph(self.source, g)

        #  Add tooltips
        hover = self.fp.select(dict(type=HoverTool))
        hover.tooltips = [("type", "@raft_type"), ("test", "@z"), ("ccd", "@ccd"), ("raft", "@raft"),
                          ("amp", "@amp")]

        self.fp.title.text = self.title_run_base + " Full focal plane: " + self.test_name

        #  Suppress Axes
        self.fp.xaxis.visible = False  # Hide x-axis
        self.fp.yaxis.visible = False  # Hide y-axis

        #  Suppress Grid Lines
        self.fp.xgrid.grid_line_color = None  # Remove x-grid lines
        self.fp.ygrid.grid_line_color = None  # Remove y-grid lines

        # primary test heatmaps and histogram content

        self.hist_source = ColumnDataSource(data=dict(top=[], x=[], vbar_width=[]))

        lower, upper, mask = self.do_test_stuff(t_source=self.source, h_source=self.hist_source, t_test_name="z", use_slider=False,
                                                mask_in=None)
        # seems to be a chicken and egg timing situation for the slider with changing values and defining the callback
        # so this is not using update_slider.

        step = (upper - lower) / 20.
        self.slider = RangeSlider(start=lower, end=upper, value=(lower, upper), step=step,
                                  format=BasicTickFormatter(), title="test value range")
        self.slider.on_change('value_throttled', self.update)

        self.color_mapper.low = lower * 0.8 if lower > 0 else lower * 1.2
        self.color_mapper.high = upper * 1.1

        self.histo1.vbar(top="top", x="x", width="vbar_width", alpha=0.3, fill_color="red", source=self.hist_source)

        # secondary test heatmaps and histogram content

        self.t2_hist_source = ColumnDataSource(data=dict(top=[], x=[], t2_vbar_width=[]))

        t2_lower, t2_upper, _ = self.do_test_stuff(t_source=self.source, h_source=self.t2_hist_source, t_test_name="test2",
                                            use_slider=False,
                                            mask_in=mask)

        self.histo2.vbar(top="top", x="x", width="t2_vbar_width", alpha=0.3, fill_color="red", source=self.t2_hist_source)

        raft_type = np.array(self.source_dict["raft_type"])
        view_ITL = CDSView(filter=BooleanFilter([True if t == "ITL" else False for t in raft_type]))
        view_E2V = CDSView(filter=BooleanFilter([True if t == "E2V" else False for t in raft_type]))

        self.scatter12.scatter(x="z", y="test2", source=self.source, view=view_ITL, color="blue", legend_label="ITL")
        self.scatter12.scatter(x="z", y="test2", source=self.source, view=view_E2V, color="red", legend_label="E2V")

        self.scatter12.y_range = Range1d(start=t2_lower, end=t2_upper)
        self.scatter12.x_range = Range1d(start=lower, end=upper)

        hover_s = self.scatter12.select(dict(type=HoverTool))
        hover_s.tooltips = [("type", "@raft_type"), ("test", "@z"), ("test2", "@test2"),
                            ("ccd", "@ccd"), ("raft", "@raft"), ("amp", "@amp")]

        canvas_layout = layout(self.exit_button,
                                row(self.type_dropdown,
                                column( self.clip_select, row(self.run_text_box, self.good_runs_dropdown),
                                        self.run_pickle_dropdown),
                                self.name_dropdown, self.slider,
                                    column(self.div_slider_check, self.slider_checkbox_group),
                                column(self.st_div, self.second_toggle),
                                    self.second_dropdown, self.log_div),
                                row(self.fp, column(self.histo1, self.scatter12, self.histo2)))

        # Add the layout to the current document
        curdoc().add_root(canvas_layout)
        curdoc().title = "LSSTCam focal plane EO viewer"

    def create_widgets(self):

        self.log_div = Div(text="Log:<br>", width=400, height=150)

        self.type_dropdown = Select(title="Pick type", value="all", options=["all", "E2V", "ITL"])
        self.name_dropdown = Select(title="Pick test", value=self.test_name, options=self.name_list)
        self.run_pickle_dropdown = Select(title="Pick pickle", value=self.in_file,
                                          options=list(self.pickled_runs),
                                          width=400)

        self.second_dropdown = Select(title="Pick second test", value=self.second_test_name, options=self.name_list)
        self.second_dropdown.visible = False

        self.run_text_box = TextInput(title="Pick run", value="None")
        self.good_runs_dropdown = Select(title="Pick run", value=self.good_runs["E1110"],
                                         options=self.good_runs_versions, width=200)
        if not self.DM_stack:
            self.run_text_box.visible = False
            self.good_runs_dropdown.visible = False
            self.generate_log_message(self.log_div, "No DM stack or EO - run selection disabled")

        self.exit_button = Button(label="Exit", button_type="danger")
        self.exit_button.on_click(self.stop_server)

        self.second_toggle = RadioButtonGroup(labels=["On", "Off"], active=1)
        self.st_div = Div(text="Second histos")

        # Create a CheckboxButtonGroup widget
        self.slider_checkbox_group = CheckboxButtonGroup(labels=["CMap refresh"], active=[])

        # Create a Div to display the current state
        self.div_slider_check = Div(text="state: On")

        # Add TapTool
        self.taptool = TapTool()

        self.clip_select = TextInput(title="Set clip sigma", value=str(self.clip_threshold), width=75)

        # Add a color bar

        self.color_mapper = LinearColorMapper(palette="Inferno256", low=self.min_z, high=self.max_z)

        self.color_bar = ColorBar(color_mapper=self.color_mapper, location=(0, 0))

    def set_callbacks(self):

        self.name_dropdown.on_change('value', self.update)
        self.second_dropdown.on_change('value', self.update)
        self.run_text_box.on_change('value', self.update)
        # Attach the callback to the slider and dropdown
        self.clip_select.on_change('value', self.update)
        self.type_dropdown.on_change('value', self.update)
        self.run_pickle_dropdown.on_change('value', self.update)
        self.good_runs_dropdown.on_change('value', self.update)

        # Attach the callback to the checkbox's active property
        self.slider_checkbox_group.on_change('active', self.slider_checkbox_callback)

        # Attach the stop function to the button click event
        self.exit_button.on_click(self.stop_server)

        self.second_toggle.on_change("active", self.second_callback)

        # Attach the callback to the TapTool's event
        self.fp.add_tools(self.taptool)
        self.fp.on_event('tap', self.tap_callback)

        self.fp.add_layout(self.color_bar, 'right')

    # Define a callback to toggle the visibility of the plot
    def second_callback(self, attr, old, new):
        if self.second_toggle.active == 0:  # "On"
            self.histo2.visible = True
            self.scatter12.visible = True
            self.second_dropdown.visible = True
            self.histo1.height = 320
        else:  # "Off"
            self.histo2.visible = False
            self.scatter12.visible = False
            self.second_dropdown.visible = False
            self.histo1.height = 640

    # Define a callback to update the div whenever the checkbox state changes
    def slider_checkbox_callback(self, attr, old, new):
        state = "Off" if new else "On"
        self.cm_refresh = False if new else True
        self.div_slider_check.text = f"state: {state}"

    # Define a function to stop the server - define async functions to ensure the log msg and button
    # colour change happen before stopping the server

    def stop_server(self):
        curdoc().add_next_tick_callback(lambda: self.async_generate_log_message(self.log_div, "Server is shutting down..."))
        curdoc().add_next_tick_callback(lambda: self.change_button_color(self.exit_button, "light"))
        curdoc().add_next_tick_callback(self.exit_server)

    # Function to update the log message in the Div
    async def async_generate_log_message(self, log_div, message):
        log_div.text = message

    async def exit_server(self):
        print("Server is shutting down...")
        IOLoop.current().stop()

    async def change_button_color(self, button, color):
        button.button_type = color

    # Define a callback function for TapTool
    def tap_callback(self, event):
        # used for selecting a single raft to view; then toggle back
        selected = self.source.selected
        try:
            selected_index = self.source.selected.indices[0]
        except IndexError:
            self.generate_log_message(self.log_div, "Hit whitespace! Try again")
            return

        selected_data = self.source.data
        raft_value = selected_data['raft'][selected_index]
        ccd_value = selected_data['ccd'][selected_index]
        amp_value = selected_data['amp'][selected_index]

        # Unselect at the end of the callback
        self.source.selected.indices = []
        self.generate_log_message(self.log_div, f"Selected raft: {raft_value}, ccd: {ccd_value}, amp: {amp_value}")

        # reset sensor type selection

        self.type_dropdown.value = "all"

        if self.current_raft is None:
            # switch from fp to either CR or main fp raft
            self.current_raft = raft_value
            if self.do_CR and self.current_raft in list(self.CR_layout.keys()):
                self.source.data = dict(x=self.source_dict_CR["x"], y=self.source_dict_CR["y"], z=self.source_dict_CR["z"],
                                   ccd=self.source_dict_CR["ccd"], raft=self.source_dict_CR["raft"], amp=self.source_dict_CR["amp"],
                                   angle=self.source_dict_CR["angle"], raft_type=self.source_dict_CR["raft_type"])
                self.source_static = deepcopy(self.source_dict_CR)
            else:
                self.source.data = dict(x=self.source_dict_raft["x"], y=self.source_dict_raft["y"], z=self.source_dict_raft["z"],
                                   ccd=self.source_dict_raft["ccd"], raft=self.source_dict_raft["raft"],
                                   amp=self.source_dict_raft["amp"],
                                   angle=self.source_dict_raft["angle"], raft_type=self.source_dict_raft["raft_type"])

                self.source_static = deepcopy(self.source_dict_raft)

            kwargs = {"t_name": self.test_name, "single_raft": self.current_raft}
            kwargs2 = {"t_name": self.second_test_name, "single_raft": self.current_raft}

            self.fp.title.text = self.title_run_base + " " + self.current_raft + ": " + self.test_name
            self.generate_log_message(self.log_div, "Switched to single raft mode: " + self.current_raft)
        else:
            # switch from single raft to full fp
            self.current_raft = None
            self.source.data = dict(x=self.source_dict_fp["x"], y=self.source_dict_fp["y"], z=self.source_dict_fp["z"],
                               ccd=self.source_dict_fp["ccd"], raft=self.source_dict_fp["raft"], amp=self.source_dict_fp["amp"],
                               angle=self.source_dict_fp["angle"], raft_type=self.source_dict_fp["raft_type"])

            self.source_static = deepcopy(self.source_dict_fp)

            kwargs = {"t_name": self.test_name, "single_raft": self.current_raft}
            kwargs2 = {"t_name": self.second_test_name, "single_raft": self.current_raft}

            self.fp.title.text = self.title_run_base + " Full focal plane: " + self.test_name

            self.generate_log_message(self.log_div, "Switched to full fp mode")

        new_test_data = self.get_new_test(**kwargs)
        self.source.data["z"] = list(new_test_data)
        self.source_static["z"] = list(new_test_data)
        t2_new_test_data = self.get_new_test(**kwargs2)
        self.source.data["test2"] = list(t2_new_test_data)
        self.source_static["test2"] = list(t2_new_test_data)

        lower, upper, mask = self.do_test_stuff(t_source=self.source, h_source=self.hist_source, t_test_name="z",
                                                use_slider=False)
        rc = self.update_slider(lower, upper)

        self.histo1.title.text = self.test_name

        # re histogram 2nd test

        t2_lower, t2_upper, _ = self.do_test_stuff(t_source=self.source, h_source=self.t2_hist_source, t_test_name="test2",
                                                   use_slider=False,
                                                   mask_in=mask)

        self.scatter12.y_range = Range1d(start=t2_lower, end=t2_upper)
        self.scatter12.x_range = Range1d(start=lower, end=upper)

        self.generate_log_message(self.log_div, "Ready")

    def update(self, attr, old, new):
        # Define callback to update "source.data" ColumnDataSource via most of the widgets

        # Get the new range from the slider
        selected_name = self.name_dropdown.value
        second_name = self.second_dropdown.value
        selected_run = self.run_text_box.value
        run_pickle = self.run_pickle_dropdown.value
        good_run = self.good_runs_dropdown.value

        if self.clip_threshold != float(self.clip_select.value):
            self.clip_threshold = float(self.clip_select.value)
            self.generate_log_message(self.log_div, "Clipping threshold set to " + str(self.clip_threshold))

        # who triggered this?
        w = new == self.run_text_box.value
        d = new == self.name_dropdown.value
        s = new == self.second_dropdown.value
        clip = new == self.clip_select.value
        self.new_pickle = new == run_pickle
        new_good_run = new == good_run

        new_run = False
        if (selected_run != self.test_run and w) or self.new_pickle or new_good_run or new_run:
            # new run selected - replace dict of measurements - amp_results
            if self.DM_stack or self.new_pickle:

                self.good_runs_dropdown.remove_on_change('value', self.update)
                self.run_pickle_dropdown.remove_on_change('value', self.update)
                self.run_text_box.remove_on_change('value', self.update)

                if w:
                    new_run_name = self.name_dropdown.value
                    kwargs = {"run_name": selected_run}
                    self.test_run = selected_run
                    self.good_runs_dropdown.value = "None"
                    self.run_pickle_dropdown.value = "None"
                elif self.new_pickle:
                    new_run_name = run_pickle
                    kwargs = {"run_name": run_pickle}
                    self.test_run = run_pickle
                    self.run_text_box.value = "None"
                    self.good_runs_dropdown.value = "None"
                elif new_good_run:
                    new_run_name = good_run
                    kwargs = {"run_name": good_run}
                    self.test_run = good_run
                    self.run_text_box.value = "None"
                    self.run_pickle_dropdown.value = "None"

                self.good_runs_dropdown.on_change('value', self.update)
                self.run_pickle_dropdown.on_change('value', self.update)
                self.run_text_box.on_change('value', self.update)

                self.generate_log_message(self.log_div, "run_text_box selected: " + new_run_name)

                print("Fetching new run", new_run_name)
                start_time = time.time()
                self.amp_results = self.get_new_run(**kwargs)
                end_time = time.time()
                elapsed_time = end_time - start_time

                self.generate_log_message(
                    self.log_div, new_run_name + " loaded after " + str(elapsed_time) + " seconds")
                self.title_run_base = self.test_run
                new_run = True
                self.new_pickle = False
            else:
                self.generate_log_message(self.log_div, "DM stack or EO code unavailable. Request ignored: " + selected_run)
                return

        if (d and selected_name != self.test_name) or new_run or clip:
            # new test name selected. Replace "z" in source_static and source.data
            # clip the data and set the sliders to the clipped lower and upper
            self.generate_log_message(self.log_div, "getting new test data: " + selected_name)
            new_test_data = self.get_new_test(selected_name, self.current_raft)
            self.source_static["z"] = list(new_test_data)
            self.source.data["z"] = list(new_test_data)

            if not new_run:
                self.test_name = selected_name
            self.generate_log_message(self.log_div, "updating sliders for : " + selected_name)

            t_lower, t_upper = self.clip_limits(self.test_name, new_test_data, self.clip_threshold)
            mask = (new_test_data > t_lower) & (new_test_data < t_upper)
            new_masked = new_test_data[mask]
            lower, upper = self.clip_limits(self.test_name, new_masked, self.clip_threshold)

            rc = self.update_slider(lower, upper)

        if (s and self.second_test_name != second_name) or new_run:
            # select 2nd test. Replace "test2" in source_static and source.data
            self.generate_log_message(self.log_div, "getting new second test data: " + second_name)
            t2_new_test_data = self.get_new_test(second_name, self.current_raft)
            self.source_static["test2"] = list(t2_new_test_data)
            self.source.data["test2"] = self.source_static["test2"]

            if not new_run:
                self.second_test_name = second_name

        # stuff done for all entries to update - histograms are remade every time

        # fetch the test data array - "z". Sliders either were determined when the test was updated or
        # via manual adjustment. Get the data from the original test from source_static.

        lower, upper, mask = self.do_test_stuff(t_source=self.source, h_source=self.hist_source, t_test_name="z",
                                                use_slider=True,
                                                mask_in=None)
        if self.cm_refresh:
            self.color_mapper.low = lower * 0.8 if lower > 0 else lower * 1.2
            self.color_mapper.high = upper * 1.1

        self.histo1.title.text = self.test_name

        # re histogram 2nd test

        t2_lower, t2_upper, _ = self.do_test_stuff(t_source=self.source, h_source=self.t2_hist_source, t_test_name="test2",
                                                   use_slider=False,
                                                   mask_in=mask)

        self.histo2.title.text = self.second_test_name
        self.scatter12.yaxis.axis_label = self.second_test_name
        self.scatter12.xaxis.axis_label = self.test_name
        self.scatter12.y_range = Range1d(start=t2_lower, end=t2_upper)
        self.scatter12.x_range = Range1d(start=lower, end=upper)

        if self.current_raft is None:
            self.fp.title.text = self.title_run_base + " Full focal plane: " + self.test_name
        else:
            self.fp.title.text = self.title_run_base + " " + self.current_raft + " " + self.test_name

        self.generate_log_message(self.log_div, "Ready")

    # callbacks all defined

    def generate_log_message(self, log_div, message):
        self.message_log.append(message)

        if len(self.message_log) > 10:
            self.message_log.pop(0)

        self.log_div.text = "Log: <br>" + "<br>".join(self.message_log)
        curdoc().add_next_tick_callback(lambda: None)

    def clip_limits(self, name, test, threshold):

        mask = (~np.isnan(test)) & (test != self.guard_value)
        median = np.median(test[mask])
        std = np.std(test[mask])

        lower = max(min(test), median - threshold * std)
        upper = min(max(test), median + threshold * std)

        self.generate_log_message(self.log_div,
                                  f"{name} Clipping median {median:.2f} std + {std:.2f} thrsh {self.clip_threshold:.2f}")

        return lower, upper

    def do_test_stuff(self, t_source, h_source, t_test_name, use_slider=True, mask_in=None):

        z_u = np.array(self.source_static[t_test_name])
        raft_type = np.array(t_source.data["raft_type"])

        if use_slider:
            lower, upper = self.slider.value
        else:
            lower, upper = self.clip_limits(t_test_name, z_u, self.clip_threshold)

        if mask_in is None:
            # mask is channels failing cuts. Set them to a guard value.
            if self.type_dropdown.value != "all":
                mask = ((z_u < lower) | (z_u > upper) | np.isnan(z_u)) | (raft_type != self.type_dropdown.value)
            else:
                mask = (z_u < lower) | (z_u > upper) | np.isnan(z_u)
        else:
            # take mask from main test (probably)
            mask = mask_in

        # turn values black in the heatmap if colour map not refreshing with the slider values
        if not self.cm_refresh:
            z_u[mask] = self.guard_value

        t_source.data[t_test_name] = z_u

        t_mask = (lower <= z_u) & (z_u <= upper)

        if t_test_name == "test2":
            width_name = "t2_vbar_width"
        else:
            width_name = "vbar_width"

        self.re_histogram(h_source, width_name, z_u[t_mask], lower, upper)

        return lower, upper, mask

# elements are:  equivalent location on normal raft
#                rotation angle of box (rad)
#                direction (1, -1)
#                order first and second 8 segments

    def extract_signal_data(self, test_data, raft_ccd, angle, raft_ccd2=None):
        r, c = raft_ccd.split("_")

        try:
            results = np.array(list(test_data[raft_ccd].values()))[::-1]
            if raft_ccd2 is not None:
                results = np.append(results, np.array(list(test_data[raft_ccd2].values()))[::-1])
        except:
            results = np.ones(16) * self.guard_value

        # direction and order always the same for non-guiders

        direction = 1
        order = 0
        shape = (2, 8)

        # get the direction of readout and order of amps from CR_layout

        if r in list(self.CR_layout.keys()):
            if "SW" in c:
                c = "SW"

            direction = self.CR_layout[r][c][2]
            order = self.CR_layout[r][c][3]
            if angle == 0.:
                shape = (2, 8)
            else:
                shape = (8, 2)

        signal = np.zeros(shape)

        if shape == (2, 8):
            if direction == 1:
                signal[order, :] = results[0:8]
                signal[1 - order, :] = results[15:7:-1]
            else:
                signal[order, :] = results[7::-1]
                signal[1 - order, :] = results[8:16]
        elif shape == (8, 2):
            if direction == 1:
                signal[:, order] = results[0:8]
                signal[:, 1 - order] = results[15:7:-1]
            else:
                signal[:, order] = results[7::-1]
                signal[:, 1 - order] = results[8:16]

        return signal.flatten()

    def extract_amp_names(self, test_data, raft_ccd, angle, raft_ccd2=None):
        r, c = raft_ccd.split("_")
        c0 = c
        if raft_ccd2 is not None:
            _, c2 = raft_ccd2.split("_")
        else:
            c2 = c0

        try:
            results = np.array(list(test_data[raft_ccd].keys()))[::-1]
            if raft_ccd2 is not None:
                results = np.append(results, np.array(list(test_data[raft_ccd2].keys()))[::-1])
        except:
            results = np.full(16, c)

        # direction and order always the same for non-guiders

        direction = 1
        order = 0
        shape = (2, 8)

        # get the direction of readout and order of amps from CR_layout

        if r in list(self.CR_layout.keys()):
            if "SW" in c:
                c = "SW"

            direction = self.CR_layout[r][c][2]
            order = self.CR_layout[r][c][3]
            if angle == 0.:
                shape = (2, 8)
            else:
                shape = (8, 2)

        amps = np.empty(shape, dtype=object)
        ccds_c0 = np.full(shape, c0)

        if shape == (2, 8):
            ccds_c0[order, :] = c0
            ccds_c0[1 - order, :] = c2
            if direction == 1:
                amps[order, :] = results[0:8]
                amps[1 - order, :] = results[15:7:-1]
            else:
                amps[order, :] = results[7::-1]
                amps[1 - order, :] = results[8:16]
        elif shape == (8, 2):
            ccds_c0[:, order] = c0
            ccds_c0[:, 1-order] = c2
            if direction == 1:
                amps[:, order] = results[0:8]
                amps[:, 1 - order] = results[15:7:-1]
            else:
                amps[:, order] = results[7::-1]
                amps[:, 1 - order] = results[8:16]

        return amps.flatten(), ccds_c0.flatten()

    def re_histogram(self, cds, width_name, test, lower, upper):

        t_hist, t_edges = np.histogram(test, bins=100, range=(lower, upper))
        width = t_edges[1] - t_edges[0]
        t_vbar_width = np.ones_like(t_hist) * width
        cds.data = {"top": t_hist, "x": t_edges[:-1], width_name: t_vbar_width}

# set up the grid of amps
    def amp_grid(self):

        x = np.arange(self.segments) * self.amp_width
        y = np.arange(self.amps) * self.amp_length/2.
        xg, yg = np.meshgrid(x, y)
        xr, yr = np.meshgrid(y, x)

        self.x_flat = xg.flatten()
        self.y_flat = yg.flatten()
        self.xr_flat = xr.flatten()
        self.yr_flat = yr.flatten()

        self.raft_groups = [["R00", "R01", "R02", "R03", "R04"],
                      ["R10", "R11", "R12", "R13", "R14"],
                      ["R20", "R21", "R22", "R23", "R24"],
                      ["R30", "R31", "R32", "R33", "R34"],
                      ["R40", "R41", "R42", "R43", "R44"]]

        self.ccd_groups = [["S00", "S01", "S02"],
                     ["S10", "S11", "S12"],
                     ["S20", "S21", "S22"]]

        self.start_raft = {}
        x_0 = self.raft_border
        y_0 = self.raft_border

        for rg in self.raft_groups:
            for r in rg:
                self.start_raft[r] = [x_0, y_0]
                x_0 += 3 * self.amp_length + self.raft_border
            y_0 += 3 * self.amp_length + self.raft_border
            x_0 = self.raft_border

        self.start_ccd = {}
        x_0 = self.ccd_border
        y_0 = self.ccd_border

        for cg in self.ccd_groups:
            for c in cg:
                self.start_ccd[c] = [x_0, y_0]
                x_0 += self.amp_length + self.ccd_border
            y_0 += self.amp_length + self.ccd_border
            x_0 = self.ccd_border

    def CR_grid(self, raft):

        # composed of 4 sensors, 2 SW (each with 8 channels) and 2 SG with 16. The layout is rotated counterclockwise
        # use R00 as the template, starting with SG1

        CR_x = np.empty(0)
        CR_y = np.empty(0)
        CR_ccd = np.empty(0)
        CR_angle = np.empty(0)

        # SG1

        if raft == "R00" or raft == "R44":
            x_SG1 = self.x_flat + self.start_ccd[self.CR_layout[raft]["SG1"][0]][0]
            y_SG1 = self.y_flat + self.start_ccd[self.CR_layout[raft]["SG1"][0]][1]
        else:
            x_SG1 = self.xr_flat + self.start_ccd[self.CR_layout[raft]["SG1"][0]][0] + (self.amp_width + self.ccd_border)
            y_SG1 = self.yr_flat + self.start_ccd[self.CR_layout[raft]["SG1"][0]][1] - (self.amp_width + self.ccd_border)

        CR_y = np.append(CR_y, y_SG1)
        CR_x = np.append(CR_x, x_SG1)

        CR_ccd = np.append(CR_ccd, np.full(16, "SG1"))
        CR_angle = np.append(CR_angle, np.full(16, self.CR_layout[raft]["SG1"][1]))

        if raft == "R00" or raft == "R44":
            x_SW = self.x_flat + self.start_ccd[self.CR_layout[raft]["SW"][0]][0]
            y_SW = self.y_flat + self.start_ccd[self.CR_layout[raft]["SW"][0]][1]
        else:
            x_SW = self.xr_flat + self.start_ccd[self.CR_layout[raft]["SW"][0]][0] + (self.amp_width + self.ccd_border)
            y_SW = self.yr_flat + self.start_ccd[self.CR_layout[raft]["SW"][0]][1] - (self.amp_width + self.ccd_border)

        CR_x = np.append(CR_x, x_SW)
        CR_y = np.append(CR_y, y_SW)

        CR_ccd = np.append(CR_ccd, np.full(8, "SW0"))
        CR_ccd = np.append(CR_ccd, np.full(8, "SW1"))

        CR_angle = np.append(CR_angle, np.full(16, self.CR_layout[raft]["SW"][1]))

        # SG0

        if raft == "R40" or raft == "R04":
            x_SG0 = self.x_flat + self.start_ccd[self.CR_layout[raft]["SG0"][0]][0]
            y_SG0 = self.y_flat + self.start_ccd[self.CR_layout[raft]["SG0"][0]][1]
        else:
            x_SG0 = self.xr_flat + self.start_ccd[self.CR_layout[raft]["SG0"][0]][0] + (self.amp_width + self.ccd_border)
            y_SG0 = self.yr_flat + self.start_ccd[self.CR_layout[raft]["SG0"][0]][1] - (self.amp_width + self.ccd_border)

        CR_x = np.append(CR_x, x_SG0)
        CR_y = np.append(CR_y, y_SG0)

        CR_ccd = np.append(CR_ccd, np.full(16, "SG0"))
        CR_angle = np.append(CR_angle, np.full(16, self.CR_layout[raft]["SG0"][1]))

        CR_x += self.start_raft[raft][0]
        CR_y += self.start_raft[raft][1]

        CR_raft = np.full(len(CR_x), raft)
        CR_raft_type = np.full(len(CR_x), self.serial_numbers[raft]["type"])

        return CR_x, CR_y, CR_ccd, CR_raft, CR_angle, CR_raft_type

    def get_CR_test(self, raft, test_data):

        new_test = np.empty(0)
        amp_names = np.empty(0)
        ccds = np.empty(0)

        # SG1

        raft_ccd = raft + "_SG1"

        z_flat = self.extract_signal_data(test_data, raft_ccd, self.CR_layout[raft]["SG1"][1])

        new_test = np.append(new_test, z_flat)

        amp_names_flat, ccd_names_flat = self.extract_amp_names(test_data, raft_ccd, self.CR_layout[raft]["SG1"][1])
        amp_names = np.append(amp_names, amp_names_flat)
        ccds = np.append(ccds, ccd_names_flat)

        # SW0 + SW1

        SW1 = raft + "_SW1"
        SW0 = raft + "_SW0"

        z_flat = self.extract_signal_data(test_data, SW0, self.CR_layout[raft]["SW"][1], SW1)

        new_test = np.append(new_test, z_flat)

        amp_n_flat, ccd_names_flat = self.extract_amp_names(test_data, SW0, self.CR_layout[raft]["SW"][1], SW1)

        amp_names = np.append(amp_names, amp_n_flat)
        ccds = np.append(ccds, ccd_names_flat)

        # SG0

        raft_ccd = raft + "_SG0"

        z_flat = self.extract_signal_data(test_data, raft_ccd, self.CR_layout[raft]["SG0"][1])
        new_test = np.append(new_test, z_flat)

        amp_n_flat, ccd_names_flat = self.extract_amp_names(test_data, raft_ccd, self.CR_layout[raft]["SG0"][1])
        amp_names = np.append(amp_names, amp_n_flat)
        ccds = np.append(ccds, ccd_names_flat)

        return new_test, amp_names, ccds

    def get_new_test(self, t_name, single_raft=None):

        if "HIGH" in t_name or "LOW" in t_name:
            t_name_split = t_name.split("_")
            t_name = (t_name_split[0], t_name_split[1])

        self.test_data = self.amp_results[t_name]

        new_test = np.empty(0)

        for rg in self.raft_groups:
            for r in rg:
                if single_raft is not None and r != single_raft:
                    continue

                if r in list(self.CR_layout.keys()):
                    if self.do_CR:
                        R00_test, _, _ = self.get_CR_test(r, self.test_data)
                        new_test = np.append(new_test, R00_test)
                    continue

                for cd in self.ccd_groups:
                    for c in cd:
                        raft_ccd = r + "_" + c
                        z_flat = self.extract_signal_data(self.test_data, raft_ccd, 0., raft_ccd2=None)

                        new_test = np.append(new_test, z_flat)

        return new_test

    def find_run_pickles(self):

        path = Path(self.data_dir)
        self.pickled_runs = list(path.glob('*.npy'))  # '*/' for non-recursive

        self.pickled_runs = [file.as_posix() for file in self.pickled_runs]

    def get_new_run(self, run_name):
        self.generate_log_message(self.log_div, "Entered get_new_run " + run_name)

        if self.new_pickle:
            rc = self.find_run_pickles()
            with open(run_name, 'rb') as f:
                amp_data = pickle.load(f)

        else:
            repo = "/repo/main"
            butler = daf_butler.Butler(repo)

            acq_run = run_name  # form is run-id_<weekly>, eg E2233_d_2025_01_27

            pattern = f"u/lsstccs/eo_*_{acq_run}"
            collections = butler.registry.queryCollections(pattern)

            amp_data = eo_pipe.get_amp_data(repo, collections)
            self.generate_log_message(self.log_div, "new amp data acquired")

        return amp_data

    def update_slider(self, lower, upper):

        # have to turn off callback while values are changed or the callback will be triggered
        try:
            self.slider.remove_on_change('value_throttled', self.update)
        except:
            pass

        self.slider.start = lower
        self.slider.end = upper
        self.slider.value = (lower, upper)
        self.slider.step = (upper - lower) / 20.

        if abs(self.slider.start) < 0.1:
            self.slider.format = PrintfTickFormatter(format="%1.2e")
        else:
            self.slider.format = BasicTickFormatter()

        try:
            self.slider.on_change('value_throttled', self.update)
        except:
            pass

        self.color_mapper.low = lower * 0.8 if lower > 0 else lower * 1.2
        self.color_mapper.high = upper * 1.1

    def make_ccd_grid(self, r, dict_choice):
        for cd in self.ccd_groups:
            for c in cd:
                raft_ccd = r + "_" + c

                z_flat = self.extract_signal_data(self.test_data, raft_ccd, 0.)

                raft = np.full(len(z_flat), r)
                ccd = np.full(len(z_flat), c)
                angle = np.zeros(len(z_flat))
                raft_type = np.full(len(z_flat), self.serial_numbers[r]["type"])

                x_offset = self.start_raft[r][0] + self.start_ccd[c][0]
                y_offset = self.start_raft[r][1] + self.start_ccd[c][1]

                x_new = self.x_flat + x_offset
                y_new = self.y_flat + y_offset

                dict_choice["x"].extend(x_new)
                dict_choice["y"].extend(y_new)
                dict_choice["z"].extend(z_flat)
                dict_choice["ccd"].extend(ccd)
                dict_choice["raft"].extend(raft)
                dict_choice["amp"].extend(self.fp_amp_names_flat)
                dict_choice["angle"].extend(angle)
                dict_choice["raft_type"].extend(raft_type)

# set up full focal plane
    def setup_full_fp(self):
        self.source_dict_fp = {"x":[], "y":[], "z":[], "ccd":[], "raft":[], "amp":[], "test2":[], "angle":[], "raft_type":[]}

        raft_offset_x = 0
        raft_offset_y = 0

        y_scale = 3
        x_scale = 3

        for rg in self.raft_groups:
            for r in rg:
                if r in self.CR_layout.keys():
                    raft_offset_x = x_scale * self.amp_length
                    raft_offset_y = 0
                    if self.do_CR:
                        CR_x, CR_y, CR_ccd, CR_raft, CR_angle, CR_raft_type = self.CR_grid(r)
                        R00_test, CR_amp, CR_ccds = self.get_CR_test(r, self.test_data)

                        self.source_dict_fp["x"].extend(CR_x)
                        self.source_dict_fp["y"].extend(CR_y)
                        self.source_dict_fp["z"].extend(R00_test)
                        self.source_dict_fp["ccd"].extend(CR_ccds)
                        self.source_dict_fp["raft"].extend(CR_raft)
                        self.source_dict_fp["amp"].extend(CR_amp)
                        self.source_dict_fp["angle"].extend(CR_angle)
                        self.source_dict_fp["raft_type"].extend(CR_raft_type)

                    continue

                rc = self.make_ccd_grid(r, self.source_dict_fp)

        self.source_dict_fp["test2"] = self.source_dict_fp["z"]

# set up main focal plane single raft
    def setup_raft(self):
        self.source_dict_raft = {"x":[], "y":[], "z":[], "ccd":[], "raft":[], "amp":[], "test2":[], "angle":[], "raft_type":[]}

        rc = self.make_ccd_grid("R01", self.source_dict_raft)

        self.source_dict_raft["test2"] = self.source_dict_raft["z"]

    # set up single corner raft
    def setup_CR(self):
        r = "R00"
        self.source_dict_CR = {"x":[], "y":[], "z":[], "ccd":[], "raft":[], "amp":[], "test2":[], "angle":[], "raft_type":[]}

        CR_x, CR_y, CR_ccd, CR_raft, CR_angle, CR_raft_type = self.CR_grid(r)
        R00_test, CR_amp, CR_ccds = self.get_CR_test(r, self.test_data)

        self.source_dict_CR["x"].extend(CR_x)
        self.source_dict_CR["y"].extend(CR_y)
        self.source_dict_CR["z"].extend(R00_test)
        self.source_dict_CR["ccd"].extend(CR_ccds)
        self.source_dict_CR["raft"].extend(CR_raft)
        self.source_dict_CR["amp"].extend(CR_amp)
        self.source_dict_CR["angle"].extend(CR_angle)
        self.source_dict_CR["raft_type"].extend(CR_raft_type)

        self.source_dict_CR["test2"] = self.source_dict_CR["z"]


app = fp_builder()
