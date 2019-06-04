# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import numpy as np
import datetime
import time
import os
from os import path, chdir
from subprocess import call
import pandas as pd
import matplotlib.pyplot as plt
from monet.utilhysplit.statmain import MatchedData
from monet.util.svcems import SourceSummary
from monet.util.svcems import df2hash
from monet.util.svobs import SObs
from monet.util.svobs import get_tseries
import seaborn as sns
from shapely.geometry import Point
from shapely.geometry import LineString
import geopandas as gpd

from sklearn.tree import DecisionTreeClassifier
from sklearn.tree import DecisionTreeRegressor
from sklearn import tree

"""
"""


def make_dataset(df):
    """
    df should be a dataset with the appropriate variables.
    """
    # remove the target variable (so2 concentration measurement

    target = df.pop('so2').values

    dtrain = df['so2_lbs', 'wspd', 'wdir','time']

 
    #dtrain = df[['so2_lbs']].copy()
    dtree = DecisionTreeRegressor()
    fitted = dtree.fit(dtrain, target)
    dt2 = dtree(dtrain)

    pred = dtree.predict(dtrain)
   
    tree.plot_tree(fitted)
    plt.show()


def make_gpd(df, latstr, lonstr):
    
    geometry = [Point(xy) for xy in zip(df[lonstr], df[latstr])]
    df = df.drop([lonstr,latstr], axis=1)
    crs = {'init': 'epsg:4326'}
    gdf = gpd.GeoDataFrame(df, crs=crs, geometry=geometry)
    return gdf



class CemsObs(object):

    def __init__(self, obsfile, cemsfile, source_sum_file):
        """
        source_sum_file is the name of the  source_summary file.
        obsfile is the csv file.
        """
        self.obsfile = obsfile
        self.sourcesum = source_sum_file
        self.cemsfile = cemsfile
        self.sumdf = gpd.GeoDataFrame() #created by make_sumdf
        self.obs = None #SObs object

    def find_sites(self, oris, dthresh, arange=None):
        """
        returns data frame with list of measurements sites within dthresh
        (meters)  of the power plant
        """
        sumdf = gpd.GeoDataFrame() #created by make_sumdf
        if not self.sumdf.empty:
            dname = str(oris) + 'dist'
            aname = str(oris) + 'direction'
            cnames = ['siteid', 'geometry', dname, aname]
            sumdf = self.sumdf[cnames]
            sumdf = sumdf[sumdf[dname] <= dthresh]
        return sumdf

    def generate_obs(self, siteidlist):
        #obsfile = self.obsfile.replace('info_','')
        obsfile = self.obsfile
        if not os.path.isfile(obsfile):
           print(obsfile + ' does not exist')
        odf = self.obs.read_csv(obsfile, hdrs=[0])
        print('HERE', odf[0:1])
        print(odf.columns)
        odf = odf[odf["variable"] == "SO2"]
        for sid in siteidlist:
            # gets a time series of observations at sid.
            ts = get_tseries(odf, sid, var='obs', svar='siteid', convert=False) 
            yield ts    

    def get_cems(self, oris):
        cems = pd.read_csv(self.cemsfile, sep=",", index_col=[0],parse_dates=True)
        new=[]   
        for hd in cems.columns:
            temp = hd.split(',')
            temp = temp[0].replace('(','')
            try:
                new.append(int(float(temp)))
            except:
                new.append(temp)
        cems.columns = new
        #cems.set_index('time', inplace=True)
        return cems[oris]

    def get_met(self):
        met = self.obs.read_met()
        return met

    def make_sumdf(self):
        """
        creates a  geopandas dataframe with siteid, site location as POINT, distance and
        direction to each power plant.
        """
        # Needs these two files.
        obsfile = self.obsfile
        #obsfile = self.obsfile.replace('info_','')
        sourcesumfile = self.sourcesum #not used right now.

        # read cems csv file.
        sourcesum = SourceSummary().sumdf  #uses default name for file.
        sourcesum = sourcesum.groupby(['ORIS','Name','Stack height (m)',
                                       'lat','lon']).sum()
        sourcesum.reset_index(inplace=True)
        sourcesum = sourcesum[['ORIS','Name','Mean(lbs)','lat','lon']]
        sgpd = make_gpd(sourcesum, 'lat', 'lon')
        orishash = df2hash(sgpd, 'ORIS','geometry')

        # read the obs file.
        str1 = obsfile.split('.')
        dt1 = datetime.datetime.strptime(str1[0], "obs%Y%m%d") 
        dt2 = datetime.datetime.strptime(str1[1], "%Y%m%d") 
        area=''
        obs = SObs([dt1, dt2], area)
        self.obs = obs
        if not os.path.isfile(obsfile): print('not file ' + obsfile)
        odf = obs.read_csv(obsfile, hdrs=[0])
        osum = odf[['siteid','latitude','longitude']]
        osum = make_gpd(osum.drop_duplicates(), 'latitude', 'longitude')
        siteidhash = df2hash(osum,'siteid','geometry')
 
        # loop thru each measurement stations.
        for site in siteidhash.keys(): 
            #location of site
            pnt = siteidhash[site]
            # find distance  to site from all power plants
            cname = str(int(site)) + 'dist' 
            sgpd[cname] = sgpd.apply(
                               lambda row: distance(row['geometry'], pnt),
                               axis=1)
            # find direction to site from all power plants
            lname = str(int(site)) + 'direction'
            sgpd[lname] = sgpd.apply(
                               lambda row: bearing(row['geometry'], pnt),
                               axis=1)

        # loop thru each power plant.
        for oris in orishash.keys():
            # location of power plant.
            pnt = orishash[oris]

            # find distance to power plant from all sites
            cname = str(int(oris)) + 'dist' 
            osum[cname] = osum.apply(
                               lambda row: distance(row['geometry'], pnt),
                               axis=1)

            # find direction to power plant from all sites
            lname = str(int(oris)) + 'direction'
            osum[lname] = osum.apply(
                               lambda row: bearing(row['geometry'], pnt),
                               axis=1)
     
        #print('  ----------------------------------------')
        #print(osum[osum[cname]<500])
        # geopandas dataframe with siteid, site location as POINT, distance and
        # direction to each power plant.
        self.sumdf = osum
        return osum, sgpd

