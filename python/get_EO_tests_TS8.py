from get_EO_analysis_results import get_EO_analysis_results
import argparse

parser = argparse.ArgumentParser(
    description='loop through good TS8 runs.')

parser.add_argument('-t', '--test', default="gain", help="test quantity to display")
parser.add_argument('-d', '--db', default="Prod", help="eT database")

args = parser.parse_args()

runs_list = [10517, 10861, 10669, 10928, 11063, 10722, 11351, 11415, 10982,11903, 11166, 12027, 11808,
             11852, 11746, 12008, 11952, 11671, 12086, 12130, 12139]

g = get_EO_analysis_results(db=args.db)

for run in runs_list:

    raft_list, data = g.get_tests(test_type=args.test, run=run)
    res = g.get_all_results(data=data, device=raft_list)

    print("Processing raft ", raft_list)
    test_list = []
    amp_count = 0
    for ccd in res[args.test]:
        amp_tests = res[args.test][ccd]
        test_list.extend(amp_tests)
        amp_count += 16

    print("len(test_list) = ", len(test_list), " for ", amp_count, " amps")
