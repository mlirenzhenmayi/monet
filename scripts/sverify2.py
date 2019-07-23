from optparse import OptionParser
import datetime
import seaborn as sns
import matplotlib.pyplot as plt
import os
from monet.utilhysplit.hcontrol import NameList
import sys
import pandas as pd

# imported in create_map
# import cartopy.crs as ccrs
# import cartopy.feature as cfeature

"""
INPUTS: Dates to run
        Area to consider emissions from
        list of states to consider emissions from
        top level directories for
            1. code executables
            2. where output should be located.
            3. (optional) where any csv files are with emissions data.

STEPS
A. Preliminary.
1. Find Emission sources.
2. Find measurement stations in area
3. Produce map of sources and measurements.
4. Create plots of emissions vs. time
5. Create plots of measurements vs. time

Method A
1. Find measurement stations with peaks above a certain level
2. Backward trajctories from peaks?
METHOD B
OR just use geometry - every plant within 100 km as a contributer
1.
2.

B.1 trajectory runs

B.2 Dispersion runs
Create HYSPLIT input files and run HYSPLIT
1. Use emissions source to create HYSPLIT sources
TODO - need to be able to specify stack height for each source.
       Stack height for sources not available from current data sources.
       These must be looked up individually.
TODO - resolve ambiguity in local / daylight savings time in the CEMS.
2. Use measurement stations to create concenctration grids
   OR just use a large concentration grid that covers alls stations.
3. Run HYSPLIT.
TODO - should these be unit runs so a TCM can be creatd later or do runs in
some kind of chunks.

C. Evaluate HYSPLIT output and measurements.
1. create dfile (datem file) for the measurements in the HYSPLIT output directories.
TODO check that averaging time of measurements and HYSPLIT matches
2. Run c2datem and collect output from cfiles in each directory.
3. Create a modeled measurements vs. time using the output from c2datem
4. Compare the modeled and measured concentrations.
TODO what kinds of statistics?
5. create plume plots (TO DO)

EPA method code 60  = EQSA-0486-060

##ethresh attribute in Semissions class controls
##when an emitimes file is written (none written if
##emissions for that source don't exceed threshold)

"""


def create_map(fignum):
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    fig = plt.figure(fignum)
    proj = ccrs.PlateCarree()
    ax = plt.axes(projection=proj)
    gl = ax.gridlines(draw_labels=True, linewidth=2, color="gray")
    gl.ylabels_right = False
    gl.xlabels_top = False
    states = cfeature.NaturalEarthFeature(
        category="cultural",
        name="admin_1_states_provinces_lines",
        scale="50m",
        facecolor="none",
    )
    ax.add_feature(states, edgecolor="gray")
    ax.add_feature(cfeature.BORDERS)
    ax.add_feature(cfeature.LAKES)
    ax.add_feature(cfeature.RIVERS)
    ax.add_feature(cfeature.COASTLINE)
    return ax


