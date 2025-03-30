import lsst.daf.butler as daf_butler
import lsst.eo.pipe as eo_pipe
import pickle
import re
import yaml
import os

"""
Pickle all LSSTCam runs available in the butler with code versions. It selects only weeklies and then the most 
recent of those.
"""
debug = False

repo = "/repo/main"
butler = daf_butler.Butler(repo)

pattern_version = f"u/lsstccs/eo_*_*"
collections_v = butler.registry.queryCollections(pattern_version)

# Define the regular expression pattern

#  .*?_E(\d+)_(.+)$:
#  .*?_ matches any characters up to the first _E.
#  E(\d+): Matches E followed by one or more digits, capturing the digits as the first group.
#  _(.+)$: Matches an underscore followed by any characters until the end of the string, capturing this part as the second group.

pattern = r".*?_E(\d+)_(.+)$"

runs = {}
for r in collections_v:

    # Search for the pattern in the input string
    match = re.search(pattern, r)

    if match:
        E_code = f"E{match.group(1)}"  # Extract run
        w_code = f"{match.group(2)}"  # Extract DM version

        runs.setdefault(E_code, [])
        if w_code not in runs[E_code] and "/" not in w_code and "d" not in w_code:
            runs[E_code].append(w_code)

for rv in runs:
    print(rv, runs[rv][-1])

for rv in runs:
    print("Using ", rv)

    vers = runs[rv][-1]
    r_vers = rv + "_" + vers
    o = rv + "_" + vers + "_amps_data.npy"

    if os.path.isfile(o):
        print(o, "already exists. Skipping")
        continue

    pattern = f"u/lsstccs/eo_*_{r_vers}"

    print(rv, r_vers, pattern)

    try:
        collections = butler.registry.queryCollections(pattern)

        amp_data = eo_pipe.get_amp_data(repo, collections)

        with open(o, "wb") as pickle_file:
            pickle.dump(amp_data, pickle_file)
            print("Writing to", o)
    except:
        print("Error fetching ", rv)
        continue

    if debug:
        print("terminating")
        break

