# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import numpy as np
import datetime
import time
import os
from os import path, chdir
from subprocess import call
import pandas as pd

# from arlhysplit.process import is_process_running
# from arlhysplit.process import ProcessList
from monet.utilhysplit.hcontrol import HycsControl
from monet.utilhysplit.hcontrol import Species
from monet.utilhysplit.hcontrol import ConcGrid
from monet.utilhysplit.hcontrol import NameList
from monet.utilhysplit.hcontrol import writelanduse
from monet.utilhysplit.metfiles import MetFiles

"""
NAME: svhy.py
PRGMMR: Alice Crawford  ORG: ARL  
This code written at the NOAA  Air Resources Laboratory
ABSTRACT: This code manages HYSPLIT runs for Hanford resuspension project.
CTYPE: source code

List of classes and functions in this file:

FUNCTIONS
create_controls: create control and setupfiles as well as running script.

default_setup: creates default SETUP.0 file
getmetfiles:  returns met file name and directory to use based on dates.
default_control: creates default CONTROL.0 file

create_script: creates the script to run HYSPLIT runs for SO2 project
statmainstr : returns string which is used to run concmerge, c2datem, statmain.

CLASSES
class RunDescriptor:  main purpose currently is to produce a string for the
                      create_script function.


create_runlist:  returns a runlist. Similar to create_controls but does not
write CONTROL and SETUP files.
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
            yield Source(center, altitude, area, rate, date)


##------------------------------------------------------------------------------------##


def default_setup(setupname="SETUP.CFG", wdir="./", units="PPB"):
    """writes the SETUP file which is needed to run HYSPLIT.
           input rhash iu a RunParams object.
        """
    hrs = 5 * 24
    pardumpname = "PARDUMP"
    parinitname = "PARINIT"
    namelist = {}
    # namelist['delt'] =  rhash.delt          #fix time step.
    namelist["initd"] = "0"  # particle is 0  and puff is 3.
    namelist["maxdim"] = "1"
    namelist["kmix0"] = "250"  # default value is 250. controls minimum mixing depth.
    namelist["kblt"] = "2"  # Use Kantha Clayson for vertical mixing.
    namelist["kbls"] = "1"

    if units.lower().strip() == "ppb":
        namelist["ichem"] = "6"  # mass/divided by air density
        # mixing ratio.

    ##emission cycles are 24 hours and each run lasts 5 days.
    ##Also need enough particles to handle pardump from previous simulation.

    namelist["numpar"] = "24000"  # number of particles/puffs to release
    # per emission cycle.
    namelist["maxpar"] = "400000"  # maximum number of particles/puffs to simulate
    namelist["khmax"] = '72'  # maximum time to allow particles to
    # live

    ##The pardump file can be used to restart HYSPLIT if it crashes. Although the runs
    ##are short enough in this application that rather than restart a run, we would just re-run it.
    # namelist['NDUMP'] = str(int(hrs))                #create pardump file after this many hours.
    # namelist['NCYLC'] = str(int(hrs))                #add to pardump file every ncycl hours.
    namelist["POUTF"] = '"' + pardumpname + '"'  # name of pardump file
    namelist["PINPF"] = '"' + parinitname + '"'  # name of pardump file

    ##The termination grid is set in the function add_pterm_grid
    # namelist['ptrm'] = '0'                   #terminate particle outside of concentration grids
    # namelist['nbptyp'] = 1        #number of sub bins for each particle size.

    ## THIS IS NO LONGER USED.
    # namelist['p10f'] = rhash.p10f            #determines mass flux relationship in p10f to use
    # namelist['ichem'] = rhash.ichem          #resuspension run.

    nl = NameList(setupname, working_directory=wdir)
    nl.add_n(namelist)
    nl.write()


def roundtime(dto):
    """rounds input datetime to day at 00 H"""
    # return datetime.datetime(dto.year, dto.month, dto.day, 0, 0)
    return datetime.datetime(dto.year, dto.month, dto.day, 0, 0)


def default_control(name, tdirpath, runtime, sdate, cpack=1, 
                   area=None, sphash={1:'so2a'}):
    lat = 47
    lon = -101
    if cpack == 1:
        latdiff = 0.05
        londiff = 0.05
        latspan = 20
        lonspan = 20
    elif cpack == 3:  # polar grid
        latdiff = 5  # sector angle in degrees
        londiff = 2  # sector spacing in km.
        latspan = 360.0
        lonspan = 200  # downwind distance in km.
    if area:
        lat1 = area[0]
        lon1 = area[1]
        lat2 = area[2]
        lon2 = area[3]
        if lat2 < lat1:
            lat = (lat1 - lat2) * 0.5 + lat2
        else:
            lat = (lat2 - lat1) * 0.5 + lat1
        if lon2 < lon1:
            lon = (lon1 - lon2) * 0.5 + lon2
        else:
            lon = (lon2 - lon1) * 0.5 + lon1
        if cpack == 1:
            latspan = np.ceil(np.abs(lat2 - lat1)) + 1
            lonspan = np.ceil(np.abs(lon2 - lon1)) + 1

    sample_start = "00 00 00 00"
    ztop = 10000
    control = HycsControl(fname=name, working_directory=tdirpath)
    control.add_duration(runtime)
    control.add_sdate(sdate)
    control.add_ztop(ztop)
    control.add_vmotion(0)
    control.add_metfile("./", "metfilename")

    cgrid = ConcGrid(
        "junkname",
        levels=[20, 50, 100, 150, 175, 225, 300],
        centerlat=lat,
        centerlon=lon,
        latdiff=latdiff,
        londiff=londiff,
        latspan=latspan,
        lonspan=lonspan,
        sampletype=0,
        interval=(1, 0),
        sample_start=sample_start,
    )
    control.add_cgrid(cgrid)
    ##TO DO check webdep for so2
    vel = "0.0 64.0 0.0 1.9 1.24e5"  # this is dry deposition parameters
 
    klist = list(sphash.keys())
    klist.sort()
    # BAMS VOG - use Henry's constant of 1.24 molarity
    wetdepstr = "1.24 0.0 0.0"
    for ky in  klist:
        particle = Species(
           sphash[ky] , psize=0, rate=1, duration=1, wetdepstr=wetdepstr, vel=vel, density=0, shape=0
        )
        #particle.add_wetdep(wetdepstr)
        control.add_species(particle)
    control.add_location(latlon=(46, -105), alt=200, rate=0, area=0)
    control.write()


def create_runlist(tdirpath, hdirpath, sdate, edate, timechunks):
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
    from monet.utilhysplit import emitimes

    # from arlhysplit.runh import getmetfiles
    from monet.util.svdir import date2dir
    from monet.util.svdir import dir2date

    dstart = sdate
    dend = edate
    ##determines meteorological files to use.

    runlist = []
    if hdirpath[-1] != '/': hdirpath += '/'
    hysplitdir = hdirpath + "exec/"

    iii = 0
    for (dirpath, dirnames, filenames) in walk(tdirpath):
        #print(dirpath, dirnames, filenames)
        for fl in filenames:
            if iii == 0:
                firstdirpath = dirpath

            if "EMIT" in fl:
                # print(dirpath, dirnames, filenames)
                # print(fl)
                et = emitimes.EmiTimes(filename=dirpath + "/" + fl)
                if not et.read_file(): continue
                # print('NRECS', nrecs)
                # sys.exit()
                #sdate = et.cycle_list[0].sdate
                try: 
                    sdate = dir2date(tdirpath, dirpath)
                except:
                    continue
                if sdate < dstart or sdate > dend:
                    continue
                suffix = fl[4:8]
                temp = fl.split(".")
                #if temp[1] != "txt":
                #    suffix += "." + temp[1]
                temp = fl.replace('EMIT','')
                suffix = temp.replace('.txt','')
                wdir = dirpath
                if dirpath == firstdirpath:
                    parinit = (None, None, None)
                else:
                    pdate = sdate - datetime.timedelta(hours=timechunks)
                    pdir = date2dir(tdirpath, pdate, dhour=timechunks)
                    parinitA = "PARDUMP." + suffix
                    parinitB = "PARINIT." + suffix
                    parinit = (pdir, parinitA, parinitB)
                run = RunDescriptor(wdir, suffix, hysplitdir, "hycs_std", parinit)
                wr = "a"
                if iii == 0:
                    wr = "w"
                # with open(tdirpath + '/' +  scr, wr) as fid:
                # fid.write(run.script())
                # fid.write('\n\n')
                runlist.append(run)
                iii += 1
    return runlist


def find_numpar(emitfile, controlfile):
    # TO DO
    minconc = 5  # ug/m3
    # TO DO open emitfile and find highest emission
    maxemit = 1e9  # ug placeholder
    # open control file to find this.
    # find volume of concentration grid
    control = HycsControl(controlfile)
    control.read()
    cgrid = control.concgrids[0]
    volume = cgrid.latdiff * cgrid.londiff * cgrid.nlev[0]
    # Assume want 100 particles to get minconc.
    mass_per_particle = minconc * volume / 100.0
    #
    numpar = maxemit / mass_per_particle
    if numpar < 1000:
        numpar = 1000
    return np.ceil(numpar)


def read_vmix(tdirpath, sdate, edate, timchunks, sid=None):
    from monet.utilhysplit import vmixing
    dtree = dirtree(tdirpath, sdate, edate, chkdir=False, dhour=timechunks)
    vmix = vmixing.VmixingData()
    for dirpath in dtree:
        print(dirpath)
        for (d1, dirnames, filenames) in walk(dirpath):
             for fl in filenames:
                 if 'STABILITY' in fl:
                     if not sid or str(sid) in fl:
                         vmix.add_data(fl)
    return vmix.df

def create_vmix_controls(tdirpath,hdirpath,sdate,edate,timechunks, metfmt):
    """
    read the base control file in tdirpath CONTROL.0
    """
    from os import walk
    from monet.utilhysplit import emitimes
    # from arlhysplit.runh import getmetfiles
    from monet.util.svdir import dirtree
    from monet.util.svdir import date2dir
    from monet.util.svdir import dir2date
    from monet.util.datem import read_datem_file

    dstart = sdate
    dend = edate
    ##determines meteorological files to use.
    met_files = MetFiles(metfmt) 
    runlist = []  #list of RunDescriptor Objects
    hysplitdir = hdirpath + "/exec/"
    #landusedir = hdirpath + "/bdyfiles/"

    dtree = dirtree(tdirpath, sdate, edate, chkdir=False, dhour=timechunks)
    vstr = ''
    runlist = []
    for dirpath in dtree:
        print(dirpath)
        for (d1, dirnames, filenames) in walk(dirpath):
            for fl in filenames:
                #if iii == 0:
                #    firstdirpath = dirpath
                if fl=="datem.txt":
                    print(d1, dirnames, fl)
                   # read the datem.txt file
                    cols=['year','month','day','hour','duration','lat','lon','val','sid','ht']
                    dfdatem = read_datem_file(d1 + fl, colra=cols, header=2) 
                    dfdatem = dfdatem[['lat','lon','sid']]
                    dfdatem = dfdatem.drop_duplicates()
                    for index, row  in dfdatem.iterrows():
                        lat = row['lat']
                        lon = row['lon']
                        pid = int(row['sid'])
                        print('PID', str(pid))
                        ##Write a control file for this emitimes file
                        suffix = 'V' + str(pid)
                        control = HycsControl(fname='CONTROL.V',
                                  working_directory=d1, rtype='vmixing')
                        #control.read()
                        control.date = sdate
                        ##remove all the locations first and then add
                        ##locations that correspond to emittimes file.
                        control.remove_locations()
                        control.add_location(latlon=(lat, lon))
                        control.rename('CONTROL.' + suffix, working_directory=d1)
                        control.remove_metfile(rall=True)
                        ###Add the met files.
                        control.add_duration(timechunks)
                        mfiles = met_files.get_files(control.date, timechunks)
                        for mf in mfiles:
                            if os.path.isfile(mf[0] + mf[1]):
                                control.add_metfile(mf[0], mf[1])
                        #for cg in control.concgrids:
                        #    cg.outfile += "." + suffix
                        if control.num_met > 12: metgrid=True
                        else: metgrid=False 
                        control.write(metgrid=metgrid)
                        run = RunDescriptor(d1, suffix, hysplitdir, "vmixing",
                                             parinit='None')
                        runlist.append(run)
                        #vstr += 'cd ' + dirnames + '\n'
                        #vstr += '$MDL/vmixing -p' + suffix + '-a2'
                        #vstr += '\n' 
    return runlist


def create_controls(tdirpath, hdirpath, sdate, edate, timechunks, metfmt, units="ppb",
                    ):
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

    RETURNS:
    runlist : list of runDescriptor objects

    # TODO - add ability to base numpar on amount of emissions.
    # will need to read EMITTIME file and find max emission for that time
    # period. Then use 
    """
    from os import walk
    from monet.utilhysplit import emitimes
    # from arlhysplit.runh import getmetfiles
    from monet.util.svdir import dirtree
    from monet.util.svdir import date2dir
    from monet.util.svdir import dir2date


    dstart = sdate
    dend = edate
    ##determines meteorological files to use.
    met_files = MetFiles(metfmt) 

    runlist = []  #list of RunDescriptor Objects
    hysplitdir = hdirpath + "/exec/"
    landusedir = hdirpath + "/bdyfiles/"

    dtree = dirtree(tdirpath, sdate, edate, chkdir=False, dhour=timechunks)
    iii = 0
    # for (dirpath, dirnames, filenames) in walk(tdirpath):
    for dirpath in dtree:
        print(dirpath)
        for (d1, dirnames, filenames) in walk(dirpath):
            for fl in filenames:
                if iii == 0:
                    firstdirpath = dirpath
                if "EMIT" in fl:
                    # print(dirpath, dirnames, filenames)
                    suffix = fl[4:8]
                    temp = fl.split(".")
                    # print(temp)
                    # print('************')
                    if temp[1] != "txt":
                        suffix += "." + temp[1]
                    else:
                        suffix = temp[0].replace('EMIT','')
                    wdir = dirpath

                    # read emitfile and modify number of locations
                    et = emitimes.EmiTimes(filename=dirpath + "/" + fl)
                    # if the emittimes file is empty move to the next one.
                    if not et.read_file() : continue
                    

                    # number of locations is number of records
                    # in the emitimes file divided by number of speciess.
                    nrecs = et.cycle_list[0].nrecs / len(et.splist)

                    # print('NRECS', nrecs)
                    # sys.exit()
                    sdate = et.cycle_list[0].sdate
                    ##if sdate not within range given,
                    ##then skip the rest of the loop.
                    if sdate < dstart or sdate > dend:
                        continue
                    lat = et.cycle_list[0].recordra[0].lat
                    lon = et.cycle_list[0].recordra[0].lon

                    ##Write a setup file for this emitimes file
                    setupfile = NameList("SETUP.0", working_directory=tdirpath)
                    setupfile.read()
                    setupfile.add("EFILE", '"' + fl + '"')
                    setupfile.add("NDUMP", str(timechunks))
                    setupfile.add("NCYCL", str(timechunks))
                    setupfile.add("POUTF", '"PARDUMP.' + suffix + '"')
                    setupfile.add("PINPF", '"PARINIT.' + suffix + '"')
                    setupfile.add("NINIT", "1")
                    # setupfile.add('DELT', '5')
                    setupfile.rename("SETUP." + suffix, working_directory=wdir + "/")
                    setupfile.write(verbose=False)

                    ##Write a control file for this emitimes file
                    control = HycsControl(fname="CONTROL.0", working_directory=tdirpath)
                    control.read()
                    control.date = sdate
                    # remove species and add new with same
                    # attributes but different names
                    if et.splist.size > 0:
                       sp = control.species[0]
                       control.remove_species()
                       for spec in et.splist:
                           spnew = sp.copy()
                           #print('Adding species', spec)
                           spnew.name = et.sphash[spec]
                           #print(spnew.strpollutant())
                           control.add_species(spnew)  


                    ##remove all the locations first and then add
                    ##locations that correspond to emittimes file.
                    control.remove_locations()
                    nlocs = control.nlocs
                    while nlocs != nrecs:
                        if nlocs < nrecs:
                            control.add_location(latlon=(lat, lon))
                        if nlocs > nrecs:
                            control.remove_locations(num=0)
                        nlocs = control.nlocs
                    control.rename("CONTROL." + suffix, working_directory=wdir)
                    control.remove_metfile(rall=True)
                    ###Add the met files.
                    
                    #mfiles = getmetfiles(
                    #    control.date, timechunks, met_type=met_type, mdir=mdir
                    #)
                    mfiles = met_files.get_files(control.date, timechunks)
                    for mf in mfiles:
                        if os.path.isfile(mf[0] + mf[1]):
                            control.add_metfile(mf[0], mf[1])
                    for cg in control.concgrids:
                        cg.outfile += "." + suffix
                    if control.num_met > 12: metgrid=True
                    else: metgrid=False 
                    control.write(metgrid=metgrid)
                    writelanduse(landusedir=landusedir, working_directory=wdir + "/")

                    with open(wdir + "/rundatem.sh", "w") as fid:
                        fid.write("MDL=" + hysplitdir + "\n")
                        fid.write(unit_mult(units=units))
                        fid.write(statmainstr())

                    if dirpath == firstdirpath:
                        parinit = (None, None, None)
                    else:
                        sdate = dir2date(tdirpath, dirpath)
                        pdate = sdate - datetime.timedelta(hours=timechunks)
                        pdir = date2dir(tdirpath, pdate, dhour=timechunks)
                        parinitA = "PARDUMP." + suffix
                        parinitB = "PARINIT." + suffix
                        parinit = (pdir, parinitA, parinitB)
                    run = RunDescriptor(wdir, suffix, hysplitdir, "hycs_std", parinit)
                    wr = "a"
                    if iii == 0:
                        wr = "w"
                    # with open(tdirpath + '/' +  scr, wr) as fid:
                    # fid.write(run.script())
                    # fid.write('\n\n')
                    runlist.append(run)
                    iii += 1
    return runlist