class ConfigFile(NameList):
    def __init__(self, fname, working_directory="./"):
        self.lorder = None

        super().__init__(fname, working_directory)
        # the following are in the NameList class
        # self.fname
        # self.nlist  # dictionary
        # self.descrip
        # self.wdir   # working directory
        self.runtest = False

        self.bounds = None
        self.drange = "2106:1:1:2016:2:1"
        self.hdir = "./"
        self.tdir = "./"
        self.quiet = 0

        # attributes for CEMS data
        self.cems = True
        self.heat = 0
        self.emit_area = 0
        self.chunks = 5  # number of days in each emittimes file
        self.spnum = True  # different species for MODC flags
        self.byunit = True  # split emittimes by unit
        self.cunits = "PPB"  # ppb or ug/m3
        self.orislist = "None"
        self.cemsource = "api"  # get cems data from API or from ftp download

        # attributes for obs data
        self.obs = True

        self.tag = "test_run"
        self.metfmt = "/pub/archives/wrf27km/%Y/wrfout_d01_%Y%m%d.ARL"

        self.write_scripts = None

        self.create_runs = False
        self.defaults = False
        self.results = False

        # attributes for met data
        self.vmix = 0 

        if os.path.isfile(fname):
            self.read(case_sensitive=False)
            self.hash2att()
            self.fileread = True
        else:
            self.fileread = False



    def _load_descrip(self):
        lorder = []
        sp10 = " " * 11

        hstr = "daterange in form YYYY:M:D:YYYY:M:D"
        self.descrip["DRANGE"] = hstr
        lorder.append("DRANGE")

        hstr = "bounding box for data lat:lon:lat:lon \n"
        hstr += sp10 + "First pair describes lower left corner. \n"
        hstr += sp10 + "Second pair describes upper right corner."
        self.descrip["AREA"] = hstr
        lorder.append("AREA")

        hstr = " path for hysplit executable"
        self.descrip["hysplitdir"] = hstr
        lorder.append("hysplitdir")

        hstr = "top level directory path for outputs"
        self.descrip["outdir"] = hstr
        lorder.append("outdir")

        hstr = "string. run tag for naming output files such as bash scripts."
        self.descrip["tag"] = hstr
        lorder.append("tag")

        hstr = "int 0 - 2. 0 show all graphs. The graphs will pop up in\n"
        hstr += sp10 + "groups of 10, \n"
        hstr += sp10 + "1 only show maps, \n"
        hstr += sp10 + "(2) show no graphs"
        self.descrip["quiet"] = hstr
        lorder.append("quiet")

        self.descrip["CEMS"] = "(False) or True"
        lorder.append("CEMS")

        hstr = (
            "(True) or False. Create different species dependent on MODC flag values."
        )
        self.descrip["Species"] = hstr
        lorder.append("Species")

        hstr = "value to use in heat field for EMITIMES file"
        self.descrip["heat"] = hstr
        lorder.append("heat")

        hstr = "value to use in area field for EMITIMES file"
        self.descrip["EmitArea"] = hstr
        lorder.append("EmitArea")

        hstr = "List of ORIS codes to retrieve data for \n"
        hstr += sp10 + "If this value is not set then data for all ORIS codes found \n"
        hstr += sp10 + "in the defined area will be retrieved.\n"
        hstr += sp10 + "separate multiple codes with : (e.g. 8042:2712:7213)\n"
        self.descrip["oris"] = hstr
        lorder.append("oris")

        hstr = "(True) or False). Create EMITIMES for each unit."
        self.descrip["ByUnit"] = hstr
        lorder.append("ByUnit")

        hstr = "(5) Integer. Number of days in an EMITIMES file."
        self.descrip["emitdays"] = hstr
        lorder.append("emitdays")

        hstr = "(api) Download CEMS data from API or use ftp site. values are api"
        hstr += sp10 + "or ftp"
        self.descrip["cemsource"] = hstr
        lorder.append("cemsource")

        hstr = "(PPB) or ug/m3. If PPB will cause ichem=6 to be set for HYSPLIT runs."
        self.descrip["unit"] = hstr
        lorder.append("unit")

        hstr = "(False) or True. Retrieve AQS data"
        self.descrip["OBS"] = hstr
        lorder.append("OBS")

        hstr = "(False) or True. write a default CONTROL.0 and SETP.0 file to \n"
        hstr += sp10 + "the top level directory"
        self.descrip["DEFAULTS"] = hstr
        lorder.append("DEFAULTS")

        hstr = "(False) or True. Use CONTROL and SETUP in top level directory to\n"
        hstr += sp10 + "write CONTROL and SETUP files in subdirectories which \n"
        hstr += sp10 + "will call EMITIMES files. Also create bash run scripts\n"
        hstr += sp10 + "to run hysplit and then c2datem\n"
        hstr += sp10 + "\n"
        hstr += sp10 + "If a datem file with observations exists in the\n"
        hstr += sp10 + "subdirectories then will also create CONTROL\n"
        hstr += sp10 + "files for vmixing (CONTROL.V(stationid).\n"
        hstr += sp10 + "and will create a script tag.vmix.sh for running\n"
        hstr += sp10 + "vmixing.\n"
        hstr += sp10 + "See the VMIX option for reading vmixing output.\n"
        self.descrip["RUN"] = hstr
        lorder.append("RUN")

        hstr = "Meteorological files to use.\n"
        hstr += sp10 + "Format should use python datetime formatting symbols.\n"
        hstr += sp10 + "Examples:\n"
        hstr += sp10 + "/TopLevelDirectory/wrf27km/%Y/wrfout_d01_%Y%m%d.ARL\n"
        hstr += sp10 + "/TopLevelDirectory/gdas1/gdas1.%b%y.week\n"
        hstr += sp10 + 'use the word "week" to indicate when files are by week\n'
        hstr += sp10 + "week will be replaced by w1, w2, w3... as appropriate.\n"
        self.descrip["metfile"] = hstr
        lorder.append("metfile")

        hstr = "Data from vmixing \n"
        hstr += sp10 + 'if 1 create csv file and plots from vmixing output in\n'
        hstr += sp10 + 'subdirectories'
        self.descrip['vmix'] = hstr
        lorder.append('vmix')

        hstr = "(False) or True. The bash scripts for running HYSPLIT and then \n"
        hstr += sp10 + "c2datem must be run first.\n"
        hstr += sp10 + "reads datem output and creates graphs."
        self.descrip["RESULTS"] = hstr
        lorder.append("RESULTS")

        self.lorder = lorder

    def test(self, key, original):
        if key in self.nlist.keys():
            return self.nlist[key]
        else:
            return original

    def str2bool(self, val):
        if isinstance(val, bool):
            rval = val
        elif "true" in val.lower():
            rval = True
        elif "false" in val.lower():
            rval = False
        else:
            rval = False
        return rval

    def process_cemsource(self):
        cs = self.cemsource
        cs = cs.lower()
        cs = cs.strip()
        if cs not in ["ftp", "api"]:
            print("Source for CEMS data is not valid")
            print("Must choose api or ftp")
            sys.exit()
        return cs

    def process_oris(self):
        return self.orislist.split(":")

    def hash2att(self):
        ## should be all lower case here.
        ## namelist is not case sensitive and
        ## all keys are converted to lower case.

        self.bounds = self.test("area", self.bounds)
        self.drange = self.test("drange", self.drange)
        self.tag = self.test("tag", self.tag)

        self.emit_area = self.test("emitarea", self.emit_area)
        self.emit_area = float(self.emit_area)
        self.heat = self.test("heat", self.heat)
        self.heat = float(self.heat)
        self.cunits = self.test("unit", self.cunits)
        # ------------------------------------------------------
        self.orislist = self.test("oris", self.orislist)
        self.orislist = self.process_oris()
        self.hdir = self.test("hysplitdir", self.hdir)
        self.tdir = self.test("outdir", self.tdir)

        self.quiet = self.test("quiet", self.quiet)
        self.quiet = int(self.quiet)

        self.cemsource = self.test("cemsource", self.cemsource)
        self.cemsource = self.process_cemsource()

        self.chunks = self.test("emitdays", self.chunks)
        self.chunks = int(self.chunks)

        self.write_scripts = self.test("scripts", self.write_scripts)
        self.metfmt = self.test("metfile", self.metfmt)

        self.vmix = self.test('vmix', self.vmix)
        self.vmix = int(self.vmix)
        # booleans
        self.byunit = self.str2bool(self.test("byunit", self.byunit))
        self.spnum = self.str2bool(self.test("species", self.spnum))
        self.cems = self.str2bool(self.test("cems", self.cems))
        self.obs = self.str2bool(self.test("obs", self.obs))
        self.create_runs = self.str2bool(self.test("run", self.create_runs))
        self.results = self.str2bool(self.test("results", self.results))
        self.defaults = self.str2bool(self.test("defaults", self.results))


