# LSST-utils
utilities for camera data 

Examples of use for exemplar scripts:

- tabulateRaftResults.py

$ python tabulateRaftResults.py --run 3764 -r LCA-11021_RTM-004 -s read_noise

- tabulateRaftGains.py

$ python tabulateRaftGains.py --run 3764 -r LCA-11021_RTM-004

- get_read_noise.py (run on SLAC linux with direct access to image data files)

$ python get_read_noise.py -s ITL-3800C-034 -r 3764 -t fe55_raft_acq -R LCA-11021_RTM-004

- count up all e2v sensors, and how many have finished TS-3 EO testing

$ python count_ccd_test_stand.py -t e2v-CCD
