from optparse import OptionParser
import datetime
import seaborn as sns
import matplotlib.pyplot as plt
import os
from monet.utilhysplit.hcontrol import NameList
from monet.util import options_process
from monet.util import options_vmix
from monet.util import options_obs  
from monet.util import svconfig
import sys
import pandas as pd
import numpy as np

# import cartopy.crs as ccrs
# import cartopy.feature as cfeature

"""
Functions
-----------

INPUTS: 
inputs are detailed in the attributes of the ConfigFile class.

STEPS
A. Preliminary.
1. Find Emission sources.
2. Find measurement stations in area
3. Produce map of sources and measurements.
4. Create plots of emissions vs. time
5. Create plots of measurements vs. time
-----------------------------------------------
7 Main parts currently.

options.defaults - 
   import svhy
   create CONTROL.0 and SETUP.0 files

options.results -
   import svresults2
   svcems
   Uses the SourceSummary file.
   read dataA files in subdirectories
   write datem files
   plot obs and measurements

options.vmix -
   svhy
   svobs
   svmet

options.cems
   svcems

options.obs
   svobs
   svmet
   svish

options.create_runs
   svhy

options.write_scripts
   svhy

"""


parser = OptionParser()
# parser.add_option(
#    "-a", type="string", dest="state", default="ND", help="two letter state code (ND)"
# )
parser.add_option(
    "-i",
    type="string",
    dest="configfile",
    default="CONFIG.S",
    help="Name of configuration file",
)
parser.add_option(
    "-p",
    action="store_true",
    dest="print_help",
    default=False,
    help="Print help for configuration file",
)

(opts, args) = parser.parse_args()

if opts.print_help:
    print("-------------------------------------------------------------")
    print("Configuration file options (key words are not case sensitive)")
    print("-------------------------------------------------------------")
    print(options.print_help(order=options.lorder))
    sys.exit()

options = svconfig.ConfigFile(opts.configfile)
# options.fileread is a boolean attribute of ConfigFile class.
if not options.fileread:
    print("configuration file " + opts.configfile + " not found.\ngoodbye")
    sys.exit()

##------------------------------------------------------##
##------------------------------------------------------##
# Process some of the options to create new parameters.
##------------------------------------------------------##
##------------------------------------------------------##


svp = options_process.main(options)
# TO DO - may pass svp rather than individual attributes to functions.
d1 = svp.d1
d2 = svp.d2
area = svp.area
logfile = svp.logfile
source_chunks = svp.source_chunks
datem_chunks = svp.datem_chunks
tcmrun = svp.tcmrun
run_duration = svp.run_duration
rfignum = 1

##------------------------------------------------------##
# Run a test
##------------------------------------------------------##

runtest=False
if runtest:
   options_obs.test(options, d1, d2, area, source_chunks,
                    run_duration, logfile, rfignum)  
   sys.exit()

##------------------------------------------------------##
# Create default CONTROL.0 and SETUP.0 files
##------------------------------------------------------##
if options.defaults:
    with open(logfile, 'a') as fid:
        fid.write('Running  defaults\n')
    from monet.util.svhy import default_setup
    from monet.util.svhy import default_control
    print("writing control and setup")
    # if units='ppb' then ichem=6 is set to output mixing ratios.
    default_setup("SETUP.0", options.tdir, units=options.cunits)
    default_control("CONTROL.0", options.tdir, run_duration, d1, area=area)

##------------------------------------------------------##
# Plots of results
##------------------------------------------------------##
if options.results:
    with open(logfile, 'a') as fid:
     fid.write('Running  results\n')
    from monet.util.svresults2 import SVresults
    from monet.util.svcems import SourceSummary
    sss = SourceSummary(fname= options.tag + '.source_summary.csv')
    df = sss.load()
    orislist = sss.check_oris(10)
    #orislist = options.orislist
    print('ORIS LIST', orislist)
    #sys.exit()
    svr = SVresults(options.tdir, orislist=orislist, daterange=[d1, d2])
    datemfile = options.tag + "DATEM.txt"
    print("writing datem ", datemfile)
    svr.writedatem(datemfile)
    svr.fill_hash()
    print("PLOTTING")
    svr.plotall()

