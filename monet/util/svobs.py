import os
import subprocess
import pandas as pd
import numpy as np
import pickle as pickle
from optparse import OptionParser
import matplotlib.pyplot as plt
import datetime
import sys
import seaborn as sns
from monet.obs import cems_mod
from monet.obs import airnow
from monet.obs import aqs as aqs_mod
from monet.obs import ish
import monet.obs.obs_util as obs_util

# from arlhysplit import runh
from monet.util.svdir import date2dir

# from arlhysplit.models.datem import mk_datem_pkl
from monet.obs.epa_util import convert_epa_unit
from monet.util import tools

"""
WORKING ON:
check method looks at correlation of wind with SO2

"""


def get_tseries(df, siteid, var="obs", svar="siteid", convert=False):
    qqq = df["siteid"].unique()
    df = df[df[svar] == siteid]
    df.set_index("time", inplace=True)
    mult = 1
    if convert:
        mult = 1 / 2.6178
    series = df[var] * mult
    return series


def getdirection(p1, p2):
    """

    """
    deg2met = 111.0  # meters in one degree
    dlat = (p1[0] - p2[0]) * deg2met
    dlon = (p1[1] - p2[1]) * deg2met
    theta = np.arctan(dlon / dlat) * 180 / np.pi
    if dlon > 0 and dlat > 0:
        theta = theta
    elif dlat < 0:
        theta = 180 + theta
    elif dlon < 0 and dlat > 0:
        theta = 360 + theta

    distance = (dlat ** 2 + dlon ** 2) ** 0.5
    return theta, distance


