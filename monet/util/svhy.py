# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import numpy as np
import datetime
import time
import os
from os import path, chdir
from subprocess import call
import pandas as pd
#from arlhysplit.process import is_process_running
#from arlhysplit.process import ProcessList
from monet.util.hcontrol import HycsControl
from monet.util.hcontrol import Species
from monet.util.hcontrol import ConcGrid
from monet.util.hcontrol import NameList
from monet.util.hcontrol import writelanduse

"""
NAME: ashfall_base.py
UID: r100
PRGMMR: Alice Crawford  ORG: ARL  
This code written at the NOAA  Air Resources Laboratory
ABSTRACT: This code manages HYSPLIT runs for Hanford resuspension project.
CTYPE: source code

List of classes and functions in this file:

class RunParams - defines critical parameters for each run number.

-------------------------------------------------------------------------------
functions to create directory tree based on date and to get directory from date.
-------------------------------------------------------------------------------
function get_vlist
function date2dir

-------------------------------------------------------------------------------
functions and classes to create source locations.
-------------------------------------------------------------------------------
function make_sourceid - creates string from lat lon point. 
class Source  - Helper class which stores information about a source.
function source_generator (generator function) - returns a Source object
function get_landuse_sources - returns list of tuples (lat, lon) of sources which have land
                               use of 2,3 or 8 (dryland cropland, irrigated cropland, shrubland)

-------------------------------------------------------------------------------
functions and classes to create CONTROL and SETUP files
-------------------------------------------------------------------------------
function add_psizes - defines ash particle sizes and densities to be used.
function make_setup - creates SETUP.CFG needed as input to  HYSPLIT.
function getmetfiles - returns directory and name of WRF ARL files which are needed for each run.
function add_pterm_grid - add an extra concentration grid for terminating particles.
class Station - helper class which contains information about location for concentration 
function stations_info - returns a Station object.

-------------------------------------------------------------------------------
Main functions
-------------------------------------------------------------------------------

function mult_run - main function for making multiple HYSPLIT runs.

"""
def source_generator(df, area=1, altitude=10):
    """df is a pandas dataframe with index being release date and column headers showing
       location of release and values are emission rates"""
    locs = df.columns.values
    for index, row in df.iterrows(): 
        for vals in zip(locs, row):
            rate = vals[1]
            center = vals[0]
            date = index
            yield  Source(center, altitude, area, rate, date)


##------------------------------------------------------------------------------------##
##------------------------------------------------------------------------------------##
###The following functions and classes define the sources used  
## make_sourceid, Source, source_generator 
##source_generator can easily be modified to produce different sources.
##------------------------------------------------------------------------------------##
##------------------------------------------------------------------------------------##


def make_sourceid(lat, lon):
        """Returns string for identifying lat lon point"""
        latstr = str(abs(int(round(lat*100))))
        lonstr = str(abs(int(round(lon*100))))
        return latstr + '_' + lonstr


def default_landuse(landusedir, tdirpath):
    writelanduse(landusedir=landusedir , working_directory=tdirpath)


