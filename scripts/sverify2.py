from optparse import OptionParser
import datetime
import seaborn as sns
import matplotlib.pyplot as plt
import os
from monet.utilhysplit.hcontrol import NameList
import sys

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

          # self.fname
          # self.nlist  # dictionary
          # self.descrip
          # self.wdir   # working directory
          self.runtest = False

          self.bounds = None
          self.drange = "2106:1:1:2016:2:1",
          self.hdir = './'
          self.tdir = './'
          self.quiet = 0           

          # attributes for CEMS data
          self.cems = True
          self.heat = 0
          self.chunks = 5        # number of days in each emittimes file
          self.spnum = True      # different species for MODC flags
          self.byunit = True     # split emittimes by unit
          self.cunits = 'PPB'    # ppb or ug/m3

          # attributes for obs data
          self.obs = True

          self.tag = 'test_run'         
 
          self.create_runs = False
          self.defaults = False
          self.results = False
          
          self.read(case_sensitive=False)
          self.hash2att()

          

    def _load_descrip(self):
        lorder = []
        sp10 = ' ' * 11

        hstr = "daterange in form YYYY:M:D:YYYY:M:D"
        self.descrip['DRANGE'] = hstr
        lorder.append('DRANGE')

        hstr="bounding box for data lat:lon:lat:lon \n"
        hstr+=sp10+ "First pair describes lower left corner. \n"
        hstr+=sp10+ "Second pair describes upper right corner."
        self.descrip['AREA'] = hstr
        lorder.append('AREA')

        hstr = ' path for hysplit executable'
        self.descrip['hysplitdir'] = hstr
        lorder.append('hysplitdir')

        hstr = 'top level directory path for outputs'
        self.descrip['outdir'] = hstr
        lorder.append('outdir')
    
        hstr = 'string. run tag for naming output files such as bash scripts.'
        self.descrip['tag'] = hstr
        lorder.append('tag')

        hstr="int 0 - 2. 0 show all graphs. The graphs will pop up in\n"
        hstr += sp10 + "groups of 10, \n"
        hstr += sp10 + "1 only show maps, \n"
        hstr += sp10 + "(2) show no graphs"
        self.descrip['quiet'] = hstr
        lorder.append('quiet')


        self.descrip['CEMS'] = '(False) or True'
        lorder.append('CEMS')

        hstr="(True) or False. Create different species dependent on MODC flag values."
        self.descrip['Species'] = hstr
        lorder.append('Species')
  
        hstr="value to use in heat field for EMITIMES file"
        self.descrip['heat'] = hstr
        lorder.append('heat')

        hstr="(True) or False). Create EMITIMES for each unit."
        self.descrip['ByUnit'] = hstr
        lorder.append('ByUnit')
       
        hstr="(5) Integer. Number of days in an EMITIMES file."
        self.descrip['emitdays'] = hstr
        lorder.append('emitdays')

        hstr="(PPB) or ug/m3. If PPB will cause ichem=6 to be set for HYSPLIT runs."
        self.descrip['unit'] = hstr
        lorder.append('unit')

        hstr= '(False) or True. Retrieve AQS data'
        self.descrip['OBS'] = hstr
        lorder.append('OBS')

        hstr="(False) or True. write a default CONTROL.0 and SETP.0 file to \n"
        hstr += sp10 + "the top level directory"
        self.descrip['DEFAULTS'] = hstr
        lorder.append('DEFAULTS')

        hstr="(False) or True. Use CONTROL and SETUP in top level directory to\n" 
        hstr+=sp10 + "write CONTROL and SETUP files in subdirectories which \n"
        hstr+=sp10 + "will call EMITIMES files. Also create bash run scripts\n"
        hstr+=sp10 + "to run hysplit and then c2datem"
        self.descrip['RUN'] = hstr
        lorder.append('RUN')

        hstr="(False) or True. The bash scripts for running HYSPLIT and then \n"
        hstr += sp10 + "c2datem must be run first.\n" 
        hstr+=sp10 + "reads datem output and creates graphs."
        self.descrip['RESULTS'] = hstr
        lorder.append('RESULTS')

        self.lorder = lorder

    def test(self, key, original):
        if key in self.nlist.keys():
           return self.nlist[key]
        else:
           return original

    def str2bool(self,val):
        if isinstance(val, bool):
            rval = val
        elif 'true' in val.lower(): 
            rval =  True
        elif 'false' in  val.lower(): 
            rval = False
        else:
            rval = False
        return rval
 
    def hash2att(self):
        self.bounds = self.test('area', self.bounds)
        self.drange = self.test('drange', self.drange)
        self.tag = self.test('tag',self.tag)

        self.heat = self.test('heat', self.heat)
        self.heat = float(self.heat)
        self.cunits = self.test('unit',self.cunits)
        
        self.hdir = self.test('hysplitdir', self.hdir)
        self.tdir = self.test('outdir', self.tdir)
        self.quiet = self.test('quiet', self.quiet)
        self.quiet = int(self.quiet)
     
        self.chunks = self.test('emitdays', self.chunks)
        self.chunks = int(self.chunks)

        # booleans
        self.byunit = self.str2bool(self.test('ByUnit', self.byunit))
        self.spnum = self.str2bool(self.test('Species', self.spnum))
        self.cems = self.str2bool(self.test('cems', self.cems))
        self.obs = self.str2bool(self.test('obs', self.obs))
        self.create_runs = self.str2bool(self.test('run', self.create_runs))
        self.results = self.str2bool(self.test('results', self.results))