##------------------------------------------------------##
# Vmixing
##------------------------------------------------------##
#vmet is a MetObs object.
#vmetdf is the dataframe associated with that.

if options.vmix==1:
    # reads files created from vmixing program in each subdirectory.
    # creates MetObs object with matched so2 observations and vmixing data time
    # series.
 
    # FILES CREATED
    # tag + .vmixing.csv
    # PLOTS CREATED
    # histograms of wind direction conditional on concentration measurement.
    # 2d histgrams of wind direction and (currently commented out)
    vmet = options_vmix.options_vmix_main(options, d1, d2, area, source_chunks,
                                      logfile)

##------------------------------------------------------##
##------------------------------------------------------##
if options.cems:
   # OUTPUTS
   # ef SEmissions object
   # rfignum integer
   # FILES CREATED
   # source_summary.csv
   from monet.util import options_cems 
   ef, rfignum = options_cems.options_cems_main(options, d1, d2, area, 
                                                 source_chunks, logfile)
   
##------------------------------------------------------##
##------------------------------------------------------##
if options.obs:
    #OUTPUTS
    # meto - MetObs object with met observations.
    # obs  - SObs object
    # FILES CREATED
    # datem files in subdirectories
    # geometry.csv file
    # PLOTS CREATED
    # time series of observations
    # map with obs, cems, ish 
    # 2d distributions of so2 conc and wdir for sites with met data.
    meto, obs = options_obs.options_obs_main(options, d1, d2, area, source_chunks, run_duration,
                     logfile, rfignum) 

    if options.vmix==1:
       options_vmix.options_vmix_met(options, vmet, meto, logfile)

##------------------------------------------------------##
##------------------------------------------------------##

runlist = []
if options.create_runs:
    from monet.util.svhy import create_controls
    from monet.util.svhy import create_vmix_controls
    from monet.util.svhy import RunScript
    from monet.util.svhy import VmixScript
    with open(logfile, 'a') as fid:
         fid.write('creating CONTROL files\n')

    print('Creating CONTROL files')
    runlist = create_controls(
        options.tdir,
        options.hdir,
        d1,
        d2,
        source_chunks,
        options.metfmt,
        units = options.cunits,
        tcm = tcmrun
    )
    if not runlist: 
        print('No  CONTROL files created') 
        print('Check if EMITIMES files have been created')
    else:
        rs = RunScript(options.tag + ".sh", runlist, options.tdir)
    print('Creating CONTROL files for vmixing')
    runlist = create_vmix_controls(
        options.tdir,
        options.hdir,
        d1,
        d2,
        source_chunks,
        options.metfmt,
    )
    if not runlist: 
        print('No vmixing CONTROL files created. Check if datem.txt files exist')
    else:
        rs = VmixScript(options.tag + '.vmix.sh', runlist, options.tdir)

##------------------------------------------------------##
##------------------------------------------------------##

if options.write_scripts:
    from monet.util.svhy import DatemScript
    with open(logfile, 'a') as fid:
         fid.write('writing scripts\n')

    #if not runlist:
    from monet.util.svhy import create_runlist
    runlist = create_runlist(options.tdir, options.hdir, d1, d2, source_chunks)

    rs = DatemScript(
        "p1datem_" + options.tag + ".sh", runlist, options.tdir, options.cunits, poll=1
    )
    rs = DatemScript(
        "p2datem_" + options.tag + ".sh", runlist, options.tdir, options.cunits, poll=2
    )
    rs = DatemScript(
        "p3datem_" + options.tag + ".sh", runlist, options.tdir, options.cunits, poll=3
    )


##------------------------------------------------------##
# TO DO should tie numpar to the emissions amount during that time period
# as well as the resolution.
# emissions are on order of 1,000-2,000 lbs/hour (about 1,000 kg)
# 10,000 particles - each particle would be 0.1 kg or 100g.
# 0.05 x 0.05 degree area is about 30.25 km^2. 30.25e6 m^2.
# 50 meter in the vertical gives 1.5e9 m^3.
# So 1 particle in a 0.05 x 0.05 degree area is 0.067 ug/m3.
# Need a 100 particles to get to 6.7 ug/m3.
# This seems reasonable.

