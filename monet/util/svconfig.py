import os
from monet.utilhysplit.hcontrol import NameList
import sys

# import cartopy.crs as ccrs
# import cartopy.feature as cfeature

"""
Functions
-----------
Classes
---------
ConfigFile(NameList)
"""


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

        # attributes for NEI data
        self.neiconfig = None  #file which gives info on other source
        self.ndir = '/n-home/alicec/'

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
        self.ish = 0
        # directory for vmixing output
        self.vdir = None

        if os.path.isfile(fname):
            self.read(case_sensitive=False)
            self.hash2att()
            self.fileread = True
        else:
            self.fileread = False

        # attributes which are derived from input data
        self.d1 = None  # start date
        self.d2 = None  # end date
        self.area = None  # area
        self.source_chunks= None
        self.run_duration = None
        self.logfile= None
        self.fignum= None
        


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

        hstr = "top level directory path for vmixing outputs"
        self.descrip["vmixdir"] = hstr
        lorder.append("vmixdir")


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
        hstr += sp10 + "if set to -1 will create CONTROL and SETUP.CFG files\n"
        hstr += sp10 + "suitable for creating a TCM with forward runs.\n"
        hstr += sp10 + "e.g. produce unit emissions every hour."
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
  
        hstr = "(0) or 1. Retrieve met data from Integrated Surface Database"
        self.descrip["ISH"] = hstr
        lorder.append("ISH")

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

        hstr = "Data from Integrated surface database\n"
        hstr += sp10 + 'if 1 create csv file and summary file and\n'
        hstr += sp10 + 'plot locations of measurements on map (blue crosses)'
        self.descrip['ish'] = hstr
        lorder.append('ish')

        hstr = "(False) or True. The bash scripts for running HYSPLIT and then \n"
        hstr += sp10 + "c2datem must be run first.\n"
        hstr += sp10 + "reads datem output and creates graphs."
        self.descrip["RESULTS"] = hstr
        lorder.append("RESULTS")

        hstr = "0 or 1 \n"
        hstr += sp10 + 'if 1 create bash scripts to run c2datem\n'
        self.descrip['scripts'] = hstr
        lorder.append('scripts')
  
        hstr = "str. name of file with information on other sources \n"
        hstr += sp10 + 'if options.run true then will create CONTROL files for\n'
        hstr += sp10 + ' these sources based on CONTROL.0 and info in the file.\n'
        self.descrip['neiconfig'] = hstr
        lorder.append('scripts')


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
        self.neiconfig = self.test('neiconfig', self.neiconfig)
        self.ndir = self.test('neidir', self.ndir)

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
        self.vdir = self.test("vmixdir", self.vdir)
        if not self.vdir: self.vdir = self.tdir

        self.quiet = self.test("quiet", self.quiet)
        self.quiet = int(self.quiet)

        self.cemsource = self.test("cemsource", self.cemsource)
        self.cemsource = self.process_cemsource()

        self.chunks = self.test("emitdays", self.chunks)
        self.chunks = int(self.chunks)

        self.write_scripts = self.test("scripts", self.write_scripts)
        try:
            self.write_scripts = int(self.write_scripts)
        except:
            self.write_scripts = self.str2bool(self.write_scripts) 

        self.metfmt = self.test("metfile", self.metfmt)

        self.vmix = self.test('vmix', self.vmix)
        try:
            self.vmix = int(self.vmix)
        except: 
            self.vmix = self.str2bool(self.vmix) 
 
        self.ish = self.test('ish', self.ish)
        self.ish = int(self.ish)
        # booleans
        self.byunit = self.str2bool(self.test("byunit", self.byunit))
        self.spnum = self.str2bool(self.test("species", self.spnum))
        self.cems = self.str2bool(self.test("cems", self.cems))
        self.obs = self.str2bool(self.test("obs", self.obs))
        self.create_runs = self.str2bool(self.test("run", self.create_runs))
        self.results = self.str2bool(self.test("results", self.results))
        self.defaults = self.str2bool(self.test("defaults", self.results))