def unit_mult(units="ug/m3"):
    rstr = ""
    #rstr = "#emission in kg (mult by 1e9)" + "\n"
    if units.lower().strip() == "ppb":
        rstr += "#convert to volume mixing ratio"
        rstr += "#(mult by 0.4522)" + "\n"
        rstr += "mult=4.522e8" + "\n"
    else:
        rstr += "#emission in kg (mult by 1e9)" + "\n"
        rstr += "#output in ug/m3" + "\n"
        rstr += "mult=1e9 #emission in kg" + "\n"
    return rstr


def statmainstr(suffixlist=None, model=None, pstr=None):
    """
       suffixlist : list of strings
       model : string. name of output file from c2datem.
       returns string to create_script for
       running conmerge, c2datem and statmain.
    """
    csum = "cdump.sum"
    mergestr =  "$MDL/conmerge -imergefile -o" + csum + "\n"
    datem = "datem.txt"
    if not pstr: pstr= ''
    # all cdump files in the directory are merged 
    if not suffixlist:
       cdumpstr = 'ls cdump.* > mergefile \n' 
    # only certain cdump files in the directory are merged 
    elif len(suffixlist)> 1:
       cdumpstr = 'rm -f mergefile \n'
       for suffix in suffixlist:
           cdumpstr += 'ls cdump.' + suffix + ' >> mergefile \n'
    # datem run on only one cdump file in the directory.
    else:
       csum = 'cdump.' + suffixlist[0]
       cdumpstr = ''
       mergestr = ''        
       if not model: model = 'model.' + suffixlist[0] + '.txt'  

    if not model: model = 'model.txt'

    suffix = model.replace('.txt','')
    suffix = suffix.replace('model','')
    suffix = suffix + '.' + pstr.replace('-','')
 
    rstr = cdumpstr
    rstr += mergestr
    rstr +=  "$MDL/c2datem -i" + csum + " -m" + datem + " -o" 
    rstr +=  model + " -xi -z1 -c$mult "
    rstr += pstr
    rstr += "\n"
    rstr += "$MDL/statmain -d" + datem + " -r" + model + " -o\n"
    if suffix: rstr += "mv dataA.txt dataA" + suffix + ".txt \n"
    rstr += "\n"
    return rstr



