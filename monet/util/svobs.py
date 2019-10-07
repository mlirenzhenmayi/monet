import os
#import subprocess
import pandas as pd
import numpy as np
import pickle as pickle
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import datetime
import sys
import seaborn as sns
import warnings


from monet.utilhysplit import statmain
#from monet.utilhysplit import sigprocess
from monet.obs import aqs as aqs_mod
from monet.obs import airnow
import monet.obs.obs_util as obs_util
from monet.util.svdir import date2dir
#from monet.util.svmet import MetObs

"""
FUNCTIONS

find_obs_files
print_info 
read_csv
generate_obs
get_tseries

CLASSES
SObs

"""



def print_info(df, cname):
    """
    creates the info_obs files.
    """
    rdf = df.drop(['obs','time','variable','units','time_local'],axis=1)
    rdf.drop_duplicates(inplace=True)
    rdf.to_csv(cname, float_format="%g")
    #print('HEADER------')
    #print(rdf.columns.values)
    return 1 

def find_obs_files(tdirpath, sdate, edate, ftype='obs', tag=None):
    fnamelist = []
    if tag:
       fname = 'tag' + '.' + ftype +  '.csv'
       if os.path.isfile(os.path.join(tdirpath,fname)):
          fnamelist = [fname]
    else:    
        file_start = None
        file_end = None
        for item in os.listdir(tdirpath):
            #if os.path.isfile(os.path.join(tdirpath,item)):
               if item[0:3] == ftype:
                  temp = item.split('.')
                  file_start = datetime.datetime.strptime(temp[0],ftype+"%Y%m%d")
                  file_end = datetime.datetime.strptime(temp[1],"%Y%m%d")
                  file_end += datetime.timedelta(hours=23)

                  if sdate >=file_start and edate <=file_end:
                     fnamelist.append(item)
    return fnamelist

def read_csv(name, hdrs=[0]):
    # print('in subroutine read_csv', name)
    def to_datetime(d):
        return datetime.datetime.strptime(d, "%Y-%m-%d %H:%M:%S")
    obs = pd.read_csv(name, sep=",", header=hdrs, converters={"time": to_datetime})
    return obs

def generate_obs(siteidlist, obsfile):
    """
    yields a time series of measurements for each site in the siteidlist.
    """
    #obsfile = self.obsfile.replace('info_','')
    str1 = obsfile.split('.')
    dt1 = datetime.datetime.strptime(str1[0], "obs%Y%m%d") 
    dt2 = datetime.datetime.strptime(str1[1], "%Y%m%d") 
    area=''
    obs = SObs([dt1, dt2], area)
    if not os.path.isfile(obsfile):
       print(obsfile + ' does not exist')
    odf = read_csv(obsfile, hdrs=[0])
    print('HERE', odf[0:1])
    print(odf.columns)
    odf = odf[odf["variable"] == "SO2"]
    for sid in siteidlist:
        # gets a time series of observations at sid.
        ts = get_tseries(odf, sid, var='obs', svar='siteid', convert=False) 
        yield ts

def get_tseries(df, siteid, var="obs", svar="siteid", convert=False):
    #qqq = df["siteid"].unique()
    df = df[df[svar] == siteid]
    df.set_index("time", inplace=True)
    mult = 1
    #if convert:
    #    mult = 1 / 2.6178
    series = df[var] * mult
    return series


