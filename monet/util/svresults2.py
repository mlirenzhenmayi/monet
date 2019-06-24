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
import monet.util.svobs as svo
from monet.util.svobs import get_tseries
import seaborn as sns
from shapely.geometry import Point
from shapely.geometry import LineString
import geopandas as gpd

from monet.util.datem import read_dataA
from monet.util.ptools import set_date_ticks
from monet.util.ptools import generate_colors
from monet.util.ptools import set_legend
from monet.util.datem import frame2datem

"""
Here we want to define a dataset.


CemsObs class creates a geopandas dataframe which has information
on distance and direction between power plants and measurement sites.

If HYSPLIT has been run we can use the c2datem to find out which power plants
had modeled emissions which reached the sites.
We could also possibly use the HYSPLIT reader for this.


"""



def make_gpd(df, latstr, lonstr):
    
    geometry = [Point(xy) for xy in zip(df[lonstr], df[latstr])]
    df = df.drop([lonstr,latstr], axis=1)
    crs = {'init': 'epsg:4326'}
    gdf = gpd.GeoDataFrame(df, crs=crs, geometry=geometry)
    return gdf

def generate_cems(cemsfile, orislist, spnum='P1'):
    """
    return time series of measurements.
    """
    cems = pd.read_csv(cemsfile, sep=",", index_col=[0],parse_dates=True)
    new=[]   
    for hd in cems.columns:
        
        temp = hd.split(',')
        temp = temp[0].replace('(','')
        try:
            new.append(int(float(temp)))
        except:
            new.append(temp)
    cems.columns = new
    print(new)
    for col in cems.columns:
        for oris in orislist:
            if str(oris) in col and  spnum in col:
               yield cems[col]
    #cems.set_index('time', inplace=True)
        #step 1 get the cems data.
        #step 2 get the measurement data.
        #step 3 filter measurement data when cems on
        #step 4 filter measurement data when cems off
        #step 5 create cdf for each
        #step 6 compare the cdfs


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
        sourcesum = SourceSummary().sumdf  #uses default name for file.
        sourcesum = sourcesum.groupby(['ORIS','Name','Stack height (m)',
                                       'lat','lon']).sum()
        sourcesum.reset_index(inplace=True)
        sourcesum = sourcesum[['ORIS','Name','Mean(lbs)','lat','lon']]
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


