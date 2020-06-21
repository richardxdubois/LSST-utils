import glob
import sys
import os
import math
import numpy as np
from scipy.stats import linregress

from os.path import join
from astropy.io import fits

from mixcoatl.sourcegrid import DistortedGrid

from bokeh.plotting import figure, curdoc
from bokeh.palettes import Viridis256 as palette #@UnresolvedImport
from bokeh.layouts import row, column, layout, gridplot
from bokeh.models.widgets import TextInput, Dropdown, Button, RangeSlider, FileInput
from bokeh.models import CustomJS, ColumnDataSource, Legend, LinearColorMapper, ColorBar, LogColorMapper


class ccd_spacing():

    def __init__(self, dir_index=None, combo_name=None, distort_file = None):

        self.file_paths = {}
        self.raft_ccd_combo = combo_name

        self.name_ccd1 = None
        self.name_ccd2 = None
        self.names_ccd = []
        self.ccd_relative_orientation = "vertical"
        self.extrap_dir = 1.

        self.cut_spurious_spots = 80.  # spots need to be closer to another spot to include in lines
        self.lines = {}
        self.linfits = {}
        self.rotate = 3.2/57.3
        self.show_rotate = False
        self.pitch = 65.
        self.num_spots = 49

        self.ccd1_scatter = None

        self.ccd_standard = 0
        self.med_shift_x = 0.
        self.med_shift_y = 0.
        self.shift_x = []
        self.shift_y = []
        self.center_to_center = [0., 0.]
        self.d_extrap = []

        self.line_fitting = True

        self.src1 = None
        self.src2 = None

        self.clean = False
        self.srcX = [[], []]
        self.srcY = [[], []]

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

        # simulation stuff

        self.grid_data_file = distort_file

        self.sim_x = None
        self.sim_y = None

        self.sim_doit = False
        self.sim_inter_raft = False
        self.sim_distort = False

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

        # button toggle line fitting
        self.button_line_fitting = Button(label="Enable Lines", button_type="success", width=100)
        self.button_line_fitting.on_click(self.do_line_fitting)

        # sliders for offsetting spots patterns - each sets a pair of values for its coordinate
        self.slider_x = RangeSlider(title="x0 Value Range", start=-1000, end=5000, value=(self.x0_in,
                                                                                          self.x1_in),
                                    width=900,
                                    format="0[.]0000")
        self.slider_x.on_change('value_throttled', self.slider_x_select)
        self.slider_y = RangeSlider(title="y0 Value Range", start=-1000, end=5000, value=(self.y0_in,
                                                                                          self.y1_in),
                                    width=900,
                                    format="0[.]0000")
        self.slider_y.on_change('value_throttled', self.slider_y_select)

        # button to submit slider values
        self.button_submit = Button(label="Submit slider", button_type="warning", width=100)
        self.button_submit.on_click(self.do_submit)

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

        # simulation buttons

        self.button_enable_sims = Button(label="Enable sims", button_type="danger", width=100)
        self.button_enable_sims.on_click(self.do_enable_sims)

        self.button_sims_orient = Button(label="Toggle orientation", button_type="success", width=100)
        self.button_sims_orient.label = "vertical"
        self.button_sims_orient.on_click(self.do_sims_orient)

        self.button_sims_intra_raft = Button(label="Toggle intra-raft", button_type="danger", width=100)
        self.button_sims_intra_raft.label = "Intra-raft"
        self.button_sims_intra_raft.on_click(self.do_sims_intra_raft)

        self.button_sims_enable_distortions = Button(label="Toggle distortions", button_type="danger", width=100)
        self.button_sims_enable_distortions.label = "Distortions Off"
        self.button_sims_enable_distortions.on_click(self.do_sims_enable_distortions)

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

        self.min_layout = row(self.button_exit, self.drop_data, self.button_get_data, self.button_overlay_ccd,
                              self.button_overlay_grid, self.button_linfit_plots, self.button_rotate,
                              self.button_line_fitting, self.button_enable_sims, self.button_sims_orient,
                              self.button_sims_intra_raft, self.button_sims_enable_distortions)
        self.sliders_layout = column(self.slider_x, self.slider_y, self.button_submit)
        self.max_layout = column(self.min_layout, self.sliders_layout,
                                 self.button_fit)

        self.TOOLS = "pan, wheel_zoom, box_zoom, reset, save, box_select, lasso_select, tap"

    # handlers

    def update_dropdown_data(self, event):
        self.dir_index = event.item.split(",")[0].strip()
        self.raft_ccd_combo = event.item.split(",")[1].strip()
        self.drop_data.button_type = "warning"

        rc = self.do_get_data()

        return

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

    def do_rotate(self):
        self.show_rotate = not self.show_rotate
        if self.show_rotate:
            self.button_rotate.button_type = "danger"
        else:
            self.button_rotate.button_type = "success"

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
        pl = self.make_plots()
        m_new = column(self.max_layout, pl)
        self.layout.children = m_new.children

    def do_linfit_plots(self):
        p_grid = self.make_line_plots()

        m_new = column(self.max_layout, p_grid)
        self.layout.children = m_new.children

    def do_fit(self):
        rc = self.match()
        self.use_fit = True
        self.redo_fit = False
        pl = self.make_plots()
        m_new = column(self.max_layout, pl)
        self.layout.children = m_new.children
        return

    def do_submit(self):
        self.use_offsets = True
        self.use_fit = False
        pl = self.make_plots()
        m_new = column(self.max_layout, pl)
        self.layout.children = m_new.children
        return

    def slider_x_select(self, sattr, old, new):
        self.x0_in = self.slider_x.value[0]
        self.x1_in = self.slider_x.value[1]

    def slider_y_select(self, sattr, old, new):
        self.y0_in = self.slider_y.value[0]
        self.y1_in = self.slider_y.value[1]

    def do_get_data(self):

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

    def find_lines(self):

        # sort the y-coordinates for both CCDs
        self.lines = {}
        order = []
        x = []
        y = []
        rad = self.rotate * self.extrap_dir
        x1_rot = math.cos(rad) * np.array(self.srcX[0]) - math.sin(rad) * np.array(self.srcY[0])
        y1_rot = math.sin(rad) * np.array(self.srcX[0]) + math.cos(rad) * np.array(self.srcY[0])

        order.append(np.argsort(-y1_rot, kind="stable"))
        x.append(np.array(self.srcX[0])[order[0]])
        y.append(np.array(self.srcY[0])[order[0]])

        x2_rot = math.cos(rad) * np.array(self.srcX[1]) - math.sin(rad) * np.array(self.srcY[1])
        y2_rot = math.sin(rad) * np.array(self.srcX[1]) + math.cos(rad) * np.array(self.srcY[1])

        order.append(np.argsort(-y2_rot, kind="stable"))
        x.append(np.array(self.srcX[1])[order[1]])
        y.append(np.array(self.srcY[1])[order[1]])
        yrot = []
        yrot.append(np.array(y1_rot)[order[0]])
        yrot.append(np.array(y2_rot)[order[1]])

        # find lines

        for l in range(2):

            n_close = 0
            y_min = min(yrot[l])
            for nc in range(1, 10):
                ya = yrot[l][-nc - 1]
                yb = yrot[l][-nc]
                diff = yrot[l][-nc - 1] - yrot[l][-nc]
                if diff < 5.:  # look for a bunch of spots close together
                    n_close += 1
                if n_close > 4:
                    y_min = yrot[l][-nc] -10.  # back off a bit to get back the first few
                    break

            ccd = self.lines.setdefault(l, {})

            for idy, yi in enumerate(yrot[l]):
                if yi - y_min < 0.:  # spurious low point
                    continue
                line_bin = int((yi-y_min+self.pitch/5.)/self.pitch)
                if line_bin > 48:  # spurious high point
                    continue
                fl = self.lines[l].setdefault(line_bin, [])
                self.lines[l][line_bin].append([x[l][idy], y[l][idy]])

        if len(self.lines[0]) != self.num_spots or len(self.lines[1]) != self.num_spots:
            print(self.raft_ccd_combo + ": Problem finding full grid: found ", len(self.lines[0]), " and ",
                  len(self.lines[1]),
                  " spots")
            raise ValueError

        # sort lists by x

        for l in range(2):
            nl = len(self.lines[l])
            for n in range(nl):
                self.lines[l][n] = sorted(self.lines[l][n], key=lambda xy: xy[0])
                # ensure end points make sense
                if abs(self.lines[l][n][0][0] - self.lines[l][n][1][0]) > self.cut_spurious_spots:
                    del self.lines[l][n][0]
                if abs(self.lines[l][n][-1][0] - self.lines[l][n][-2][0]) > self.cut_spurious_spots:
                    del self.lines[l][n][-1]

        return

    def make_line_plots(self):

        print("# lines in ", self.name_ccd1, " ", len(self.lines[0]))
        print("# lines in ", self.name_ccd2, " ", len(self.lines[1]))

        num_spots = [len(self.lines[0][k]) for k in self.lines[0]]
        num_spots2 = [len(self.lines[1][k]) for k in self.lines[1]]
        num_spots.extend(num_spots2)
        print("Total spots = ", sum(num_spots))

        slopes = []
        slopes_ccd1 = []
        slopes_ccd2 = []
        color = ["blue", "red"]

        for l in range(2):
            for lines in self.linfits[l]:
                slopes.append(self.linfits[l][lines][0])
                if l == 0:
                    slopes_ccd1.append(self.linfits[l][lines][0])
                else:
                    slopes_ccd2.append(self.linfits[l][lines][0])

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

        n_lines = len(self.lines[0])

        slopes_diff = []
        for nl in range(n_lines):
            slopes_diff.append(self.linfits[1][nl][0] - self.linfits[0][nl][0])

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
                        y_axis_label='counts',
                        width=600)
        gr_hist = figure(tools=self.TOOLS, title="gap residuals", x_axis_label='residuals',
                         y_axis_label='counts',
                         width=600)

        pitch_hist = figure(tools=self.TOOLS, title="Spot pitch ", x_axis_label='pitch',
                            y_axis_label='counts',
                            width=600)

        off_ccd = [[0., 0.], [0., 0.]]
        if self.use_offsets:
            off_ccd = [[self.x0_in, self.y0_in], [self.x1_in, self.y1_in]]

        for l in range(2):
            spl = spot_pitch.setdefault(l, [])
            res = residuals.setdefault(l, [])
            g_res = gap_residuals.setdefault(l, [])

            for nl in range(n_lines):
                x0 = self.lines[l][nl][0][0]
                y0 = self.linfits[l][nl][0] * x0 + self.linfits[l][nl][1]
                x1 = self.lines[l][nl][-1][0]
                y1 = self.linfits[l][nl][0] * x1 + self.linfits[l][nl][1]
                x0 -= off_ccd[l][0]
                y0 -= off_ccd[l][1]
                x1 -= off_ccd[l][0]
                y1 -= off_ccd[l][1]

                if self.ccd1_scatter is not None:
                    self.ccd1_scatter.line([x0, x1], [y0, y1], line_width=2)

                n_spots = len(self.lines[l][nl])
                xp = -1.
                yp = -1.
                for s in range(n_spots):
                    x0 = self.lines[l][nl][s][0]
                    y0 = self.lines[l][nl][s][1]
                    y0_fit = self.linfits[l][nl][0] * x0 + self.linfits[l][nl][1]
                    y_diff = y0_fit - y0
                    res.append(y_diff)

                    # find spots along the gaps
                    if (self.ccd_standard == l and s == 0) or \
                            (self.ccd_standard != l and s == (n_spots - 1)):
                        g_res.append(y_diff)

                    d = 0.
                    if (xp != -1.):
                        d = math.sqrt((x0 - xp)**2 + (y0 - yp)**2)
                        spl.append(d)

                    xp = x0
                    yp = y0

                    x_spot.append(x0 - off_ccd[l][0])
                    y_spot.append(y0 - off_ccd[l][1])
                    res_spot.append(abs(y_diff))
                    pitch_spot.append(d)

            resid, bins = np.histogram(np.array(res), bins=50, range=(-5., 5.))

            w = bins[1] - bins[0]
            r_hist.step(y=resid, x=bins[:-1]+w/2., color=color[l], legend_label=self.names_ccd[l])

            g_resid, bins = np.histogram(np.array(g_res), bins=50, range=(-5., 5.))

            w = bins[1] - bins[0]
            gr_hist.step(y=g_resid, x=bins[:-1]+w/2., color=color[l], legend_label=self.names_ccd[l])

            pitches, bins = np.histogram(np.array(spl), bins=50, range=(60., 70.))
            w = bins[1] - bins[0]

            pitch_hist.step(y=pitches, x=bins[:-1]+w/2., color=color[l], legend_label=self.names_ccd[l])

        cds_spot = ColumnDataSource(dict(x=x_spot, y=y_spot, res=res_spot, pitch=pitch_spot))

        spot_heat = figure(title="Spots Grid:" + self.raft_ccd_combo, x_axis_label='x',
                           y_axis_label='y', tools=self.TOOLS)
        c_color_mapper = LinearColorMapper(palette=palette, low=64., high=66.5)
        c_color_bar = ColorBar(color_mapper=c_color_mapper, label_standoff=8, width=500, height=20,
                               border_line_color=None, location=(0, 0), orientation='horizontal')
        spot_heat.circle(x="x", y="y", source=cds_spot, color="gray", size=10,
                         fill_color={'field': 'pitch', 'transform': c_color_mapper})
        spot_heat.add_layout(c_color_bar, 'below')

        hist_list.append([r_hist, pitch_hist])
        hist_list.append([gr_hist, spot_heat])
        hist_list.append([self.ccd1_scatter])

        return gridplot(hist_list)

    def fit_line_pairs(self, line_list):

        x = []
        y = []
        for pt in line_list:
            x.append(pt[0])
            y.append(pt[1])

        order = np.argsort(np.array(x), kind="stable")
        x = np.array(x)[order]
        y = np.array(y)[order]

        slope, intercept, r_value, p_value, std_err = linregress(x, y)

        return slope, intercept, r_value, p_value, std_err

    def match_lines(self):

        # decide which CCD is the standard - the other is then measured relative to it. Pick the one that
        # is fatter on top.

        self.ccd_standard = 0
        non_standard = 1
        if len(self.lines[1][self.num_spots-1]) > len(self.lines[1][0]):
            self.ccd_standard = 1
            non_standard = 0

        n_lines = len(self.lines[0])   # they'd better both have the same number!
        self.shift_x = []
        self.shift_y = []

        for nl in range(n_lines):

            # count spots and calculate the spots gap between the CCDs
            missing_spots = self.num_spots - \
                            (len(self.lines[0][nl]) + len(self.lines[1][nl]))
            extrap_dist = (missing_spots + 1) * self.pitch  # n+1 gaps needed to add
            self.d_extrap.append(extrap_dist)

            near_end = 0
            far_end = -1
            if self.ccd_relative_orientation == "horizontal":
                far_end = 0
                near_end = -1

            x1 = self.lines[self.ccd_standard][nl][near_end][0]
            y1 = self.linfits[self.ccd_standard][nl][1] +  \
                 self.linfits[self.ccd_standard][nl][0] * x1
            x2 = self.lines[self.ccd_standard][nl][far_end][0]
            y2 = self.linfits[self.ccd_standard][nl][1] + \
                 self.linfits[self.ccd_standard][nl][0] * x2

            length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            unitSlopeX = self.extrap_dir * (x2 - x1) / length
            unitSlopeY = self.extrap_dir * (y2 - y1) / length

            new_x = x1 - extrap_dist * unitSlopeX * self.extrap_dir
            new_y = y1 - extrap_dist * unitSlopeY * self.extrap_dir

            old_x = self.lines[non_standard][nl][far_end][0]
            old_y = self.linfits[non_standard][nl][1] + self.linfits[non_standard][nl][0] * old_x

            self.shift_x.append(old_x - new_x)
            self.shift_y.append(old_y - new_y)

        self.med_shift_x = np.median(np.array(self.shift_x))
        self.med_shift_y = np.median(np.array(self.shift_y))

        self.x1_in = self.med_shift_x
        self.y1_in = 2000. + self.med_shift_y
        self.x0_in = 0.
        self.y0_in = 2000.

        centers = [2048., 2048.]
        if self.ccd_relative_orientation == "horizontal":
            c1 = [centers[0] - self.x1_in, centers[1] - self.y1_in]
            c0 = [centers[0] - self.x0_in, centers[1] - self.y0_in]
        else:
            c1 = [centers[0] - self.y1_in, centers[1] - self.x1_in]
            c0 = [centers[0] - self.y0_in, centers[1] - self.x0_in]

        self.center_to_center = np.array(c0) - np.array(c1)

        print("center to center = ", self.center_to_center)
        return

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

        if self.sim_doit:
            if self.ccd_relative_orientation == "vertical":
                X1 = self.sim_x[0]
                Y1 = self.sim_y[0]
                self.extrap_dir = 1.
            else:  # swap x and y for horizontal pairing
                Y1 = self.sim_x[0]
                X1 = self.sim_y[0]
                self.extrap_dir = -1.
        else:
            dir_index = self.file_paths[combo_name]
            results_dirs = sorted(glob.glob(dir_index))
            for result_dir in results_dirs:
                print(result_dir)

            infile1, infile2 = sorted(glob.glob(join(results_dirs[0], '*_source_catalog.cat')))
            print(infile1)
            print(infile2)

            self.name_ccd1 = os.path.basename(infile1).split("_source")[0]
            self.name_ccd2 = os.path.basename(infile2).split("_source")[0]
            self.names_ccd = [self.name_ccd1, self.name_ccd2]

            s1 = self.name_ccd1.split("_")[1]
            s2 = self.name_ccd2.split(("_"))[1]
            kw_x = 'base_SdssShape_x'
            kw_y = 'base_SdssShape_y'
            self.extrap_dir = 1.

            if int(s1[1]) == int(s2[1]):
                self.ccd_relative_orientation = "vertical"
            else:
                self.ccd_relative_orientation = "horizontal"  # swap x and y
                kw_x = 'base_SdssShape_y'
                kw_y = 'base_SdssShape_x'
                self.extrap_dir = -1.

            self.src1 = fits.getdata(infile1)
            X1 = self.src1[kw_x]
            Y1 = self.src1[kw_y]

        median_x1 = np.median(np.array(X1))
        median_y1 = np.median(np.array(Y1))
        dist_x = 16 * self.pitch
        dist_y = 27 * self.pitch
        x_min = median_x1 - dist_x
        x_max = median_x1 + dist_x
        y_min = median_y1 - dist_y
        y_max = median_y1 + dist_y

        if self.clean:
            for n, x in enumerate(X1):
                if x > x_min and x < x_max and Y1[n] > y_min and Y1[n] < y_max:
                    self.srcX[0].append(x)
                    self.srcY[0].append(Y1[n])
        else:
            self.srcX[0] = X1
            self.srcY[0] = Y1

        self.srcX[0] = np.array((self.srcX[0]))
        self.srcY[0] = np.array((self.srcY[0]))

        if self.sim_doit:
            if self.ccd_relative_orientation == "vertical":
                X2 = self.sim_x[1]
                Y2 = self.sim_y[1]
                self.extrap_dir = 1.
            else:  # swap x and y for horizontal pairing
                Y2 = self.sim_x[1]
                X2 = self.sim_y[1]
                self.extrap_dir = -1.
        else:
            self.src2 = fits.getdata(infile2)
            X2 = self.src2[kw_x]
            Y2 = self.src2[kw_y]

        median_x2 = np.median(np.array(X2))
        median_y2 = np.median(np.array(Y2))

        x_min = median_x2 - dist_x
        x_max = median_x2 + dist_x
        y_min = median_y2 - dist_y
        y_max = median_y2 + dist_y

        if self.clean:
            for n, x in enumerate(X2):
                if x > x_min and x < x_max and Y2[n] > y_min and Y2[n] < y_max:
                    self.srcX[1].append(x)
                    self.srcY[1].append(Y2[n])
        else:
            self.srcX[1] = X2
            self.srcY[1] = Y2

        self.srcX[1] = np.array((self.srcX[1]))
        self.srcY[1] = np.array((self.srcY[1]))

        print("# spots on ", self.name_ccd1, " ", len(self.srcX[0]))
        print("# spots on ", self.name_ccd2, " ", len(self.srcX[1]))

        if len(self.srcX[0]) == 0 or len(self.srcX[1]) == 0:
            print(self.raft_ccd_combo + ": Problem with input data: found ", len(self.srcX[0]), " and ",
                  len(self.srcX[1]), " spots")
            raise ValueError

        if self.show_rotate:
            rad = self.rotate * self.extrap_dir
            x1_rot = math.cos(rad) * self.srcX[0] - math.sin(rad) * self.srcY[0]
            y1_rot = math.sin(rad) * self.srcX[0] + math.cos(rad) * self.srcY[0]
            x2_rot = math.cos(rad) * self.srcX[1] - math.sin(rad) * self.srcY[1]
            y2_rot = math.sin(rad) * self.srcX[1] + math.cos(rad) * self.srcY[1]

            self.srcX[0] = x1_rot
            self.srcY[0] = y1_rot
            self.srcX[1] = x2_rot
            self.srcY[1] = y2_rot

        if self.line_fitting:
            rc = self.find_lines()

            self.linfits = {}

            for c in range(2):
                lf = self.linfits.setdefault(c, {})
                for lines in self.lines[c]:
                    lf.setdefault(lines, {})
                    slope, intercept, r_value, p_value, std_err = self.fit_line_pairs(self.lines[c][lines])
                    self.linfits[c][lines] = [slope, intercept, r_value, p_value, std_err]

            rc = self.match_lines()

        self.slider_x.value = (self.x0_in, self.x1_in)
        self.slider_y.value = (self.y0_in, self.y1_in)

        return

    def data_2_model(self, x0_guess, y0_guess, src=None):

        model_grid = SourceGrid.from_source_catalog(src, y0_guess=y0_guess, x0_guess=x0_guess)

        gY, gX = model_grid.make_grid(49, 49)

        return model_grid, gY, gX

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

        x1 = np.array(self.srcX[0]) - o1
        y1 = np.array(self.srcY[0]) - o2
        x2 = np.array(self.srcX[1]) - o3
        y2 = np.array(self.srcY[1]) - o4

        self.ccd1_scatter = figure(title="Spots Grid:" + self.name_ccd1, x_axis_label='x',
                                   y_axis_label='y', tools=self.TOOLS)

        source_g = None
        cg = None
        if self.overlay_grid and self.use_fit:
            source_g = ColumnDataSource(dict(x=self.gX2, y=self.gY2))
            cg = self.ccd1_scatter.circle(x="x", y="y", source=source_g, color="gray", size=10)

        source_1 = ColumnDataSource(dict(x=x1, y=y1))
        c1 = self.ccd1_scatter.circle(x="x", y="y", source=source_1, color="blue")

        source_2 = ColumnDataSource(dict(x=x2, y=y2))
        p2 = figure(title="Spots Grid: " + self.name_ccd2, x_axis_label='x',
                    y_axis_label='y', tools=self.TOOLS)

        if self.overlay_ccd:
            c2 = self.ccd1_scatter.circle(x="x", y="y", source=source_2, color="red")
            self.ccd1_scatter.height = 900
            self.ccd1_scatter.width = 900
            self.ccd1_scatter.title.text = "Spots Grid: " + self.name_ccd2 + " " + self.name_ccd1

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
            plots_layout = layout(row(self.ccd1_scatter, p2))

        return plots_layout

    def match(self):
        # Need an intelligent guess

        model_grid1, self.gY1, self.gX1 = self.data_2_model(x0_guess=self.x0_in, y0_guess=self.y0_in,
                                                            src=self.src1)

        model_grid2, self.gY2, self.gX2 = self.data_2_model(x0_guess=self.x1_in, y0_guess=self.y1_in,
                                                            src=self.src2)

        print('Grid 1:', model_grid1.x0, model_grid1.y0, model_grid1.theta)
        print('Grid 2:', model_grid2.x0, model_grid2.y0, model_grid2.theta)

        # Ignore rotation for now
        self.dy0 = model_grid2.y0 - model_grid1.y0
        self.dx0 = model_grid2.x0 - model_grid1.x0

    def simulate_response(self, distort=False):

        # get the distortions file - contains undistorted grid + deviations
        # cases to handle:
        #  distort or not
        #  vertical or horizontal pairing
        #  intra or extra-raft pairing

        grid = DistortedGrid.from_fits(self.grid_data_file)
        xg = grid['X']
        yg = grid['Y']
        dxg = grid['DX']
        dyg = grid['DY']

        ccd_gap = 250.  # pixels - 0.25 mm at 10 um/px
        raft_gap = 500.  # 0.5 mm

        gap = ccd_gap
        if self.sim_inter_raft:
            gap = raft_gap

        distance_grid_ctr = 4096. + gap/2.

        self.sim_x = [[], []]
        self.sim_y = [[], []]

        f_distort = 0.
        if self.sim_distort:
            f_distort = 1.

        if self.ccd_relative_orientation == "vertical":

            for idx, xs in enumerate(xg):
                if xs < -gap / 2.:
                    self.sim_x[1].append(distance_grid_ctr + xs + dxg[idx] * f_distort)
                    self.sim_y[1].append(yg[idx] + dyg[idx] * f_distort)
                elif xs > gap /2.:
                    self.sim_x[0].append(xs + dxg[idx] * f_distort)
                    self.sim_y[0].append(yg[idx] + dyg[idx] * f_distort)

        else:
            for idy, ys in enumerate(yg):
                if ys < -gap / 2.:
                    self.sim_y[0].append(distance_grid_ctr + ys + dyg[idy] * f_distort)
                    self.sim_x[0].append(xg[idy] + dxg[idy] * f_distort)
                elif ys > gap / 2.:
                    self.sim_y[1].append(ys + dyg[idy] * f_distort)
                    self.sim_x[1].append(xg[idy] + dxg[idy] * f_distort)
        return

    def loop(self):
        if not self.init:
            rc = self.get_data(combo_name=self.raft_ccd_combo)

        if not self.line_fitting:
            self.button_line_fitting.button_type = "danger"

        self.layout = layout(self.max_layout)
