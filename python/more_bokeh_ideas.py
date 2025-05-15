import numpy as np
from bokeh.plotting import figure, show
from bokeh.models import ColumnDataSource, HoverTool, CustomJS, Div
from bokeh.layouts import column
from bokeh.io import curdoc

# Sample Data for the main figure
N = 500
x = np.random.normal(size=N) * 3
y = np.random.normal(size=N) * 3
sizes = np.random.random(size=N) * 15

# Create a ColumnDataSource for the main plot
source = ColumnDataSource(data=dict(x=x, y=y, sizes=sizes, index=list(range(N))))

# Create a Bokeh figure
p = figure(width=600, height=600, tools='box_zoom, reset, hover', title="Hover over the circles")

# Create the scatter glyph AND store it as a renderer for the HoverTool later
scatter_renderer = p.scatter(x='x', y='y', size='sizes', source=source, alpha=0.6, hover_color="red", hover_alpha=0.8)

# Create a ColumnDataSource for the thumbnail images, initialized with an empty image
thumb_source = ColumnDataSource(data=dict(image_url=['image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==']))

# Hover tool with a basic tooltip (and the image link)
thumb_div = """
    <div>
        <h3>@index</h3>
        <div>
            <img
                src="@image_url" height="400" alt="Static Image"
            >
        </div>
    </div>
"""
#hover = HoverTool(renderers=[scatter_renderer], tooltips=thumb_div)
hover = HoverTool(tooltips=thumb_div)
hover_test = HoverTool(tooltips="""
    <div>
        <h3>@index</h3>
        <div>
            <img
                src="@image_url" height="400" alt="Static Image"
            >
        </div>
    </div>
""", renderers=[scatter_renderer])

# Custom JavaScript function to generate the thumbnail charts
code = """
    const geometry = cb_data.geometry;
    const indices = cb_data['index'].indices;
    const x = geometry.x;
    const y = geometry.y;
    //console.log("Entered callback");
    const tn_t1 = '<div><h3>@index</h3><div><img src="';
    //console.log(tn_t1);
    const tn_t2 = '" height="400" alt="Static Image"></div></div>';
    //console.log(tn_t2) 
    
    if (indices.length != 0) {
        console.log("Selected index: ", geometry);

        const thumbnail_x = Array.from({ length: 100 }, (_, i) => i / 10); // X-values
        const thumbnail_y = thumbnail_x.map(val => Math.sin(val) * y); // Y-values

        const thumbCanvas = document.createElement('canvas');
        thumbCanvas.width = 100;
        thumbCanvas.height = 80;
        const thumbCtx = thumbCanvas.getContext('2d');

        // Draw the thumbnail plot (line)
        thumbCtx.beginPath();
        thumbCtx.strokeStyle = 'navy';
        thumbCtx.moveTo(thumbnail_x[0], thumbnail_y[0]);

        for (let i = 1; i < thumbnail_x.length; i++) {
            thumbCtx.lineTo(thumbnail_x[i], thumbnail_y[i]);
        }
        thumbCtx.stroke();

        let thumbImageURL = '';
        try {
            thumbImageURL = thumbCanvas.toDataURL();
            console.log("Data URL created: " + thumbImageURL.substring(0, 50) + "...");
        } catch (e) {
            console.error("Error creating Data URL: ", e);
            thumbImageURL = 'image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==';  // transparent 1x1 gif
        }

        thumbImageURL = 'https://web.stanford.edu/~dubois/India2016/images/IndiaLocations2016.png'; // Just to simplify
        thumb_source.data['image_url'] = [thumbImageURL];
        console.log("File URL created: " + thumbImageURL.substring(0, 50) + "...");
        
        thumb_source.data.image_url = [thumbImageURL];
        let tn_text = tn_t1 + thumbImageURL + tn_t2;
        hover.tooltips = tn_text;
        //console.log("index = ", index)
        //console.log(thumb_div.text);
        console.log(thumb_source.data);
        //thumb_source.change.emit();
    }
"""

# Create and configure CustomJS callback
callback = CustomJS(args=dict(source=source, thumb_source=thumb_source, hover=hover), code=code)

# Tooltip parameters
hover.callback = callback

# Add tooltip to the figure
p.add_tools(hover)

# Prepare the layout and show it
layout = column(p)

# IMPORTANT: for deployment, show() is replaced by curdoc().add_root()
#curdoc().add_root(layout)
show(layout)