def gpd2csv(gpd, outfile, names={'x':'longitude','y':'latitude'}):
    df = gpd.drop('geometry', axis=1)
    df[names['x']] = gpd.geometry.apply(lambda p:p.x)
    df[names['y']] = gpd.geometry.apply(lambda p:p.y)
    df.to_csv(outfile, float_format='%g', index=False)


def distance(p1,p2):
    """
    p1 : shapely Point
    p2 : shapely Point

    x should be longitude
    y should be latitude
    """
    deg2km = 111.111  #
    a1 = p2.x-p1.x # distance in degrees
    a2 = p2.y-p1.y # distance in degrees.
    # change to meters.
    a2 = a2 * deg2km
    # estimate using latitude halfway between.
    a1 = a1 * deg2km * np.cos(np.radians(0.5*(p1.y+p2.y))) 
    return (a1**2 + a2**2)**0.5

def bearing(p1, p2):
    """
    p1 : shapely Point
    p2 : shapely Point

    x should be longitude
    y should be latitude
    """
    deg2met = 111.0  # doesn't matter.
    a1 = p2.x-p1.x # distance in degrees
    a2 = p2.y-p1.y # distance in degrees.
    # change to meters.
    a2 = a2 * deg2met
    # estimate using latitude halfway between.
    a1 = a1 * deg2met * np.cos(np.radians(0.5*(p1.y+p2.y))) 

    #a1 = np.cos(p1.y)*np.sin(p2.y)-np.sin(p1.y)*np.cos(p2.y)*np.cos(p2.x-p1.x)
    #a2 = np.sin(p2.x-p1.x)*np.cos(p2.y)
    angle = np.arctan2(a1, a2)
    angle = (np.degrees(angle) + 360) %360
    return angle


