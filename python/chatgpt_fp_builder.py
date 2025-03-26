import numpy as np
from bokeh.io import curdoc
from bokeh.layouts import layout, row, column
from bokeh.models import TextInput, Select, Button, RadioButtonGroup, Div, RangeSlider, TapTool, HoverTool
from tornado.ioloop import IOLoop
from copy import deepcopy


class FocalPlaneBuilder:
    def __init__(self, source_dict_raft, source_dict_fp, p, raft_groups, ccd_groups, min_z, max_z, test_name,
                 second_test_name):
        self.source_dict_raft = source_dict_raft
        self.source_dict_fp = source_dict_fp
        self.p = p
        self.raft_groups = raft_groups
        self.ccd_groups = ccd_groups
        self.current_raft = None
        self.test_name = test_name
        self.second_test_name = second_test_name

        self.source_static = deepcopy(self.source_dict_raft)
        self.source = {'data': {"z": [], "test2": [], "x": [], "y": [], "ccd": [], "raft": [], "amp": []}}
        self.log_div = Div(text="Log:<br>", width=400, height=150)

        self.fp2s = self.setup_plot()
        self.slider = self.setup_slider(min_z, max_z)

        self.name_list = self.setup_name_list(self.p.keys())
        self.name_dropdown = Select(title="Pick test", value=self.test_name, options=self.name_list)
        self.second_dropdown = Select(title="Pick second test", value=self.second_test_name, options=self.name_list)
        self.second_dropdown.visible = False

        self.run_text_box = TextInput(title="Pick run", value="None")

        self.exit_button = Button(label="Exit", button_type="danger")
        self.exit_button.on_click(self.stop_server)

        self.second_toggle = RadioButtonGroup(labels=["On", "Off"], active=1)
        self.st_div = Div(text="Second histos")

        self.update_callback()

        self.layout = layout(self.exit_button, row(self.run_text_box, self.name_dropdown, self.slider,
                                                   column(self.st_div, self.second_toggle), self.second_dropdown,
                                                   self.log_div), row(self.fp, column(self.p1, self.fp2s, self.fp2)))
        curdoc().add_root(self.layout)

    def setup_plot(self):
        taptool = TapTool()
        fp.add_tools(taptool)
        return fp

    def setup_slider(self, min_z, max_z):
        step = (max_z - min_z) / 20.
        slider = RangeSlider(start=min_z, end=max_z, value=(min_z, max_z), step=step, title="test value range")
        return slider

    def setup_name_list(self, tests):
        name_list = []
        for elem in tests:
            if isinstance(elem, tuple) and len(elem) == 2:
                name_list.append(f"{elem[0]}_{elem[1]}")
            else:
                name_list.append(elem)
        return name_list

    def stop_server(self):
        self.generate_log_message("Server is shutting down...")
        print("Server is shutting down...")
        IOLoop.current().stop()

    def update_callback(self):
        self.slider.on_change('value', self.update)
        self.name_dropdown.on_change('value', self.update)
        self.second_dropdown.on_change('value', self.update)
        self.run_text_box.on_change('value', self.update)

    def get_new_test(self, test_name, single_raft=None):
        t_name = self.parse_test_name(test_name)
        test_data = self.p[t_name]
        return self.collect_test_data(test_data, single_raft)

    def parse_test_name(self, test_name):
        if "HIGH" in test_name or "LOW" in test_name:
            t_name_split = test_name.split("_")
            return (t_name_split[0], t_name_split[1])
        return test_name

    def collect_test_data(self, test_data, single_raft=None):
        new_test = np.empty(0)
        for rg in self.raft_groups:
            for r in rg:
                if single_raft and r != single_raft: continue
                if r in ["R00", "R40", "R04", "R44"]: continue
                for cd in self.ccd_groups:
                    for c in cd:
                        z_flat = self.extract_signal_data(test_data, r, c)
                        new_test = np.append(new_test, z_flat)
        return new_test

    def extract_signal_data(self, test_data, r, c):
        raft_ccd = r + "_" + c
        results = np.array(list(test_data[raft_ccd].values()))[::-1]
        signal = np.zeros((2, 8))
        signal[1, :] = results[8:16][::-1]
        signal[0, :] = results[0:8]
        return signal.flatten()

    def update(self, attr, old, new):
        new_test_data = self.get_new_test(self.test_name, single_raft=self.current_raft)
        self.source['data']["z"] = list(new_test_data)
        self.source_static["z"] = list(new_test_data)
        t2_new_test_data = self.get_new_test(self.second_test_name, single_raft=self.current_raft)
        self.source['data']["test2"] = list(t2_new_test_data)
        self.source_static["test2"] = list(t2_new_test_data)

        if self.current_raft:
            self.fp.title.text = "Raft " + self.current_raft + ": " + self.test_name
            self.generate_log_message("Switched to single raft mode: " + self.current_raft)
        else:
            self.source['data'].update(
                dict(x=self.source_dict_fp["x"], y=self.source_dict_fp["y"], z=self.source_dict_fp["z"],
                     ccd=self.source_dict_fp["ccd"], raft=self.source_dict_fp["raft"], amp=self.source_dict_fp["amp"]))
            self.fp.title.text = "Full focal plane: " + self.test_name
            self.generate_log_message("Switched to full fp mode")

    def generate_log_message(self, message):
        self.log_div.text += "<br>" + message


fp_builder = FocalPlaneBuilder(source_dict_raft, source_dict_fp, p, raft_groups, ccd_groups, min_z, max_z, test_name,
                               second_test_name)
