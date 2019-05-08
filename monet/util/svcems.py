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
# from arlhysplit.runh import source_generator
# from arlhysplit.runh import create_plume
# from arlhysplit.tcm import TCM
from monet.utilhysplit import emitimes

# from monet.obs.epa_util import convert_epa_unit

"""
SEmissions class
"""

class SourceSummary:

    def __init__(self, tdir='./', fname='source_summary.csv', data=pd.DataFrame()):
          
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
        tempdf=self.sumdf[['ORIS','Max(lbs)']]
        tempdf.groupby('ORIS').max() 
        df = tempdf[tempdf['Max(lbs)'] >  threshold]
        goodoris = df['ORIS'].unique()
        return goodoris

    def operatingtime(self, data1):
        grouplist = ['oris', 'unit' ]
        keep = grouplist.copy()
        keep.append('OperatingTime')
        data1 = cems_api.keepcols(data1, keep)
        optime = data1.groupby(grouplist).sum()
        optime.reset_index(inplace=True) 
        return optime 

    def  create(self,data1):
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
        print(data1.columns)
        optime = self.operatingtime(data1)
        # only average when plant was operating.
        #data0 = data1.copy()
        # only average when plant was operating.
        data1 = data1[data1['OperatingTime']>0]
        # 
        grouplist = ['oris', 'unit', 'facility_name', 'latitude','longitude', 'stackht']
        keep = grouplist.copy()
        keep.append('so2_lbs')
        print(keep)
        # drop columns not in the keep list.
       
        data1 = cems_api.keepcols(data1, keep)
       
        # get the mean of so2_lbs
        meandf = data1.groupby(grouplist).mean()
        # get the max of so2_lbs
        maxdf = data1.groupby(grouplist).max()
        meandf.reset_index(inplace=True) 
        maxdf.reset_index(inplace=True) 
        # merge so mean and max in same DataFrame
        sumdf = pd.merge(meandf, maxdf, how='left', left_on=grouplist,
                         right_on=grouplist)
        
        sumdf = pd.merge(sumdf, optime, how='left', left_on=['oris','unit'],
                         right_on=['oris','unit'])
        sumdf.columns= columns
        return sumdf

    def __str__(self):
        print('Placeholder for Source Summary String')

    def load(self, tdir=None, name=None):
        if not name: name = self.fname
        if not tdir: tdir = self.tdir 
        if os.path.isfile(tdir + name):
            df = pd.read_csv(tdir + name, header=None)
        else:
            df = pd.DataFrame()
        return df

    def print(self, tdir='./', name="source_summary.csv"):
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

    def __init__(self, dates, area,  tdir="./", source_thresh=100):
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
        """
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
        self.meanhash={}

    def find(self, testcase=False, byunit=False, verbose=False):
        """find emissions using the CEMS class

           prints out list of emissions soures with information about them.

        """
        area = self.area
        if testcase:
            efile = "emission_02-28-2018_103721604.csv"
            self.cems.load(efile, verbose=verbose)
        else:
            data = self.cems.add_data([self.d1, self.d2], area,  verbose=True)
        source_summary = SourceSummary(data=data)
        self.meanhash = df2hash(source_summary.sumdf,'ORIS','Max(lbs)')
        print('MEANHASH')
        print(self.meanhash)

        # remove sources which do not have high enough emissions.
        self.goodoris = source_summary.check_oris(self.ethresh)
        self.df = data[data['oris'].isin(self.goodoris)]
        source_summary.print()


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
            self.find()
        ut = unit
        sources = cems_api.cemspivot(self.df,
            (stype), cols=['oris','stackht'], daterange=[self.d1, self.d2], verbose=False)
        droplist=[]
        cnew = []
        if verbose: print('----GET SOURCES columns------')
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
        lonhash = df2hash(self.df, 'oris','latitude')
        lathash = df2hash(self.df, 'oris','longitude')
        newcolumn = []
        for val in sources.columns:
            lat = lathash[val[0]]
            lon = lonhash[val[0]]
            newcolumn.append((val[0], val[1], lat, lon))
        sources.columns = newcolumn
        #######################################################################
        #######################################################################
        return sources

    # def create_heatfile(self,edate, schunks=1000, tdir='./', unit=True):

    def create_emitimes(self, edate, schunks=1000, tdir="./", unit=True):
        """
        create emitimes file for CEMS emissions.
        edate is the date to start the file on.
        Currently, 24 hour cycles are hard-wired.
        """
        df = self.get_so2_sources(unit=unit)
        print('CREATE EMITIMES in SVCEMS')
        print(df[0:72])
        dfheat = df *0
        #dfheat = self.get_heat(unit=unit)
        #if unit:
        #    dfstack = self.get_stackvalues(unit=unit)
        locs = df.columns.values
        done = False
        iii = 0
        d1 = edate
        while not done:
            d2 = d1 + datetime.timedelta(hours=schunks - 1)
            dftemp = df.loc[d1:d2]
            hdf = dfheat[d1:d2]
            if unit:
                sdf = dfstack[d1:d2]
            if dftemp.empty:
                break
            self.emit_subroutine(dftemp, hdf, d1, schunks, tdir, unit=unit)
            if unit:
                self.emit_subroutine(
                    dftemp, sdf, d1, schunks, tdir, unit=unit, bname="STACKFILE"
                )
            d1 = d2 + datetime.timedelta(hours=1)
            iii += 1
            if iii > 1000:
                done = True
            if d1 > self.d2:
                done = True

    # def emit_subroutine(self, df, dfheat):

    def emit_subroutine(
        self, df, dfheat, edate, schunks, tdir="./", unit=True, bname="EMIT"
    ):
        """
        create emitimes file for CEMS emissions.
        edate is the date to start the file on.
        Currently, 24 hour cycles are hard-wired.
        """
        # df = self.get_so2()
        # dfheat = self.get_heat()
        locs = df.columns.values
        for hdr in locs:
            # print('HEADER', hdr)
            d1 = edate  # date to start emitimes file.
            dftemp = df[hdr]
            dfh = dfheat[hdr]

            oris = hdr[0]
            ename = bname + str(oris)
            if unit:
                sid = hdr[4]
                ename += "." + str(sid)
            height = hdr[1]
            lat = hdr[2]
            lon = hdr[3]
            # hardwire 1 hr duraton of emissions.
            record_duration = "0100"
            area = 1
            # output directory is determined by tdir and starting date.
            # chkdir=True means date2dir will create the directory if
            # it does not exist already.
            odir = date2dir(tdir, edate, dhour=schunks, chkdir=True)
            ename = odir + ename + ".txt"
            efile = emitimes.EmiTimes(filename=ename)
            if "STACK" in bname:
                hstring = efile.header.replace(
                    "HEAT(w)", "DIAMETER(m) TEMP(K) VELOCITY(m/s)"
                )
                efile.modify_header(hstring)
            # hardwire 24 hour cycle length
            dt = datetime.timedelta(hours=24)
            efile.add_cycle(d1, "0024")
            for date, rate in dftemp.iteritems():
                if date >= edate:
                    heat = dfh[date]
                    check = efile.add_record(
                        date, record_duration, lat, lon, height, rate, area, heat
                    )
                    if not check:
                        d1 = d1 + dt
                        efile.add_cycle(d1, "0024")
                        check2 = efile.add_record(
                            date, record_duration, lat, lon, height, rate, area, heat
                        )
                        if not check2:
                            print("sverify WARNING: record not added to EmiTimes")
                            print(date.strftime("%Y %m %d %H:%M"))
                            print(str(lat), str(lon), str(rate), str(heat))
                            break
            efile.write_new(ename)

    def plot(self, save=True, quiet=True, maxfig=10):
        """plot time series of emissions"""
        if self.cems.df.empty:
            self.find()
        sns.set()
        namehash = cems_api.get_lookuphash(self.df, 'oris', 'facility_name')
        data1 = cems_api.cemspivot(self.df, 
            ("so2_lbs"), cols=['oris'], daterange=[self.d1, self.d2], verbose=False)
        print('SVCEMS plot method')
        print("*****************")
        print(data1.columns)
        print("*****************")
        for loc in data1.keys():
            print(loc)
            fig = plt.figure(self.fignum)
            ax = fig.add_subplot(1, 1, 1)
            data = data1[loc] * self.lbs2kg
            ax.plot(data, "--b.")
            plt.ylabel("SO2 mass kg")
            plt.title(str(loc) + " " + namehash[loc])
            if save:
                figname = self.tdir + "/cems." + str(int(loc)) + ".jpg"
                plt.savefig(figname)
            if self.fignum > maxfig:
                if not quiet:
                    plt.show()
                plt.close("all")
                self.fignum = 0
            print("plotting cems figure " + str(self.fignum))
            self.fignum += 1

    def map(self, ax):
        """plot location of emission sources"""
        #if self.cems.df.empty:
        #    self.find()
        plt.sca(ax)
        oris = self.df['oris'].unique()
        print(oris)
        lonhash = cems_api.get_lookuphash(self.df, 'oris','latitude')
        lathash = cems_api.get_lookuphash(self.df, 'oris','longitude')
        # fig = plt.figure(self.fignum)
        for loc in oris:
            try: 
                lat = lathash[loc]
            except:
                loc= None
            if loc:
                lat = lathash[loc]
                lon = lonhash[loc]
                # print('PLOT', str(lat), str(lon))
                # plt.text(lon, lat, (str(loc) + ' ' + str(self.meanhash[loc])), fontsize=12, color='red')
                #pstr = str(loc) + " \n" + str(int(self.meanhash[loc])) + "kg"
                #if self.meanhash[loc] > self.ethresh:
                if loc in self.goodoris:
                    #ax.text(lon, lat, pstr, fontsize=12, color="red")
                    ax.plot(lon, lat, "ko")
                else:
                    ax.text(lon, lat, str(int(loc)), fontsize=8, color="k")
                    ax.plot(lon, lat, "k.")

