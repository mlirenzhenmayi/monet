# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import numpy as np
import datetime
import time
import os
from os import path, chdir
from subprocess import call
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from shapely.geometry import Point
from shapely.geometry import LineString
import geopandas as gpd
import sys

from monet.util.svcems import SourceSummary
from monet.util.svcems import df2hash
from monet.util.svcems import CEMScsv
from monet.util.svobs import SObs
import monet.util.svobs as svo
from monet.util.svobs import get_tseries

"""
Functions and classes in this module investiage the relationship
between AQS measurements and CEMS data and met data.

CemsObs class creates a geopandas dataframe which has information
on distance and direction between power plants and measurement sites.

TO DO????
If HYSPLIT has been run we can use the c2datem to find out which power plants
had modeled emissions which reached the sites.
We could also possibly use the HYSPLIT reader for this.
"""

class Hclass:
    # helper class. not used yet.
    def __init__(self, name, bins=None):
        self.name = sname
        self.binlist = bins
        if not self.binlist: self.binlist = []       
  
    def makebins(self, bins):
        # bins is list of tuples with lower and upper bounds on the bin.
        self.binlist = bins 

    def addbin(self, sbin):
        self.binlist.append(sbin)

def classify(df):
    # not used yet.

    wbin = [1,1]  # wind direction
    ebin = [1,1]  # emissions
    sbins = [1,1] # stability
    mbins = [1,1]  # so2 measurement
    # for each measurement bin
    for hc in hlist:
        dft = df.copy()
        for bn in hc.binlist:
            dft = dft[dft[hc.name]>=bn[0] and dft[hc.name]<=bn[1]]
       
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
        # inputs
        self.obsfile = obsfile
        self.sourcesum = source_sum_file
        self.cemsfile = cemsfile

        # outputs
        self.sumdf = gpd.GeoDataFrame() #created by make_sumdf

        # internal use
        self.obs = None #SObs object
        # create self.obs file.
        self.get_obs()

    def add_geometry(self, gname = 'geometry.csv'):
        return -1 

    def match(self):
        #cems = 
        return 1 

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

    def get_met(self):
        metdf = self.obs.read_met()
        return metdf

    def get_met_site(self, site):
        metdf = self.obs.read_met()
        cols = metdf.columns.values
        for val in cols:
            if "siteid" in val:
                cname = val
        sra = self.met[cname].unique()
        if site in sra:
           df = metdf[metdf[cname] == site]
        else:
           df = pd.DataFrame()
        #sitdf = metdf[
        return df


    #def plot_sumdf(self):
    def get_obs(self):
        # read the obs file.
        str1 = self.obsfile.split('.')
        dt1 = datetime.datetime.strptime(str1[0], "obs%Y%m%d") 
        dt2 = datetime.datetime.strptime(str1[1], "%Y%m%d") 
        area=''
        obs = SObs([dt1, dt2], area)
        self.obs = obs


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
        sourcesum = SourceSummary(fname=self.sourcesum).sumdf  #uses default name for file.
        print(sourcesum.columns.values)
        sourcesum = sourcesum.groupby(['ORIS','Name','Stack height (m)',
                                       'lat','lon']).sum()
        sourcesum.reset_index(inplace=True)
        sourcesum = sourcesum[['ORIS','Name','Total(tons)','lat','lon']]
        sgpd = make_gpd(sourcesum, 'lat', 'lon')
        orishash = df2hash(sgpd, 'ORIS','geometry')

        
        # read the obs file.
        self.get_obs()

        if not os.path.isfile(obsfile): print('not file ' + obsfile)
        odf = svo.read_csv(obsfile, hdrs=[0])
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
    # creates geometry.csv file
    df = gpd.drop('geometry', axis=1)
    df[names['x']] = gpd.geometry.apply(lambda p:p.x)
    df[names['y']] = gpd.geometry.apply(lambda p:p.y)
    df.to_csv(outfile, float_format='%g', index=False)

def geometry2hash(sid, fname='geometry.csv'):
    df = load_geometry(fname)
    dirhash = {}
    disthash = {}
    if df.empty:
        return disthash, dirhash
    df = df[df['siteid'] == sid]
    for val in df.columns.values:
        if 'dist' in val:
            oris = val.replace('dist', '')
            dlist = df[val].tolist()
            if dlist:
                disthash[oris] = dlist[0]
        if 'direction' in val: 
            oris = val.replace('direction', '')
            dlist = df[val].tolist()
            if dlist:
                dirhash[oris] = df[val].tolist()[0]

    return disthash, dirhash

def load_geometry(fname = 'geometry.csv'):
    df = pd.DataFrame()
    if os.path.isfile(fname):
        chash = {"siteid":int}
        df = pd.read_csv(fname, sep=',', converters=chash)
        return df
    else:
        print('FILE NOT FOUND ', fname)
        return df

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


