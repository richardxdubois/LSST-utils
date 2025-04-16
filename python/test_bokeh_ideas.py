from bokeh.layouts import column, layout, row
from bokeh.plotting import figure, show
from bokeh.models import HoverTool, ColumnDataSource, CustomJS
from bokeh.embed import components
from bokeh.document import Document

# Function to locate a specific object by ID in the Bokeh document
def find_object_by_id(doc, obj_id):
      for model in doc.roots:  # check roots
        if model.id == obj_id:
          return model
        for submodel in model.references(): # check references
          if submodel.id == obj_id:
              return submodel
      return None

# Sample data for the main plot
source = ColumnDataSource(data=dict(x=[1, 2, 3, 4, 5], y=[6, 7, 2, 4, 5], names=["A", "B", "C", "D", "E"]))

# Sample data for the hover plot
hover_source = ColumnDataSource(data=dict(x_hover=[0, 1, 2], y_hover=[0, 1, 0]))


# Create a hidden Bokeh figure for the tooltip
hover_plot = figure(
    width=200,
    height=150,
    title="Hover Plot"
)

hover_plot.line(x="x_hover", y="y_hover", source=hover_source)

# Get the components (script and div)
script, div = components(hover_plot)


# print the components
#print(f"script:\n{script}\n\n")
print(f"div:\n{div}\n\n")

# Extract the ID using string splitting
prefix = '<div id="'
div_id = 0
if div.startswith(prefix):
     start_pos = len(prefix)
     end_pos = div.find('"', start_pos)
     if end_pos != -1:
       div_id = div[start_pos:end_pos]
       print(f"Extracted div id: {div_id}")

# Create the main figure
main_plot = figure(
    width=400,
    height=300,
    title="Main Plot"
)

main_plot.scatter(x='x', y='y', size=10, source=source)

# Get the document from the plot
doc = Document()
doc.add_root(main_plot)

bokeh_id = "p1006"
obj = find_object_by_id(doc, bokeh_id)
if obj:
  print(f"Object with ID '{bokeh_id}': {obj}")
  print(f"Type: {type(obj)}")
  if hasattr(obj, 'name'):
      print(f"Name: {obj.name}")
else:
  print(f"No Bokeh object found with ID: '{bokeh_id}'")

# Configure the HoverTool to embed the figure in the tooltip
tooltips = """
    <div>
        <div>@names</div>
        <div><img src="@image" height="100"></div>
    </div>
"""

callback_code = """
    function findCanvasId(plotDiv) {

          const plotContainer = document.getElementById(plotDiv);
          if(plotContainer) {
            const canvas = plotContainer.querySelector('canvas');
        
            if(canvas) {
                return canvas.id;
            }
            else
                return null;
            }
          else {
            return null
          }
        }
    
    function convertCanvasToImage(canvasId) {
      const canvas = document.getElementById(canvasId); // Get the canvas element
      if (canvas) {
        const dataURL = canvas.toDataURL("image/png"); // Convert to base64 PNG
        const image = new Image(); // create an image element
        image.src = dataURL;
    
         document.body.appendChild(image); // display the image
    
        return dataURL; // return the dataURL to use elsewhere
    
      } else {
        console.error("Canvas element not found:", canvasId);
        return null;
      }
    }

    const data = source.data;
    const hoverData = hover_source.data;
    const index = cb_data.index;

    if (index === null || index === undefined || index.length === 0)
        return;

    // Get x and y from hovered point
    const x = data['x'][index[0]];
    const y = data['y'][index[0]];

    // Update hover data
    hoverData['x_hover'] = [x - 0.5, x, x + 0.5];
    hoverData['y_hover'] = [y - 0.3, y + 0.4, y - 0.3];

    // Update the source.
    hover_source.change.emit();
    
    const div_id = divId; // from the previous python section
    const canvasId = findCanvasId(div_id);

    if(canvasId) {
        const imageDataURL = convertCanvasToImage(canvasId);
        // imageDataURL can be used to be shown or sent to server
    
    }
    else {
     console.log("could not find the canvasId");
    }
    """


# Define a CustomJS callback that updates hover data on hover
h_callback = CustomJS(args=dict(hover_source=hover_source, source=source, divId=div_id), code=callback_code)
hover = HoverTool(tooltips=tooltips)
hover.callback = h_callback

main_plot.add_tools(hover)

print(main_plot, hover_plot, hover, hover.callback)

canvas = layout(column(main_plot))

# Show the main plot
show(canvas)
