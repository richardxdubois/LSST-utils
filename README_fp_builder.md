# Instructions for running the trial fp builder bokeh server app 2025-03-12

Purpose of the app is to provide exploration of per-amp calibrations and the Run7 EO test campaign,
using heatmaps of parameters across the full focal plane, coupled with
histograms of selected parameters and optiional correlation with a second
parameter.


##  DM stack (example of version v28.0.1):

source /cvmfs/sw.lsst.eu/linux-x86_64/lsst_distrib/v28.0.1/loadLSST-ext.bash

setup lsst_distrib

setup -r ~lsstccs/prod/eo_pipe -j

## Invocation:

bokeh serve /sdf/home/r/richard/rubin-user/gitstuff/LSST-utils/python/fp_builder.py --args --app_config /sdf/ho
me/r/richard/rubin-user/camera/fp.yaml

## View the output in your local web browser:

Tunnel to the node you ran the server to access port 5006:

ssh -L 5006:localhost:5006 <jumped to devl node>

(if not already defined in your .ssh/config file, here is the full proxy
jump syntax:

ssh -L 5006:localhost:5006 -J richard@s3dflogin.slac.stanford.edu richard@sdfiana034

(if you're at the summit and cannot reach s3dflogin, replace it with the "rocky" bastion host, and then fully s
pecify
sdfiana034.sdf.slac.stanford.edu. rocky requires Duo/TFA)

assuming sdfiana034 as the working node; of course, use your own account name)

then point your local browser to localhost:5006/trial_fp_builder

## Usage notes:

 * fp.yaml sets up a pickle file for run E1110 to get going
 * calibrations can be selected from the calibrations run text box. As of this writing, "defaults" and "DM-50336" are
   available as pickle files for quicker access; butler fetching is quite slow.
 * different runs can be obtained in the run dialogue box by specifying the
   run in the form <run id>_<code version>, eg E1880_w_2025_02
 * Most of the Run 7 runs have been pickled. They are much faster to access than querying
   the butler. Currently, run 6 runs have not been pickled and their format is
   (eg)13551_<code_version>
 * select desired test from the pull-down menu
 * hover over the focal plane to see (raft, CCD, amp, test value)
 * sliders update the focal plane and histograms in real time
 * click on the focal plane to select a single raft; click again (anywhere on
   the focal plane to return to full fp mode (if you click whitespace, there
   will be a log message to that effect and you can try again)
 * examine a 2nd test by turning on the second test switch. Then select the
   desired test. A scatterplot and histogram appear. It can be hidden by
   turning the switch off again.
 * You'll see a new box appear to select a 2nd run to compare to the original run. 
   Turning off the Second run mode will return to single run mode.
 * use the Exit button to terminate the app (unless you are sharing a server)

## Notes and caveats:

 * Due to Cyber restrictions, it is too complicated to run this in the USDF
   RSP - access to the port is restricted and involves setting up ingress.
 * If you are using a communal server, just kill your browser session when you're done.
   The Exit button shuts down the server for all.	
 * the run selection box will be invisible if you have not set up the DM
   stack or EO code
 * histograms use clipped medians to determine ranges. SciPy's winsorize is used to 
   eliminate extreme outliers.The threshold can be changed with the Set clip sigma dialogue.
   Clipping can be turned off.
 * heatmap values are set to a guard value for entries that are NaNs or outside the
   slider limits, so they will appear as the blackest in the focal plane.
 * loading a new run can take a while (minutes), especially if the run is not
   in the weka cache. The pickle file for E2233 was provided for quick access.
 * in the very unlikely case someone else is running this on the same node,
   you can use a different port by adding "--port <different port> before
   the "--args" in the bokeh server invocation. Of course, you would need to 
   update your tunneled port as well. Multiple users can attach independently to
   a server instance.
 * the CMap refresh button toggles the colour map updating after each slider change, or not.
   Default is not.
