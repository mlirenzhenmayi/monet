from __future__ import print_function
import os
import datetime
import time
import sys
import pandas as pd
import numpy as np
import requests
#import pytz
import seaborn as sns
from urllib.parse import quote
import monet.obs.obs_util as obs_util
import matplotlib.pyplot as plt
from monet.util.svconstants import Constants
from monet.util.svcems import determine_size
from monet.util.svcems import determine_color
"""
PGRMMER: Alice Crawford   ORG: ARL
This code written at the NOAA air resources laboratory
Python 3

"""
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

class NeiSummary:

    def __init__(self, fname="nei_summary.csv",
                 data = pd.DataFrame(), area=None):
        if area: self.area = area
        else: self.area = 'all'
        self.fname = fname
        self.commentchar = '#'
        self.order = ['EIS_ID', 'latitude',
                      'longitude','SO2_tpy', 'SO2_kgph', 'facility','naics']
        self.fmts = ["{0:>10.11s}", "{:10.4f}", "{:10.4f}", "{:10.2f}",
                     "{:10.2f}", "{0:>10.11s}", "{0:>10.11s}"]
        ct = Constants()
        self.tons2kg = ct.tons2kg  #907 kg in 1 ton. 

        if not data.empty:
            data['SO2_tpy'] = data['SO2_tpy'].astype('float')
            data.sort_values(by=['SO2_tpy'], axis=0, inplace=True, ascending=False)
        self.df = data
    #def create(self):

    def load(self, fname=None):     
        if not fname: fname = self.fname
        dtp = {'latitude':float, 'longitude':float, 'SO2_tpy':float}
        dtp['SO2_kgph'] = float
        dtp['facility'] = str
        dtp['naics'] = str
        dtp['EIS_ID'] = str
        print('LOADING', fname)
        time.sleep(5)
        df = pd.read_csv(fname, sep=",", header=[0], comment=self.commentchar, dtype=dtp)
        # remove extra spaces from string fields
        for val in ['EIS_ID', 'facility', 'naics']:
            df[val] = df.apply(lambda row: row[val].strip(), axis=1) 
        self.df = df
        return df

    def print(self, fname=None):
        if not fname: fname = self.fname
        if self.df.empty:
           print("No NEI sources")
        else:
           eislist = self.df
           with open(fname, "w") as fid:
                rstr = self.commentchar + 'Area ' + str.join(',',list(map(str, self.area)))
                rstr += '\n'
                rstr += str.join(', ',self.order)
                rstr += '\n'
                fid.write(rstr)
                fid.write(self.create_string(self.df))

    def create_string(self, df):
        rstr = ""
        for index, row in df.iterrows():
            if row['SO2_tpy'] >= 0.1:
                for val in zip(self.order, self.fmts):
                    ft = val[1]
                    iii = val[0]
                    rstr += ft.format(row[iii])
                    rstr += ', '
                rstr += '\n'
        return rstr
    
    def map(self, ax):
        nei_map(ax, self.df, self.tons2kg)


class NeiData:

    def __init__(self, tdir, year=2014):
        if tdir[-1] != '/': tdir += '/'
        fname = tdir + 'NEI_YYYYv2facilities_SO2_only_csv.csv'
        self.fname = fname.replace('YYYY', str(year))
        self.df = pd.DataFrame()
        #tpy is tons per year
        ct = Constants()
        self.tons2kg = ct.tons2kg  #907 kg in 1 ton. 
        self.area = None

        # naics 221112 is code for "fossil fuel electric power generation
        # naics 325180 basic inorganic chemical manufacturing
        # naics 324199 manufacturing petroleum products
        # naics 324110 refinery
        # naics 327213 glass manufacturing
        

    def write_summary(self, tdir, fname):
        ns = NeiSummary(fname, self.df, self.area)
        ns.print() 

    def load(self):
        alldata = []
        nlen = 40
        with open(self.fname, encoding='utf8', errors='ignore') as fid:
             iii=0
             for line in fid:
                 line = line.replace('"','')
                 temp = line.split(',')
                 temp = temp[0:7]
                 if iii>0 and len(temp) == nlen:
                     alldata.append(temp)
                 else:
                     cols = temp
                     if iii==0: nlen = len(cols)
                 iii+=1
                 #if iii> 50: break
        df = pd.DataFrame.from_records(alldata, columns=cols)
        self.df = df
        self.rename()
        self.df['latitude'] = self.df['latitude'].astype('float')
        self.df['longitude'] = self.df['longitude'].astype('float')
        self.df['SO2_tpy'] = self.df['SO2_tpy'].astype('float')
        self.df['SO2_kgph'] = self.df['SO2_tpy'] * self.tons2kg / (24*365)
        #df = pd.read_csv(self.fname)
        #col = df.column.values
        #print(col)
        #return df

    def rename(self):
        new = []
        for val in self.df.columns.values:
            if val.strip() == 'long' : new.append('longitude')
            elif val=='lat': new.append('latitude')
            else:
                new.append(val.strip())
        self.df.columns = new
          
    def filter(self, area):
        self.area = area
        if area:
            self.df = obs_util.latlonfilter(
                self.df, (area[0], area[1]), (area[2], area[3])
            )


    def map(self, ax):
        nei_map(self.df, ax, self.tons2kg)



def nei_map(sumdf, ax, tons2kg):
    """plot location of emission sources"""
    # if self.cems.df.empty:
    #    self.find()
    plt.sca(ax)
    keep = [
        "latitude",
        "longitude",
        "SO2_tpy",
        "EIS_ID"
    ]
    sumdf = sumdf[keep]
    #sumdf = sumdf.reset_index()
    lathash = df2hash(sumdf, "EIS_ID", "latitude")
    lonhash = df2hash(sumdf, "EIS_ID", "longitude")
    tothash = df2hash(sumdf, "EIS_ID", "SO2_tpy")
    # fig = plt.figure(self.fignum)
    for loc in tothash.keys():
        try:
            lat = lathash[loc]
        except:
            loc = None
        if loc:
            lat = lathash[loc]
            lon = lonhash[loc]
            ms = 10
            # convert from ton/year to kg/hour
            mass = float(tothash[loc]) * tons2kg / (365.0 * 24.0)
            cs = determine_color(mass, unit='kg') 
            ms = determine_size(mass, unit='kg')
            #if loc in self.goodoris:
            #print('pl ' + str(loc) + ' ' + str(tothash[loc]) + ' ' + str(ms))
            ax.plot(lon, lat, "o", markeredgecolor=cs, markerfacecolor=cs, markersize=ms, linewidth=2, mew=1)




   
