import argparse
from ccd_spacing import ccd_spacing
import subprocess

print("in main")

parser = argparse.ArgumentParser(
    description='Examine CCD spot images to look at spacing')

# The following are 'convenience options' which could also be specified in
# the filter string
parser.add_argument('-d', '--dir',
                    default='/Volumes/External_SSD_Deb/LSST/Data/GridSpacing/',
                    help="default directory to use")
parser.add_argument('-o', '--output', default='/Users/richard/LSST/Code/misc/CCD_grids/',
                    help="output directory path")
parser.add_argument('--out_params', default='CCD_grids_params.csv',
                    help="output params file spec")
parser.add_argument('-g', '--grid', default=
                    '/Volumes/External_SSD_Deb/LSST/misc/CCD_grids/optics_distorted_grid_norm.fits',
                    help="grid distortions file")
parser.add_argument('-s', '--single', default="yes", help="run first combo")

args = parser.parse_args()
print(args.dir)
cS = ccd_spacing(dir_index=args.dir, distort_file=args.grid)


for combos in cS.file_paths:
    command_args = "-W 20 -R rhel7 python batch_ccd_spacing.sh --single yes -c " + combos
    print(command_args)
    #subprocess.run(["bsub", command_args])
    if args.single == "yes":
        break
