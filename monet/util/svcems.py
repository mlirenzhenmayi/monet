import os
import sys
import subprocess
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
import seaborn as sns
from monet.obs import cems_api
import monet.obs.obs_util as obs_util

# from arlhysplit import runh
from monet.util.svdir import date2dir
from timezonefinder import TimezoneFinder

# from arlhysplit.runh import source_generator
# from arlhysplit.runh import create_plume
# from arlhysplit.tcm import TCM
from monet.utilhysplit import emitimes
from shapely.geometry import Point
import geopandas as gpd
import pandas as pd
import warnings
# from monet.obs.epa_util import convert_epa_unit

"""
SEmissions class

methods:
  __init__
  find
  get_so2_sources
  get_heat
  get_stackvalues
  check_oris
  get_sources
  create_emitimes
  emit_subroutine
  plot
  map

# in script
  A. ef.find
  B  ef.plot
  C  ef.create_emitimes
  D  er.map

SourceSummary class
"""


def get_timezone(lat, lon):
    """ returns time difference in hours"""
    tf = TimezoneFinder()
    tz = tf.closest_timezone_at(lng=lon, lat=lat)
    #print("TZ-------------", tz, lat, lon)
    dtest = datetime.datetime(2010, 2, 1, 0)
    t1 = pd.Timestamp(dtest).tz_localize(tz) # local time
    t2 = t1.tz_convert("utc")                # utc time

    t1 = t1.tz_localize(None)
    t2 = t2.tz_localize(None)
    # returns hours. must add this to local time to get utc.
    return (t2 - t1).seconds / 3600.0


class SourceSummary:
    def __init__(self, tdir="./", fname="source_summary.csv", data=pd.DataFrame()):

        if not data.empty:
            self.sumdf = self.create(data)
        else:
            self.sumdf = self.load(tdir, fname)

        self.tdir = tdir
        self.fname = fname

    def check_oris(self, threshold):
        """
        return list of oris codes for which the max emission was above
        threshold.
        """
        tempdf = self.sumdf[["ORIS", "Max(lbs)"]]
        tempdf.groupby("ORIS").max()
        df = tempdf[tempdf["Max(lbs)"] > threshold]
        goodoris = df["ORIS"].unique()
        return goodoris

    def operatingtime(self, data1):
        grouplist = ["oris", "unit"]
        keep = grouplist.copy()
        keep.append("OperatingTime")
        data1 = cems_api.keepcols(data1, keep)
        optime = data1.groupby(grouplist).sum()
        optime.reset_index(inplace=True)
        return optime

    def create(self, data1):
        """
        creates a dataframe with columns 
        oris
        unit (id of monitoring location)
        Name (facilities name)
        lat
        lon
        Stack Height (m)
        Mean(lbs)  (mean 1 hour emission over the time period) 
        Max(lbs)  (Max 1 hour emission over the time period) 
        """
        columns = [
            "ORIS",
            "unit",
            "Name",
            "lat",
            "lon",
            "Stack height (m)",
            "Mean(lbs)",
            "Max(lbs)",
            "OperatingTime",
        ]
        #print(data1.columns)
        optime = self.operatingtime(data1)
        # only average when plant was operating.
        # data0 = data1.copy()
        # only average when plant was operating.
        data1 = data1[data1["OperatingTime"] > 0]
        #
        grouplist = [
            "oris",
            "unit",
            "facility_name",
            "latitude",
            "longitude",
            "stackht",
        ]
        keep = grouplist.copy()
        keep.append("so2_lbs")
        #print(keep)
        # drop columns not in the keep list.

        data1 = cems_api.keepcols(data1, keep)

        # get the mean of so2_lbs
        meandf = data1.groupby(grouplist).mean()
        # get the max of so2_lbs
        maxdf = data1.groupby(grouplist).max()
        meandf.reset_index(inplace=True)
        maxdf.reset_index(inplace=True)
        # merge so mean and max in same DataFrame
        sumdf = pd.merge(
            meandf, maxdf, how="left", left_on=grouplist, right_on=grouplist
        )

        sumdf = pd.merge(
            sumdf,
            optime,
            how="left",
            left_on=["oris", "unit"],
            right_on=["oris", "unit"],
        )
        sumdf.columns = columns
        return sumdf

    def __str__(self):
        print("Placeholder for Source Summary String")

    def load(self, tdir=None, name=None):
        if not name:
            name = self.fname
        if not tdir:
            tdir = self.tdir
        if os.path.isfile(tdir + name):
            # df = pd.read_csv(tdir + name, header=None)
            df = pd.read_csv(tdir + name)
        else:
            df = pd.DataFrame()
        return df

    def print(self, tdir="./", name="source_summary.csv"):
        fname = tdir + name
        self.sumdf.to_csv(fname)


