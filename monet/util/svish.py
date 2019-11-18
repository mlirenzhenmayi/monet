import os
import subprocess
import pandas as pd
import numpy as np
import pickle as pickle
from optparse import OptionParser
import datetime
import sys
import monet
#from  monet.obs import *
from monet.obs import ish
#import monet.obs.obs_util as obs_util
import matplotlib.pyplot as plt
import seaborn as sns
#from monet import MONET
from monet.util.svobs import find_obs_files

"""
verify NWP met data with met station measurements.

INPUTS: Dates to run
        Areas to look at

"""

def relh(x):
    #temp should be in Celsius
    #dewpoint should be in Celsius 
    dewpoint = x['dpt']
    temp = x['t']
    nnn = 7.5 * dewpoint / (237.3 + dewpoint) 
    mmm = 7.5 * temp / (237.3 + temp) 
    vap = 6.11 * 10**(nnn)
    satvap = 6.11 * 10**(mmm)
    rh = vap / satvap * 100
    return rh


def rplot(df):
    fig = plt.figure(1)
    ax = fig.add_subplot(3,1,1)
    ax.plot(df['time'], df['relh'], '-b.')
    ax2 = fig.add_subplot(3,1,2)
    ax2.plot(df['time'], df['dpt'], '-b.')
    ax3 = fig.add_subplot(3,1,3)
    ax3.plot(df['time'], df['t'], '-b.')
    plt.show()

def r2plot(df):
    sns.set()
    fig = plt.figure(1)
    ax2 = fig.add_subplot(2,1,1)
    ax2.plot(df['time'], df['dpt'], '-b.')
    ax2.set_xlabel('Time')
    ax2.set_ylabel('Dew Point')
    ax3 = fig.add_subplot(2,1,2)
    ax3.plot(df['time'], df['t'], '-b.')
    ax3.set_xlabel('Time')
    ax3.set_ylabel('Temperature')
    ax3 = fig.add_subplot(2,1,2)
    plt.show()


class Mverify(object):

    def __init__(self, dates, area):
        """
        self.sources: pandas dataframe
            sources are created from a CEMSEmissions class object in the get_sources method.
        """
        ##dates to consider.
        self.d1 = dates[0]
        self.d2 = dates[1]
        self.dates = dates
        #area to consider
        self.area = area
        self.df = pd.DataFrame()
        #self.metdir = '/pub/archives/wrf27km/'
        #self.hdir = '/n-home/alicec/Ahysplit/trunk/exec/'
        #self.tdir = '/pub/Scratch/alicec/SO2/'

        self.fignum = 1
        self.csvfile = 'ish.csv'


    def load(self):
        return -1

    def save(self, tdir):
        df = self.df.copy()
        fname = os.path.join(tdir, self.csvfile)
        df.to_csv(fname, header=True, float_format="%g")

    def find_csv(self, tdir):
         # checks to see if a downloaded csv file in the correct date range
         # exists.
         names = []
         names =  find_obs_files(tdir, self.d1, self.d2, ftype='ish', tag=None)
         # if it exists then
         if len(names) > 0:
            self.csvfile = (names[0])
            pload = True
         else: 
            self.csvfile = ("ish" + self.d1.strftime("%Y%m%d.") +
                             self.d2.strftime("%Y%m%d.") + "csv")
            pload = False
         return pload

    def from_csv(self, tdir):
        pload = self.find_csv(tdir)
        if pload:
           print('LOADING ish data')
           fname = os.path.join(tdir, self.csvfile)
           self.df = pd.read_csv(fname)
           print(self.df[0:10])
           self.makelatlon()
           print(self.df['latlon'][0:10])
        return pload 


    def makelatlon(self):
        def latlon(lat, lon):
            return(lat, lon)

        self.df['latlon'] = self.df.apply(lambda row:
                                    latlon(row['latitude'],
                                    row['longitude']), axis=1)


    def filter(self):
        df = self.df[['time','station_id', 'eleve', 'wdir',
                     'wdir_quailty','ws', 'ws_quality','ceiling',
                     'ceiling_quality', 'station name', 'dpt','t','relh',
                     'latitude', 'longitude', 'latlon']]
        return df


    def print_summary(self, fname):
        df = self.df[['station_id','latitude', 'longitude','station name']]
        df = df.drop_duplicates()
        rstr=""
        for val in df.columns.values:
            rstr += str(val) + " ,   "
        rstr += '\n'
        sep = ' , '
        for index, row in df.iterrows():
            rstr += str(row['station_id']) + sep
            rstr += "{0:10.3f}".format(row['latitude']) + sep
            rstr += "{0:10.3f}".format(row['longitude']) + sep
            rstr += row['station name'] + '\n'
        with open(fname, 'w') as fid:
             fid.write(rstr)  

    def find_obs(self, tdir=None):
        pload = self.from_csv(tdir)
        if not pload:
            mdata = ish.ISH()
            #self.obs = monet.obs.aqs.add_data(self.dates)
            self.df = mdata.add_data(self.dates, country=None, box=self.area, resample=False)
            self.df['relh'] = self.df.apply(relh, axis=1) 
            self.makelatlon()

            #self.df['latlon'] = str(self.df['latitude']) + ' ' + str(self.df['longitude'])
            print(self.df[0:10])
            print(self.df['latitude'].unique())
            print(self.df['longitude'].unique())
            print(self.df.columns.values)
            #r2plot(self.df)

    def map(self, ax):
        clr = sns.xkcd_rgb['royal blue'] 
        clr = sns.xkcd_rgb['green'] 
        latlons = self.df['latlon'].unique()
        for loc in latlons:
            lat = loc[0]
            lon = loc[1]
            ax.plot(lon, lat, color=clr, marker='d', markersize=10, linewidth=10)



