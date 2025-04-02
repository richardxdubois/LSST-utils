from bokeh.models import Select, GlobalInlineStyleSheet
from bokeh.plotting import show, curdoc
from bokeh.layouts import row, layout, column

options = ['option1', 'option2', 'option3', 'option4']

css = """
    select.bk-input option[value="option1"] {
        color: orange;
    }
    select.bk-input option[value="option2"] {
        color: green;
    }
    select.bk-input option[value="option3"] {
        color: #ff0000;
    }
"""
stylesheet_0 = """
.bk-input-group{
    color: #ff0000;
    font-weight: bold;
    background-color: #cccccc;
}
"""
#stylesheet = GlobalInlineStyleSheet(css=stylesheet_0)

select1 = Select(title="Choose an option", value="option1", options=options, stylesheets=[css])
canvas_layout = layout(select1)

curdoc().clear()
curdoc().add_root(canvas_layout)