# options = ConfigFile('CONFIG.S')

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

options = ConfigFile(opts.configfile)

if opts.print_help:
    print("-------------------------------------------------------------")
    print("Configuration file options (key words are not case sensitive)")
    print("-------------------------------------------------------------")
    print(options.print_help(order=options.lorder))
    sys.exit()

if not options.fileread:
    print("configuration file " + opts.configfile + " not found.\ngoodbye")
    sys.exit()


temp = options.drange.split(":")
try:
    d1 = datetime.datetime(int(temp[0]), int(temp[1]), int(temp[2]), 0)
except BaseException:
    print("daterange is not correct " + options.drange)
try:
    d2 = datetime.datetime(int(temp[3]), int(temp[4]), int(temp[5]), 23)
except BaseException:
    print("daterange is not correct " + temp)

# for running with the test.csv file
if options.runtest and options.cems:
    d1 = datetime.datetime(2016, 1, 2, 0)
    d2 = datetime.datetime(2016, 1, 9, 0)

if options.bounds:
    temp = options.bounds.split(":")
    latll = float(temp[0])
    lonll = float(temp[1])
    latur = float(temp[2])
    lonur = float(temp[3])
    area = (latll, lonll, latur, lonur)
else:
    area = None


# for running with the test.csv file
if options.runtest and options.cems:
    latll = 30
    lonll = -80
    latur = 40
    lonur = -100
    area = (latll, lonll, latur, lonur)