class SObs(object):
    """This class for running the SO2 HYSPLIT verification.

       methods
       -------
       find
       plot
       save (saves to a csv file)
       read_csv (reads from csv file)
       check
    """

    def __init__(self, dates, area, states=["nd"], tdir="./"):
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
        self.states = states

        # top level directory for outputs
        self.tdir = tdir

        # area to consider
        self.area = area

        # name of pkl file to save data to.
        self.pfile = (
            "./"
            + "obs"
            + self.d1.strftime("%Y%m%d.")
            + self.d2.strftime("%Y%m%d.")
            + "pkl"
        )
        # name of csv file to save data to.
        self.csvfile = (
            "obs" + self.d1.strftime("%Y%m%d.") + self.d2.strftime("%Y%m%d.") + "csv"
        )

        # keeps track of current figure number for plotting
        self.fignum = 1

        # self obs is a Dataframe returned by either the aqs or airnow MONET
        # class.
        self.obs = pd.DataFrame()
        # siteidlist is list of siteid's of measurement stations that we want to look at.
        # if emptly will look at all stations in the dataframe.
        self.siteidlist = []

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

    def plot(self, save=True, quiet=True, maxfig=10):
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

    def read_csv(self, name, hdrs=[0]):
        # print('in subroutine read_csv', name)
        def to_datetime(d):
            return datetime.datetime.strptime(d, "%Y-%m-%d %H:%M:%S")

        obs = pd.read_csv(name, sep=",", header=hdrs, converters={"time": to_datetime})
        return obs

    def create_pickle(self, tdir="./"):
        pickle.dump(self.obs, open(tdir + self.pfile, "wb"))

    def find(
        self,
        verbose=False,
        pload=True,
        getairnow=False,
        tdir="./",
        test=False,
        units="UG/M3",
    ):
        """
        Parameters
        -----------
        verbose   : boolean
        pload     : boolean
                    if True try to load from csv file.
        getairnow : boolean
        tdir      : string
        test      : boolean
        """
        area = self.area

        make_csv = True  # to create/load from a csv file set to TRUE
        if test:
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
        elif pload:
            try:
                print("trying to load file")
                print(tdir + self.csvfile)
                self.obs = self.read_csv(tdir + self.csvfile, hdrs=[0])
            except BaseException:
                pload = False
            mload = True
            try:
                met_obs = self.read_csv(tdir + "met" + self.csvfile, hdrs=[0, 1])
            except BaseException:
                mload = False
                print("did not load metobs from file")
            # except:
            #    print("No met file to load")
            #    print(tdir + 'met' + self.csvfile)
            # print('Failed to load')
            if pload:
                print("Loaded csv file file " + tdir + self.csvfile)
        if not pload:
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
       
        print("HEAD", self.obs.columns.values)
        # filter by area.
        if area:
            self.obs = obs_util.latlonfilter(
                self.obs, (area[0], area[1]), (area[2], area[3])
            )
        rt = datetime.timedelta(hours=72)
        self.obs = obs_util.timefilter(self.obs, [self.d1, self.d2 + rt])
        # save all the data here.
        if not pload:
            if make_csv:
                self.save(tdir, self.csvfile)
                # now create a dataframe with met data.
                # print(self.obs.columns.values)
                print("saving to file ", tdir + "met" + self.csvfile)
        # else:
        # if not mload:
        print("Making metobs from obs")
        met_obs = tools.long_to_wideB(self.obs)  # pivot table
        met_obs.to_csv(tdir + "met" + self.csvfile, header=True, float_format="%g")

        # now create a dataframe with data for each site.
        obs_info = tools.get_info(self.obs)
        print("saving to file ", tdir + "info_" + self.csvfile)
        obs_info.to_csv(tdir + "info_" + self.csvfile, float_format="%g")
        self.met = met_obs
        # this would be used for filtering by a list of siteid's.
        siteidlist = np.array(self.siteidlist)
        if siteidlist.size:
            self.obs = self.obs[self.obs["siteid"].isin(siteidlist)]
            iii = 0
            sym = [["r.", "bd"], ["r.", "c."]]
            # for sid in siteidlist:
            #    print('HERE -------------------' + str(sid))
            #    #self.obs.check_mdl(sid, sym=sym[iii])
            #    iii+=1
            #    plt.show()
        if verbose:
            obs_util.summarize(self.obs)
        self.ohash = obs_util.get_lhash(self.obs, "siteid")

        # get rid of the meteorological variables in the file.
        self.obs = self.obs[self.obs["variable"] == "SO2"]
        # convert units of SO2
        units = units.upper()
        if units == "UG/M3":
            self.obs = convert_epa_unit(self.obs, obscolumn="obs", unit=units)

    def check(self):
        """
        plot obs versus some of the met data available.
        """
        # print(type(self.met))
        # print(self.met.columns.values)
        cols = self.met.columns.values
        for val in cols:
            if "siteid" in val[0]:
                cname = val
        # cname = ('siteid', 'Unnamed: 2_level_1')
        sra = self.met[cname].unique()
        print(sra)
        for site in sra:
            df = self.met[self.met[cname] == site]

            print(df.columns.values)
            xtest = df[("WD", "Degrees Compass")]
            ytest = df[("WS", "m/s")]
            ztest = df[("SO2", "ppb")]
            y = df[("SO2", "ppb")]
            x = ("WD", "Degrees Compass")
            y = ("SO2", "ppb")
            z = ("WS", "m/s")

            if np.isnan(xtest).all():
                continue
            if np.isnan(ztest).all():
                continue
            # print(x[1:10])
            # print(y[1:10])
            # camp=sns.cubehelix_palette(as_cmap=True, dark=0, light=1,
            #                           reverse=True)
            fig = plt.figure(1)
            ax1 = fig.add_subplot(1, 3, 1)
            plt.set_gca(ax1)
            ggg = sns.jointplot(x=x, y=y, data=df, kind="hex", color="b")
            ggg.plot_joint(plt.scatter, c="m", s=30, linewidth=1, marker=".")
            ax2 = fig.add_subplot(1, 3, 2)
            plt.set_gca(ax2)
            ggg = sns.jointplot(x=z, y=y, data=df, kind="hex", color="b")
            ggg.plot_joint(plt.scatter, c="m", s=30, linewidth=1, marker=".")
            ax3 = fig.add_subplot(1, 3, 3)
            plt.set_gca(ax3)
            ggg = sns.jointplot(x=x, y=z, data=df, kind="hex", color="b")
            ggg.plot_joint(plt.scatter, c="m", s=30, linewidth=1, marker=".")

            # sns.jointplot(x=x, y=y, kind="hex", camp=camp)
            print("---------------")
            # plt.plot(x,y, 'k.')
            plt.title(str(site), y=0.8)
            plt.show()
            # plt.scatter(xtest,ytest,c=ztest)
            # plt.contourf([xtest,ytest],ztest)
            # plt.show()

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

    def old_obs2datem(self):
        """
        write datemfile.txt. observations in datem format
        """
        sdate = self.d1
        edate = self.d2
        obs_util.write_datem(self.obs, sitename="siteid", drange=[sdate, edate])

    def get_map_info(self):
        return self.ohash

    def map(self, ax):
        """
        ax : map axes object?
        """
        plt.sca(ax)
        clr = sns.xkcd_rgb["cerulean"]
        # sns.set()
        for key in self.ohash:
            latlon = self.ohash[key]
            plt.text(latlon[1], latlon[0], str(key), fontsize=7, color="red")
            plt.plot(latlon[1], latlon[0], color=clr, marker="*")
        return 1
