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
parser.add_argument('-e', '--executable', default="../bin/", help="path to shell script")
parser.add_argument('--out_params', default=None,
                    help="output params directory spec")
parser.add_argument('--pickle', default=None, help="output directory for pickle of cS.sensor")
parser.add_argument('--logs', default=None, help="output directory for batch logs")
parser.add_argument('-g', '--grid', default=None, help="grid distortions file")
parser.add_argument('-s', '--single', default="yes", help="run first combo")

args = parser.parse_args()
print(args.dir)
cS = ccd_spacing(dir_index=args.dir, distort_file=args.grid)

distort_file = " -g " + args.grid
spot_files = " -d " + args.dir
out_files = " --output " + args.output

for combos in cS.file_paths:
    out_csv = " --out_params " + args.out_params + combos + ".csv"
    log_file = args.logs + combos + ".log"
    batch_bits = "-W 4 -R centos7 -o " + log_file

    command_args = batch_bits + " " + args.executable + "batch_ccd_spacing.sh --single yes " \
                  + " --pickle " + args.pickle + " -c " + combos
    command_args += distort_file + spot_files + out_csv + out_files
    print(command_args)
    subprocess.Popen("bsub " + command_args, shell=True)
    if args.single == "yes":
        break