class SObs(object):
    """This class for running the SO2 HYSPLIT verification.
    

       methods
       -------
       find
       plot
       save (saves to a csv file)
       check
    """
    def __init__(self, dates, area, tdir="./", tag=None):
        """
        area is a tuple or list of four floats
        states : list of strings
                 Currently not used
        tdir : string : top level directory
        TODO - currently state codes are not used.
        """
        # dates to consider.
        self.d1 = dates[0]
        self.d2 = dates[1]
        # not used
        #self.states = states

        # top level directory for outputs
        self.tdir = tdir

        # area to consider
        self.area = area

        # name of csv file to save data to.
        self.csvfile = None
        self.pload = True
        self.find_csv()
        
        # keeps track of current figure number for plotting
        self.fignum = 1

        # self obs is a Dataframe returned by either the aqs or airnow MONET
        # class.
        self.obs = pd.DataFrame()
        self.dfall = pd.DataFrame()
        # siteidlist is list of siteid's of measurement stations that we want to look at.
        # if emptly will look at all stations in the dataframe.
        self.siteidlist = []

    def find_csv(self):
         # checks to see if a downloaded csv file in the correct date range
         # exists.
         names = []
         names =  find_obs_files(self.tdir, self.d1, self.d2, tag=None)
         # if it exists then
         if len(names) > 0:
            self.csvfile = (names[0])
            self.pload = True
         else: 
            self.csvfile = ("obs" + self.d1.strftime("%Y%m%d.") +
                             self.d2.strftime("%Y%m%d.") + "csv")
            self.pload = False

    def plumeplot(self):
        """
        Not working?
        To plot with the plume want list for each time of
        location and value
        """
        phash = {}
        temp = obs_util.timefilter(self.obs, [d1, d1])
        sra = self.obs["siteid"].unique()
        # for sid in sra:
        #    phash[d1] = (sid, self.obs
        #     df = df[df[svar] == siteid]
        #     val = df['obs']

    def generate_ts(self, sidlist=None):
        """
        Input
        list of site ids (optional).
        If None will loop through all.
        Returns
        siteid (int), pandas time series of obs, pandas time series of mdl.
        """
 
        # get list of siteids.
        if not sidlist:
            sra = self.obs["siteid"].unique()
        else:
            sratest = self.obs["siteid"].unique()
            sra = []
            # test to make sure 
            for sid in sidlist:
                if sid in sratest: sra.append(sid) 
                else: print('WARNING siteid not found ', str(sid), type(sid)) 
        for sid in sra:
            ts = get_tseries(self.obs, sid, var="obs", svar="siteid", convert=False)
            ms = get_tseries(self.obs, sid, var="mdl", svar="siteid")
            yield sid, ts, ms

    def autocorr(self):
        """
        autocorrelation of measurements
        """
        for sid, ts, ms in self.generate_ts(sidlist=None):
            alist = []
            nlist = np.arange(0,48)
            for nnn in nlist:
                alist.append(ts.autocorr(lag=nnn))
            plt.plot(nlist, alist, 'k.')
            plt.title(str(sid))
            plt.savefig(str(sid) + 'obs.autocorr.jpg')
            plt.show()    

    def get_peaks(self, sidlist=None, pval=[0.95,1], plotfigs=True):
        """
        for each obs data series creates a CDF of values which are above mdl.
        Finds values which have prob between pval[0] and pval[1] and returns
        series of just those values.

        Can be used to identify peaks or valleys.
        """
        for sid, ts, ms in self.generate_ts(sidlist=sidlist):
            # get minimum detectable level
            mdl = np.max(ms.values)
            # create copy of series
            tso = ts.copy()
            # include only values above mdl
            ts = ts[ts > mdl]
            # find value in which prob(data < val) == pval 
            valA = statmain.probof(ts.values, pval[0])
            valB = statmain.probof(ts.values, pval[1])
            # data in which values are >= val.
            tsp = ts[ts >= valA]
            tsp = tsp[tsp <= valB]
            # plot peaks as well as CDF's.
            if plotfigs:
                fig = plt.figure(1)
                ax1 = fig.add_subplot(1,1,1)
                ax1.plot(tso.index.tolist(), tso.values, '-k', linewidth=0.5)
                ax1.plot(tsp.index.tolist(), tsp.values, 'r.', linewidth=0.5)
                ax1.plot(ms.index.tolist(), ms, '-b')
                plt.title(str(sid))
                fig = plt.figure(2)
                ax = fig.add_subplot(1,1,1)
                cx, cy = statmain.cdf(ts.values)
                statmain.plot_cdf(cx, cy, ax) 
                cx, cy = statmain.cdf(tso.values)
                statmain.plot_cdf(cx, cy, ax) 
                ax.plot(valA, pval[0], 'b.')
                ax.plot(valB, pval[1], 'b.')
                plt.show()
            # sid is site number
            # tsp is a time series of peaks
            yield sid, tsp 

    #def show_peaksA(self):
        # investigated using scipy signal peak finders.
        # not very satisfactory.
    #    for sid, ts, ms in self.generate_ts():
    #        tso = ts.copy()
    #        mdl = np.max(ms.values)
    #        print('MDL', mdl)
    #        zeros = ts <= mdl 
    #        ts[zeros] = 0
            
    #        fts = pd.Series(sigprocess.filter(ts), ts.index.tolist())

    #        peaks = sigprocess.findpeak_cwt(fts)
    #        peaks = sigprocess.findpeak_simple(tso) 
    #        tsp = tso.iloc[peaks] 
            
    #        plt.plot(tso.index.tolist(), tso.values, '-k', linewidth=0.5)
            #plt.plot(fts.index.tolist(), fts.values, '--g')
    #        plt.plot(tsp.index.tolist(), tsp.values, 'r.')
    #        plt.plot(ms.index.tolist(), ms, '-b')
    #        plt.title(sid)
    #        plt.show() 

    def plot(self, save=True, quiet=True, maxfig=10 ):
        """plot time series of observations"""
        sra = self.obs["siteid"].unique()
        print("PLOT OBSERVATION SITES")
        print(sra)
        sns.set()
        sns.set_style('whitegrid')
        dist = []
        if len(sra) > 20:
            if not quiet:
                print("Too many sites to pop up all plots")
            quiet = True
        for sid in sra:
            ts = get_tseries(self.obs, sid, var="obs", svar="siteid", convert=False)
            ms = get_tseries(self.obs, sid, var="mdl", svar="siteid")
            dist.extend(ts.tolist())
            fig = plt.figure(self.fignum)
            # nickname = nickmapping(sid)
            ax = fig.add_subplot(1, 1, 1)
            # plt.title(str(sid) + '  (' + str(nickname) + ')' )
            plt.title(str(sid))
            ax.set_xlim(self.d1, self.d2)
            ts.plot()
            ms.plot()
            if save:
                figname = self.tdir + "/so2." + str(sid) + ".jpg"
                plt.savefig(figname)
            if self.fignum > maxfig:
                if not quiet:
                    plt.show()
                plt.close("all")
                self.fignum = 0
            # if quiet: plt.close('all')
            print("plotting obs figure " + str(self.fignum))
            self.fignum += 1

        # sns.distplot(dist, kde=False)
        # plt.show()
        # sns.distplot(np.array(dist)/2.6178, kde=False, hist_kws={'log':True})
        # plt.show()
        # sns.distplot(np.array(dist)/2.6178, kde=False, norm_hist=True, hist_kws={'log':False, 'cumulative':True})
        # plt.show()

    def save(self, tdir="./", name="obs.csv"):
        fname = tdir + name
        self.obs.to_csv(fname)

    def read_met(self):
        tdir='./'
        mname=tdir + "met" + self.csvfile
        if(os.path.isfile(mname)):
            met = pd.read_csv(mname, parse_dates=True)
        else:
            met = pd.DataFrame()
        return(met)

    def runtest(self):
        aqs = aqs_mod.AQS()
        basedir = os.path.abspath(os.path.dirname(__file__))[:-4]
        fn = "testaqs.csv"
        fname = os.path.join(basedir, "data", fn)
        df = aqs_mod.load_aqs_file(fname, None)
        self.obs = aqs_mod.add_data2(df) 
        print("--------------TEST1--------------------------------") 
        print(self.obs[0:10])
        rt = datetime.timedelta(hours=72)
        self.obs = obs_util.timefilter(self.obs, [self.d1, self.d2 + rt])
        print("--------------TEST2--------------------------------")
        print(self.obs[0:10])
        self.save(tdir, "testobs.csv")

    def find(
        self,
        verbose=False,
        getairnow=False,
        tdir="./",
        test=False,
        units="UG/M3",
    ):
        """
        Parameters
        -----------
        verbose   : boolean
        getairnow : boolean
        tdir      : string
        test      : boolean
        """
        area = self.area
   
        if test:
           runtest
        elif self.pload:
            self.obs = read_csv(tdir + self.csvfile, hdrs=[0])
            print("Loaded csv file file " + tdir + self.csvfile)
            mload = True
            try:
                met_obs = read_csv(tdir + "met" + self.csvfile, hdrs=[0, 1])
            except BaseException:
                mload = False
                print("did not load metobs from file")
        elif not self.pload:
            print("LOADING from EPA site. Please wait\n")
            if getairnow:
                aq = airnow.AirNow()
                aq.add_data([self.d1, self.d2], download=True)
            else:
                aq = aqs_mod.AQS()
                self.obs = aq.add_data(
                    [self.d1, self.d2],
                    param=["SO2", "WIND", "TEMP", "RHDP"],
                    download=False,
                )
            # aq.add_data([self.d1, self.d2], param=['SO2','WIND','TEMP'], download=False)
            #self.obs = aq.df.copy()
       
        print("HEADERS in OBS: ", self.obs.columns.values)
        # filter by area.
        if area:
            self.obs = obs_util.latlonfilter(
                self.obs, (area[0], area[1]), (area[2], area[3])
            )
        # filter by time
        rt = datetime.timedelta(hours=72)
        self.obs = obs_util.timefilter(self.obs, [self.d1, self.d2 + rt])

        # if the data was not loaded from a file then save all the data here.
        if not self.pload:
            self.save(tdir, self.csvfile)
            print("saving to file ", tdir + "met" + self.csvfile)

        self.dfall = self.obs.copy()
        # now create a dataframe with data for each site.
        # get rid of the meteorological (and other) variables in the file.
        self.obs = self.obs[self.obs["variable"] == "SO2"]
        # added back in 8/12/2019
        print_info(self.obs, tdir+ "/info_" + self.csvfile)
        if verbose:
            obs_util.summarize(self.obs)
        # get rid of the meteorological variables in the file.
        #self.obs = self.obs[self.obs["variable"] == "SO2"]
        # convert units of SO2
        units = units.upper()
        #if units == "UG/M3":
        #    self.obs = convert_epa_unit(self.obs, obscolumn="obs", unit=units)

    #def get_met_data(self):
    #    """
    #    Returns a MetObs object.
    #    """
    #    print("Making metobs from obs")
    #    meto = MetObs()
    #    meto.from_obs(self.dfall)
    #    return meto

    def bysiteid(self, siteidlist):
        obs = self.obs[self.obs["siteid"].isin(siteidlist)]
        return obs         

    def obs2datem(self, edate, ochunks=(1000, 1000), tdir="./"):
        """
        ##https://aqsdr1.epa.gov/aqsweb/aqstmp/airdata/FileFormats.html
        ##Time GMT is time of dat that sampling began.
        edate: datetime object
        ochunks: tuple (integer, integer)
                 Each represents hours

        tdir: string
              top level directory for output.
        """
        print("WRITING MEAS Datem FILE")
        print(self.obs["units"].unique())
        d1 = edate
        done = False
        iii = 0
        maxiii = 1000
        oe = ochunks[1]
        oc = ochunks[0]
        while not done:
            d2 = d1 + datetime.timedelta(hours=oc - 1)
            d3 = d1 + datetime.timedelta(hours=oe - 1)
            odir = date2dir(tdir, d1, dhour=oc, chkdir=True)
            dname = odir + "datem.txt"

            obs_util.write_datem(
                self.obs, sitename="siteid", drange=[d1, d3], dname=dname
            )
            d1 = d2 + datetime.timedelta(hours=1)
            iii += 1
            if d1 > self.d2:
                done = True
            if iii > maxiii:
                done = True
                print("WARNING: obs2datem, loop exceeded maxiii")

    #def old_obs2datem(self):
    #    """
    #    write datemfile.txt. observations in datem format
    #    """
    #    sdate = self.d1
    #    edate = self.d2
    #    obs_util.write_datem(self.obs, sitename="siteid", drange=[sdate, edate])

    def get_map_info(self):
        ohash = obs_util.get_lhash(self.obs, "siteid")
        return ohash

    #def try_ar(self):
    #    from monet.util.armodels import ARtest
    #    for sid, ts, ms in self.generate_ts():
    #        nnn= int(len(ts)/2.0)
    #        ts1 = ts[0:nnn]
    #        ts2 = ts[nnn:]
    #        print('SITE', sid)
    #        ar = ARtest(ts1, ts2)
             

    def map(self, ax):
        """
        ax : map axes object?
        """
        ohash = obs_util.get_lhash(self.obs, "siteid")
        plt.sca(ax)
        clr = sns.xkcd_rgb["cerulean"]
        # sns.set()
        for key in ohash:
            latlon = ohash[key]
            plt.text(latlon[1], latlon[0], str(key), fontsize=7, color="red")
            plt.plot(latlon[1], latlon[0], color=clr, marker="*")
        return 1