class RunScriptClass:

    def __init__(self, name, runlist, tdirpath):
        self.scriptname = name 
        self.tdirpath = tdirpath
        #self.runlist = sorted(runlist)
        self.runlist = runlist
        self.main()

    def make_hstr(self):
        return ""

    def main(self):
        rstr = self.make_hstr()
        if self.runlist: 
            rstr += "MDL=" + self.runlist[0].hysplitdir + "\n"
            #rstr += unit_mult(units=units)
            iii=0
            for runstr in self.mainstr_generator():
                rstr += runstr
        with open(self.tdirpath + "/" + self.scriptname, "w") as fid:
            fid.write(rstr)

    def mainstr_generator(self):
        iii = 0
        prev_directory = ' '
        for run in self.runlist:
            dstr = ''
            if run.directory != prev_directory:
               dstr += "cd " + run.directory + "\n\n"
            dstr += self.mstr(run)
            prev_directory = run.directory
            iii += 1
            yield dstr
       
    def mstr(self, run):
        return run.directory


class VmixScript(RunScriptClass):

    def mstr(self, run):
        rstr= '$MDL/vmixing -a2 -p' + run.suffix
        rstr += '\n'
        return rstr


class DatemScript(RunScriptClass):
    """
    Creates bash script which will 
    3. run conmerge merge cdump files from different power plants
    4. run c2datem to extract concentrations at stations
    5. run statmain to create file with concentrations and obs. 
    runlist : list of RunDescriptor objects
    tdirpath : string
               top directory path.

    """
    def __init__(self, name, runlist, tdirpath, unit, poll=1):
        # note that poll>=1 (input to c2datem)
        self.unit = unit
        if poll: self.pstr = '-p' + str(poll)
        else: self.pstr = ''
        super().__init__(name, runlist, tdirpath)

    def make_hstr(self):
        return unit_mult(self.unit)

    def mainstr_generator(self):
        iii = 0
        prev_directory = ' '
        prev_oris = ' '
        suffixlist = []
        for run in self.runlist:
            dstr=''
            if run.directory != prev_directory:
               dstr += "cd " + run.directory + "\n\n"
               #dstr += statmainstr()
               prev_directory = run.directory
            oris = run.get_oris()
            if oris != prev_oris and iii!=0: 
                dstr += statmainstr(suffixlist=suffixlist, model=model,
                         pstr=self.pstr)
                suffixlist = []
            model = 'model_' + oris + '.txt'
            suffixlist.append(run.suffix)           
            prev_oris = oris
            iii+=1 
            yield dstr


