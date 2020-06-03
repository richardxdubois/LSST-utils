import argparse
from ccd_spacing import ccd_spacing
from bokeh.plotting import curdoc

print("in main")

parser = argparse.ArgumentParser(
    description='Examine CCD spot images to look at spacing')

# The following are 'convenience options' which could also be specified in
# the filter string
parser.add_argument('-d', '--dir',
                    default='/Users/richard/LSST/Data/GridSpacing/6872D_spacing/spacing_169.6_-274.9_016/',
                    help="default directory to use")
args = parser.parse_args()
print(args.dir)
cS = ccd_spacing(dir_index=args.dir)
rc = cS.loop()

curdoc().add_root(cS.layout)
curdoc().title = "CCD Grid Spacing"
