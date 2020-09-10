import glob
import sys
import os
import math
import pickle
import numpy as np
from scipy import optimize
from sklearn import linear_model
from scipy.spatial import distance
#from exploreFocalPlane import exploreFocalPlane
#from exploreRaft import exploreRaft
import lmfit

from os.path import join
from astropy.io import fits

from mixcoatl.sourcegrid import grid_fit, DistortedGrid
#from mixcoatl.gridFitTask import GridFitTask, DistortedGrid

from bokeh.plotting import figure, curdoc
from bokeh.palettes import Viridis256 as palette #@UnresolvedImport
from bokeh.layouts import row, column, layout, gridplot
from bokeh.models.widgets import TextInput, Dropdown, Button, Slider, FileInput
from bokeh.models import CustomJS, ColumnDataSource, Legend, LinearColorMapper, ColorBar, LogColorMapper, Arrow, \
    NormalHead


class sensor():

    def __init__(self):

        # input data from spot finding

        self.src = None
        self.spot_input = None

        # orientation to work in - is sensor boundary perpendicular to x or y in original coordinates.
        self.orientation = None

        # cleaned spot data
        self.spot_cln = None

        # fitted grid spots
        self.fitted_grid = None

        self.name = None
        self.sensor_type = None

        # found lines
        self.lines = {}
        self.grid_index = None

        # fitted lines
        self.linfits = {}
        self.x_center = None
        self.y_center = None

        # grid fit results

        self.grid_fit_results = None
        self.grid_x = None
        self.grid_y = None
        self.grid_distances = None
        self.grid_whiskers = None


