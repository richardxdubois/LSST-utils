from bokeh.layouts import column, layout, row
from bokeh.plotting import figure, show, save
from bokeh.models import HoverTool, ColumnDataSource, CustomJS

ten_photos = [
    "https://web.stanford.edu/~dubois/India2016/images/dscn6869.jpg",
    "https://web.stanford.edu/~dubois/India2016/images/dscn6870.jpg",
    "https://web.stanford.edu/~dubois/India2016/images/dscn6874.jpg",
    "https://web.stanford.edu/~dubois/India2016/images/dscn68675.jpg",
    "https://web.stanford.edu/~dubois/India2016/images/dscn6876.jpg",
    "https://web.stanford.edu/~dubois/India2016/images/dscn6880.jpg",
    "https://web.stanford.edu/~dubois/India2016/images/dscn6881.jpg",
    "https://web.stanford.edu/~dubois/India2016/images/dscn6885.jpg",
    "https://web.stanford.edu/~dubois/India2016/images/dscn6887.jpg",
    "https://web.stanford.edu/~dubois/India2016/images/dscn6889.jpg"
    ]

# Sample data for the main plot
source = ColumnDataSource(data=dict(x=[1, 2, 3, 4, 5], y=[6, 7, 2, 4, 5], names=["A", "B", "C", "D", "E"],
                                    image_url=ten_photos[:5]))

# Sample data for the hover plot
x_hover = [0, 1, 2]
y_hover = [0, 1, 0]
image_urls = ["", "", ""]
hover_source = ColumnDataSource(data=dict(x_hover=x_hover, y_hover=y_hover, image_url=image_urls))


# Create a hidden Bokeh figure for the tooltip
hover_plot = figure(width=200, height=150, title="Hover Plot")

#hover_plot.line(x="x_hover", y="y_hover", source=hover_source)
hover_plot.line(x=x_hover, y=y_hover)

# Create the main figure
main_plot = figure(width=400, height=300, title="Main Plot")

mp = main_plot.scatter(x='x', y='y', size=10, source=source)

# Configure the HoverTool to embed the figure in the tooltip

thumb_div = """
    <div>
        <h3>@names</h3>
        <div>
            <img
                src="@image_url" height="400" alt="Static Image"
            >
        </div>
    </div>
"""

callback_code = """

   //console.log("Finding Bokeh Plot Div ID...");
    // Function to find the div ID of the Bokeh plot
    function findBokehDivId() {
        console.log("Entered findBokehDivId()");
        var plotDiv = document.querySelector('.bk-layer.bk-events'); // Assuming .bk-plot is a unique class for your plot's div
        //var plotDiv = document.querySelector('.bk-Column').shadowRoot.lastChild.shadowRoot.querySelector('.bk-Figure').shadowRoot.querySelectorAll('.bk-layer .bk-events')
        console.log("PlotDiv", plotDiv);
        if (plotDiv) {
            console.log("Bokeh Plot Div ID: " + plotDiv.id);
            // Here you can perform other operations using the div ID, if needed
        } else {
            console.log("Bokeh Plot Div not found.");
        }
    } 
    function convertCanvasToImage(canvasId) {
      const canvas = document.getElementById(canvasId); // Get the canvas element
      if (canvas) {
        const dataURL = canvas.toDataURL("image/png"); // Convert to base64 PNG
        const image = new Image(); // create an image element
        image.src = dataURL;
    
         document.body.appendChild(image); // display the image
        console.log("found dataURL");
        return dataURL; // return the dataURL to use elsewhere
    
      } else {
        console.error("Canvas element not found:", canvasId);
        return null;
      }
    }

    const data = source.data;
    const hoverData = hover_source.data;
    const index = cb_data.index;

    if (index === null || index === undefined || index.indices.length === 0)
        return;
    console.log(cb_data);
    console.log("url", source.data["image_url"][index]);
    // Get x and y from hovered point
    const x = data['x'][index];
    const y = data['y'][index];
    console.log("x, y", x, y);

    // Update hover data
    hoverData['x_hover'] = [x - 0.5, x, x + 0.5];
    hoverData['y_hover'] = [y - 0.3, y + 0.4, y - 0.3];

    // Update the source.
    hover_source.change.emit();

    // Call the function when the document is ready
    console.log("About to look for divid");
    //document.addEventListener('DOMContentLoaded', function() {
        findBokehDivId();
    //});
    """


# Define a CustomJS callback that updates hover data on hover
#h_callback = CustomJS(args=dict(hover_source=hover_source, source=source, divId=div_id), code=callback_code)
h_callback = CustomJS(args=dict(hover_source=hover_source, source=source), code=callback_code)

hover = HoverTool(tooltips=thumb_div, renderers=[mp])
hover.callback = h_callback

main_plot.add_tools(hover)

print(main_plot, hover_plot, hover, hover.callback)

canvas = layout(column(main_plot, hover_plot))

# Show the main plot
save(canvas)