class RunScript(RunScriptClass):
    """
    Creates bash script which will 
    1. Copy pardump files for use as parinit files
    2. run HYSPLIT
    """

    def __init__(self, name, runlist, tdirpath):
        self.logfile = 'runlogfile.txt'
        super().__init__(name, runlist, tdirpath)

    def mainstr_generator(self):
        iii = 0
        nice=True
        prev_directory = ' '
        for run in self.runlist:
            rstr = ''
            if run.directory != prev_directory:
                if iii != 0:
                    rstr += "wait" + "\n\n"
                    rstr += 'echo "Finished ' + prev_directory + '"  >> ' 
                    rstr += self.logfile
                    rstr += "\n\n"
                    rstr += "#-----------------------------------------\n"
                rstr += "cd " + run.directory + "\n\n"
            if run.parinitA != "None":
                rstr += "cp " + run.parinit_directory + run.parinitA
                rstr += " " + run.parinitB + "\n"
            if nice: rstr += 'nice '
            rstr += "${MDL}" + run.hysplit_version + " " + run.suffix
            rstr += " & \n"
            prev_directory = run.directory
            iii += 1
            yield rstr
        ##add line to copy PARDUMP file from one directory to PARINIT file

class RunDescriptor(object):
    def __init__(
        self,
        directory,
        suffix,
        hysplitdir,
        hysplit_version="hycs_std",
        parinit=(None, None, None),
    ):
        self.hysplitdir = hysplitdir  # directory where HYSPLIT executable is.
        self.hysplit_version = hysplit_version  # name of hysplit executable to
        self.directory = directory  # directory where CONTROL and SETUP files are.
        self.suffix = suffix  # this should be a string.
        self.parinitA = str(parinit[1])  # parinit file associated with the run.
        self.parinitB = str(parinit[2])  # parinit file associated with the run.
        self.parinit_directory = str(
            parinit[0]
        )  # parinit file associated with the run.
        # should be full path.

    def __lt__(self, other):
        """
        lt and eq so runlist can be sorted according to
        directory and then to suffix.
        """
        if self.directory == other.directory:
           t1 = self.suffix < other.suffix
        else:
           t1 = self.directory < other.directory
        return t1

    def __eq__(self, other):
        t1 = self.directory == other.directory
        t2 = self.suffix == other.suffix
        return t1 and t2

    def get_oris(self):
        oris = self.suffix.split('_')[0]
        return oris

    def get_unit(self):
        try:
            unit = self.suffix.split('_')[1]
        except:
            unit = 'None'
        return unit


    def check_parinit(self):
        """
        Check if the parinit input file needed for the run exists.
        TODO- need to check if it is finished being written!
        """
        if self.parinitA:
            return os.path.isfile(self.parainit_directory + "/" + self.parinitA)
        else:
            return True

    def get_parinit(self):
        from shutil import copyfile

        if os.path.isfile(self.parainit_directory + "/" + self.parinitA):
            copyfile(
                self.parinit_directory + self.parinitA, self.directory + self.parinitB
            )

    def script(self, nice=True):
        """ produces a string that could be put in a bash script
        change to directory where CONTROL file resides
        run hysplit 
        """
        rstr = "cd " + self.directory + "\n"
        ##add line to copy PARDUMP file from one directory to PARINIT file
        ##in working directory
        if self.parinitA:
            rstr += "cp " + self.parinit_directory + self.parinitA
            rstr += " " + self.parinitB + "\n"
        if nice: rstr += 'nice '
        rstr += self.hysplitdir + self.hysplit_version + " " + self.suffix
        return rstr


def pick_format(mtype='wrf'): 
    fmt=''
    if mtype == 'wrf':
       fmt = "/pub/archives/wrf27km/%Y/wrfout_d01_%Y%m%d.ARL"
       hours = 24
    return fmt, hours