#options = ConfigFile('CONFIG.S')

parser = OptionParser()
#parser.add_option(
#    "-a", type="string", dest="state", default="ND", help="two letter state code (ND)"
#)
parser.add_option(
    "-i",
    type="string",
    dest="configfile",
    default='CONFIG.S',
    help="Name of configuration file"
)
parser.add_option(
    "-p",
    action="store_true",
    dest="print_help",
    default=False,
    help="Print help for configuration file"
)

(opts, args) = parser.parse_args()

options = ConfigFile(opts.configfile)

if opts.print_help:
   print(options.print_help(order=options.lorder))
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

print('AREA in sverify', area)

#states = []
#if options.state:
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

    # if units='ppb' then ichem=6 is set to output mixing ratios.
    default_setup("SETUP.0", options.tdir, units=options.cunits)
    default_control("CONTROL.0", options.tdir, run_duration, d1, area=area)

if options.create_runs:
    from monet.util.svhy import create_controls
    from monet.util.svhy import create_script

    runlist = create_controls(
        options.tdir, options.hdir, d1, d2, source_chunks, units=options.cunits
    )
    create_script(
        runlist, options.tdir, options.tag, units=options.cunits, write=True
    )
    # runhandler(runlist, 5, options.tdir)

if options.results:
    from monet.util.svhy import create_runlist
    from monet.util.svresults import results
    from monet.util.svresults import CemsObs
    from monet.util.svresults import gpd2csv

    runlist = create_runlist(options.tdir, options.hdir, d1, d2, source_chunks)
    results("outfile.txt", runlist)

rfignum = 1
if options.cems:
    from monet.util.svcems import SEmissions

    ef = SEmissions([d1, d2], area,  tdir=options.tdir, spnum=options.spnum)
    ef.find()
    if options.quiet ==0: 
        ef.nowarning_plot(save=True, quiet=False)
    ef.create_emitimes(
        ef.d1, schunks=source_chunks, tdir=options.tdir, unit=options.byunit,
                       heat=options.heat
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

    obs = SObs([d1, d2], area,  tdir=options.tdir)
    obs.fignum = rfignum
    obs.find(pload=True, tdir=options.tdir, test=options.runtest,
              units=options.cunits)
    try:
        obs.check()
    except BaseException:
        print("No met data for stations.")
    # sys.exit()
    obs.obs2datem(d1, ochunks=(source_chunks, run_duration), tdir=options.tdir)


    # output file with distances and directons from power plants to aqs sites.
    obsfile = obs.csvfile
    sumfile = 'source_summary.csv'
    cemsfile = 'cems.csv'
    t1 = os.path.isfile(obsfile)
    t2 = os.path.isfile(sumfile)
    t3 = os.path.isfile(cemsfile)
    if t1 and t2 and t3:
          from monet.util.svresults import CemsObs
          from monet.util.svresults import gpd2csv
          cando = CemsObs(obsfile, cemsfile, sumfile)
          osum, gsum = cando.make_sumdf()
          gpd2csv(osum, 'geometry.csv')

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




##------------------------------------------------------##