def df2hash(df, key, value):
    """ create a dictionary from two columns
        in a pandas dataframe. 
    """
    if key not in df.columns:
        return None
    if value not in df.columns:
        return None
    dseries = df.set_index(key)
    dseries = dseries[value]
    return dseries.to_dict()


class SEmissions(object):
    """This class for running the SO2 HYSPLIT verification.
       self.cems is a CEMS object

       methods
       find_emissions
       get_sources
       plot - plots time series of emissions
       map  - plots locations of power plants on map
    """

    def __init__(self, dates, area, tdir="./", source_thresh=100, spnum=False,
                  tag=None):
        """
        self.sources: pandas dataframe
            sources are created from a CEMSEmissions class object in the get_sources method.

        area: list or tuple of four floats
             (lat, lon, lat, lon) describing lower left and upper right corner
              of area to consider. Note that the user is responsible for
              requestiong all states that may lie within this area.
        states: list of strings
              list of two letter state abbreviations. Data for all states listed
              will be downloaded and then stations outside of the area requested
              will be pruned.

        source_thresh : float
              sources which do not have a maximum value above this in the time
              period specifed by dateswill not be
              considered.

        spnum : boolean
              True - sort emissions onto different species depending on MODC
              flag value. (see modc2spnum method)
              False - ignore MODC flag value.
        """
        self.tag = tag
        self.df = pd.DataFrame()
        self.dfu = pd.DataFrame()
        # data frame for uncertain emissions.
        # MODC >= 8
        self.dfu = pd.DataFrame()
        self.sources = pd.DataFrame()

        # dates to consider.
        self.d1 = dates[0]
        self.d2 = dates[1]
        # area to consider
        self.area = area
        self.tdir = tdir
        self.fignum = 1
        # self.sources is a DataFrame returned by the CEMS class.
        self.cems = cems_api.CEMS()
        self.ethresh = source_thresh  # lbs emittimes only created if max emission over

        self.lbs2kg = 0.453592
        self.logfile = "svcems.log.txt"
        self.meanhash = {}
        # CONTROLS whether emissions are put on different species
        # according to SO2MODC flag.
        self.use_spnum= spnum

    def find(self, testcase=False, byunit=False, verbose=False):
        """find emissions using the CEMS class

           prints out list of emissions soures with information about them.

        """
        print('FIND')
        area = self.area
        if testcase:
            efile = "emission_02-28-2018_103721604.csv"
            self.cems.load(efile, verbose=verbose)
        else:
            data = self.cems.add_data([self.d1, self.d2], area, verbose=True)

        source_summary = SourceSummary(data=data)
        self.meanhash = df2hash(source_summary.sumdf, "ORIS", "Max(lbs)")
        # print('MEANHASH')
        # print(self.meanhash)

        # remove sources which do not have high enough emissions.
        self.goodoris = source_summary.check_oris(self.ethresh)
        self.df = data[data["oris"].isin(self.goodoris)].copy()
        source_summary.print()

        lathash = df2hash(self.df, "oris", "latitude")
        lonhash = df2hash(self.df, "oris", "longitude")

        # convert time to utc
        tzhash = {}
        for oris in self.df["oris"].unique():
            # tz = cems_api.get_timezone_offset(lathash[oris], lonhash[oris])
            tz = get_timezone(lathash[oris], lonhash[oris])
            tzhash[oris] = datetime.timedelta(hours=tz)

        def loc2utc(local, oris, tzhash):
            if isinstance(local, str): 
                print('NOT DATE', local)
                utc = local
            else:
                try:
                    utc = local + tzhash[oris]
                except:
                    #print('LOCAL', local)
                    #print('oris', oris)
                    #print('tzhash', tzhash)
                    utc = 'None'
            return utc

        # all these copy statements are to avoid the warning - a value is trying
        # to be set ona copy of a dataframe.
        self.df["time"] = self.df.apply(
            lambda row: loc2utc(row["time local"], row["oris"], tzhash), axis=1
        )
        temp = self.df[self.df.time == 'None']
        print('TEMP with None time\n', temp[0:20])
        self.df = self.df[self.df.time != 'None'] 
         

    def get_so2_sources(self, unit=False):
        sources = self.get_sources(stype="so2_lbs", unit=unit)
        sources = sources * self.lbs2kg  # convert from lbs to kg.
        return sources

    def get_heat(self, unit=False):
        """
        return dataframe with heat from the CEMS file
        """
        sources = self.get_sources(stype="heat_input (mmbtu)", unit=unit)
        mult = 1.055e9 / 3600.0  # mmbtu to watts
        mult = 0  # the heat input from the CEMS files is not the correct value to
        # use.
        sources = sources * mult
        return sources

    def get_stackvalues(self, unit=False):
        """
        return dataframe with string which has stack diamter, temperature
        velocity  obtained from the ptinv file.
        """
        sources = self.get_sources(stype="stack values", unit=unit)
        # mult = 1.055e9 / 3600.0  #mmbtu to watts
        # mult=0  ##the heat input from the CEMS files is not the correct value to
        # use.
        # sources = sources * mult
        return sources

    def check_oris(self, series, oris):
        """
        Only model sources for which maxval is above the set threshold.
        """
        print(oris, "CHECK COLUMN---------------------------")
        nanum = series.isna().sum()
        series.dropna(inplace=True)
        maxval = np.max(series)
        print("Number of Nans", nanum)
        print("Max value", maxval)
        rval = False
        if maxval > self.ethresh:
            rval = True
        else:
            print("DROPPING")
        return rval

    def get_sources(self, stype="so2_lbs", unit=False, verbose=True):
        """
        Returns a dataframe with rows indexed by date.
        column has info about lat, lon,
        stackheight in meters,
        orisp code
        values are
        if stype=='so2_lbs'  so2 emissions
        if stype='

        """
        # print("GET SOURCES")
        if self.df.empty:
            print('SOURCES EMPTY')
            self.find()
        ut = unit
        df = obs_util.timefilter(self.df, [self.d1, self.d2])
        df = self.modc2spnum(df)
      
        #-------------------------------
        #-------------------------------
        # set negative values to 0.
        def remove_negs(x):
            if x < 0:
               return 0
            else:
               return x       
 
        df[stype] = df.apply(
            lambda row: remove_negs(row[stype]), axis=1
           )
        #-------------------------------
        #-------------------------------


        #dftemp = df[df["spnum"] == 1]
        #dftemp = df[df["spnum"] == 2]
        #dftemp = df[df["spnum"] == 3]
        #print("SP 3", dftemp.SO2MODC.unique())
        #print("OP TIME", dftemp.OperatingTime.unique())
        if not self.use_spnum:
           # set all species numbers to 1
           df['spnum'] = 1
        cols = ["oris", "stackht", "spnum"]
        if unit: cols.append('unit')
        # cols=['oris']
        sources = pd.pivot_table(
            df, index=["time"], values=stype, columns=cols, aggfunc=np.sum
        )
        # sources = cems_api.cemspivot(self.df,
        #    (stype), cols=['oris','stackht'], daterange=[self.d1, self.d2], verbose=False)
        droplist = []
        cnew = []
        #if verbose:
        #    print("----GET SOURCES columns------")
        columns = list(sources.columns.values)
        # print('----columns------')
        # print(columns) #EXTRA
        # print(stackhash)
        # print('----columns------')
        #######################################################################
        #######################################################################
        # original column header contains either just ORIS code or
        # (ORIS,UNITID)
        # This block adds additional information into the COLUMN HEADER.
        # lat lon information is added here because they are floats.
        # when creating the pivot table, do not want to have extra columns if
        # floats are slightly different.
        lathash = df2hash(self.df, "oris", "latitude")
        lonhash = df2hash(self.df, "oris", "longitude")
        newcolumn = []
        cols = sources.columns
        if isinstance(cols, str):
            cols = [cols]
        for val in cols:
            lat = lathash[val[0]]
            lon = lonhash[val[0]]
            tp = (val[0], val[1], lat, lon, val[2])
            if unit: tp = (val[0], val[1], lat, lon, val[2], val[3])
            newcolumn.append(tp)
           
        sources.columns = newcolumn
        #######################################################################
        #######################################################################
        #print("SOURCES ", sources.columns)
        return sources

    # def create_heatfile(self,edate, schunks=1000, tdir='./', unit=True):

    def read_csv(self, name="cems.csv"):
        cems = pd.read_csv(name, sep=",")
        return cems

    def make_csv(self, df, cname='cems.csv'):
        new = []
        df.fillna(0, inplace=True)
        for hd in df.columns:
            try:
                cstr=hd[0] + ' P' + str(hd[4])
            except:
                cstr = hd
            try:
                cstr += ' U' + str(hd[5])
            except:
                pass
            new.append(cstr)
        df.columns = new
        if self.tag: cname = str(self.tag) + '.cems.csv'
        df.to_csv(cname)

    def create_emitimes(self, edate, schunks=1000, tdir="./", unit=True, heat=0,
                         emit_area=0):
        """
        One of the main methods. 
        create emitimes file for CEMS emissions.
        edate: datetime : the date to start the file on.
        Currently, 24 hour cycles are hard-wired.


        self.get_so2_sources
        """
        df = self.get_so2_sources(unit=unit)
        # df = self.get_sources()
        self.make_csv(df.copy())
        print("CREATE EMITIMES in SVCEMS")
        #print(df[0:72])
        # placeholder. Will later add routine to get heat for plume rise
        # calculation.

        dfheat = df.copy() * 0 + heat
        # dfheat = self.get_heat(unit=unit)
        # if unit:
        #    dfstack = self.get_stackvalues(unit=unit)
        locs = df.columns.values
        done = False
        iii = 0
        d1 = edate
        # loop to create each emittimes file.
        while not done:
            d2 = d1 + datetime.timedelta(hours=schunks - 1)
            dftemp = df.loc[d1:d2]
            hdf = dfheat.loc[d1:d2]
            #if unit:
            #    sdf = dfstack[d1:d2]
            # if no emissions during time period then break.
            if dftemp.empty:
                break
            self.emit_subroutine(dftemp, hdf, d1, schunks, tdir, unit=unit,
                                  emit_area=emit_area)
            # create separate EMIT TIMES file for each unit.
            # these are named STACKFILE rather than EMIT
            #if unit:
            #    self.emit_subroutine(
            #        dftemp, sdf, d1, schunks, tdir, unit=unit, bname="STACKFILE"
            #    )
            d1 = d2 + datetime.timedelta(hours=1)
            iii += 1
            if iii > 1000:
                done = True
            if d1 > self.d2:
                done = True

    # def emit_subroutine(self, df, dfheat):

    def emit_subroutine(
        self, df, dfheat, edate, schunks, tdir="./", unit=True, bname="EMIT",
        emit_area=0):
        """
        create emitimes file for CEMS emissions.
        edate is the date to start the file on.
        Currently, 24 hour cycles are hard-wired.
        """
        # df = self.get_so2()
        # dfheat = self.get_heat()
        locs = df.columns.values
        prev_oris = 'none'
        ehash = {}
        
        # get list of oris numbers
        orislist = []
        unithash = {}
        for hdr in locs:
            oris = hdr[0]
            orislist.append(oris)
            unithash[oris] = []
 
        for hdr in locs:
            oris = hdr[0]
            #print(hdr)
            if unit:  mid = hdr[5]
            else: mid='None'
            unithash[oris].append(mid) 
              
        orislist = list(set(orislist))
        sphash = {1:'MEAS', 2:'EST1', 3:'EST2'}

        # create a dictionary with key oris number and value and EmiTimes
        # object.
        for oris in orislist:
            for mid in unithash[oris]:
                # output directory is determined by tdir and starting date.
                # chkdir=True means date2dir will create the directory if
                # it does not exist already.
                ename = bname + str(oris)
                if unit: ename = ename + '_' + str(mid)
                odir = date2dir(tdir, edate, dhour=schunks, chkdir=True)
                ename = odir + ename + ".txt"
                if unit: key = str(oris) + str(mid)
                else: key = oris
                ehash[key] =  emitimes.EmiTimes(filename=ename)
                ehash[key].set_species(sphash)



        # now this loop fills the EmitTimes objects
        for hdr in locs:
            oris = hdr[0]
            d1 = edate  # date to start emitimes file.
            dftemp = df[hdr]
            dfh = dfheat[hdr]
            dftemp.fillna(0, inplace=True)
            dftemp = dftemp[dftemp!=0]
            #ename = bname + str(oris)
            #if unit:
            #    sid = hdr[4]
            #   ename += "." + str(sid)
            height = hdr[1]
            lat = hdr[2]
            lon = hdr[3]
            spnum = hdr[4]
            key = oris
            if unit: 
               mid = hdr[5]
               key += str(mid)
            # hardwire 1 hr duraton of emissions.
            record_duration = "0100"
            # pick which EmitTimes object we are working with.
            efile = ehash[key]
            # output directory is determined by tdir and starting date.
            # chkdir=True means date2dir will create the directory if
            # it does not exist already.
            #odir = date2dir(tdir, edate, dhour=schunks, chkdir=True)
            #ename = odir + ename + ".txt"
            #efile = emitimes.EmiTimes(filename=ename)
            # this was creating a special file for a pre-processing program
            # that would take diameter, temp and velocity to compute plume rise.
            if "STACK" in bname:
                hstring = efile.header.replace(
                    "HEAT(w)", "DIAMETER(m) TEMP(K) VELOCITY(m/s)"
                )
                efile.modify_header(hstring)
            # hardwire 24 hour cycle length
            dt = datetime.timedelta(hours=24)
            efile.add_cycle(d1, "0024")
            for date, rate in dftemp.iteritems():
                #if spnum!=1: print(date, rate, spnum)
                if date >= edate:
                    heat = dfh[date]
                    check = efile.add_record(
                        date, record_duration, lat, lon, height, rate, emit_area, heat, spnum
                    )
                    nnn=0
                    
                    while not check:
                        d1 = d1 + dt
                        efile.add_cycle(d1, "0024")
                        check = efile.add_record(
                            date,
                            record_duration,
                            lat,
                            lon,
                            height,
                            rate,
                            emit_area,
                            heat,
                            spnum,
                        )
                        nnn+=1
                        if nnn > 20:
                           break
                        #if not check2:
                        #    print("sverify WARNING: record not added to EmiTimes")
                        #    print(date.strftime("%Y %m %d %H:%M"))
                        #    print(str(lat), str(lon), str(rate), str(heat))
                        #    break
        # here we write the EmitTimes files
        for ef in ehash.values():
            ef.write_new(ef.filename)

    def modc2spnum(self, dfin):
        """
        The modc is a flag which give information about if the
        value was measured or estimated.
        Estimated values will be carried by different particles.
        spnum will indicate what species the emission will go on. 

        # According to lookups MODC values
        # 01 primary monitoring system
        # 02 backup monitoring system
        # 03 alternative monitoring system
        # 04 backup monitoring system

        # 06 average hour before/hour after
        # 07 average hourly

        # 21 negative value replaced with 0.
        # 08 90th percentile value in Lookback Period
        # 09 95th precentile value in Lookback Period
        # etc.

        # values between 1-4  - Species 1 (high certainty)
        # 6-7  - Species 2  (medium certainty)
        # higher values - Species 3 (high uncertainty)

        # when operatingTime is 0, the modc is Nan
        # these are set as Species 1 since 0 emissions is certain.

        # sometimes negative emissions are associated with higher MODC
        # not sure why this is.
        """
        df = dfin.copy()

        def sort_modc(x):
            try:
               val = int(x["SO2MODC"])
            except:
               val = 99

            try:
               optime = float(x["OperatingTime"])
            except:
               optime = 99


            if val in [1, 2, 3, 4]:
                return 1
            if val in [6, 7]:
                return 2
            else:
                if optime < 0.0001:
                    return 1
                else:
                    return 3


        #print('USE SPNUM', self.use_spnum)
        #if self.use_spnum: 
        df["spnum"] = df.apply(sort_modc, axis=1)
        #else: 
        #    df["spnum"] = 1
        #print(df.columns)
        #temp = df[df['so2_lbs']>0]
        #print(temp[['time','SO2MODC','spnum','so2_lbs']][0:10]) 
        return df


    def nowarning_plot(self, save=True, quiet=True, maxfig=10):
        with warnings.catch_warnings():
             warnings.simplefilter("ignore")
             self.plot(save, quiet, maxfig)

    def plot(self, save=True, quiet=True, maxfig=10):
        """plot time series of emissions"""
        if self.df.empty:
            print('PLOT EMPTY')
            self.find()
        sns.set()
        namehash = df2hash(self.df, "oris", "facility_name")
        # ---------------
        df = obs_util.timefilter(self.df, [self.d1, self.d2])
        df = self.modc2spnum(df)
        cols = ["oris", "spnum"]
        data1 = pd.pivot_table(
            df, index=["time"], values="so2_lbs", columns=cols, aggfunc=np.sum
        )
        data2 = pd.pivot_table(
            df, index=["time"], values="SO2MODC", columns=cols, aggfunc=np.sum
        )
        # ---------------
        # data1 = cems_api.cemspivot(self.df,
        #    ("so2_lbs"), cols=['oris'], daterange=[self.d1, self.d2], verbose=False)
        #print("SVCEMS plot method")
        #print("*****************")
        #print(data1.columns)
        #print("*****************")
        clrs = ["b.", "g.", "r."]
        jjj = 0
        ploc = 0
        for ky in data1.keys():
            loc = ky[0]
            spnum = ky[1]
            if spnum==1: clr = "b."
            elif spnum==2: clr = "g."
            elif spnum==3: clr = "r."
            else: clr = 'k.'
            if loc != ploc:
                self.fignum += 1
                jjj = 0
            fig = plt.figure(self.fignum)
            ax = fig.add_subplot(2, 1, 1)
            ax2 = fig.add_subplot(2, 1, 2)
            data = data1[ky] * self.lbs2kg
            ax.plot(data, clr)
            ax2.plot(data2[ky], clr)
            
            ax.set_ylabel("SO2 mass kg")
            ax2.set_ylabel("SO2 MODC value")
            plt.sca(ax) 
            plt.title(str(loc) + " " + namehash[loc])
            if save:
                figname = self.tdir + "/cems." + str(int(loc)) + ".jpg"
                plt.savefig(figname)
            if self.fignum > maxfig:
                if not quiet:
                    plt.show()
                plt.close("all")
                self.fignum = 0
            ploc = loc
            jjj += 1
        plt.show()
        # self.fignum += 1

    def map(self, ax):
        """plot location of emission sources"""
        # if self.cems.df.empty:
        #    self.find()
        plt.sca(ax)
        oris = self.df["oris"].unique()
        if isinstance(oris, str):
            oris = [oris]
        lathash = df2hash(self.df, "oris", "latitude")
        lonhash = df2hash(self.df, "oris", "longitude")
        # fig = plt.figure(self.fignum)
        for loc in oris:
            try:
                lat = lathash[loc]
            except:
                loc = None
            if loc:
                lat = lathash[loc]
                lon = lonhash[loc]
                # print('PLOT', str(lat), str(lon))
                # plt.text(lon, lat, (str(loc) + ' ' + str(self.meanhash[loc])), fontsize=12, color='red')
                # pstr = str(loc) + " \n" + str(int(self.meanhash[loc])) + "kg"
                # if self.meanhash[loc] > self.ethresh:
                if loc in self.goodoris:
                    # ax.text(lon, lat, pstr, fontsize=12, color="red")
                    ax.plot(lon, lat, "ko")
                else:
                    ax.text(lon, lat, str(int(loc)), fontsize=8, color="k")
                    ax.plot(lon, lat, "k.")
