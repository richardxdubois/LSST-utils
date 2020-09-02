#!/bin/sh
source activate python3
export PYTHONPATH = /u/ey/richard/LSST/mixcoatl/python
python /u/ey/richard/LSST/LSST-utils/python/run_ccd_spacing.py $*