# states = []
# if options.state:
#    temp = options.state.split(":")
#    for tt in temp:
#        states.append(tt.lower())

# TO DO should tie numpar to the emissions amount during that time period
# as well as the resolution.
# emissions are on order of 1,000-2,000 lbs/hour (about 1,000 kg)
# 10,000 particles - each particle would be 0.1 kg or 100g.
# 0.05 x 0.05 degree area is about 30.25 km^2. 30.25e6 m^2.
# 50 meter in the vertical gives 1.5e9 m^3.
# So 1 particle in a 0.05 x 0.05 degree area is 0.067 ug/m3.
# Need a 100 particles to get to 6.7 ug/m3.
# This seems reasonable.

# source_chunks specify how many source times go into
# an emittimes file. They will also determine the directory
# tree structure. Since directories will be according to run start times.
days = options.chunks
source_chunks = 24 * days

# run_duration specifies how long each run lasts.
# the last emissions will occur after the time specified in
# source_chunks,
# METHOD A
# The run ends at the end of the emittimes file. However,
# a pardump file is generated which is used to initialize the next run.
##
run_duration = 24 * (days) + 2
run_duration = source_chunks
datemchunks = source_chunks
ncycle = source_chunks

# METHOD B
# The run will need to extend beyond this time.
# the amount of observation data in the datem file should match the run time.
# run_duration = 24*(days+2)
# datemchunks = run_duration

# mkdir is a generator
# mkdir = dirtree(options.tdir, d1, d2,  dhour = 24*days)
# for sdir in mkdir:
#    print(sdir)

if options.defaults:
    from monet.util.svhy import default_setup
    from monet.util.svhy import default_control
    print("writing control and setup")
    # if units='ppb' then ichem=6 is set to output mixing ratios.
    default_setup("SETUP.0", options.tdir, units=options.cunits)
    default_control("CONTROL.0", options.tdir, run_duration, d1, area=area)

if options.results:
    from monet.util.svresults2 import SVresults
    from monet.util.svcems import SourceSummary
    sss = SourceSummary()
    df = sss.load()
    orislist = sss.check_oris(10)
    svr = SVresults(options.tdir, orislist=orislist, daterange=[d1, d2])
    # svr.fill_hash()
    datemfile = options.tag + "DATEM.txt"
    print("writing datem ", datemfile)
    svr.writedatem(datemfile)
    #sys.exit()
    svr.fill_hash()
    print("PLOTTING")
    svr.plotall()

vmetdf = pd.DataFrame()
if options.vmix==1:
   from monet.util.svhy import read_vmix
   from monet.util.svobs import SObs
   from monet.util.svobs import vmixing2metobs
   df = read_vmix(options.tdir, d1, d2, source_chunks, sid=None)

   if not df.empty:
      # start getting obs data to compare with.
      obs = SObs([d1, d2], area, tdir=options.tdir)
      obs.find(tdir=options.tdir, test=options.runtest, units=options.cunits)
      #met = obs.met

      vmet = vmixing2metobs(df,obs.obs)
      sites = vmet.get_sites()
      pstr=''
      for sss in sites:
           pstr += str(sss) + ' ' 
      print('Plotting met data for sites ' + pstr)
      quiet=True
      if options.quiet < 2:
          quiet=False
      vmet.plot_ts(quiet=quiet, save=True) 
      vmet.nowarning_plothexbin(quiet=quiet, save=True) 
      vmet.to_csv(options.tdir, csvfile = 'vmixing.' + options.tag + '.csv')
      vmetdf = vmet.df
   else:
      print('No vmixing data available')

