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
from monet.util.svmet import MetObs
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

options = svconfig.ConfigFile(opts.configfile)
if opts.print_help:
    print("-------------------------------------------------------------")
    print("Configuration file options (key words are not case sensitive)")
    print("-------------------------------------------------------------")
    print(options.print_help(order=options.lorder))
    sys.exit()

#options = svconfig.ConfigFile(opts.configfile)
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

# create an instance of the MetObs class.
vmet = MetObs()

##------------------------------------------------------##
# Run a test
##------------------------------------------------------##

runtest=False
if runtest:
   options_obs.test(options, d1, d2, area, source_chunks,
                    run_duration, logfile, rfignum, svp.ensemble)  
   sys.exit()

##------------------------------------------------------##
# Create default CONTROL.0 and SETUP.0 files
##------------------------------------------------------##
if options.defaults and not svp.ensemble:
    with open(logfile, 'a') as fid:
        fid.write('Running  defaults\n')
    from monet.util.svhy import default_setup
    from monet.util.svhy import default_control
    print("writing control and setup")
    # if units='ppb' then ichem=6 is set to output mixing ratios.
    default_setup("SETUP.0", options.tdir, units=options.cunits)
    default_control("CONTROL.0", options.tdir, run_duration, d1, area=area)
# if ensemble then copy CONTROL.0 and SETUP.0 to ensemble directories
if options.defaults and svp.ensemble:
    from monet.util.svens import ensemble_defaults
    ensemble_defaults(options.tdir)

##------------------------------------------------------##
## Get the CEMS data.
##------------------------------------------------------##
if options.cems:
   # OUTPUTS
   # ef SEmissions object
   # rfignum integer
   # FILES CREATED
   # source_summary.csv
   from monet.util import options_cems 
   ef, rfignum = options_cems.options_cems_main(options, d1, d2, area, 
                                                 source_chunks, logfile,
                                                svp.ensemble)
##------------------------------------------------------##
## Get observational data
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
                     logfile, rfignum, svp.ensemble) 

##------------------------------------------------------##
# Create CONTROL and SETUP files in subdirectories.
##------------------------------------------------------##
# FILES created
# CONTROL and SETUP and ASCDATA.CFG files in each subdirectory.
# CONTROL files for vmixing. 
# bash script to run HYSPLIT
# bash script to run vmixing
if options.create_runs:
   tcmrun=False
   from monet.util.options_run import options_run_main
   options_run_main(options, d1, d2, source_chunks, tcmrun)


oldrunlist = False
runlist = []
if oldrunlist:
    from monet.util.svhy import create_controls
    from monet.util.svhy import create_vmix_controls
    from monet.util.svhy import RunScript
    from monet.util.svhy import VmixScript
    from monet.util.svhy import DatemScript
    from monet.util.svcems import SourceSummary
    with open(logfile, 'a') as fid:
         fid.write('creating CONTROL files\n')

    if options.neiconfig:
       from monet.util import nei
       from monet.util.svhy import nei_controls
       ns = nei.NeiSummary()
       print('WRITING EIS CONTROLS')
       sss = SourceSummary(fname = options.tag + '.source_summary.csv')
       
       neidf = ns.load(fname = options.tdir + '/neifiles/' + options.neiconfig) 
       #ns.remove_cems(sss.sumdf)
       #ns.print(fname = options.tdir + '/neifiles/CONFIG.NEWNEI')
       neidf = ns.df
       nei_runlist = nei_controls(options.tdir, options.hdir, neidf, d1, d2, source_chunks, options.metfmt,
                    units = options.cunits, tcm=tcmrun)
       #if not nei_runlist:
       #   print('NO CONTROL files for NEI sources ')
       #   #sys.exit()
       #else:
       #   print('Making script for NEI sources ')
       #   print(len(nei_runlist))
       #   rs = RunScript(options.tag + "_nei.sh", nei_runlist, options.tdir)
       #   print('Making DATEM script for NEI sources ')
       #   rs = DatemScript(
       #   options.tag + "_nei_datem.sh", nei_runlist, options.tdir, options.cunits, poll=1
       #   )

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
    #else:
    #    print('Creating batch script for HYSPLIT runs')
    #    rs = RunScript(options.tag + ".sh", runlist, options.tdir)
    #sys.exit()
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
    #else:
    #    rs = VmixScript(options.tag + '.vmix.sh', runlist, options.tdir)
    #    print('creating vmixing CONTROL files created.')