def default_setup(setupname='SETUP.CFG',  wdir='./' ):
        """writes the SETUP file which is needed to run HYSPLIT.
           input rhash iu a RunParams object.
        """
        hrs = 5*24
        pardumpname='PARDUMP'
        parinitname='PARINIT'
        namelist={}
        #namelist['delt'] =  rhash.delt          #fix time step.
        namelist['initd'] = '0'                  #particle is 0  and puff is 3.
        namelist['maxdim'] = '1'           
        namelist['kmix0'] = '250'                #default value is 250. controls minimum mixing depth.
        namelist['kblt'] =  '2'                  #Use Kantha Clayson for vertical mixing. 
        namelist['kbls'] =  '1'
        namelist['numpar'] =  '10000'      #number of particles/puffs to release per hour.
        namelist['maxpar'] =  '100000'       #maximum number of particles/puffs to simulate

        ##The pardump file can be used to restart HYSPLIT if it crashes. Although the runs
        ##are short enough in this application that rather than restart a run, we would just re-run it.
        #namelist['NDUMP'] = str(int(hrs))                #create pardump file after this many hours.
        #namelist['NCYLC'] = str(int(hrs))                #add to pardump file every ncycl hours.
        namelist['POUTF'] = '"' + pardumpname + '"'     #name of pardump file
        namelist['PINPF'] = '"' + parinitname + '"'     #name of pardump file

        ##The termination grid is set in the function add_pterm_grid
        #namelist['ptrm'] = '0'                   #terminate particle outside of concentration grids
        #namelist['nbptyp'] = 1        #number of sub bins for each particle size.
  
        ## THIS IS NO LONGER USED.
        #namelist['p10f'] = rhash.p10f            #determines mass flux relationship in p10f to use
        #namelist['ichem'] = rhash.ichem          #resuspension run.

        nl = NameList(setupname, working_directory=wdir)
        nl.add_n(namelist)
        nl.write()


def roundtime(dto):
    """rounds input datetime to day at 00 H"""
    #return datetime.datetime(dto.year, dto.month, dto.day, 0, 0)
    return datetime.datetime(dto.year, dto.month, dto.day, 0, 0)
    

def getmetfiles(sdate, runtime, verbose=False, warn_file = 'MetFileWarning.txt', met_type='wrf27',  
                mdir='./', altdir='./'):
    '''Input start date and run time and returns list of tuples - (meteorological file directory, meteorological files)
       to use for HYSPLIT run.
       INPUTS:
       sdate : start date (datetime object)
       runtime : in hours
       verbose : print out extra messages if True
       met_type : always WRF for this project
       mdir : directory where met files should be accessed from
       altdir : directory where met files may be stored. If they do not exist in mdir, then the routine will look in
                the altdir and copy them to the mdir.

       OUTPUT:
       List of tuples with (met dir, met filename)    
       If the met files cannot be found in the mdir or the altdir then
    '''
    verbose=True
    mdirbase = mdir.strip()
    if mdirbase[-1] != '/': mdirbase += '/'
    dt =datetime.timedelta(days=1)
    mfiles=[]
    mdirlist = []
    sdate = sdate.replace(tzinfo=None)
    if runtime < 0:
       runtime = abs(runtime)
       end_date = sdate
       sdate = (end_date - datetime.timedelta(hours=runtime))
    else:
       end_date = (sdate +  datetime.timedelta(hours=runtime))
    edate = sdate
    notdone=True
    if verbose: print('GETMET', sdate, edate, end_date, runtime)
    zzz=0
    while notdone:
        yr = edate.strftime("%Y")
        if met_type=='ERA5':
            fmt =      'ERA5_%Y%m.ARL'  
            temp =  edate.strftime(fmt)
            edate = edate + datetime.timedelta(hours=24)
        elif met_type=='wrf27':
            fmt = 'wrfout_d01_%Y%m%d.ARL'
            temp =  edate.strftime(fmt)
            mdir = mdirbase +  yr + '/'
            edate = edate + datetime.timedelta(hours=24)
        else: temp='none'
        if not path.isfile(mdir + temp):
            print('WARNING', mdir + temp,  ' meteorological file does not exist')  
            with open(warn_file, 'a') as fid:
                 fid.write('WARNING ' + mdir + temp + ' meteorological file does not exist\n') 
        else:
           mfiles.append(temp) 
           mdirlist.append(mdir)
           if verbose: print('Adding',  temp, ' meteorological file')  
        if verbose: print(edate, end_date)
        if edate > end_date:
            notdone=False 
        if zzz>12:
            notdone=False
            print('WARNING: more than 12 met files')
        zzz+=1
    #return mdir, mfiles
    return list(zip(mdirlist, mfiles))


