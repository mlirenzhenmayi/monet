# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import numpy as np
import datetime
import time
import os
from os import path, chdir
from subprocess import call
import pandas as pd
from monet.utilhysplit.statmain import MatchedData
from monet.util.svcems import SourceSummary
from monet.util.svcems import df2hash
from monet.util.svobs import SObs
import seaborn as sns
from shapely.geometry import Point
from shapely.geometry import LineString
import geopandas as gpd

"""
"""

def make_gpd(df, latstr, lonstr):
    
    geometry = [Point(xy) for xy in zip(df[lonstr], df[latstr])]
    df = df.drop([lonstr,latstr], axis=1)
    crs = {'init': 'epsg:4326'}
    gdf = gpd.GeoDataFrame(df, crs=crs, geometry=geometry)
    return gdf


def cems2obs(obsfile, cemsfile):

    # read cems csv file.
    # create the SObs  ojbect.
    sourcesum = SourceSummary().sumdf  
    sourcesum = sourcesum.groupby(['ORIS','Name','Stack height (m)',
                                   'lat','lon']).sum()
    sourcesum.reset_index(inplace=True)
    sourcesum = sourcesum[['ORIS','Name','Mean(lbs)','lat','lon']]

    sgpd = make_gpd(sourcesum, 'lat', 'lon')
    #print(sgpd[0:10])
    print(sgpd[0:10])
    #sgpd.set_index('ORIS', inplace=True)
    #print(sgpd[0:10])

    str1 = obsfile.split('.')
    dt1 = datetime.datetime.strptime(str1[0], "info_obs%Y%m%d") 
    dt2 = datetime.datetime.strptime(str1[1], "%Y%m%d") 
    area=''
    obs = SObs([dt1, dt2], area)
    odf = obs.read_csv(obsfile, hdrs=[0])
    #print('----------------------------------------')
    osum = odf[['siteid','latitude','longitude']]
    osum = make_gpd(osum.drop_duplicates(), 'latitude', 'longitude')
    #print(osum[0:10])
    #odf = make_gpd(odf, 'latitude', 'longitude')

    orishash = df2hash(sgpd, 'ORIS','geometry')
    # for each power plant:

    def makeline(p1, p2):
        br = bearing(p2,p1)
        return(br)
        #return LineString([p1,p2])
        #return p1

    for oris in orishash.keys():
        cname = str(int(oris)) + 'dist' 
        pnt = orishash[oris]
        #pnt = 2
        #print('ORIS', oris, type(orishash[oris]))
        osum[cname] = osum.distance(orishash[oris]) 
        lname = str(int(oris)) + 'direction'
        osum[lname] = osum.apply(
                           lambda row: bearing(row['geometry'], pnt),
                           axis=1)
    print('  ----------------------------------------')
    print(osum[osum[cname]<3])
        #osum[lname] = osum.apply(makeline(pnt, osum['geometry']), axis=1)
    #print(' ALL DISTANCE ----------------------------------------')
    #print(osum[0:20])
    return -1 

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
    for run in runlist:
        fname = run.directory + "/dataA.txt"
        print(fname)
        tempdf = read_dataA(fname)
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