class ccd_spacing():

    def __init__(self, dir_index=None, combo_name=None, distort_file=None, pickles_dir=None):

        self.file_paths = {}
        self.raft_ccd_combo = combo_name

        self.sensor = None

        self.name_ccd1 = None
        self.name_ccd2 = None
        self.names_ccd = []
        self.ccd_relative_orientation = "vertical"
        self.extrap_dir = 1.

        self.use_pickles = False
        self.pickles_dir = pickles_dir

        self.lines = {}
        self.linfits = {}
        self.rotate = 3.11/57.3   # obtained from undistorted grid model
        self.show_rotate = False
        self.pitch = 65.34        # obtained from undistorted grid model
        self.cut_spurious_spots = 68.  # spots need to be closer to another spot to include in lines
        self.num_spots = 49

        #self.raft_types = {}
        #eFP = exploreFocalPlane()
        #eR = exploreRaft()
        #raft_list = eFP.focalPlaneContents()
        #for raft in raft_list:
        #    self.raft_types[raft[1]] = eR.raft_type(raft[0])
        #print(self.raft_types)

        self.raft_types = {'R00': 'ITL', 'R04': 'ITL', 'R40': 'ITL', 'R44': 'ITL', 'R01': 'ITL', 'R02': 'ITL',
                           'R03': 'ITL', 'R10': 'ITL', 'R11': 'e2v', 'R12': 'e2v', 'R13': 'e2v', 'R14': 'e2v',
                           'R20': 'ITL', 'R21': 'e2v', 'R22': 'e2v', 'R23': 'e2v', 'R24': 'e2v', 'R30': 'e2v',
                           'R31': 'e2v', 'R32': 'e2v', 'R33': 'e2v', 'R34': 'e2v', 'R41': 'ITL', 'R42': 'ITL',
                           'R43': 'ITL'}


        self.ccd1_scatter = None

        self.ccd_standard = 0
        self.med_shift_x = 0.
        self.med_shift_y = 0.
        self.shift_x = []
        self.shift_y = []
        self.mean_slope_diff = None
        self.center_to_center = [0., 0.]
        self.d_extrap = []

        self.line_fitting = False

        self.infile1 = None
        self.infile2 = None
        self.src1 = None
        self.src2 = None

        self.clean = True
        self.cln_box_half = 16  # half size of box around grid for cleaning - half grid direction
        self.cln_box_full = 27  # half size of box around grid for cleaning - full grid direction

        self.srcX = [[], []]
        self.srcY = [[], []]

        self.srcXErr = [[], []]  # derived from 2nd moments & flux for now
        self.srcYErr = [[], []]
        self.srcFlux = [[], []]

        self.gX1 = None
        self.gY1 = None
        self.gX2 = None
        self.gY2 = None

        self.x0_in = -100.
        self.y0_in = 2000.
        self.rot0_in = 0.

        self.x1_in = 4150.
        self.y1_in = 2000.
        self.rot1_in = 0.

        self.x0_fit = None
        self.y0_fit = None
        self.rot0_fit = None

        self.x1_fit = None
        self.y1_fit = None
        self.rot1_fit = None

        self.dx0 = None
        self.dy0 = None
        self.dtheta0 = None

        # simulation stuff

        self.grid_data_file = distort_file
        self.grid = None
        self.grid_x0 = None
        self.grid_y0 = None
        self.grid_x1 = None
        self.grid_y1 = None

        self.sim_x = None
        self.sim_y = None
        self.sim_moments = None
        self.sim_flux = None

        self.sim_doit = False
        self.sim_inter_raft = False
        self.sim_distort = False
        self.sim_rotate = 0.
        self.sim_offset = 0.

        # flags

        self.use_fit = False
        self.use_offsets = False
        self.init = False  # true if initialized (reset to False when getting new data)
        self.overlay_ccd = False  # true to put CCDs on same plot
        self.overlay_grid = False # true overlay grid on CCDs
        self.redo_fit = True

        self.dir_index = dir_index

        # set up buttons etc

        # button to terminate app
        self.button_exit = Button(label="Exit", button_type="danger", width=100)
        self.button_exit.on_click(self.do_exit)

        # button view rotated grids for binning
        self.button_rotate = Button(label="Rotate", button_type="danger", width=100)
        self.button_rotate.on_click(self.do_rotate)

        # button to enable using pickle files for input
        self.button_pickle = Button(label="Use Pickles", button_type="danger", width=100)
        self.button_pickle.on_click(self.do_pickle)

        # button toggle line fitting
        self.button_line_fitting = Button(label="Enable Lines", button_type="success", width=100)
        self.button_line_fitting.on_click(self.do_line_fitting)

        # sliders for offsetting spots patterns
        self.slider_x0 = Slider(title="x0 Value Range", start=-1000, end=5000, value=self.x0_in,
                                    width=900,
                                    format="0[.]0000")
        self.slider_x0.on_change('value_throttled', self.slider_x0_select)
        self.slider_y0 = Slider(title="y0 Value Range", start=-1000, end=5000, value=self.y0_in,
                                    width=900,
                                    format="0[.]0000")
        self.slider_y0.on_change('value_throttled', self.slider_y0_select)
        self.slider_x1 = Slider(title="x1 Value Range", start=-1000, end=5000, value=self.x1_in,
                                    width=900,
                                    format="0[.]0000")
        self.slider_x1.on_change('value_throttled', self.slider_x1_select)
        self.slider_y1 = Slider(title="y1 Value Range", start=-1000, end=5000, value=self.y1_in,
                                    width=900,
                                    format="0[.]0000")
        self.slider_y1.on_change('value_throttled', self.slider_y1_select)

        # button to submit slider values
        self.button_submit = Button(label="Submit slider", button_type="warning", width=100)
        self.button_submit.on_click(self.do_submit)

        # text box for box sizes in cleanup step
        self.text_box_half = TextInput(value=str(self.cln_box_half), title="Half size cln (px)")
        self.text_box_half.on_change('value', self.update_box_half)
        self.text_box_full = TextInput(value=str(self.cln_box_full), title="Full size cln (px)")
        self.text_box_full.on_change('value', self.update_box_full)

        # button to change data source
        self.button_get_data = Button(label="Refresh Data", button_type="warning", width=100)
        self.button_get_data.on_click(self.do_get_data)

        # button to perform fit
        self.button_fit = Button(label="Fit", button_type="warning", width=100)
        self.button_fit.on_click(self.do_fit)

        # button to toggle CCD overlay
        self.button_overlay_ccd = Button(label="Overlay CCDs", button_type="danger", width=100)
        self.button_overlay_ccd.on_click(self.do_overlay_ccd)

        # button to toggle grid overlay from fit
        self.button_overlay_grid = Button(label="Overlay grid", button_type="danger", width=100)
        self.button_overlay_grid.on_click(self.do_overlay_grid)

        # button to make plots from line fits
        self.button_linfit_plots = Button(label="Linfit plots", button_type="success", width=100)
        self.button_linfit_plots.on_click(self.do_linfit_plots)

        # button to make plots from grid fits
        self.button_gridfit_plots = Button(label="gridfit plots", button_type="success", width=100)
        self.button_gridfit_plots.on_click(self.do_gridfit_plots)

        # simulation buttons

        self.button_enable_sims = Button(label="Enable sims", button_type="danger", width=100)
        self.button_enable_sims.on_click(self.do_enable_sims)

        self.button_sims_orient = Button(label="Toggle orientation", button_type="success", width=100)
        self.button_sims_orient.label = "horizontal"
        self.button_sims_orient.on_click(self.do_sims_orient)

        self.button_sims_intra_raft = Button(label="Toggle intra-raft", button_type="danger", width=100)
        self.button_sims_intra_raft.label = "Intra-raft"
        self.button_sims_intra_raft.on_click(self.do_sims_intra_raft)

        self.button_sims_enable_distortions = Button(label="Toggle distortions", button_type="success", width=100)
        self.button_sims_enable_distortions.label = "Distortions On"
        self.button_sims_enable_distortions.on_click(self.do_sims_enable_distortions)

        self.text_sims_rotate = TextInput(value="0.", title="Sims Rot'n (rad)")
        self.text_sims_rotate.on_change('value', self.update_sims_rotate)
        self.text_sims_offset = TextInput(value="0.", title="Sims offset (px)")
        self.text_sims_offset.on_change('value', self.update_sims_offset)

        # do stuff in init

        rc = self.find_files()
        self.menu_data = []
        for name in self.file_paths:
            self.menu_data.append((name, self.file_paths[name] + ", " + name))

        # drop down menu of test names, taking the menu from self.menu_test
        self.drop_data = Dropdown(label="Select data", button_type="warning", menu=self.menu_data, width=150)
        self.drop_data.on_click(self.update_dropdown_data)

        # layouts

        self.layout = None

        sims_layout = row(self.button_enable_sims, self.button_sims_orient,
                          self.button_sims_intra_raft, self.button_sims_enable_distortions,
                          self.text_sims_offset, self.text_sims_rotate)

        self.min_layout = column(row(self.button_exit, self.drop_data, self.button_get_data, self.button_overlay_ccd,
                              self.button_overlay_grid, self.button_linfit_plots, self.button_rotate,
                              self.button_line_fitting, self.button_pickle),
                                 row(self.text_box_half, self.text_box_full))
        self.sliders_layout = column(row(self.slider_x0, self.slider_y0), row(self.slider_x1, self.slider_y1),
                                     self.button_submit)
        self.max_layout = column(self.min_layout, sims_layout, self.sliders_layout,
                                 row(self.button_fit, self.button_gridfit_plots))

        self.TOOLS = "pan, wheel_zoom, box_zoom, reset, save, box_select, lasso_select, tap"

        # set up DistortedGrid

        self.grid = DistortedGrid.from_fits(self.grid_data_file)
        normalized_shifts = (self.grid.norm_dy, self.grid.norm_dx)
        self.distorted_grid = DistortedGrid(xstep=self.pitch, ystep=self.pitch, theta=-self.rotate, x0=0, y0=0,
                                            ncols=self.num_spots, nrows=self.num_spots,
                                            normalized_shifts=normalized_shifts)

    # handlers

    def get_pickle_file(self):
        s_p = self.pickles_dir + self.raft_ccd_combo + ".p"
        pickle_file = open(s_p, "rb")
        pickle_obj = pickle.load(pickle_file)
        pickle_file.close()
        self.sensor = pickle_obj

        # re-establish global state

        self.ccd_relative_orientation = self.sensor[0].orientation
        self.extrap_dir = 1.
        if self.ccd_relative_orientation == "vertical":
            self.extrap_dir = -1.
        name_bits = self.raft_ccd_combo.split("_")
        self.name_ccd1 = name_bits[0] + "_" + name_bits[1]
        self.name_ccd2 = name_bits[2] + "_" + name_bits[3]
        self.names_ccd = [self.name_ccd1, self.name_ccd2]

        self.x0_in = pickle_obj[0].grid_fit_results.params["x0"].value
        self.y0_in = pickle_obj[0].grid_fit_results.params["y0"].value
        self.x1_in = pickle_obj[1].grid_fit_results.params["x0"].value
        self.y1_in = pickle_obj[1].grid_fit_results.params["y0"].value

        self.grid_x0 = self.x0_in
        self.grid_x1 = self.x1_in
        self.grid_y0 = self.y0_in
        self.grid_y1 = self.y1_in

        return

    def update_dropdown_data(self, event):
        self.dir_index = event.item.split(",")[0].strip()
        self.raft_ccd_combo = event.item.split(",")[1].strip()
        self.drop_data.button_type = "warning"

        self.use_offsets = True
        rc = self.do_get_data()

        return

    def update_box_half(self, sattr, old, new):
        self.cln_box_half = float(self.text_box_half.value)
        return

    def update_box_full(self, sattr, old, new):
        self.cln_box_full = float(self.text_box_full.value)
        return

    def do_pickle(self):
        self.use_pickles = not self.use_pickles
        if self.use_pickles:
            self.button_pickle.button_type = "success"
        else:
            self.button_pickle.button_type = "danger"

    def do_exit(self):
        print("Shutting down app")
        sys.exit(0)

    def do_enable_sims(self):
        self.sim_doit = not self.sim_doit
        if self.sim_doit:
            self.button_enable_sims.button_type = "success"
        else:
            self.button_enable_sims.button_type = "danger"

        return

    def do_sims_orient(self):
        if self.ccd_relative_orientation == "vertical":
            self.ccd_relative_orientation = "horizontal"
        else:
            self.ccd_relative_orientation = "vertical"

        self.button_sims_orient.label = self.ccd_relative_orientation

        return

    def do_sims_intra_raft(self):
        self.sim_inter_raft = not self.sim_inter_raft
        if self.sim_inter_raft:
            self.button_sims_intra_raft.button_type = "success"
        else:
            self.button_sims_intra_raft.button_type = "danger"

        return

    def do_sims_enable_distortions(self):
        self.sim_distort = not self.sim_distort
        if self.sim_distort:
            self.button_sims_enable_distortions.button_type = "success"
            self.button_sims_enable_distortions.label = "Distortions On"
        else:
            self.button_sims_enable_distortions.button_type = "danger"
            self.button_sims_enable_distortions.label = "Distortions Off"
        return

    def update_sims_rotate(self, sattr, old, new):
        self.sim_rotate = float(self.text_sims_rotate.value)
        return

    def update_sims_offset(self, sattr, old, new):
        self.sim_offset = float(self.text_sims_offset.value)
        return

    def do_rotate(self):
        self.show_rotate = not self.show_rotate
        if self.show_rotate:
            self.button_rotate.button_type = "success"
        else:
            self.button_rotate.button_type = "danger"

    def do_line_fitting(self):
        self.line_fitting = not self.line_fitting
        if self.line_fitting:
            self.button_line_fitting.button_type = "success"
        else:
            self.button_line_fitting.button_type = "danger"

    def do_overlay_ccd(self):
        self.overlay_ccd = not self.overlay_ccd
        if self.overlay_ccd:
            self.button_overlay_ccd.button_type = "success"
        else:
            self.button_overlay_ccd.button_type = "danger"
        pl = self.make_plots()
        m_new = column(self.max_layout, pl)
        self.layout.children = m_new.children

    def do_overlay_grid(self):
        self.overlay_grid = not self.overlay_grid
        if self.overlay_grid:
            self.button_overlay_grid.button_type = "success"
        else:
            self.button_overlay_grid.button_type = "danger"

        rc = self.setup_grid()
        pl = self.make_plots()
        m_new = column(self.max_layout, pl)
        self.layout.children = m_new.children

    def do_linfit_plots(self):
        p_grid = self.make_line_plots()

        m_new = column(self.max_layout, p_grid)
        self.layout.children = m_new.children

    def do_gridfit_plots(self):
        p_grid = self.make_fit_plots()

        m_new = column(self.max_layout, p_grid)
        self.layout.children = m_new.children

    def iterate_fit(self):
        # hack in case fit and lines are off by a spot - inflate long edge guess by 5% and re-fit
        inflate = 1.0075
        pitch_frac = 0.3

        if self.line_fitting:
            if self.ccd_relative_orientation == "horizontal":
                if abs(abs(self.center_to_center[0]) - abs(self.dx0)) > pitch_frac*self.pitch:
                    if self.ccd_standard == 0:
                        self.grid_x1 *= inflate
                    else:
                        self.grid_x0 *= inflate
                    print("refit")
                    rc = self.match()

            else:
                if abs(abs(self.center_to_center[1]) - abs(self.dy0)) > pitch_frac*self.pitch:
                    if self.ccd_standard == 0:
                        self.grid_y1 *= inflate
                    else:
                        self.grid_y0 *= inflate
                    print("refit")
                    rc = self.match()

    def do_fit(self):
        self.use_fit = True
        rc = self.match()
        self.redo_fit = False
        rc = self.iterate_fit()

        # set slider values to zero to be offsets from grid centers
        self.slider_x0.value = 0.
        self.slider_y0.value = 0.
        self.slider_x1.value = 0.
        self.slider_y1.value = 0.

        pl = self.make_plots()
        m_new = column(self.max_layout, pl)
        self.layout.children = m_new.children
        return

    def do_submit(self):
        self.use_offsets = True
        if self.use_fit:
            self.grid_x0 += self.slider_x0.value
            self.grid_y0 += self.slider_y0.value
            self.grid_x1 += self.slider_x1.value
            self.grid_y1 += self.slider_y1.value

        pl = self.make_plots()
        m_new = column(self.max_layout, pl)
        self.layout.children = m_new.children
        return

    def slider_x0_select(self, sattr, old, new):
        self.x0_in = self.slider_x0.value

    def slider_y0_select(self, sattr, old, new):
        self.y0_in = self.slider_y0.value

    def slider_x1_select(self, sattr, old, new):
        self.x0_in = self.slider_x1.value

    def slider_y1_select(self, sattr, old, new):
        self.y0_in = self.slider_y1.value

    def do_get_data(self):

        if self.use_pickles:
            rc = self.get_pickle_file()
            self.drop_data.label = self.raft_ccd_combo
        else:
            try:
                rc = self.get_data()
            except ValueError:
                self.drop_data.button_type = "danger"
                m_new = column(self.max_layout)
                self.layout.children = m_new.children
                return

        self.use_offsets = False
        self.use_fit = False
        self.redo_fit = True
        pl = self.make_plots()
        m_new = column(self.max_layout, pl)
        self.layout.children = m_new.children

    # worker routines

    def find_files(self):

        base_dir = self.dir_index
        self.file_paths = {}
        result_dirs = sorted(glob.glob(base_dir + "/*/*/"))

        for result_dir in result_dirs:
            try:  # bail if 2 files not found
                infile1, infile2 = sorted(glob.glob(join(result_dir, '*_source_catalog.cat')))
            except ValueError:
                continue

            name_ccd1 = os.path.basename(infile1).split("_source")[0].strip()
            name_ccd2 = os.path.basename(infile2).split("_source")[0].strip()
            combo_name = name_ccd1 + "_" + name_ccd2

            try:
                self.file_paths[combo_name] = result_dir
            except KeyError:
                self.file_paths[combo_name + "_1"] = result_dir

        return

    def find_lines(self, x_in, y_in):

        if self.ccd_relative_orientation == "horizontal":
            x_use = x_in
            y_use = y_in
        else:
            x_use = y_in
            y_use = x_in

        # sort the y-coordinates
        rad = self.rotate * self.extrap_dir
        x_rot = math.cos(rad) * np.array(x_use) - math.sin(rad) * np.array(y_use)
        y_rot = math.sin(rad) * np.array(x_use) + math.cos(rad) * np.array(y_use)

        order = np.argsort(-y_rot, kind="stable")
        x = np.array(x_use)[order]
        y = np.array(y_use)[order]
        y_rot_ordered = np.array(y_rot)[order]

        # find lines

        n_close = 0
        y_min = min(y_rot_ordered)
        for nc in range(1, 10):
            ya = y_rot_ordered[-nc - 1]
            yb = y_rot_ordered[-nc]
            diff = y_rot_ordered[-nc - 1] - y_rot_ordered[-nc]
            if diff < 5.:  # look for a bunch of spots close together
                n_close += 1
            if n_close > 4:
                y_min = y_rot_ordered[-nc] - 10.  # back off a bit to get back the first few
                break

        ccd = {}

        for idy, yi in enumerate(y_rot_ordered):
            if yi - y_min < 0.:  # spurious low point
                continue
            line_bin = int((yi-y_min+self.pitch/5.)/self.pitch)
            if line_bin > 48:  # spurious high point
                continue
            fl = ccd.setdefault(line_bin, [])
            if self.ccd_relative_orientation == "horizontal":
                ccd[line_bin].append([x[idy], y[idy]])
            else:
                ccd[line_bin].append([y[idy], x[idy]])

        if len(ccd) != self.num_spots:
            print(self.raft_ccd_combo + ": Problem finding full grid: found ", len(ccd),
                  " lines")
            raise ValueError

        # sort lists by x

        nl = len(ccd)
        for n in range(nl):
            ccd[n] = sorted(ccd[n], key=lambda xy: xy[0])
        #    # ensure end points make sense
        #    if abs(ccd[n][0][0] - ccd[n][1][0]) > self.cut_spurious_spots:
        #        del ccd[n][0]
        #    if abs(ccd[n][-1][0] - ccd[n][-2][0]) > self.cut_spurious_spots:
        #        del ccd[n][-1]

        return ccd

    def make_line_plots(self):

        print("# lines in ", self.name_ccd1, " ", len(self.sensor[0].lines))
        print("# lines in ", self.name_ccd2, " ", len(self.sensor[1].lines))

        num_spots = [len(self.sensor[0].lines[k]) for k in self.sensor[0].lines]
        num_spots2 = [len(self.sensor[1].lines[k]) for k in self.sensor[1].lines]
        num_spots.extend(num_spots2)
        print("Total spots = ", sum(num_spots))

        coord = 0
        if self.ccd_relative_orientation == "vertical":
            coord = 1

        slopes = []
        slopes_ccd1 = []
        slopes_ccd2 = []
        color = ["blue", "red"]

        for l in range(2):
            for lines in self.sensor[l].linfits:
                slopes.append(self.sensor[l].linfits[lines][0])
                if l == 0:
                    slopes_ccd1.append(self.sensor[l].linfits[lines][0])
                else:
                    slopes_ccd2.append(self.sensor[l].linfits[lines][0])

        s_hist, bins = np.histogram(np.array(slopes), bins=20)
        p_hist = figure(tools=self.TOOLS, title="All slopes", x_axis_label='slope', y_axis_label='counts',
                        width=600)

        p_hist.vbar(top=s_hist, x=bins[:-1], width=bins[1]-bins[0], fill_color='red', fill_alpha=0.2)

        s1_hist, bins = np.histogram(np.array(slopes_ccd1), bins=20)
        p1_hist = figure(tools=self.TOOLS, title=self.name_ccd1 + " slopes", x_axis_label='slope', \
                                                                                y_axis_label='counts',
                        width=600)

        p1_hist.vbar(top=s1_hist, x=bins[:-1], width=bins[1]-bins[0], fill_color='red', fill_alpha=0.2)

        s2_hist, bins = np.histogram(np.array(slopes_ccd2), bins=20)
        p2_hist = figure(tools=self.TOOLS, title=self.name_ccd2 + " slopes", x_axis_label='slope', \
                                                                                y_axis_label='counts',
                        width=600)

        p2_hist.vbar(top=s2_hist, x=bins[:-1], width=bins[1]-bins[0], fill_color='red', fill_alpha=0.2)

        ex_hist, bins = np.histogram(np.array(self.d_extrap), bins=20)
        pex_hist = figure(tools=self.TOOLS, title="Extrapolation distance", x_axis_label='distance (px)',
                          y_axis_label='counts',
                        width=600)

        pex_hist.vbar(top=ex_hist, x=bins[:-1], width=bins[1]-bins[0], fill_color='red', fill_alpha=0.2)

        shy_hist, bins = np.histogram(np.array(self.shift_y), bins=20)
        shexy_hist = figure(tools=self.TOOLS, title="y shift distance", x_axis_label='distance (px)',
                          y_axis_label='counts',
                        width=600)

        shexy_hist.vbar(top=shy_hist, x=bins[:-1], width=bins[1]-bins[0], fill_color='red', fill_alpha=0.2)

        shx_hist, bins = np.histogram(np.array(self.shift_x), bins=20)
        shexx_hist = figure(tools=self.TOOLS, title="x shift distance", x_axis_label='distance (px)',
                          y_axis_label='counts',
                        width=600)

        shexx_hist.vbar(top=shx_hist, x=bins[:-1], width=bins[1]-bins[0], fill_color='red', fill_alpha=0.2)

        n_lines = len(self.sensor[0].lines)

        slopes_diff = []
        for nl in range(n_lines):
            slopes_diff.append(self.sensor[1].linfits[nl][0] - self.sensor[0].linfits[nl][0])

        sd_hist, bins = np.histogram(np.array(slopes_diff), bins=20)
        pd_hist = figure(tools=self.TOOLS, title="delta slopes", x_axis_label='slope difference',
                         y_axis_label='counts',
                         width=600)

        s1v2 = figure(title="Slopes: " + self.name_ccd1 + " vs " + self.name_ccd2,
                      x_axis_label=self.name_ccd1 + ' slope',
                      y_axis_label=self.name_ccd2 + ' slope',
                      tools=self.TOOLS)
        source_s1v2 = ColumnDataSource(dict(y=slopes_ccd2, x=slopes_ccd1))
        s1v2.circle(x="x", y="y", source=source_s1v2, color="blue")

        sdvnl = figure(title="Slope diff vs line #: " + self.raft_ccd_combo,
                       x_axis_label='slope difference',
                       y_axis_label='line #',
                       tools=self.TOOLS)
        source_sdvnl = ColumnDataSource(dict(x=slopes_diff, y=range(n_lines)))
        sdvnl.circle(x="x", y="y", source=source_sdvnl, color="blue")

        pd_hist.vbar(top=sd_hist, x=bins[:-1], width=bins[1] - bins[0], fill_color='red', fill_alpha=0.2)

        svl1 = figure(title=self.name_ccd1 + ": slope vs line #", x_axis_label='line #',
                    y_axis_label='slope', tools=self.TOOLS)
        source_svl1 = ColumnDataSource(dict(y=slopes_ccd1, x=range(n_lines)))
        svl1.circle(x="x", y="y", source=source_svl1, color="blue")
        svl2 = figure(title=self.name_ccd2 + ": slope vs line #", x_axis_label='line #',
                    y_axis_label='slope', tools=self.TOOLS)
        source_svl2 = ColumnDataSource(dict(y=slopes_ccd2, x=range(n_lines)))
        svl2.circle(x="x", y="y", source=source_svl2, color="blue")

        hist_list = [[p_hist, pd_hist], [shexx_hist, shexy_hist], [pex_hist], [s1v2, sdvnl],
                     [p1_hist, p2_hist], [svl1, svl2]]

        # overlay fit lines on scatterplots

        spot_pitch = {}
        residuals = {}
        gap_residuals = {}
        x_spot = []
        y_spot = []
        res_spot = []
        pitch_spot = []

        r_hist = figure(tools=self.TOOLS, title="residuals", x_axis_label='residuals',
                        y_axis_label='counts', x_range=(0.5, 1.5),
                        width=600)
        gr_hist = figure(tools=self.TOOLS, title="gap residuals", x_axis_label='residuals',
                         y_axis_label='counts', x_range=(-1.5, 1.5),
                         width=600)

        pitch_hist = figure(tools=self.TOOLS, title="Spot pitch ", x_axis_label='pitch',
                            y_axis_label='counts',
                            width=600)

        off_ccd = [[0., 0.], [0., 0.]]
        if self.use_fit:
            off_ccd[0] = [-self.dx0, -self.dy0]
            print("make_line_plots: use for fitted offsets ", off_ccd)
        elif self.use_offsets:
            off_ccd = [[self.x0_in, self.y0_in], [self.x1_in, self.y1_in]]

        for l in range(2):
            spl = spot_pitch.setdefault(l, [])
            res = residuals.setdefault(l, [])
            g_res = gap_residuals.setdefault(l, [])

            for nl in range(n_lines):
                x0 = self.sensor[l].lines[nl][0][0]
                y0 = self.sensor[l].linfits[nl][0] * x0 + self.sensor[l].linfits[nl][1]
                x1 = self.sensor[l].lines[nl][-1][0]
                y1 = self.sensor[l].linfits[nl][0] * x1 + self.sensor[l].linfits[nl][1]
                x0 -= off_ccd[l][0]
                y0 -= off_ccd[l][1]
                x1 -= off_ccd[l][0]
                y1 -= off_ccd[l][1]

                if self.ccd1_scatter is not None:
                    self.ccd1_scatter.line([x0, x1], [y0, y1], line_width=2)

                n_spots = len(self.sensor[l].lines[nl])
                xp = -1.
                yp = -1.
                c_diff = -1.
                for s in range(n_spots):
                    x0 = self.sensor[l].lines[nl][s][0]
                    y0 = self.sensor[l].lines[nl][s][1]
                    if self.ccd_relative_orientation == "horizontal":  # get perpendicular coord residual
                        y0_fit = self.sensor[l].linfits[nl][0] * x0 + self.sensor[l].linfits[nl][1]
                        c_diff = y0_fit - y0
                    else:
                        x0_fit = (y0 - self.sensor[l].linfits[nl][1])/self.sensor[l].linfits[nl][0]
                        c_diff = x0_fit - x0

                    res.append(c_diff + 1.)

                    # find spots along the gaps
                    if (self.ccd_standard == l and s == 0) or \
                            (self.ccd_standard != l and s == (n_spots - 1)):
                        g_res.append(c_diff)

                    d = 0.
                    if (xp != -1.):
                        d = math.sqrt((x0 - xp)**2 + (y0 - yp)**2)
                        spl.append(d)

                    xp = x0
                    yp = y0

                    x_spot.append(x0 - off_ccd[l][0])
                    y_spot.append(y0 - off_ccd[l][1])
                    res_spot.append(abs(c_diff))
                    pitch_spot.append(d)

            resid, bins = np.histogram(np.array(res), bins=200, range=(-2., 2.))
            w = bins[1] - bins[0]

            popt = [0., 0., 0.]
            if not (self.sim_doit and not self.sim_distort):
                popt, _ = optimize.curve_fit(self.gaussian, bins[:-1]+w/2., resid)
            r_sigma = abs(popt[2])
            r_mu = 1. - popt[1]
            print("residual for ", self.names_ccd[l], " mean: ", r_mu, " sigma: ", r_sigma)

            r_hist.step(y=resid, x=bins[:-1]+w/2., color=color[l], legend_label=self.names_ccd[l] + " σ = " +
                         f'{r_sigma:.3f}')

            g_resid, bins = np.histogram(np.array(g_res), bins=200, range=(-2., 2.))

            w = bins[1] - bins[0]
            gr_hist.step(y=g_resid, x=bins[:-1]+w/2., color=color[l], legend_label=self.names_ccd[l])

            pitches, bins = np.histogram(np.array(spl), bins=200, range=(64., 67.))
            w = bins[1] - bins[0]

            pitch_hist.step(y=pitches, x=bins[:-1]+w/2., color=color[l], legend_label=self.names_ccd[l])

        far = -1
        near = 0
        #if self.ccd_relative_orientation == "vertical":
        #    far = 0
        #    near = -1

        grid_width = []
        for num_lin in range(n_lines):  # end to end grid width
            x10 = self.sensor[self.ccd_standard].lines[num_lin][far][0]
            y10 = self.sensor[self.ccd_standard].linfits[num_lin][1] + \
                 self.sensor[self.ccd_standard].linfits[num_lin][0] * x10
            x21 = self.sensor[1-self.ccd_standard].lines[num_lin][near][0]
            y21 = self.sensor[1-self.ccd_standard].linfits[num_lin][1] + \
                  self.sensor[1-self.ccd_standard].linfits[num_lin][0] * x21

            x21 -= self.shift_x[num_lin]
            y21 -= self.shift_y[num_lin]
            dist = math.hypot(x21-x10, y21-y10)/self.pitch  # distance in spots
            grid_width.append(dist)

        gw, bins = np.histogram(np.array(grid_width), bins=50)
        w = bins[1] - bins[0]
        gw_hist = figure(tools=self.TOOLS, title="Grid width ", x_axis_label='width (spots)',
                            y_axis_label='counts',
                            width=600)
        gw_hist.vbar(top=gw, x=bins[:-1], width=bins[1]-bins[0], fill_color='red', fill_alpha=0.2)

        cds_spot = ColumnDataSource(dict(x=x_spot, y=y_spot, res=res_spot, pitch=pitch_spot))

        spot_heat = figure(title="Spots Grid: spot pitch " + self.raft_ccd_combo, x_axis_label='x',
                           y_axis_label='y', tools=self.TOOLS)
        c_color_mapper_sp = LinearColorMapper(palette=palette, low=64., high=66.5)
        c_color_bar_sp = ColorBar(color_mapper=c_color_mapper_sp, label_standoff=8, width=500, height=20,
                               border_line_color=None, location=(0, 0), orientation='horizontal')
        spot_heat.circle(x="x", y="y", source=cds_spot, color="gray", size=10,
                         fill_color={'field': 'pitch', 'transform': c_color_mapper_sp})
        spot_heat.add_layout(c_color_bar_sp, 'below')

        c_color_mapper_res = LogColorMapper(palette=palette, low=0.001, high=2.)
        c_color_bar_res = ColorBar(color_mapper=c_color_mapper_res, label_standoff=8, width=500, height=20,
                               border_line_color=None, location=(0, 0), orientation='horizontal')
        res_heat = figure(title="Spots Grid: residuals (-1, 1)  " + self.raft_ccd_combo, x_axis_label='x',
                           y_axis_label='y', tools=self.TOOLS)
        res_heat.circle(x="x", y="y", source=cds_spot, color="gray", size=10,
                         fill_color={'field': 'res', 'transform': c_color_mapper_res})
        res_heat.add_layout(c_color_bar_res, 'below')

        hist_list.append([r_hist, pitch_hist])
        hist_list.append([gr_hist, gw_hist])
        hist_list.append([res_heat, spot_heat])
        hist_list.append([self.ccd1_scatter])

        print("Mean spot pitch 0: ", np.mean(np.array(spot_pitch[0])), " 1: ", np.mean(np.array(spot_pitch[1])))
        mean_delta_slope = np.mean(np.array(slopes_diff))
        print("Mean delta slope: ", mean_delta_slope
              )
        return gridplot(hist_list)

    def gaussian(self, x, amplitude, mean, stddev):
        return amplitude * np.exp(-0.5 * ((x - mean) / stddev) ** 2)

    def fit_line_pairs(self, line_list):

        x = []
        y = []
        for pt in line_list:
            x.append(pt[0])
            y.append(pt[1])

        order = np.argsort(np.array(x), kind="stable")
        x = np.array(x)[order].reshape(-1, 1)
        y = np.array(y)[order]

        # https://scikit-learn.org/stable/modules/generated/
        #                     sklearn.linear_model.RANSACRegressor.html#sklearn.linear_model.RANSACRegressor
        # Robustly fit linear model with RANSAC algorithm
        ransac = linear_model.RANSACRegressor()
        ransac.fit(x, y)
        inlier_mask = ransac.inlier_mask_
        outlier_mask = np.logical_not(inlier_mask)

        return ransac.estimator_.coef_[0], ransac.estimator_.intercept_, outlier_mask

    def missing_internal_spots(self, sensor_num, line_num):

        coord = 0
        if self.ccd_relative_orientation == "vertical":
            coord = 1

        num_holes = 0
        len_line = len(self.sensor[sensor_num].lines[line_num])
        for spot in range(len_line-1):   # check for internal gaps
            dist = abs(self.sensor[sensor_num].lines[line_num][spot+1][coord] -
                   self.sensor[sensor_num].lines[line_num][spot][coord])
            if dist > self.cut_spurious_spots:
                num_holes += int(dist/self.pitch/0.95 - 1)  # estimate number missing spots from length of hole

        return num_holes

    def match_lines(self):

        # decide which CCD is the standard - the other is then measured relative to it. Pick the one that
        # is fatter on top.

        self.ccd_standard = 0
        non_standard = 1
        #if len(self.sensor[1].lines[self.num_spots-1]) > len(self.sensor[1].lines[0]):
        #    self.ccd_standard = 1
        #    non_standard = 0

        if self.ccd_relative_orientation == "vertical":
            co = 1
        else:
            co = 0
        m_0 = self.sensor[0].lines[0][0][co]
        m_1 = self.sensor[1].lines[1][0][co]
        if m_1 < m_0:
                self.ccd_standard = 1
                non_standard = 0

        n_lines = len(self.sensor[0].lines)   # they'd better both have the same number!
        self.shift_x = []
        self.shift_y = []
        slope_difference = []
        internal_hole_sums = [0, 0]

        for nl in range(n_lines):

            # count spots and calculate the spots gap between the CCDs
            internal_hole = [self.missing_internal_spots(0, nl), self.missing_internal_spots(1, nl)]
            internal_hole_sums[0] += internal_hole[0]
            internal_hole_sums[1] += internal_hole[1]
            nspots0 = len(self.sensor[0].lines[nl])
            nspots1 = len(self.sensor[1].lines[nl])
            missing_spots = self.num_spots - (nspots0 + nspots1 +
                            internal_hole[0] + internal_hole[1])

            # distance between first spot on standard CCD and last spot on the other
            extrap_dist = (missing_spots + 1) * self.pitch  # gaps needed to add
            self.d_extrap.append(extrap_dist)

            near_end = 0
            far_end = -1
            #if self.ccd_relative_orientation == "vertical":
            #    far_end = 0
            #    near_end = -1

            x1 = self.sensor[self.ccd_standard].lines[nl][near_end][0]
            y1 = self.sensor[self.ccd_standard].linfits[nl][1] +  \
                 self.sensor[self.ccd_standard].linfits[nl][0] * x1
            x2 = self.sensor[self.ccd_standard].lines[nl][far_end][0]
            y2 = self.sensor[self.ccd_standard].linfits[nl][1] + \
                 self.sensor[self.ccd_standard].linfits[nl][0] * x2

            # work out how to extrapolate along the line a given distance

            length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

            unitSlopeX = (x2 - x1) / length
            unitSlopeY = (y2 - y1) / length

            # new_ is coordinate of other sensor last spot in the standard sensor's system

            new_x = x1 - extrap_dist * unitSlopeX
            new_y = y1 - extrap_dist * unitSlopeY

            # old_ is the coordinate of the last spot in the non-standard's system

            old_x = self.sensor[non_standard].lines[nl][far_end][0]
            old_y = self.sensor[non_standard].linfits[nl][1] + \
                    self.sensor[non_standard].linfits[nl][0] * old_x

            # shift is the offset per line to move the non-standard sensor into the standard's system

            self.shift_x.append(old_x - new_x)
            self.shift_y.append(old_y - new_y)

            slope_difference.append(math.atan(self.sensor[1].linfits[nl][0]) -
                                    math.atan(self.sensor[0].linfits[nl][0]))

        print("Found internal holes: ", internal_hole_sums)

        self.med_shift_x = np.median(np.array(self.shift_x))
        self.med_shift_y = np.median(np.array(self.shift_y))
        #if self.ccd_relative_orientation == "horizontal":
        #    self.med_shift_x = np.min(np.array(self.shift_x))
        #    self.med_shift_y = np.median(np.array(self.shift_y))
        #else:
        #    self.med_shift_x = np.median(np.array(self.shift_x))
        #    self.med_shift_y = np.min(np.array(self.shift_y))

        self.mean_slope_diff = np.mean(np.array(slope_difference[18:25]))  # try middle of line range

        xc, yc = self.find_center_spots()
        self.sensor[0].x_center = xc[0]
        self.sensor[0].y_center = yc[0]
        self.sensor[1].x_center = xc[1]
        self.sensor[1].y_center = yc[1]

        self.med_shift_x = (np.mean(np.array(xc[1])) - np.mean(np.array(xc[0]))) * self.extrap_dir
        self.med_shift_y = (np.mean(np.array(yc[1])) - np.mean(np.array(yc[0]))) * self.extrap_dir

        if self.ccd_relative_orientation == "horizontal":
            self.x1_in = self.med_shift_x
            self.y1_in = 2100. + self.med_shift_y

            self.x0_in = 0.
            self.y0_in = 2100.
        else:
            self.x0_in = self.med_shift_x
            self.y0_in = self.med_shift_y

            self.x1_in = 0.
            self.y1_in = 0.

        # grid centers are in the coordinate system of the respective sensor

        self.grid_x0 = np.mean(np.array(xc[0]))
        self.grid_y0 = np.mean(np.array(yc[0]))

        self.grid_x1 = np.mean(np.array(xc[1]))
        self.grid_y1 = np.mean(np.array(yc[1]))

        print("line fitter grid centers: x0, y0, x1, y1 ", self.grid_x0, self.grid_y0, self.grid_x1, self.grid_y1)

        # rotate the non-standard sensor into the standard sensor's frame to get the offsets estimate

        #        centers = [2048., 2048.]
        centers = [2100., 2100.]

        if self.ccd_standard == 0:
            x0 = self.grid_x0
            y0 = self.grid_y0
            x1, y1 = self.rotate_xy(self.grid_x1-2048., self.grid_y1-2048., -self.mean_slope_diff)
            x1 += 2048.
            y1 += 2048.
        else:
            x1 = self.grid_x1
            y1 = self.grid_y1
            x0, y0 = self.rotate_xy(self.grid_x0-2048., self.grid_y0-2048., -self.mean_slope_diff)
            x0 += 2048.
            y0 += 2048.

        c1 = [centers[0] - x1, centers[1] - y1]
        c0 = [centers[0] - x0, centers[1] - y0]
        self.center_to_center = np.array(c0) - np.array(c1)

        print("line fit final coords: , x0, y0, x1, y1 ", x0, y0, x1, y1)
        print("x0_in, y0_in, x1_in, y1_in = ", self.x0_in, self.y0_in, self.x1_in, self.y1_in)
        print("shift x, y = ", self.med_shift_x, self.med_shift_y)
        print("standard CCD ", self.ccd_standard, self.names_ccd[self.ccd_standard],
              self.ccd_relative_orientation)
        print("(x, y) center to center = ", self.center_to_center, "mean slope diff ", self.mean_slope_diff)

        return

    def find_center_spots(self):

        # Reminder of what needs doing:
        #  For horizontal pairings, lines are extrapolated towards the grid center for both sensors:
        #  in the negative direction from the near end for the sensor whose x coordinates start at zero and positive
        #  from the far end for those with coordinates ending around 4000.
        #
        #  Similarly for vertically paired, the direction is negative for y coords near zero and positive
        #  for those near 4000. Near and far ends follow the same pattern
        #
        # self.ccd_standard is set by this criteria, and in all cases, ccd_standard == 0 for horizontal
        # and 1 for vertical pairings.

        non_standard = 1
        xc = {}
        yc = {}

        for s in self.sensor:
            lxc = xc.setdefault(s, [])
            lyc = yc.setdefault(s, [])

            for nl in range(49):

                # get the spot pitches near the sensor edges
                distances = distance.cdist(self.sensor[s].lines[nl],
                                                self.sensor[s].lines[nl],
                                                metric="euclidean")
                dists_near = [distances[d, d+1] for d in range(4)]
                pitch_near = np.mean(np.array(dists_near))
                len_line = len(self.sensor[s].lines[nl])
                dists_far = [distances[d, d + 1] for d in range(len_line-5,len_line-1)]
                pitch_far = np.mean(np.array(dists_far))

                # count spots and calculate the spots gap between the CCDs
                internal_hole = [self.missing_internal_spots(0, nl), self.missing_internal_spots(1, nl)]
                nspots = len(self.sensor[s].lines[nl])
                missing_spots = 25 - (nspots + internal_hole[s])

                # distance first spot on standard CCD or last spot on the other to the grid center spot
                extrap_dist = (missing_spots) * self.pitch  # gaps needed to add

                x1 = self.sensor[s].lines[nl][0][0]
                y1 = self.sensor[s].linfits[nl][1] +  \
                     self.sensor[s].linfits[nl][0] * x1
                x2 = self.sensor[s].lines[nl][-1][0]
                y2 = self.sensor[s].linfits[nl][1] + \
                     self.sensor[s].linfits[nl][0] * x2

                # work out how to extrapolate along the line a given distance

                length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

                unitSlopeX = (x2 - x1) / length
                unitSlopeY = (y2 - y1) / length

                #if self.ccd_relative_orientation == "horizontal":
                #    unitSlopeY = self.sensor[s].linfits[nl][0]
                #    unitSlopeX = math.sqrt(1.-unitSlopeY**2)
                #else:
                #    unitSlopeX = self.sensor[s].linfits[nl][0]
                #    unitSlopeY = math.sqrt(1. - unitSlopeX ** 2)

                # new_ is coordinate of other sensor last spot in the standard sensor's system

                if s == self.ccd_standard:
                    extrap_dist = (missing_spots) * pitch_near  # gaps needed to add
                    new_x = x1 - extrap_dist * unitSlopeX
                    new_y = y1 - extrap_dist * unitSlopeY
                else:
                    extrap_dist = (missing_spots) * pitch_far  # gaps needed to add
                    new_x = x2 + extrap_dist * unitSlopeX
                    new_y = y2 + extrap_dist * unitSlopeY

                # old_ is the coordinate of the last spot in the non-standard's system

                old_x = self.sensor[non_standard].lines[nl][-1][0]
                old_y = self.sensor[non_standard].linfits[nl][1] + \
                        self.sensor[non_standard].linfits[nl][0] * old_x

                shift_old_x = new_x
                shift_old_y = new_y

                xc[s].append(shift_old_x)
                yc[s].append(shift_old_y)
            print("spot centers ", s, " x: ", np.mean(np.array(xc[s])), " y:", np.mean(np.array(yc[s])))

        return xc, yc

    def get_data(self, combo_name=None):

        print(" Entered get_data")

        self.srcX = [[], []]
        self.srcY = [[], []]

        if self.sim_doit:
            rc = self.simulate_response()
            combo_name = self.raft_ccd_combo = "Sim_x_Sim_y"
            self.name_ccd1 = "Sim_x"
            self.name_ccd2 = "Sim_y"
            self.names_ccd = [self.name_ccd1, self.name_ccd2]

        if combo_name is None:
            combo_name = self.raft_ccd_combo
        else:
            self.raft_ccd_combo = combo_name

        self.drop_data.label = combo_name

        infile1 = None
        infile2 = None

        if self.sim_doit:
            X1 = self.sim_x[0]
            Y1 = self.sim_y[0]
            self.extrap_dir = 1.

            if self.ccd_relative_orientation == "vertical":
                self.extrap_dir = -1.
        else:
            dir_index = self.file_paths[combo_name]
            results_dirs = sorted(glob.glob(dir_index))
            for result_dir in results_dirs:
                print(result_dir)

            self.infile1, self.infile2 = sorted(glob.glob(join(results_dirs[0], '*_source_catalog.cat')))
            print(self.infile1)
            print(self.infile2)

            self.name_ccd1 = os.path.basename(self.infile1).split("_source")[0]
            self.name_ccd2 = os.path.basename(self.infile2).split("_source")[0]
            self.names_ccd = [self.name_ccd1, self.name_ccd2]

            r1 = self.name_ccd1.split("_")[0]
            r2 = self.name_ccd2.split(("_"))[0]
            s1 = self.name_ccd1.split("_")[1]
            s2 = self.name_ccd2.split(("_"))[1]
            self.extrap_dir = 1.

            if int(s1[1]) == int(s2[1]):
                self.ccd_relative_orientation = "horizontal"
            else:
                self.ccd_relative_orientation = "vertical"
                self.extrap_dir = -1.

        self.sensor = {}
        self.sensor[0] = sensor()
        self.sensor[1] = sensor()

        kw_x = 'base_SdssShape_x'
        kw_y = 'base_SdssShape_y'
        kw_xx = 'base_SdssShape_xx'
        kw_yy = 'base_SdssShape_yy'
        kw_flux = 'base_SdssShape_instFlux'

        # use simulation data
        if self.sim_doit:
            self.sensor[0].spot_input = dict(x=self.sim_x[0], y=self.sim_y[0], xx=self.sim_moments[0],
                                             yy=self.sim_moments[0], flux=self.sim_flux[0])
            self.sensor[1].spot_input = dict(x=self.sim_x[1], y=self.sim_y[1], xx=self.sim_moments[1],
                                             yy=self.sim_moments[1], flux=self.sim_flux[1])
        else:   # use projector data
            self.sensor[0].src = fits.getdata(self.infile1)
            self.sensor[0].spot_input = dict(x=self.sensor[0].src[kw_x], y=self.sensor[0].src[kw_y],
                                             xx=self.sensor[0].src[kw_xx], yy=self.sensor[0].src[kw_yy],
                                             flux=self.sensor[0].src[kw_flux])
            self.sensor[0].orientation = self.ccd_relative_orientation
            self.sensor[0].sensor_type = self.raft_types[r1]
            self.sensor[0].name = self.name_ccd1

            self.sensor[1].src = fits.getdata(self.infile2)
            self.sensor[1].spot_input = dict(x=self.sensor[1].src[kw_x], y=self.sensor[1].src[kw_y],
                                             xx=self.sensor[1].src[kw_xx], yy=self.sensor[1].src[kw_yy],
                                             flux=self.sensor[1].src[kw_flux])
            self.sensor[1].orientation = self.ccd_relative_orientation
            self.sensor[1].sensor_type = self.raft_types[r2]
            self.sensor[1].name = self.name_ccd2

        num_spots_0 = len(self.sensor[0].spot_input["x"])
        num_spots_1 = len(self.sensor[1].spot_input["x"])

        print("# spots on ", self.name_ccd1, " ", num_spots_0)
        print("# spots on ", self.name_ccd2, " ", num_spots_1)

        if num_spots_0 == 0 or num_spots_1 == 0:
            print(self.raft_ccd_combo + ": Problem with input data: found ", num_spots_0, " and ",
                  num_spots_1, " spots")
            raise ValueError

        outliers_count = [0, 0]

        for s in self.sensor:

            if self.clean:
                self.sensor[s].spot_cln = self.do_clean(self.sensor[s].spot_input,
                                                        self.ccd_relative_orientation)

        # process the data

            if self.line_fitting:
                self.sensor[s].lines = self.find_lines(x_in=self.sensor[s].spot_cln["x"],
                                                       y_in=self.sensor[s].spot_cln["y"])
                # decide which CCD is the standard - the other is then measured relative to it. Pick the one that
                # is fatter on top.

        if self.line_fitting:

            self.ccd_standard = 0
            non_standard = 1
            # if len(self.sensor[1].lines[self.num_spots-1]) > len(self.sensor[1].lines[0]):
            #    self.ccd_standard = 1
            #    non_standard = 0

            co = 0
            if self.ccd_relative_orientation == "vertical":
                co = 1

            m_0 = self.sensor[0].lines[0][0][co]
            m_1 = self.sensor[1].lines[0][0][co]
            if m_1 < m_0:
                self.ccd_standard = 1

            for s in self.sensor:
                self.sensor[s].linfits = {}

                for lc, lines in enumerate(self.sensor[s].lines):
                    outliers_count = [0, 0]
                    self.sensor[s].linfits.setdefault(lines, {})

                    slope, intercept, outlier_mask = self.fit_line_pairs(self.sensor[s].lines[lines])
                    for idel, pt in enumerate(self.sensor[s].lines[lines]):  # remove outliers from line
                        if outlier_mask[idel]:
                            del self.sensor[s].lines[lines][idel]
                            outliers_count[s] += 1

                    self.sensor[s].linfits[lines] = [slope, intercept]

        if self.line_fitting:
            rc = self.match_lines()

        num_spots_cln_0 = len(self.sensor[0].spot_cln["x"])
        num_spots_cln_1 = len(self.sensor[1].spot_cln["x"])

        print("# spots after cln ", self.name_ccd1, " ", num_spots_cln_0)
        print("# spots after cln ", self.name_ccd2, " ", num_spots_cln_1)

        print("removed outliers: ", outliers_count)
        self.slider_x0.value = self.x0_in
        self.slider_y0.value = self.y0_in
        self.slider_x1.value = self.x1_in
        self.slider_y1.value = self.y1_in

        return

    def do_clean(self, sensor, orientation):

        out_x = []
        out_order = []
        out_y = []
        median_x = np.nanmedian(np.array(sensor["x"]))
        median_y = np.nanmedian(np.array(sensor["y"]))

        box_x = self.cln_box_half
        box_y = self.cln_box_full
        if orientation == "vertical":
            box_x = self.cln_box_full
            box_y = self.cln_box_half

        dist_x = box_x * self.pitch
        dist_y = box_y * self.pitch
        x_min = median_x - dist_x
        x_max = median_x + dist_x
        y_min = median_y - dist_y
        y_max = median_y + dist_y

        for n, x in enumerate(sensor["x"]):
            if np.isnan(x) or np.isnan(sensor["y"][n]) or np.isnan(sensor["flux"][n]):  # there be nan's in the input data!
                continue
            if sensor["xx"][n] < 4.5 or sensor["xx"][n] > 7.:  # spots with sensible moments
                continue
            if sensor["yy"][n] < 4.5 or sensor["yy"][n] > 7.:  # spots with sensible moments
                continue
            if x > x_min and x < x_max and \
                sensor["y"][n] > y_min and sensor["y"][n] < y_max:
                out_x.append(x)
                out_y.append(sensor["y"][n])
                out_order.append(n)

        out_dict = dict(x=np.array(out_x), y=np.array(out_y), order=out_order)

        return out_dict

    def data_2_model(self, srcX, srcY, ncols, nrows, x0_guess, y0_guess, distortions=None):

        result = grid_fit(srcX=srcX, srcY=srcY, ncols=ncols, nrows=nrows,
                          y0_guess=y0_guess, x0_guess=x0_guess, normalized_shifts=distortions,
                          brute_search=False, vary_theta=True)

        return result

    def make_plots(self):

        print("Entered make_plots")
        if self.use_fit:
            o1 = -self.dx0
            o2 = -self.dy0
            o3 = 0.
            o4 = 0.
        else:
            o1 = o2 = o3 = o4 = 0.
            if self.use_offsets:
                o1 = self.x0_in
                o2 = self.y0_in
                o3 = self.x1_in
                o4 = self.y1_in
        print("make_plots: offset = ", o1,o2, o3, o4)

        x1 = np.array(self.sensor[0].spot_cln["x"]) - o1
        y1 = np.array(self.sensor[0].spot_cln["y"]) - o2
        x2 = np.array(self.sensor[1].spot_cln["x"]) - o3
        y2 = np.array(self.sensor[1].spot_cln["y"]) - o4

        if self.show_rotate:
            rad = self.sim_rotate
            x2_rot = math.cos(rad) * x2 - math.sin(rad) * y2
            y2_rot = math.sin(rad) * x2 + math.cos(rad) * y2

            x2 = x2_rot
            y2 = y2_rot

        self.ccd1_scatter = figure(title="Spots Grid:" + self.name_ccd1, x_axis_label='x',
                                   y_axis_label='y', tools=self.TOOLS)

        source_g = None
        cg = None
