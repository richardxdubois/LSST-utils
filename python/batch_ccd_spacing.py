import argparse
from ccd_spacing import ccd_spacing
import sys

print("in main")

parser = argparse.ArgumentParser(
    description='Examine CCD spot images to look at spacing')

# The following are 'convenience options' which could also be specified in
# the filter string
parser.add_argument('-d', '--dir',
                    default='/Users/richard/LSST/Data/GridSpacing/',
                    help="default directory to use")
parser.add_argument('-o', '--output', default='/Users/richard/LSST/Code/misc/CCD_grids/',
                    help="output directory path")
parser.add_argument('--out_params', default='CCD_grids_params.csv',
                    help="output params file spec")
parser.add_argument('-g', '--grid', default=
                    '/Users/richard/LSST/Code/misc/CCD_grids/optical_distortion_grid.fits',
                    help="grid distortions file")

args = parser.parse_args()
print(args.dir)
cS = ccd_spacing(dir_index=args.dir, combo_name=args.combo, distort_file=args.grid)


for combos in cS.file_paths:
    comm = "bsub python run_ccd_spacing.py "