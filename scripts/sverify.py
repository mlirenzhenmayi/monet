from optparse import OptionParser
import datetime
import seaborn as sns
import matplotlib.pyplot as plt
#imported in create_map
#import cartopy.crs as ccrs
#import cartopy.feature as cfeature

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
    gl = ax.gridlines(draw_labels=True, linewidth=2, color='gray')
    gl.ylabels_right=False
    gl.xlabels_top = False
    states = cfeature.NaturalEarthFeature(category='cultural',
             name='admin_1_states_provinces_lines', scale='50m',
             facecolor='none')
    ax.add_feature(states, edgecolor='gray')
    ax.add_feature(cfeature.BORDERS)
    ax.add_feature(cfeature.LAKES)
    ax.add_feature(cfeature.RIVERS)
    ax.add_feature(cfeature.COASTLINE)
    return(ax)


parser = OptionParser()

parser.add_option('-a', type="string", dest="state", default="ND",\
                  help='two letter state code (ND)')
parser.add_option('-b', type="string", dest="bounds", default=None,\
                  help='bounding box for data lat:lon:lat:lon \
                  First pair describes lower left corner. \
                  Second pair describes upper right corner.')
parser.add_option('-d', type="string", dest="drange", \
                  default="2106:1:1:2016:2:1", \
                  help='daterange in form YYYY:M:D:YYYY:M:D')
parser.add_option('-y', type="string", dest="hdir", default="", \
                  help='directory path for hysplit')
parser.add_option('-o', type="string", dest="tdir", default="./", \
                  help='directory path for outputs')
parser.add_option('-q', type="int", dest="quiet", default=0, \
                  help='default 0 show all graphs. The graphs will pop up in\
                        groups of 10, \
                        1 only show maps, \
                        2 show no graphs')
parser.add_option('--cems', action="store_true", dest="cems", default=False,\
                  help='Find and plot SO2 emissions')
parser.add_option('--obs', action="store_true", dest="obs", default=False, \
                   help='Find and plot SO2 observations')
parser.add_option('--def', action="store_true", dest="defaults", default=False, \
                   help='write a default CONTROL and SETP file to the top\
                         directory')
parser.add_option('--run', type="string", dest="create_runs", default=None, \
                   help='Use CONTROL and SETUP in top level directory to \
                         write CONTROL and SETUP files in subdirectories which\
                         will call EMITIMES files. Also create bash run script\
                         in top level directory.')
parser.add_option('--results', action="store_true", dest="results",
                   default=False)

##-----##
#parser.add_option('--run', action="store_true", dest="runh", default=False)
#parser.add_option('--map', action="store_true", dest="emap", default=False)
#parser.add_option('--plote', action="store_true", dest="eplot", default=False, \
#                  help='plot emissions')
#parser.add_option('--datem', action="store_true", dest="datem", default=False)
#parser.add_option('--rundatem', action="store_true", dest="rundatem", default=False)
#parser.add_option('--pickle', action="store_true", dest="pickle", default=False)
#parser.add_option('--tcm', action="store_true", dest="tcm", default=False)
#parser.add_option('--test', action="store_true", dest="runtest", default=False)
#parser.add_option('--obs', action="store_true", dest="findobs", default=False)
#parser.add_option('-x', action="store_false", dest="opkl", default=True)
(options, args) = parser.parse_args()

#opkl = options.opkl

temp = options.drange.split(':')
try:
    d1 = datetime.datetime(int(temp[0]), int(temp[1]), int(temp[2]), 0)
except:
    print('daterange is not correct ' + options.drange)
try:
    d2 = datetime.datetime(int(temp[3]), int(temp[4]), int(temp[5]), 0)
except:
    print('daterange is not correct ' + temp)

if options.bounds:
   temp=options.bounds.split(':')
   latll=float(temp[0])
   lonll=float(temp[1])
   latur=float(temp[2])
   lonur=float(temp[3])
   area = (latll, lonll, latur, lonur)

