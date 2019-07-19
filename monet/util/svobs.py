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
from monet.obs import aqs as aqs_mod
from monet.obs import airnow
import monet.obs.obs_util as obs_util

# from arlhysplit import runh
from monet.util.svdir import date2dir

# from arlhysplit.models.datem import mk_datem_pkl
from monet.obs.epa_util import convert_epa_unit
from monet.util import tools

"""
FUNCTIONS

find_obs_files


WORKING ON:
check method looks at correlation of wind with SO2

"""



    


def get_info(df):
    rdf = df.drop(['obs','time','variable','units','time_local'],axis=1)
    rdf.drop_duplicates(inplace=True)
    #print('HEADER------')
    #print(rdf.columns.values)
    return rdf  

def find_obs_files(tdirpath, sdate, edate, tag=None):
    fnamelist = []
    if tag:
       fname = 'tag' + '.obs' '.csv'
       if os.path.isfile(os.path.join(tdirpath,fname)):
          fnamelist = [fname]
    else:    
        file_start = None
        file_end = None
        for item in os.listdir(tdirpath):
            #if os.path.isfile(os.path.join(tdirpath,item)):
               if item[0:3] == 'obs':
                  temp = item.split('.')
                  file_start = datetime.datetime.strptime(temp[0],"obs%Y%m%d")
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
    qqq = df["siteid"].unique()
    df = df[df[svar] == siteid]
    df.set_index("time", inplace=True)
    mult = 1
    if convert:
        mult = 1 / 2.6178
    series = df[var] * mult
    return series


def vmixing2metobs(vmix, obs):
    """
    take vmixing dataframe and SO2 measurement dataframe and 
    combine into a MetObs object.
    """
    print('--------------')
    
    obs = obs[['time','siteid','obs','mdl']]
    #print(obs.dtypes)
    #print(vmix.dtypes)
    obs.columns = ['date','sid','so2','mdl']
    print(obs['sid'].unique())
    print(vmix['sid'].unique())


    dfnew = pd.merge(obs,
                     vmix,
                     how='left',
                     left_on=['date','sid'],
                     right_on=['date','sid']
                     )
    dfnew = dfnew.drop_duplicates()
    print(dfnew[0:10])
    met = MetObs(tag='vmix')
    met.from_vmix(dfnew)
    return  met       
 
     

def heatmap(x,y, ax, bins=(50,50)):
    heatmap, xedges, yedges = np.histogram2d(x,y, bins=(bins[0],bins[1]))
    extent = [xedges[0], xedges[-1], yedges[0], yedges[-1]]
    cb = ax.imshow(heatmap, extent=extent)
    
def hexbin(x,y,ax,sz=50,mincnt=1):
    cm='Paired'
    cb = ax.hexbin(x,y, gridsize=sz, cmap=cm, mincnt=mincnt)
    plt.colorbar(cb)

def jointplot(x, y, data, fignum=1):
    fig = plt.figure(fignum)
    #ax1 = fig.add_subplot(1, 3, 1)
    #plt.set_gca(ax1)
    ggg = sns.jointplot(x=x, y=y, data=df, kind="hex", color="b")
    ggg.plot_joint(plt.scatter, c="m", s=30, linewidth=1, marker=".")