class SVresults:

    """
    ATTRIBUTES:
    tdirpath : str : top level directory for results.
    df       : pandas DataFrame
    orislist : list of oris numbers in the area
    sidlist  : list of station id's in the area
    dhash    : dictionary  
               key is oris code and value is DataFrame with
               model and observation data from the dataA output
               from statmain.
             
 
    METHODDS:
    __init__
    fill_hash
    find_files
    writedatem
    fromdataA


    Caveats - there should be no extra dataA files in the directories.
    
    """
    def __init__(self, tdirpath, orislist=None, daterange=None): 
        ## inputs
        self.tdirpath = tdirpath 
        self.orislist = orislist 
        self.daterange = daterange

        ## outputs
        self.df = pd.DataFrame() 
        self.sidlist = [] 
        self.dhash = {}

        ## internal use
        self.plist = ['p1','p2','p3']
        self.chash = {}  #dict. key is oris code. value is a color.
        self.set_colors()
 
    def fill_hash(self): 
        for oris in self.orislist: 
           for poll in self.plist:
               flist = self.find_files(oris, poll=poll) 
               df = self.fromdataA(flist) 
               self.dhash[(str(oris),poll)] = df 
               if not df.empty: sidlist = df['sid'].unique() 
               self.sidlist.extend(sidlist) 
        self.sidlist = list(set(self.sidlist))              




    def dirpath2date(self, dirpath):
        temp = dirpath.split('/')
        year = None
        month = None
        day = None
        for val in temp:
            if not val:
               pass 
            elif val[0] == 'y':
               try:
                   year = int(val.replace('y',''))
               except:
                   pass
            elif val[0] == 'm':
               try:
                   month = int(val.replace('m',''))
               except:
                   pass
            elif val[0] == 'd':
               try:
                   day = int(val.replace('d',''))
               except:
                   pass
        if year and month and day:
           rval =  datetime.datetime(year, month, day)
        else:
           rval = None
        return rval

    def datetest(self, dirpath):
        if not self.daterange:
           rval = True
        else:
           date = self.dirpath2date(dirpath)
           if not date:
              rval = False
           else:
               if date >= self.daterange[0] and date <= self.daterange[1]:
                  rval = True
               else:
                  rval = False
        return rval

    def find_files(self, oris, poll='p1'): 
        """ oris should be oris number or None
            poll should indicate species (p1, p2, p3) or be None.

        if both are None then will return all files with dataA in the name.
        if oris indicated will return only dataA files with indicated oris code.
        if poll indicated will return only dataA files with indicated species.
        """
        dataA_files = []
        for (dirpath, dirnames, filenames) in os.walk(self.tdirpath):

            # if 
            if not self.datetest(dirpath): continue 

            for fl in filenames:
                test1 = 'dataA' in fl

                if not oris: test2 = True
                else:  test2 = str(oris) in fl
            
                if not poll: test3 = True
                else:  test3 = poll in fl
                
                if test1 and test2 and test3: 
                    dataA_files.append(dirpath + '/' + fl)
                    print(dirpath + '/' + fl)
        return dataA_files 

    def writedatem(self, dfile, bymonth=True):
        flist = self.find_files(oris=None)
        df = self.fromdataA(flist)
        #df.set_index('date', inplace=True)
        if df.empty: return
        print(df[0:10])
        #df = self.massage_df(df)
        #df = df.resample("H").asfreq()
        #df = df.reset_index()
        #df.drop('Num', axis=1, inplace=True)
        #print('WRITING--------------------------')
        #print(df[0:10])
        sidlist = df['sid'].unique()
        for sid in sidlist:
            dftemp = df[df['sid'] == sid] 
            dftemp.set_index('date', inplace=True)
            #dftemp = dftemp.resample("H").asfreq()
            try:
                dftemp = self.massage_df(dftemp)
            except:
                print('Problem with ' + str(sid))
                print(dftemp[0:10])
                continue
            dftemp.reset_index(inplace=True)
            dfile2 = str(sid) + '.' + dfile
            frame2datem(dfile2, dftemp, 
                    cnames=['date','duration','lat', 'lon',
                           'obs','model','sid','altitude'] )
            if bymonth:
                dftemp["month"] = dftemp["date"].map(lambda x: x.month)
                mnths = dftemp['month'].unique()
                print('MONTHS', mnths)
            else:
                mnths = []
            for mmm in mnths:
                dfile2 = str(sid) + ".month" + str(mmm) + "." + dfile
                #dftemp["month"] = dftemp["date"].map(lambda x: x.month)
                dfmonth= dftemp[dftemp["month"] == mmm]
                frame2datem(dfile2, dfmonth, 
                    cnames=['date','duration','lat', 'lon',
                           'obs','model','sid','altitude'] )


    def fromdataA(self, filelist):
        """
        reads file output by datem.
        filelist : list of strings. filenames for the datem files.
        """
        # Initialize dataframe to store c2datem output in.
        df = pd.DataFrame()
        nnn = 0
        # read output from c2datem in each subdirectory.
        #for run in runlist:
        #print('LIST', filelist)
        mcols = ['lat','lon','sid','obs','date']
        mcols = ['sid', 'date', 'lat','lon','obs']
        for fname  in filelist:
            # read the c2datem output.
            tempdf = read_dataA(fname)
            tempdf.drop(['Num'], inplace=True, axis=1)
            if nnn == 0 and not tempdf.empty:
                df = tempdf.copy()
                #df = df.set_index(mcols)
                nnn += 1
            elif not tempdf.empty:
                #tempdf = tempdf.set_index(mcols)
                #print('***-----------')
                #print(df.sort_values('model', ascending=False)[0:10])
                #print('merging', fname)
                #print(tempdf.sort_values('model',ascending=False)[0:10])
                #print('-----------')
                df = pd.concat([df, tempdf], sort=True).groupby(mcols).sum().reset_index()
                #df = df + tempdf 
                #df = pd.merge(df, tempdf, left_on=mcols, right_on=mcols)
                #print(df.sort_values('model',ascending=False)[0:10])
                #print('***-----------')
            elif tempdf.empty:
                print("-----------------------------")
                print("WARNING: svresults2.py results method empty dataframe")
                print(fname)
                print("-----------------------------")
        #print(df[0:10])
        if not df.empty:
            df["duration"] = "0100"
            df["altitude"] = 20
            # print(df[0:10])
            # frame2datem(dfile, df, cnames=['date','duration','lat', 'lon',
            #                        'obs','model','sid','altitude'] )

            # TO DO.
            # fill missing data with 0. MAY NEED TO CHANGE THIS.
            df["obs"].fillna(0, inplace=True)
            df["model"].fillna(0, inplace=True)
            df2 = df.copy()
            #df2 = df.reset_index()
            #df2.drop('Num', axis=1, inplace=True)
            #df2 = df.copy()
            #df2 = df.set_index("date")
        else:
            df2 = pd.DataFrame()
        return df2 
        # 

    def colorhash(self):
        """
        Assign a specific color to each ORIS code.
        """
        clr = generate_colors()       
        chash = {}
        for oris in self.orislist:
            chash[str(oris)] = next(clr)
        return chash

    def set_colors(self, chash=None):
        if not chash: chash = self.colorhash()
        self.chash = chash       
        return chash 
 
    def plotall(self):
        sns.set()
        for sid in self.sidlist:
            figa = plt.figure(1)
            figb = plt.figure(3)
            figc = plt.figure(4)
            fig2 = plt.figure(2)
            ax1a = figa.add_subplot(1,1,1)
            ax1b = figb.add_subplot(1,1,1)
            ax1c = figc.add_subplot(1,1,1)

            ax2 = fig2.add_subplot(1,1,1)
            iii=0
            mall = pd.DataFrame()
            mall1 = pd.DataFrame()
            chash = self.colorhash()
            for poll in self.plist: 
                for oris in self.orislist:
                    df = self.dhash[(str(oris), poll)]
                    if df.empty: continue
                    print(df[0:10])
                    print(df.columns)
                    dftemp = df[df["sid"] == sid]
                    dftemp.set_index('date', inplace=True)
                    dftemp = self.massage_df(dftemp)
                    obs = dftemp["obs"]
                    model = dftemp["model"]
                    if iii==0: 
                        ax1a.plot(obs.index.tolist(), obs.values, '-k')
                        ax2.plot(obs.index.tolist(), obs.values, '-k',label='Obs')
                    if model.values.any(): 
                        if np.max(model.values) > 0:
                            if poll=='p1': axp = ax1a
                            elif poll=='p2': axp = ax1b
                            elif poll=='p3': axp = ax1c
                            else:
                                print('poll number ' , poll)
                                axp=ax1a
                            print('CHASH', type(chash))
                            print(type(model))
                            axp.plot(model.index.tolist(), model.values,
                                     chash[str(oris)],
                                     label=str(oris))
                            if iii==0:
                               mall = model
                               if poll==1: mall1 = model
                            else:
                               mall =  mall.add(model, fill_value=0) 
                               if poll==1: 
                                   mall1 = mall1.add(model, fill_value=0)
                    iii+=1
                ax2.plot(mall.index.tolist(), mall.values, sns.xkcd_rgb['hot pink'],
                         label='ALL')
                #ax2.plot(mall1.index.tolist(), mall1.values, sns.xkcd_rgb['pink'],
                #         label='ALL high certainty')
                set_date_ticks(ax1a)
                set_date_ticks(ax1b)
                set_date_ticks(ax1c)
                set_date_ticks(ax2)
                set_legend(ax1a)
                set_legend(ax2)
                ax1a.set_title(str(sid) + ' ' + str(poll))
                plt.show()

    def massage_df(self, df):
            dftemp = df.copy()
            #dftemp = df[df["sid"] == site]
            dftemp = dftemp.resample("H").asfreq()
            dftemp["obs"].fillna(0, inplace=True)
            dftemp["model"].fillna(0, inplace=True)
            dftemp["duration"].fillna(method="bfill", inplace=True)
            dftemp["lat"].fillna(method="bfill", inplace=True)
            dftemp["lon"].fillna(method="bfill", inplace=True)
            dftemp["sid"].fillna(method="bfill", inplace=True)
            dftemp["altitude"].fillna(method="bfill", inplace=True)
            return dftemp
            #msitedata = MatchedData(obs, model)