def default_control(name, tdirpath, runtime, sdate):
    cdiff = 0.05
    span = 20
    sample_start = "00 00 00 00" 
    ztop = 10000
    lat = 47
    lon = -101
    control=HycsControl(fname=name, working_directory=tdirpath)
    control.add_duration(runtime)
    control.add_sdate(sdate)
    control.add_ztop(ztop)
    control.add_vmotion(0)
    control.add_metfile('./', 'metfilename')
  
    cgrid = ConcGrid("junkname", levels=[20,50,100,150,175,225,300],
                     centerlat=lat, centerlon=lon,
                     latdiff = cdiff, londiff= cdiff,
                     latspan=span, lonspan = span,
                     sampletype=0, interval =(1,0), sample_start = sample_start) 
    control.add_cgrid(cgrid) 
    ##TO DO check webdep for so2
    vel = "0.0 64.0 0.0 1.9 1.24e5" #this is dry deposition parameters
    particle = Species('so2a' , psize=0, rate=1, duration=1, wetdep=0, vel=vel,
                       density=0, shape=0)
    control.add_species(particle)
    control.add_location(latlon=(46,-105), alt=200, rate = 0, area=0) 
    control.write()
    print('WROTE ' + tdirpath + name)




def create_runlist(tdirpath, hdirpath, sdate, edate, timechunks, 
                   bg=True):
    """
    read the base control file in tdirpath CONTROL.0
    read the base SETUP.0 file in tdirpath
    walk through all subdirectories in tdirpath.
    For each file with  EMIT as part of the filename
        1. read the file and get number of records in each cycle.
        2. take the suffix from the file
    return list of RunDescriptor objects
    tdirpath: str
              top level directory for output.
    tdirpath: str
              directory for hysplit executable
    sdate : datetime object
    edate : datetime object
    timechunks : integer
            run duration.
    """
    from os import walk
    from monet.util import emitimes 
    #from arlhysplit.runh import getmetfiles
    from monet.util.svdir import date2dir

    dstart = sdate
    dend = edate
    ##determines meteorological files to use.

    runlist = []
    hysplitdir = hdirpath + '/exec/'

    iii=0
    for (dirpath, dirnames, filenames) in walk(tdirpath):
        #print(dirpath, dirnames, filenames)
        for fl in filenames:
            if iii==0: firstdirpath = dirpath

            if 'EMIT' in fl: 
                #print(dirpath, dirnames, filenames)
                #print(fl)   
                et = emitimes.EmiTimes(filename=dirpath+'/' + fl) 
                et.read_file()
                #print('NRECS', nrecs)
                #sys.exit()
                sdate = et.cycle_list[0].sdate
                if sdate < dstart or sdate > dend: 
                   continue
                suffix = fl[4:8]
                wdir=dirpath
                if dirpath == firstdirpath:
                    parinit =(None, None, None)
                else:
                    pdate = sdate - datetime.timedelta(hours=timechunks)
                    pdir = date2dir(tdirpath, pdate, dhour=timechunks)
                    parinitA = 'PARDUMP.' + suffix
                    parinitB = 'PARINIT.' + suffix
                    parinit = (pdir, parinitA, parinitB)
                run = RunDescriptor(wdir, suffix, hysplitdir,\
                      'hycs_std', parinit) 
                wr='a'
                if iii==0: wr='w'
                #with open(tdirpath + '/' +  scr, wr) as fid:
                # fid.write(run.script())
                # fid.write('\n\n')
                runlist.append(run)
                iii+=1
    return runlist



