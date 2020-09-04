#!/bin/bash
source ~/anaconda3/etc/profile.d/conda.sh
conda activate bokeh_env
export PYTHONPATH=u/ey/richard/LSST/mixcoatl/python
python /u/ey/richard/LSST/LSST-utils/python/run_ccd_spacing.py $*
