#!/bin/sh
source activate bokeh_env
export PYTHONPATH = /u/ey/richard/LSST/mixcoatl/python
python /u/ey/richard/LSST/LSST-utils/python/run_ccd_spacing.py $*
