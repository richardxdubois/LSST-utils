import argparse
from ccd_spacing import ccd_spacing
import subprocess

print("in main")

parser = argparse.ArgumentParser(
    description='Examine CCD spot images to look at spacing')

# The following are 'convenience options' which could also be specified in
# the filter string
parser.add_argument('-d', '--dir',
                    default=None, help="default directory to use")
parser.add_argument('-o', '--output', default=None, help="output directory path")
parser.add_argument('--out_params', default='CCD_grids_params.csv',
                    help="output params file spec")
parser.add_argument('-g', '--grid', default=None, help="grid distortions file")
parser.add_argument('-s', '--single', default="yes", help="run first combo")

args = parser.parse_args()
print(args.dir)
cS = ccd_spacing(dir_index=args.dir, distort_file=args.grid)

distort_file = " -g " + args.grid
spot_files = " -d " + args.dir
out_csv = " --out_params " + args.out_params
out_files = " --output " + args.output

for combos in cS.file_paths:
    command_args = "-W 20 -R rhel7 python batch_ccd_spacing.sh --single yes -c " + combos
    command_args += distort_file + spot_files + out_csv + out_files
    print(command_args)
    #subprocess.run(["bsub", command_args])
    if args.single == "yes":
        break
