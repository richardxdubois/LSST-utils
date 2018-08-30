from get_EO_analysis_results import get_EO_analysis_results
from  eTraveler.clientAPI.connection import Connection
import numpy as np
from bokeh.layouts import row, column
from bokeh.models import BoxSelectTool, LassoSelectTool, Spacer
from bokeh.plotting import figure, curdoc
from bokeh.models.widgets import TextInput

connect = Connection(operator='richard', db='Prod', exp='LSST-CAMERA', prodServer=True)

g = get_EO_analysis_results(db='Prod', server='Prod')

raft_list, data = g.get_tests(site_type="BNL-Raft", test_type="gain", run=7983)
res = g.get_results(test_type="gain", data=data, device=raft_list)

test_list = []

for ccd in res:
    test_list.extend(res[ccd])

x = np.array(test_list)

''' Present a scatter plot with linked histograms on both axes.
Use the ``bokeh serve`` command to run the example by executing:
    bokeh serve selection_histogram.py
at your command prompt. Then navigate to the URL
    http://localhost:5006/selection_histogram
in your browser.
'''

print 'firing up the bokeh server with a scatterplot'

TOOLS="pan,wheel_zoom,box_select,lasso_select,reset"

hhist, hedges = np.histogram(x, bins=20)
ph = figure(tools=TOOLS,title="Gains")
ph.step(range(len(hhist)), hhist, legend="Run: 7983")

text_input = TextInput(value="7983", title="BNL Raft Run")


layout = column(text_input, ph)

curdoc().add_root(layout)
curdoc().title = "Selection Histogram"

def update(attr, old, new):
    raft_list, data = g.get_tests(site_type="BNL-Raft", test_type="gain", run=text_input.value)
    res_new = g.get_results(test_type="gain", data=data, device=raft_list)

    test_list_new = []

    for ccd in res_new:
        test_list_new.extend(res_new[ccd])

    x_new = np.array(test_list_new)
    hhist_new, _ = np.histogram(x_new, bins=20)
    ph.step(range(len(hhist_new)), hhist_new, color='red', legend="Run:"+text_input.value)


text_input.on_change('value', update)