rfignum = 1
if options.cems:
    from monet.util.svcems import SEmissions

    print(options.orislist[0])
    if options.orislist[0] != "None":
        alist = options.orislist
        byarea = False
    else:
        alist = area
        byarea = True
    ef = SEmissions(
        [d1, d2],
        alist,
        area=byarea,
        tdir=options.tdir,
        spnum=options.spnum,
        tag=options.tag,
        cemsource=options.cemsource,
    )
    ef.find()
    if options.quiet == 0:
        ef.nowarning_plot(save=True, quiet=False)
    else:
        ef.nowarning_plot(save=True, quiet=True)
    ef.create_emitimes(
        ef.d1,
        schunks=source_chunks,
        tdir=options.tdir,
        unit=options.byunit,
        heat=options.heat,
        emit_area=options.emit_area,
    )
    rfignum = ef.fignum
    if options.quiet == 1:
        plt.close("all")
        rfignum = 1
    if not options.obs:
        print("map fig number  " + str(rfignum))
        mapfig = plt.figure(rfignum)
        axmap = create_map(rfignum)
        ef.map(axmap)
        plt.savefig(options.tdir + "map.jpg")
        if options.quiet < 2:
            plt.show()

if options.obs:
    import sys
    from monet.util.svobs import SObs

    obs = SObs([d1, d2], area, tdir=options.tdir)
    obs.fignum = rfignum
    obs.find(tdir=options.tdir, test=options.runtest, units=options.cunits)
    meto = obs.get_met_data()
    meto.to_csv(options.tdir, csvfile = obs.csvfile)
    
    obs.obs2datem(d1, ochunks=(source_chunks, run_duration), tdir=options.tdir)

    ################################################################################ 
    # output file with distances and directons from power plants to aqs sites.
    obsfile = obs.csvfile
    sumfile = "source_summary.csv"
    cemsfile = options.tag + ".cems.csv"
    t1 = os.path.isfile(obsfile)
    t2 = os.path.isfile(sumfile)
    t3 = os.path.isfile(cemsfile)
    if t1 and t2 and t3:
        from monet.util.svresults2 import CemsObs
        from monet.util.svresults2 import gpd2csv
        cando = CemsObs(obsfile, cemsfile, sumfile)
        osum, gsum = cando.make_sumdf()
        gpd2csv(osum, "geometry.csv")
    ################################################################################ 

    obs.plot(save=True, quiet=options.quiet)
    fignum = obs.fignum
    if options.quiet == 1:
        plt.close("all")
        fignum = 1
    axmap = create_map(fignum)
    obs.map(axmap)
    print("map fig number  " + str(fignum))
    if options.cems:
        ef.map(axmap)
    plt.sca(axmap)
    plt.savefig(options.tdir + "map.jpg")
    if options.quiet < 2:
        plt.show()
    else:
       plt.close('all')
    sites = meto.get_sites()
    pstr=''
    for sss in sites:
        pstr += str(sss) + ' ' 
    print('Plotting met data for sites ' + pstr)
  
    if options.quiet < 2:
        meto.nowarning_plothexbin(quiet=False, save=True)
    else:
        meto.nowarning_plothexbin(quiet=True, save=True)
   
    plt.close('all')
    
    # compare vmixing output with met data from AQS. 
    if not vmetdf.empty and not meto.df.empty:
       from monet.util.svobs import metobs2matched
       mdlist = metobs2matched(vmetdf, meto.df)
       fignum=10
       for md in mdlist:
           print('MATCHED DATA CHECK')
           print(md.stn)
           print(md.obsra[0:10])
           print('---------------------')
           
           fig = plt.figure(fignum)
           ax = fig.add_subplot(1,1,1)
           md.plotscatter(ax)
           save_str = str(md.stn[0]) + '_' + str(md.stn[1])
           plt.title(save_str)
           plt.savefig(save_str + '.jpg')
           fignum+=1
           if str(md.stn[1])=='WDIR' or str(md.stn[1])=='WS':
              fig = plt.figure(fignum)
              ax = fig.add_subplot(1,1,1)
              wdir=False
              if md.stn[1] == 'WDIR': wdir=True
              md.plotdiff(ax, wdir=wdir)
              save_str = 'TS_' + str(md.stn[0]) + '_' + str(md.stn[1])
              plt.savefig(save_str + '.jpg')
              fignum+=1
       if options.quiet < 2: 
          plt.show()
       else:
          plt.close()





runlist = []
if options.create_runs:
    from monet.util.svhy import create_controls
    from monet.util.svhy import create_vmix_controls
    from monet.util.svhy import RunScript
    from monet.util.svhy import VmixScript

    print('Creating CONTROL files')
    runlist = create_controls(
        options.tdir,
        options.hdir,
        d1,
        d2,
        source_chunks,
        options.metfmt,
        units = options.cunits
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


if options.write_scripts:
    from monet.util.svhy import DatemScript

    if not runlist:
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
