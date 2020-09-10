import argparse
import numpy as np
from ccd_spacing import ccd_spacing

print("in main")

parser = argparse.ArgumentParser(
    description='Examine CCD spot images to look at spacing')

# The following are 'convenience options' which could also be specified in
# the filter string
parser.add_argument('-d', '--dir',
                    default=None, help="default directory to use")
parser.add_argument('-o', '--output', default=None, help="output directory path")
parser.add_argument('-e', '--executable', default="../bin/", help="path to shell script")
parser.add_argument('-m', '--mode', default="vertical", help="horizontal or vertical")
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

distances = {}

for combos in cS.file_paths:
    cS.raft_ccd_combo = combos
    rc = cS.get_pickle_file()

    if cS.ccd_relative_orientation != args.mode:
        continue

    for s in range(2):
        c = distances.setdefault(combos, {})
        sd = c.setdefault(s, [])
        c[s] = cS.sensor[s].grid_distances

    if args.single == "yes":
        break

dist_sums = []

for co in distances:
    dist_sums = np.vstack(dist_sums, distances[co][0])

dist_mean = np.mean(dist_sums, axis=2)
dist_std = np.std(dist_sums, axis=2)