#        if self.overlay_grid and self.use_fit:
        if self.overlay_grid:
            gY, gX = self.distorted_grid.get_source_centroids()
            gY += self.grid_y1-o4
            gX += self.grid_x1-o3

            source_g = ColumnDataSource(dict(x=gX, y=gY))
            cg = self.ccd1_scatter.circle(x="x", y="y", source=source_g, color="gray", size=2)

        source_1 = ColumnDataSource(dict(x=x1, y=y1))
        c1 = self.ccd1_scatter.circle(x="x", y="y", source=source_1, color="blue")

        source_2 = ColumnDataSource(dict(x=x2, y=y2))
        p2 = figure(title="Spots Grid: " + self.name_ccd2, x_axis_label='x',
                    y_axis_label='y', tools=self.TOOLS)

        if self.overlay_ccd:
            c2 = self.ccd1_scatter.circle(x="x", y="y", source=source_2, color="red")
            self.ccd1_scatter.height = 900
            self.ccd1_scatter.width = 900
            self.ccd1_scatter.title.text = "Spots Grid: " + self.name_ccd1 + " " + self.name_ccd2

            legend_it = [(self.name_ccd1, [c1]), (self.name_ccd2, [c2])]
            if cg is not None:
                legend_it.append(("Grid", [cg]))
            legend = Legend(items=legend_it)
            self.ccd1_scatter.add_layout(legend, 'above')

            plots_layout = layout(row(self.ccd1_scatter))
        else:
            p2.circle(x="x", y="y", source=source_2, color="red")
            if self.overlay_grid and self.use_fit:
                p2.circle(x="x", y="y", source=source_g, color="gray")
            plots_layout = row(self.ccd1_scatter, p2)

        print("add grid center pt to scatter plot")
        self.ccd1_scatter.circle(x=self.grid_x0-o1, y=self.grid_y0-o2, color="black")
        if self.overlay_ccd:
            self.ccd1_scatter.circle(x=self.grid_x1-o3, y=self.grid_y1-o4, color="green")
        else:
            p2.circle(x=self.grid_x1 - o3, y=self.grid_y1 - o4, color="green")

        # get errors and fluxes
        color = ["blue", "red"]

        flux_hist = figure(title="Spots Grid: fluxes  " + self.raft_ccd_combo, x_axis_label='flux (counts)',
                           y_axis_label='y', y_axis_type="log", x_axis_type="log", tools=self.TOOLS)
        xx_hist = figure(title="Spots Grid: x moment  " + self.raft_ccd_combo, x_axis_label='xx (px^2x)',
                           y_axis_label='y', tools=self.TOOLS)
        yy_hist = figure(title="Spots Grid: y moment  " + self.raft_ccd_combo, x_axis_label='yy (px^2)',
                           y_axis_label='y', tools=self.TOOLS)
        xErr_hist = figure(title="Spots Grid: x errors  " + self.raft_ccd_combo, x_axis_label='dx (px)',
                           y_axis_label='y', y_axis_type="log", x_axis_type="log", tools=self.TOOLS)
        yErr_hist = figure(title="Spots Grid: y errors  " + self.raft_ccd_combo, x_axis_label='dy (px)',
                           y_axis_label='y', y_axis_type="log", x_axis_type="log", tools=self.TOOLS)

        for s, sensor in enumerate(self.sensor):
            fl = self.sensor[sensor].spot_input["flux"]
            order = self.sensor[sensor].spot_cln["order"]
            flux = fl[order]
            flux = np.nan_to_num(flux, nan=100000.)
            fh, binh = np.histogram(flux, bins=100)
            w = binh[1] - binh[0]
            flux_hist.step(y=fh, x=binh[:-1]+w/2., color=color[s], legend_label=self.names_ccd[s])

            xx = self.sensor[sensor].spot_input["xx"][self.sensor[sensor].spot_cln["order"]]
            xxh, binh = np.histogram(xx, bins=100, range=(0.,10.))
            w = binh[1] - binh[0]
            xx_hist.step(y=xxh, x=binh[:-1]+w/2., color=color[s], legend_label=self.names_ccd[s])

            yy = self.sensor[sensor].spot_input["xx"][self.sensor[sensor].spot_cln["order"]]
            yyh, binh = np.histogram(yy, bins=100, range=(0.,10.))
            w = binh[1] - binh[0]
            yy_hist.step(y=yyh, x=binh[:-1]+w/2., color=color[s], legend_label=self.names_ccd[s])

            dx = np.sqrt(xx/flux)
            dxh, binh = np.histogram(dx, bins=100)
            w = binh[1] - binh[0]
            xErr_hist.step(y=dxh, x=binh[:-1]+w/2., color=color[s], legend_label=self.names_ccd[s])

            dy = np.sqrt(yy/flux)
            dyh, binh = np.histogram(dy, bins=100)
            w = binh[1] - binh[0]
            yErr_hist.step(y=dyh, x=binh[:-1]+w/2., color=color[s], legend_label=self.names_ccd[s])

        final_layout = layout(plots_layout, row(xx_hist, yy_hist), row(xErr_hist, yErr_hist), flux_hist)

        return final_layout

    def setup_grid(self):
        if self.grid is None:
            self.grid = DistortedGrid.from_fits(self.grid_data_file)

        self.gX1 = self.grid.x
        self.gY1 = self.grid.y
        self.gX2 = self.grid.x
        self.gY2 = self.grid.y

        if self.sim_distort:
            self.gX1 += self.grid.norm_dx
            self.gY1 += self.grid.norm_dy
            self.gX2 += self.grid.norm_dx
            self.gY2 += self.grid.norm_dy

    def match(self):

        print("start fitting with guesses ", self.grid_x0, self.grid_y0, self.grid_x1, self.grid_y1)
        print("add distortions ", self.sim_distort)
        distortions = None

        rc = self.setup_grid()

        if self.sim_distort:
            distortions = (self.grid.norm_dy, self.grid.norm_dx)
        else:
            print("distortions disabled ", distortions)

        # Need an intelligent guess

        model_grid1 = self.data_2_model(srcX=self.sensor[0].spot_cln["x"], srcY=self.sensor[0].spot_cln["y"],
                                        ncols=49, nrows=49,
                                        x0_guess=self.grid_x0, y0_guess=self.grid_y0,
                                        distortions=distortions)
        s = model_grid1.params["x0"].stderr
        print(self.name_ccd1, lmfit.fit_report(model_grid1))

        model_grid2 = self.data_2_model(srcX=self.sensor[1].spot_cln["x"], srcY=self.sensor[1].spot_cln["y"],
                                        ncols=49, nrows=49,
                                        x0_guess=self.grid_x1, y0_guess=self.grid_y1,
                                        distortions=distortions)

        s = model_grid2.params["x0"].stderr
        print(self.name_ccd2, lmfit.fit_report(model_grid2))

        self.sensor[0].grid_fit_results = model_grid1
        self.sensor[1].grid_fit_results = model_grid2

        print('Grid 1:', model_grid1.params['x0'].value, model_grid1.params['y0'].value,
              model_grid1.params['theta'].value)
        print('Grid 2:', model_grid2.params['x0'].value, model_grid2.params['y0'].value,
              model_grid2.params['theta'].value)

        self.dtheta0 = model_grid2.params['theta'].value - model_grid1.params['theta'].value

        # rotate the non standard sensor center by -dtheta0 to get back into the standard sensor frame
        non_standard = (1 - self.ccd_standard)
        x0n = self.sensor[non_standard].grid_fit_results.params["x0"] - 2048.
        y0n = self.sensor[non_standard].grid_fit_results.params["y0"] - 2048.
        xn, yn = self.rotate_xy(x=x0n, y=y0n, theta=-self.dtheta0)
        # restore coordinate system back to (0,0) in corner
        xn += 2048.
        yn += 2048.
        print("fit rotating sensor ", non_standard, " : ", xn, yn)

        sgn = (1 - 2*self.ccd_standard)
        self.dx0 = (xn - self.sensor[self.ccd_standard].grid_fit_results.params["x0"]) * sgn
        self.dy0 = (yn - self.sensor[self.ccd_standard].grid_fit_results.params["y0"]) * sgn
        print("Fit: dx, dy, dtheta ", self.dx0, self.dy0, self.dtheta0)

        # reset grid guesses

        self.grid_x0 = model_grid1.params['x0'].value
        self.grid_x1 = model_grid2.params['x0'].value
        self.grid_y0 = model_grid1.params['y0'].value
        self.grid_y1 = model_grid2.params['y0'].value

        # look at fit results

        rc = self.match_line_spots_to_grid(id_sensor=0)
        rc = self.match_line_spots_to_grid(id_sensor=1)

        return

    def rotate_xy(self, x=None, y=None, theta=None):

        xn = x * math.cos(theta) - y * math.sin(theta)
        yn = x * math.sin(theta) + y * math.cos(theta)

        return xn, yn

    def match_line_spots_to_grid(self, id_sensor):

        # loop over lines starting from the outer edges of the grid
        # assumes spots on lines are all good (cleaning has been done) and that every first spot per line is there

        distorted_grid = DistortedGrid(xstep=self.sensor[id_sensor].grid_fit_results.params["xstep"].value,
                                       ystep=self.sensor[id_sensor].grid_fit_results.params["ystep"].value,
                                       theta=self.sensor[id_sensor].grid_fit_results.params["theta"].value,
                                       x0=self.sensor[id_sensor].grid_fit_results.params["x0"].value,
                                       y0=self.sensor[id_sensor].grid_fit_results.params["y0"].value,
                                       ncols=self.num_spots, nrows=self.num_spots)

        self.sensor[id_sensor].grid_y, self.sensor[id_sensor].grid_x = distorted_grid.get_source_centroids()

        spots_grid_index = []
        self.sensor[id_sensor].grid_index = {}
        self.sensor[id_sensor].grid_distances = [0.]*len(self.sensor[id_sensor].grid_x)
        self.sensor[id_sensor].grid_whiskers = [0.]*len(self.sensor[id_sensor].grid_x)

        num_lines = len(self.sensor[id_sensor].lines)

        for lines in range(num_lines):
            num_spots = len(self.sensor[id_sensor].lines[lines])
            gi = self.sensor[id_sensor].grid_index.setdefault(lines, [0]*num_spots)

            # get distances between spots
            distances = distance.cdist(self.sensor[id_sensor].lines[lines],
                                       self.sensor[id_sensor].lines[lines],
                                       metric="euclidean")
            if self.ccd_relative_orientation == "horizontal":
                grid_index = 0
                dist_2_next = 0
                spot_index = 0
                # loop over spots on the line and jump grid index values if there are gaps
                sp_order = list(range(num_spots))
                if self.ccd_standard == id_sensor:
                    sp_order = sp_order[::-1]

                for sp in sp_order:
                    sgn = 1.
                    end = 0
                    if self.ccd_standard == id_sensor:
                        sgn = -1
                        end = 1
                        spot_index += round(dist_2_next/self.pitch) * sgn
                        grid_index = int(num_lines * (num_lines + spot_index -1) + lines)
                    else:
                        sgn = 1.
                        spot_index += round(dist_2_next / self.pitch) * sgn
                        grid_index = int(num_lines * spot_index + lines)
                    gi[sp] = int(grid_index)
                    dist, whisker = self.grid_whiskers(sensor=id_sensor, line=lines, spot=sp, grid_index=grid_index)
                    self.sensor[id_sensor].grid_distances[grid_index] = dist
                    self.sensor[id_sensor].grid_whiskers[grid_index] = whisker
                    try:
                        if self.ccd_standard == id_sensor:
                            dist_2_next = distances[sp-1, sp]  # distance to previous spot
                        else:
                            dist_2_next = distances[sp, sp + 1]  # distance to previous spot
                    except:  # bail on the last point
                        pass
            else:  # vertical sensor pairing - lines run vertically - grid indexing is orthogonal to horiz mode

                grid_index = 0
                spot_index = 0
                dist_2_next = 0
                # loop over spots on the line and jump grid index values if there are gaps
                sp_order = list(range(num_spots))
                if self.ccd_standard == id_sensor:
                    sp_order = sp_order[::-1]

                for sp in sp_order:
                    sgn = 1.
                    if self.ccd_standard == id_sensor:
                        sgn = -1
                        spot_index += round(dist_2_next/self.pitch) * sgn
                        grid_index = int(num_lines * (lines + 1) + spot_index - 1)
                    else:
                        sgn = 1
                        spot_index += round(dist_2_next / self.pitch) * sgn
                        grid_index = int(num_lines * lines + spot_index)

                    gi[sp] = int(grid_index)
                    dist, whisker = self.grid_whiskers(sensor=id_sensor, line=lines, spot=sp, grid_index=grid_index)
                    self.sensor[id_sensor].grid_distances[grid_index] = dist
                    self.sensor[id_sensor].grid_whiskers[grid_index] = whisker
                    try:
                        if self.ccd_standard == id_sensor:
                            dist_2_next = distances[sp-1, sp]  # distance to previous spot
                        else:
                            dist_2_next = distances[sp, sp + 1]  # distance to previous spot
                    except:  # bail on the last point
                        pass

        return

    def grid_whiskers(self, sensor=None, line=None, spot=None, grid_index=None):

        x_spot = self.sensor[sensor].lines[line][spot][0]
        y_spot = self.sensor[sensor].lines[line][spot][1]

        x_grid = self.sensor[sensor].grid_x[grid_index]
        y_grid = self.sensor[sensor].grid_y[grid_index]

        dist = math.hypot(x_spot - x_grid, y_spot - y_grid)
        whisker = [x_spot - x_grid, y_spot - y_grid]

        return dist, whisker

    def make_fit_plots(self):

        print("entered make_fit_plots")

        # residuals from the fit

        color = ["blue", "red"]
        fr0_hist = figure(title="Fit residuals:  " + self.sensor[0].name, x_axis_label='residual (px)',
                           y_axis_label='count', tools=self.TOOLS)
        fr1_hist = figure(title="Fit residuals:  " + self.sensor[1].name, x_axis_label='residual (px)',
                           y_axis_label='count', tools=self.TOOLS)

        fit_res0 = self.sensor[0].grid_fit_results.residual
        mean_res0 = np.mean(fit_res0)
        h0, b0 = np.histogram(fit_res0, bins=50)

        w = b0[1] - b0[0]
        fr0_hist.step(y=h0, x=b0[:-1] + w / 2., color=color[0], legend_label=self.sensor[0].name)

        fit_res1 = self.sensor[1].grid_fit_results.residual
        mean_res1 = np.mean(fit_res1)
        h1, b1 = np.histogram(fit_res1, bins=50)

        w = b1[1] - b1[0]
        fr1_hist.step(y=h1, x=b1[:-1] + w / 2., color=color[1], legend_label=self.sensor[1].name)

        # compare fitted grid to spots

        c_color_mapper_res = LinearColorMapper(palette=palette, high=2.)
        c_color_bar_res = ColorBar(color_mapper=c_color_mapper_res, label_standoff=8, width=500, height=20,
                                   border_line_color=None, location=(0, 0), orientation='horizontal')

        sxp_s = {}
        syp_s = {}
        sdist_s = {}
        whiskers = {}
        dist_heat = {}
        dist_spot = {}
        whisker_plot = {}

        for s in range(2):

            sxp = sxp_s.setdefault(s, [])
            syp = syp_s.setdefault(s, [])
            sdist = sdist_s.setdefault(s, [])
            swhiskers = whiskers.setdefault(s, [])

            for sp in range(self.num_spots*self.num_spots):
                sg_dist = self.sensor[s].grid_distances[sp]
                if sg_dist == 0.:  # missing spot on grid
                    continue

                x_sp = self.sensor[s].grid_x[sp] + self.sensor[s].grid_whiskers[sp][0]
                y_sp = self.sensor[s].grid_y[sp] + self.sensor[s].grid_whiskers[sp][1]
                sxp.append(x_sp)
                syp.append(y_sp)
                sdist.append(sg_dist)
                swhiskers.append(self.sensor[s].grid_whiskers[sp])

            dist_spot[s] = ColumnDataSource(dict(x=sxp_s[s], y=syp_s[s], res=sdist_s[s]))

            dist_heat[s] = figure(title="Spots Grid: residuals  " + self.sensor[s].name, x_axis_label='x',
                                  y_axis_label='y', tools=self.TOOLS, height=1000, width=1000,
                                  tooltips=[
                                      ("x", "@x"), ("y", "@y"), ("distance", "@res")]
                                  )
            dist_heat[s].circle(x="x", y="y", source=dist_spot[s], color="gray", size=10,
                             fill_color={'field': 'res', 'transform': c_color_mapper_res})
            dist_heat[s].add_layout(c_color_bar_res, 'below')

            whisker_plot[s] = figure(title="Spots Grid: whiskers 10x  " + self.sensor[s].name, x_axis_label='x',
                                  y_axis_label='y', tools=self.TOOLS, height=1000, width=1000)

            for iw, w in enumerate(whiskers[s]):
                x1 = sxp_s[s][iw]
                x2 = sxp_s[s][iw] - w[0]

                y1 = syp_s[s][iw]
                y2 = syp_s[s][iw] - w[1]

                unitSlopeX = (x2 - x1) / sdist_s[s][iw]
                unitSlopeY = (y2 - y1) / sdist_s[s][iw]

                x3 = x1 + unitSlopeX * sdist_s[s][iw] * 10.
                y3 = y1 + unitSlopeY * sdist_s[s][iw] * 10.

                whisker_plot[s].line([x1, x3], [y1, y3],
                                     line_width=4)

        fh = column(row(fr0_hist, fr1_hist), row(dist_heat[0], dist_heat[1]),
                    row(whisker_plot[0], whisker_plot[1]))

        return fh

    def simulate_response(self, distort=False):

        # get the distortions file - contains undistorted grid + deviations
        # cases to handle:
        #  distort or not
        #  vertical or horizontal pairing
        #  intra or extra-raft pairing

        # grid is centered on (0,0) and rotated by self.rotate

        yg, xg = self.distorted_grid.get_source_centroids(distorted=self.sim_distort)

        ccd_gap = 28.  # pixels - 0.25 mm at 10 um/px with 42 mm wide sensor to give 42.25 mm separation
        dead_region = 100.
        raft_gap = 50.  # 0.5 mm gap between rafts, which are 127 mm wide

        gap = ccd_gap
        if self.sim_inter_raft:
            gap = raft_gap

        distance_grid_ctr = 4197.

        self.sim_x = [[], []]
        self.sim_y = [[], []]
        self.sim_moments = [[], []]
        self.sim_flux = [[], []]

        if self.ccd_relative_orientation == "horizontal":

            for idx, xs in enumerate(xg):

                # sensor 0 is the standard (pixels start at zero in its counting)
                if xs > (gap /2. + dead_region):
                    self.sim_x[0].append(xs - gap/2.)
                    self.sim_y[0].append(distance_grid_ctr/2. + yg[idx])
                else:
                    # x10 is in sensor 1's frame - will rotate sensor 1 relative to sensor 0
                    # shift x10, y10 to center on the middle of the sensor
                    x10 = distance_grid_ctr/2. + xs + gap/2.   # x ~2048 means near end of sensor
                    y10 = yg[idx]                              # y ~0 for center of sensor

                    # rotate around the sensor center and then shift back to (0,0) frame in corner of sensor
                    x11 = math.cos(self.sim_rotate) * x10 - math.sin(self.sim_rotate) * y10 + distance_grid_ctr/2.
                    y11 = math.sin(self.sim_rotate) * x10 + math.cos(self.sim_rotate) * y10 + self.sim_offset \
                        + distance_grid_ctr/2.

                    # cut out spots in sensor 1's frame
                    if x11 - distance_grid_ctr < (-gap / 2. - dead_region):
                        self.sim_x[1].append(x11)
                        self.sim_y[1].append(y11)
        else:
            for idy, ys in enumerate(yg):
                if ys > (gap / 2. + dead_region):
                    self.sim_y[0].append(ys - gap/2.)
                    self.sim_x[0].append(distance_grid_ctr/2. + xg[idy])
                else:
                    # y00 in sensor 1's frame
                    y00 = distance_grid_ctr/2. + ys + gap/2.
                    x00 = xg[idy]

                    x01 = math.cos(self.sim_rotate) * x00 - math.sin(self.sim_rotate) * y00 + self.sim_offset \
                          + distance_grid_ctr / 2.
                    y01 = math.sin(self.sim_rotate) * x00 + math.cos(self.sim_rotate) * y00 + distance_grid_ctr/2.
                    if y01 - distance_grid_ctr < (-gap / 2. - dead_region):
                        self.sim_y[1].append(y01)
                        self.sim_x[1].append(x01)

        self.sim_moments[0] = np.array([5.]*len(self.sim_x[0]))
        self.sim_moments[1] = np.array([5.] * len(self.sim_x[1]))
        self.sim_flux[0] = np.array([50000.]*len(self.sim_x[0]))
        self.sim_flux[1] = np.array([50000.]*len(self.sim_x[1]))

        return

    def loop(self):
        if not self.init:
            rc = self.get_data(combo_name=self.raft_ccd_combo)

        if not self.line_fitting:
            self.button_line_fitting.button_type = "danger"

        self.layout = layout(self.max_layout)