def results(dfile, runlist, xmeas=1):
    """
    reads file output by datem.
    """
    from monet.util.datem import read_dataA
    from monet.util.datem import frame2datem
    import matplotlib.pyplot as plt

    # Initialize dataframe to store c2datem output in.
    df = pd.DataFrame()
    nnn = 0
    # read output from c2datem in each subdirectory.
    dlist=[]
    for run in runlist:
        dlist.append(run.directory)

    dlist =  list(set(dlist))

    #for run in runlist:
    for rdir in dlist:
        fname = rdir + "/dataA.txt"
        print(fname)
        tempdf = read_dataA(fname)
        print(tempdf[0:10])
        if nnn == 0 and not tempdf.empty:
            df = tempdf.copy()
            nnn += 1
        elif not tempdf.empty:
            df = pd.merge(df, tempdf, how="outer")
        elif tempdf.empty:
            print("-----------------------------")
            print("WARNING: svhy.py results method empty dataframe")
            print(fname)
            print("-----------------------------")
    df["duration"] = "0100"
    df["altitude"] = 20
    # print(df[0:10])
    # frame2datem(dfile, df, cnames=['date','duration','lat', 'lon',
    #                        'obs','model','sid','altitude'] )

    # TO DO.
    # fill missing data with 0. MAY NEED TO CHANGE THIS.
    df["obs"].fillna(0, inplace=True)
    df["model"].fillna(0, inplace=True)
    df2 = df.set_index("date")
    mdata = MatchedData(df2["obs"], df2["model"])
    print("*ALL*")
    # print(df2[0:10])
    print(mdata.find_stats())
    sns.set()
    ##create datem output for each month (for nick)
    mnths = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    for mmm in mnths:
        dfile2 = "month" + str(mmm) + "." + dfile
        df["month"] = df["date"].map(lambda x: x.month)
        print(df[0:10])
        dftemp = df[df["month"] == mmm]
        print("Writing datem file ", dfile2)
        frame2datem(
            dfile2,
            dftemp,
            cnames=[
                "date",
                "duration",
                "lat",
                "lon",
                "obs",
                "model",
                "sid",
                "altitude",
            ],
        )
    ##plot obs vs. model for each site.
    for site in df["sid"].unique():
        # for site in []:
        dfile2 = str(site) + "." + dfile
        dftemp = df[df["sid"] == site]
        dftemp.set_index("date", inplace=True)
        dftemp = dftemp.resample("H").asfreq()
        dftemp["obs"].fillna(0, inplace=True)
        dftemp["model"].fillna(0, inplace=True)
        dftemp["duration"].fillna(method="bfill", inplace=True)
        dftemp["lat"].fillna(method="bfill", inplace=True)
        dftemp["lon"].fillna(method="bfill", inplace=True)
        dftemp["sid"].fillna(method="bfill", inplace=True)
        dftemp["altitude"].fillna(method="bfill", inplace=True)
        dftemp.reset_index(inplace=True)
        # print(dftemp[0:10])
        for mmm in mnths:
            dfile2 = str(site) + ".month" + str(mmm) + "." + dfile
            dftemp2 = dftemp.copy()
            dftemp2["month"] = dftemp["date"].map(lambda x: x.month)
            print(df[0:10])
            dftemp2 = dftemp2[dftemp2["month"] == mmm]
            frame2datem(
                dfile2,
                dftemp2,
                cnames=[
                    "date",
                    "duration",
                    "lat",
                    "lon",
                    "obs",
                    "model",
                    "sid",
                    "altitude",
                ],
            )

        dftemp.set_index("date", inplace=True)
        obs = dftemp["obs"]
        model = dftemp["model"]
        msitedata = MatchedData(obs, model)
        dhash = msitedata.find_stats()
        print(str(site))
        print("RMSE", str(dhash["rmse"]))
        print("NMSE", str(dhash["nmse"]))
        # plt.plot(obs,'--r')
        # plt.plot(model,'--k')
        obs.plot()
        model.plot()
        plt.title(str(site))
        plt.savefig("c." + str(site) + ".jpg")
        plt.show()