def create_controls(tdirpath, hdirpath, sdate, edate, timechunks, 
                   bg=True):
    """
    read the base control file in tdirpath CONTROL.0
    read the base SETUP.0 file in tdirpath
    walk through all subdirectories in tdirpath.
    For each file with  EMIT as part of the filename
        1. read the file and get number of records in each cycle.
        2. take the suffix from the file
        3. Print out a CONTROL file with same suffix and
              1. duration set by timechunks input
              2. number of starting locations matching the EMITIMES file
              3. start date matching EMITIMES file.
              4. meteorological files matching the dates              
        4. Print out a SETUP file with same suffix and
              1. initialized with parinit file from previous time period.
              2. output pardump file with same suffix at end of run.
              3. set ninit to 1.
              4. set delt=5 (TO DO- why?) 
        5. write out landuse file
        6. write script in tdirpath for running HYSPLIT.

    tdirpath: str
              top level directory for output.
    tdirpath: str
              directory for hysplit executable
    sdate : datetime object
    edate : datetime object
    timechunks : integer
            run duration.
    """
    from os import walk
    from monet.util import emitimes 
    #from arlhysplit.runh import getmetfiles
    from monet.util.svdir import dirtree
    from monet.util.svdir import date2dir

    dstart = sdate
    dend = edate
    ##determines meteorological files to use.
    met_type='wrf27'
    mdir='/pub/archives/wrf27km/' 

    runlist = []
    hysplitdir = hdirpath + '/exec/'
    landusedir = hdirpath + '/bdyfiles/'

    base_control = HycsControl(fname='CONTROL.0', working_directory=tdirpath) 
    base_setup = NameList('SETUP.0', working_directory=tdirpath)    
    dtree = dirtree(tdirpath, sdate, edate, chkdir=False, dhour=timechunks) 
    iii=0
    for (dirpath, dirnames, filenames) in walk(tdirpath):
        #print(dirpath, dirnames, filenames)
        for fl in filenames:
            if iii==0: firstdirpath = dirpath
            if 'EMIT' in fl: 
                print(dirpath, dirnames, filenames)
                print(fl)   
                suffix = fl[4:8]
                wdir=dirpath

                ##read emitfile and modify number of locations
                et = emitimes.EmiTimes(filename=dirpath+'/' + fl) 
                et.read_file()
                print(str(et.ncycles)) 
                nrecs = et.cycle_list[0].nrecs
                #print('NRECS', nrecs)
                #sys.exit()
                sdate = et.cycle_list[0].sdate
                ##if sdate not within range given,
                ##then skip the rest of the loop.
                if sdate < dstart or sdate > dend: 
                   continue
                lat=et.cycle_list[0].recordra[0].lat
                lon=et.cycle_list[0].recordra[0].lon

                ##Write a setup file for this emitimes file 
                setupfile = NameList('SETUP.0', working_directory=tdirpath)    
                setupfile.read() 
                setupfile.add('EFILE', '"' + fl + '"')
                setupfile.add('NDUMP', str(timechunks))
                setupfile.add('NCYCL', str(timechunks))
                setupfile.add('POUTF', '"PARDUMP.' + suffix + '"')
                setupfile.add('PINPF', '"PARINIT.' + suffix + '"')
                setupfile.add('NINIT', '1')
                setupfile.add('DELT', '5')
                setupfile.rename('SETUP.' + suffix, working_directory=wdir+'/')
                setupfile.write(verbose=True)
             
                ##Write a control file for this emitimes file 
                control = HycsControl(fname='CONTROL.0', working_directory=tdirpath) 
                control.read()
                control.date = sdate
                ##remove all the locations first and then add
                ##locations that correspond to emittimes file.
                control.remove_locations()
                nlocs = control.nlocs
                while nlocs != nrecs:
                     if nlocs < nrecs:
                        control.add_location(latlon=(lat,lon))
                     if nlocs > nrecs:
                        control.remove_locations(num=0)        
                     nlocs = control.nlocs
                control.rename('CONTROL.' + suffix, working_directory=wdir)
                control.remove_metfile(rall=True)
                ###Add the met files.
                mfiles = getmetfiles(control.date, timechunks, met_type=met_type, mdir=mdir)
                for mf in mfiles:
                    if os.path.isfile(mf[0] + mf[1]):
                       control.add_metfile(mf[0], mf[1])
                for cg in control.concgrids:
                    cg.outfile += '.' + suffix
                    ##not a good way to find center because
                    ##want grids of all the files to be the same so they can be
                    ##added
                    #cg.centerlat = lat
                    #cg.centerlon = lon
                control.write()
                writelanduse(landusedir=landusedir , working_directory=wdir + '/')

                with open(wdir + '/rundatem.sh', 'w') as fid:
                     fid.write('MDL=' + hysplitdir + '\n')
                     fid.write('mult=1e9 #emission in kg' + '\n')
                     fid.write(statmainstr())

                if dirpath == firstdirpath:
                    parinit =(None, None, None)
                else:
                    pdate = sdate - datetime.timedelta(hours=timechunks)
                    pdir = date2dir(tdirpath, pdate, dhour=timechunks)
                    parinitA = 'PARDUMP.' + suffix
                    parinitB = 'PARINIT.' + suffix
                    parinit = (pdir, parinitA, parinitB)
                run = RunDescriptor(wdir, suffix, hysplitdir,\
                      'hycs_std', parinit) 
                wr='a'
                if iii==0: wr='w'
                #with open(tdirpath + '/' +  scr, wr) as fid:
                # fid.write(run.script())
                # fid.write('\n\n')
                runlist.append(run)
                iii+=1
    return runlist