class MetObs(object):

    def __init__(self, tag=None):
        self.df = pd.DataFrame()
        self.columns_original = []
        self.fignum = 1
        self.tag = tag

    def from_vmix(self,df):
        self.df = df
        self.columns_original = self.df.columns.values
        self.rename_columns()
       

    def from_obs(self, obs):
        print("Making metobs from obs")
        self.df = tools.long_to_wideB(obs)  # pivot table
        self.columns_original = self.df.columns.values
        self.rename_columns()
        # checking to see if there is met data in the file.
        testcols = ['WD','RH','TEMP','WS']
        overlap = [x for x in testcols if x in self.df.columns.values]
        if not overlap:
           self.df = pd.DataFrame()  
           print('No Met Data Found') 
        else:
           self.df = self.df.dropna(axis=0, how='all', subset=overlap)


    def to_csv(self,tdir, csvfile=None):
        if self.df.empty: return -1
        if not csvfile: csvfile = ''
        df = self.df.copy()
        df.columns = self.columns_original
        df.to_csv(tdir + "met" + csvfile, header=True, float_format="%g")
          
 
    def rename_sub(self, istr):
        rstr = istr
        if 'WD' in istr: rstr = 'WDIR'
        if 'RH' in istr: rstr = 'RH'
        if 'T02M' in istr: rstr = 'TEMP'
        if 'WS' in istr: rstr = 'WS'
        if 'date' in istr: rstr = 'time'
        if 'SO2' in istr.upper(): rstr = 'SO2'
        if 'sid' in istr: rstr = 'siteid'
        return rstr

    def get_sites(self):
        if self.df.empty: return []
        return self.df['siteid'].unique()
   
    def rename_columns(self):
        newc = []
        for col in self.df.columns.values:
            if isinstance(col, tuple):
               if 'obs' not in col[0]:
                   val = col[0].strip()
               else:
                   val = col[1].strip()
            else:
               val = col
            newc.append(self.rename_sub(val))
        self.df.columns = newc 
        
    def nowarning_plothexbin(self, save=True, quiet=True):
        # get "Adding an axes using the same arguments as previous axes
        # warnings. This is intended behavior so want to suppress warning.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.plothexbin(save, quiet)


    def plot_ts(self, save=False, quiet=False):
        if self.df.empty: return -1
        sns.set()
        slist = self.get_sites()
        print('SSSSSSSSS ', slist)
        for site in slist:
            fig = plt.figure(self.fignum)
            fig.set_size_inches(10,5)
            # re-using these axis produces a warning.
            ax1 = fig.add_subplot(1,1,1)
            ax2 = ax1.twinx()

            df = self.df[self.df['siteid'] == site]
            df = df.set_index('time')
            so2 = df['SO2']
            wdir = df['WDIR']
            ax2.plot(wdir, 'b.')
            ax1.plot(so2, '-k')

            ax1.set_ylabel('so2 (ppb)')
            ax2.set_ylabel('Wind direction (degrees)')
            plt.title(str(site))
            if not quiet:
                plt.show()
            if save:
                tag = self.tag
                if not tag: tag = ''
                plt.savefig(tag + str(site) + '.met_ts.jpg')
            plt.close() 

    def plothexbin(self, save=True, quiet=True): 
        if self.df.empty: return -1
        slist = self.get_sites()
        print('SSSSSSSSS ', slist)
        for site in slist:
            fig = plt.figure(self.fignum)
            fig.set_size_inches(10,5)
            # re-using these axis produces a warning.
            ax1 = fig.add_subplot(1,2,1)
            ax2 = fig.add_subplot(1,2,2)

            df = self.df[self.df['siteid'] == site]
            print('HEXBIN for site ' , site) 
            print(df[0:10])
            #df.columns = self.met_header(df.columns)
            #print(df.columns.values)
            #xtest = df[("WD", "Degrees Compass")]
       
            xtest = df["WDIR"]
            ytest = df["WS"]
            ztest = df["SO2"]
        
            if np.isnan(xtest).all():
                print('No data WDIR')
                continue
            if np.isnan(ztest).all():
                print('No data so2')
                continue
    
            hexbin(xtest, ztest, ax1)  
            hexbin(ytest, ztest, ax2) 
            ax1.set_xlabel('Wind Direction ')
            ax2.set_xlabel('Wind Speed ')
            ax1.set_ylabel('SO2 (ppb)')
            plt.title(str(site))
            plt.tight_layout() 
            if save:
                tag = self.tag
                if not tag: tag = ''
                plt.savefig(tag + str(site) + '.met_dist.jpg')
            #self.fignum +=1
            if not quiet:
                plt.show()
            # clearing the axes does not
            # get rid of warning.
            plt.cla()
            plt.clf()
            plt.close()  


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

    def plot(self, save=True, quiet=True, maxfig=10 ):
        """plot time series of observations"""
        sra = self.obs["siteid"].unique()
        print("PLOT OBSERVATION SITES")
        print(sra)
        sns.set()
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
        if verbose:
            obs_util.summarize(self.obs)
        # get rid of the meteorological variables in the file.
        #self.obs = self.obs[self.obs["variable"] == "SO2"]
        # convert units of SO2
        units = units.upper()
        if units == "UG/M3":
            self.obs = convert_epa_unit(self.obs, obscolumn="obs", unit=units)

    def get_met_data(self):
        """
        Returns a MetObs object.
        """
        print("Making metobs from obs")
        meto = MetObs()
        meto.from_obs(self.dfall)
        return meto

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