states=[]
if options.state:
   temp=options.state.split(':')
   for tt in temp: 
       states.append(tt.lower())
 
#if options.bounds.lower().strip() == 'nd':
#    area = [44.5,-105.0, 49.5, -97.0]
#    states=['nd']
##else:
#    area = None
#    state=[options.area.strip()]

#sv = SO2Verify([d1,d2], area, state)

##emissions are on order of 1,000-2,000 lbs (about 1,000 kg)
##10,000 particles - each particle would be 0.1 kg or 100g.
##0.05 x 0.05 degree area is about 30.25 km^2. 30.25e6 m^2.
##50 meter in the vertical gives 1.5e9 m^3.
##So 1 particle in a 0.05 x 0.05 degree area is 0.067 ug/m3.
##Need a 100 particles to get to 6.7 ug/m3.
##This seems reasonable.

days=5
##source_chunks specify how many source times go into 
##an emittimes file. They will also determine the directory
##tree structure. Since directories will be according to run start times.
source_chunks = 24*days

##run_duration specifies how long each run lasts.
##the last emissions will occur after the time specified in
##source_chunks, 
##METHOD A
##The run ends at the end of the emittimes file. However,
##a pardump file is generated which is used to initialize the next run.
##
run_duration = 24*(days) + 2
run_duration = source_chunks  
datemchunks = source_chunks
ncycle = source_chunks

##METHOD B
##The run will need to extend beyond this time.
##the amount of observation data in the datem file should match the run time.
#run_duration = 24*(days+2)
#datemchunks = run_duration

##mkdir is a generator
#mkdir = dirtree(options.tdir, d1, d2,  dhour = 24*days)
#for sdir in mkdir:
#    print(sdir)

if options.defaults:
   from monet.util.svhy import default_setup
   from monet.util.svhy import default_control
   default_setup('SETUP.0', options.tdir)
   default_control('CONTROL.0', options.tdir, run_duration, d1)

if options.create_runs:
   from monet.util.svhy import create_controls
   from monet.util.svhy import create_script
   runlist = create_controls(options.tdir, options.hdir, d1, d2, source_chunks)
   create_script(runlist, options.tdir, options.create_runs, write=True)
   #runhandler(runlist, 5, options.tdir)

if options.results:
   from monet.util.svhy import create_runlist
   from monet.util.svhy import results
   runlist = create_runlist(options.tdir, options.hdir, d1, d2, source_chunks)
   results('outfile.txt', runlist)   

rfignum=1
if options.cems:
    from monet.util.svcems import SEmissions
    ef = SEmissions([d1,d2], area, states, tdir=options.tdir)
    ef.find()
    ef.print_source_summary(options.tdir)
    ef.plot(save=True, quiet=options.quiet)
    ef.create_emitimes(ef.d1, schunks=source_chunks, tdir=options.tdir)
    rfignum = ef.fignum 
    if options.quiet==1:
       plt.close('all')
       rfignum=1
    if not options.obs:
        print('map fig number  ' + str(rfignum))
        mapfig = plt.figure(rfignum)
        axmap = create_map(rfignum)
        ef.map(axmap)
        plt.savefig(options.tdir + 'map.jpg')
        if options.quiet<2:
            plt.show()
        
    
if options.obs:
    from monet.util.svobs import SObs
    obs = SObs([d1,d2], area, states, tdir=options.tdir)
    obs.fignum=rfignum
    obs.find(pload=True, tdir=options.tdir)
    obs.obs2datem(d1, ochunks=(source_chunks, run_duration), tdir=options.tdir) 
    obs.plot(save=True, quiet=options.quiet)
    fignum = obs.fignum 
    if options.quiet==1:
       plt.close('all')
       fignum=1
    axmap = create_map(fignum)
    obs.map(axmap)
    print('map fig number  ' + str(fignum))
    if options.cems:
       ef.map(axmap)
    plt.sca(axmap)
    plt.savefig(options.tdir + 'map.jpg')
    if options.quiet<2:
       plt.show()


##------------------------------------------------------##