def results(dfile, runlist):
    from monet.util.datem import read_dataA
    from monet.util.datem import frame2datem
    import matplotlib.pyplot as plt
    df = pd.DataFrame()
    nnn=0
    for run in runlist:
        fname = run.directory + '/dataA.txt'
        tempdf = read_dataA(fname)
        if nnn==0 and not tempdf.empty:
           df = tempdf.copy()
           nnn+=1
        elif not tempdf.empty:
           df = pd.merge(df, tempdf, how='outer')
        elif tempdf.empty:
           print('-----------------------------')
           print('WARNING: svhy.py results method empty dataframe')
           print(fname)
           print('-----------------------------')
    df['duration'] = "0100"
    df['altitude'] = 20
    print(df[0:10])
    #frame2datem(dfile, df, cnames=['date','duration','lat', 'lon',
    #                        'obs','model','sid','altitude'] )
    for site in df['sid'].unique():
        dfile2 = str(site) + '.' + dfile 
        dftemp = df[df['sid']==site]
        dftemp.set_index('date', inplace=True)
        dftemp = dftemp.resample('H').asfreq()
        dftemp['obs'].fillna(0, inplace=True)
        dftemp['model'].fillna(0, inplace=True)
        dftemp['duration'].fillna(method='bfill', inplace=True)
        dftemp['lat'].fillna(method='bfill', inplace=True)
        dftemp['lon'].fillna(method='bfill', inplace=True)
        dftemp['sid'].fillna(method='bfill', inplace=True)
        dftemp['altitude'].fillna(method='bfill', inplace=True)
        dftemp.reset_index(inplace=True)
        #print(dftemp[0:10])
        #frame2datem(dfile2, dftemp, cnames=['date','duration','lat', 'lon',
        #                    'obs','model','sid','altitude'] )
         
        dftemp.set_index('date', inplace=True)
        obs= dftemp['obs']
        model = dftemp['model']
        plt.plot(obs,'--r')
        plt.plot(model,'--k')
        plt.title(str(site))
        plt.show()


def statmainstr():
    """returns string to create_script for
       running conmerge, c2datem and statmain.
    """
    csum = 'cdump.sum'
    datem = 'datem.txt'
    model = 'model.txt' 
    rstr = 'ls cdump.???? > mergefile \n'
    rstr += '$MDL/conmerge -imergefile -o' + csum + '\n'
    rstr += '$MDL/c2datem -i' + csum + ' -m' + datem +  ' -o' + model + \
            ' -xi -z1 -c$mult \n'
    rstr += '$MDL/statmain -d' + datem + ' -r' + model + ' -o\n\n'
    return rstr 


