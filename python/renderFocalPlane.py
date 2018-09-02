from __future__ import print_function
import numpy as np
import random

from bokeh.models import ColumnDataSource, DataRange1d, Plot, LinearAxis, Grid, LogColorMapper
from bokeh.models.glyphs import Patches
from bokeh.plotting import figure, output_file, show, save
from bokeh.palettes import Viridis6 as palette
from bokeh.layouts import row, layout

"""
Create a rendering of the focal plane, composed of science and corner rafts, each made of sensors with 
their amplifiers.
"""

class renderFocalPlane():

    def __init__(self):
        # define primitives for amps, sensors and rafts

        self.amp_width = 1/8.
        self.ccd_width = 1.
        self.raft_width = 3.

        self.raft_slot_names = ["R01", "R02", "R03",
                                "R10", "R11", "R12", "R13", "R14",
                                "R20", "R21", "R22", "R23", "R24",
                                "R30", "R21", "R32", "R33", "R34",
                                "R41", "R42", "R43"
                                ]
        self.raft_center_x = [-3., 0., 3.,
                              -6., -3., 0, 3., 6.,
                              -6., -3., 0, 3., 6.,
                              -6., -3., 0, 3., 6.,
                              -3., 0., 3.
                              ]
        self.raft_center_y = [6., 6., 6.,
                              3., 3., 3., 3., 3.,
                              0., 0., 0., 0., 0.,
                              -3., -3., -3., -3., -3.,
                              -6., -6., -6.
                              ]

        self.ccd_center_x = [-1., 0., 1.,
                             -1., 0., 1.,
                             -1., 0., 1.
                             ]
        self.ccd_center_y = [1., 1., 1.,
                             0., 0., 0.,
                             -1., -1., -1.
                             ]

        self.amp_center_x = [-self.ccd_width/2.-self.amp_width/2.+(j+1)/8. for j in range(8)]
        self.amp_center_x.extend([-self.ccd_width/2.-self.amp_width/2.+(j+1)/8. for j in range(8)])

        self.amp_center_y = [0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25]
        self.amp_center_y.extend([-0.25, -0.25, -0.25, -0.25, -0.25, -0.25, -0.25, -0.25])


    def render(self):

        TOOLS = "pan,wheel_zoom,reset,hover,save"
        color_mapper = LogColorMapper(palette=palette)

        p = figure(
            title="Focal plane", tools=TOOLS,
            tooltips=[
                ("Raft", "@raft_name"), ("CCD", "@ccd_number"), ("Amp", "@amp_number"),
                ("test_q", "@test_q")
            ],
            x_axis_location=None, y_axis_location=None,)
        p.grid.grid_line_color = None
        p.hover.point_policy = "follow_mouse"

        #p.patches('x', 'y', source=source,
        #          fill_alpha=0.7, line_color="blue", line_width=0.5)

        p.rect(x=[0], y=[0], width=15., height=15., color="red", fill_alpha=0.1)

        x = []
        y = []
        raft_name = []
        ccd_number = []
        amp_number = []
        test_q = []

        for raft in range(21):

            raft_x = self.raft_center_x[raft]
            raft_y = self.raft_center_y[raft]
            p.rect(x=[raft_x], y=[raft_y], width=self.raft_width,
                    height=self.raft_width, color="blue", fill_alpha=0.)

            for ccd in range(9):
                cen_x = raft_x  + self.ccd_center_x[ccd]
                cen_y = raft_y  - self.ccd_center_y[ccd]

                p.rect(x=[cen_x], y=[cen_y], width=self.ccd_width, height=self.ccd_width, color="green",
                       fill_alpha=0.)

                for amp in range(16):

                    a_cen_x = cen_x + self.amp_center_x[amp]
                    a_cen_y = cen_y + self.amp_center_y[amp]

                    x.append(a_cen_x)
                    y.append(a_cen_y)
                    raft_name.append(self.raft_slot_names[raft])
                    ccd_number.append(ccd)
                    amp_number.append(amp)
                    ran = random.uniform(0.,1000.)
                    test_q.append(ran)

        source = ColumnDataSource(dict(x=x, y=y, raft_name=raft_name, ccd_number=ccd_number,
                                  amp_number=amp_number, test_q=test_q))

        p.rect(x='x', y='y', source=source, width=self.amp_width, height=self.ccd_width/2.,
            color="black",
            fill_alpha=0.7, fill_color={ 'field': 'test_q', 'transform': color_mapper})

        h_q, bins = np.histogram(np.array(test_q))
        h = figure(title="Test quantity", tools=TOOLS)
        h.quad(top=h_q, bottom=0, left=bins[:-1], right=bins[1:], fill_color='blue', fill_alpha=0.2)

        l = layout(row(p,h))

        show(l)

if __name__ == "__main__":

    rFP = renderFocalPlane()
    rFP.render()