##------------------------------------------------------##
##------------------------------------------------------##
# FILES created
# bash scripts to run c2datem on the results.

if options.write_scripts:
    from monet.util.svhy import VmixScript
    from monet.util.svhy import DatemScript
    from monet.util.svhy import RunScript
    with open(logfile, 'a') as fid:
         fid.write('writing scripts\n')
    print('writing vmix script')
    #if not runlist:
    from monet.util.svhy import create_runlist
    runlist = create_runlist(options.tdir, options.hdir, d1, d2, source_chunks)
    rs = VmixScript(options.tag + '.vmix.sh', runlist, options.tdir)
    rs = RunScript(options.tag + ".sh", runlist, options.tdir)
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
    # 2d histgrams of wind direction 
    vmet = options_vmix.options_vmix_main(options, d1, d2, area, source_chunks,
                                      logfile)
    # if the meto object was created with obs then can compare obserbed met to
    # vmixing met.
    if options.obs: 
        options_vmix.options_vmix_met(options, vmet, meto, logfile)

    #sys.exit()
    #   # this adds met data to the datem file for Nick.
    #   dothis=False 
    #   if dothis:
    #       from monet.util.svresults2 import SVresults
    #       svr = SVresults(options.tdir, orislist=orislist, daterange=[d1, d2])
    #       svr.readc2datem()
    #       svr.add_metobs(vmet.df, orislist=orislist)
    #       datemfile = options.tag + "DATEM.txt"
    #       print("writing datem ", datemfile)
    #       svr.writedatem_enhanced(dfile=datemfile)
       
##------------------------------------------------------##
##------------------------------------------------------##
# Plots of results
##------------------------------------------------------##
if options.results:
    from monet.util import options_model
    from monet.util import nei
    print('OPTIONS RESULTS')
    if not options.vmix==1: 
        #vmet = meto
        vmet = options_vmix.get_vmet(options, d1, d2, area,
                                     source_chunks,logfile)
        print('VMET', vmet)
        vmet.set_geoname(options.tag + '.geometry.csv')
        if options.neiconfig:
          ns = nei.NeiSummary()
          ns.load(options.tdir + 'neifiles/' + options.neiconfig)
          vmet.add_nei_data(ns.df)

    options_model.options_model_main(options, d1, d2, vmet, logfile)


    #sss = SourceSummary(fname= options.tag + '.source_summary.csv')
    #df = sss.load()
    #orislist = sss.check_oris(10)
    #orislist = options.orislist
    #print('ORIS LIST', orislist)
    #sys.exit()
    #svr = DatemOutput(options.tdir, orislist=orislist, daterange=[d1, d2])
    #flist = svr.find_files()
    #svr.create_df(flist)
    #pdf = svr.get_pivot() 
   

    #datemfile = options.tag + "DATEM.txt"
    #print("writing datem ", datemfile)
    ##svr.writedatem(datemfile)
    #svr.fill_hash()
    #print("PLOTTING")
    #svr.plotall()

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


# 0.01 x 0.01 degre area is about 1.23 km^2. 1.23e6m^2
# 50 meter in the vertical gives 6.16e7 m^3.
# Emissions are about 3000 lbs/hour (1360 kg)
# 24,000 particles = 1360 kg
# each particle is 0.056 kg or 56 g.
# 1 particle in a grid square is about 1 ug/m3.
# that doesn't seem great.
# maybe with the hour averaging it is ok?