def create_script(runlist, tdirpath, scriptname,write=True):
    """
    Creates bash script which will 
    1. Copy pardump files for use as parinit files
    2. run HYSPLIT
    3. run conmerge merge cdump files from different power plants
    4. run c2datem to extract concentrations at stations
    5. run statmain to create file with concentrations and obs. 
    runlist : list of RunDescriptor objects
    tdirpath : string
               top directory path.

    """
    scr = scriptname
    logfile= tdirpath + 'runlogfile.txt'
    iii=0
    prev_directory = 'None'
    rstr=''
    rstr='MDL=' + runlist[0].hysplitdir + '\n'
    rstr+= 'mult=1e9 #emissions are in kg and measurements are in ug\n\n #-------------------\n'
    dstr = rstr
    for run in runlist:
        if run.directory != prev_directory: 
           if iii!=0:
              rstr += 'wait' + '\n\n'
              rstr += 'echo "Finished ' +  prev_directory + '"  >> ' + logfile
              rstr += '\n\n'
              #rstr += statmainstr()
              dstr += statmainstr()
              rstr += '#-----------------------------------------\n' 
           rstr += 'cd ' + run.directory  + '\n\n'
           dstr += 'cd ' + run.directory  + '\n\n'
        ##add line to copy PARDUMP file from one directory to PARINIT file 
        ##in working directory
        if run.parinitA != 'None':
            rstr += 'cp ' + run.parinit_directory +  run.parinitA 
            rstr += ' ' + run.parinitB  + '\n'
        rstr += '${MDL}' +  run.hysplit_version + ' '  + run.suffix 
        rstr += ' & \n'
        prev_directory=run.directory
        iii+=1
    rstr += statmainstr()
    dstr += statmainstr()
    if write:
        with open(tdirpath + '/' +  scr, 'w') as fid:
            fid.write(rstr)
        with open(tdirpath + '/datem_' +  scr, 'w') as fid:
            fid.write(dstr)
    return rstr

class RunDescriptor(object):

    def __init__(self, directory, suffix, hysplitdir, \
                 hysplit_version='hycs_std', parinit=(None, None, None)):
        self.hysplitdir = hysplitdir  #directory where HYSPLIT executable is.
        self.hysplit_version = hysplit_version  #name of hysplit executable to
        self.directory = directory #directory where CONTROL and SETUP files are.
        self.suffix = suffix       #this should be a string.
        self.parinitA = str(parinit[1])     #parinit file associated with the run.
        self.parinitB = str(parinit[2])    #parinit file associated with the run.
        self.parinit_directory = str(parinit[0])    #parinit file associated with the run.
                                   #should be full path.

    def check_parinit(self):
        """
        Check if the parinit input file needed for the run exists.
        TODO- need to check if it is finished being written!
        """
        if self.parinitA:
           return os.path.isfile(self.parainit_directory + '/' + self.parinitA)
        else:
           return True
    

    def get_parinit(self):
        from shutil import copyfile
        if os.path.isfile(self.parainit_directory + '/' + self.parinitA):
            copyfile(self.parinit_directory + self.parinitA, \
                     self.directory + self.parinitB)

    def script(self):
        """ produces a string that could be put in a bash script
        change to directory where CONTROL file resides
        run hysplit 
        """
        rstr = 'cd ' + self.directory  + '\n'
        ##add line to copy PARDUMP file from one directory to PARINIT file 
        ##in working directory
        if self.parinitA:
            rstr += 'cp ' + self.parinit_directory +  self.parinitA 
            rstr += ' ' + self.parinitB  + '\n'
        rstr += self.hysplitdir +  self.hysplit_version + ' '  + self.suffix 
        return rstr

