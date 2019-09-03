import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import datetime
#import sys
import seaborn as sns
import warnings
from monet.utilhysplit import statmain

# from arlhysplit.models.datem import mk_datem_pkl
#from monet.obs.epa_util import convert_epa_unit
from monet.util import tools
from monet.util.svan1 import geometry2hash

"""
FUNCTIONS

Functions for looking at metdata with observations
vmixing2metobs
metobs2matched

CLASSES
MetObs

"""


def obs2metobs(obsobject):
    """
    input SVobs object.
    output MetObs object.
    """
    meto = MetObs()
    meto.from_obs(obsobject.dfall)
    return meto

def vmixing2metobs(vmix, obs):
    """
    take vmixing dataframe and SO2 measurement dataframe and 
    combine into a MetObs object.
    """
    print('--------------')
    met = MetObs(tag='vmix')
    if not vmix.empty and not obs.empty:
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
        #print(dfnew[0:10])
        met.from_vmix(dfnew)
    return met

def heatmap(x,y, ax, bins=(50,50)):
    heatmap, xedges, yedges = np.histogram2d(x,y, bins=(bins[0],bins[1]))
    extent = [xedges[0], xedges[-1], yedges[0], yedges[-1]]
    cb = ax.imshow(heatmap, extent=extent)
    
def hexbin(x,y,ax,sz=50,mincnt=1, cbar=True):
    cm='Paired'
    cm=sns.cubehelix_palette(8, start=0, rot=0.5, as_cmap=True, reverse=False)
    cb = ax.hexbin(x,y, gridsize=sz, cmap=cm, mincnt=mincnt)
    if cbar: plt.colorbar(cb)

def myhistA(hhh, ax, bins=None, label=None):
    # same as myhist except use snsdistplot
    if not bins:
        sns.distplot(hhh, label=label)
    else:
        sns.distplot(hhh, bins=bins, label=label)
    plt.legend()

def myhist(hhh, ax, bins=None, label=None, color='b'):
    # hist works better than sns.distplot.
    if not bins:
        sns.distplot(hhh, label=label)
    else:
        ax.hist(hhh, density=True, bins=bins, label=label, color=color,
                alpha=0.5 )
    plt.legend()


def addplants(site, ax, ymax=20, dthresh=150, add_text=True,
              geoname='geometry.csv'):
    # add vertical lines with direction to power plants to the
    # 2d histogram of so2 concentration vs. wind speed.
    disthash, dirhash = geometry2hash(site, fname=geoname)
    iii=0
    tlist = [] # list of tuples, oris, distance, direction

    for oris in dirhash.keys():
        try:
            ddd = float(disthash[oris])
        except:
            print('FAILED at', oris, site, disthash[oris])
            continue

        if ddd < dthresh:
            try:
                xxx = float(dirhash[oris])
            except:
                print('FAILED at', oris, site, dirhash[oris])
                continue
            ty = ymax - iii * ymax/10.0
            #yyy = [0,ty] 
            #print(xxx, oris, site)
            tlist.append((ddd, oris, xxx))
    # sort according to distance from site.
    tlist.sort()
    for val in tlist:
            oris = val[1]
            xxx = val[2]
            dist = val[0]
            #print(xxx, oris, site)
            ty = ymax - iii * ymax/10.0
            yyy = [0,ty] 
            try:
                ax.plot([xxx,xxx],yyy,'-k')
            except:
                print('FAILED at', xxx, oris, site)
               
            if add_text:
                tx = xxx+1
                #ty = ymax - iii * ymax/10.0
                lbl = str(oris) + ' ' + str(int(dist)) + 'km'
                ax.text(tx, ty, lbl,fontsize=10, color="blue")
            iii+=1

def jointplot(x, y, data, fignum=1):
    fig = plt.figure(fignum)
    #ax1 = fig.add_subplot(1, 3, 1)
    #plt.set_gca(ax1)
    ggg = sns.jointplot(x=x, y=y, data=df, kind="hex", color="b")
    ggg.plot_joint(plt.scatter, c="m", s=30, linewidth=1, marker=".")


def metobs2matched(met1, met2):
    """
    met1 is set to obs in the MatchedData
    met2 is set to fc in the MatchedData
    a list of MatchedData objects is returned for
    all columns with matching names.
    """

    head1 = met1.columns.values
    head2 = met2.columns.values

    sid1 = met1['siteid'].unique()
    sid2 = met2['siteid'].unique()

    samesid = [x for x in sid1 if x in sid2]
    mdlist = []
    samecols = [x for x in head1 if x in head2]
    filtercols = ['WDIR', 'WS', 'TEMP']
    samecols = [x for x in filtercols if x in samecols]
 
    mdlist = []
    for sss in samesid:
        m1temp = met1[met1['siteid'] == sss]     
        m2temp = met2[met2['siteid'] == sss]     

        m1temp.sort_values(by=['time'], axis=0, inplace=True)
        m2temp.sort_values(by=['time'], axis=0, inplace=True)
        m1temp['dup'] = m1temp.duplicated(subset=['time'], keep=False)
        m2temp['dup'] = m2temp.duplicated(subset=['time'], keep=False)


        m1temp.set_index('time', inplace=True)
        m2temp.set_index('time', inplace=True)
        for ccc in samecols:
            t1 = m1temp[ccc] 
            t2 = m2temp[ccc]

            #t1['dup'] = t1.duplicated(subset=['time'])
            #t2['dup'] = t2.duplicated(subset=['time'])

            #print('-------------------------')
            #print('TIME DUPLICATED')
            #print(t1[t1['dup']==True])
            #print(t2[t1['dup']==True])
            print(str(sss), str(ccc), '-------------------------')
            print(t1[0:10], type(t1))
            print(t2[0:10], type(t2))
            if not t1.empty and not t2.empty:
                #print('MATCHED')
                matched = statmain.MatchedData(obs=t1, fc=t2, stn=(sss,ccc)) 
                #print(matched.obsra[0:10])
                #print('-*-*-*-*')
                if not matched.obsra.empty:
                    mdlist.append(matched)
            #print('-*-*-*-*')
    return mdlist 
  

class MetObs(object):
    """
    creates plots of Meteorology and observations.
    1. time series plot
    2. hexbin plot (2d histogram of obs and wind speed/ wind direction)  
    """

    def __init__(self, tag=None, geoname='geometry.csv'):
        self.df = pd.DataFrame()
        self.columns_original = []
        self.fignum = 1
        self.tag = tag
        self.geoname = geoname
        

    def set_geoname(self, name):
        """
         name of geometry.csv file to use.
         this is needed to plot direction of power plants
        """
        self.geoname = name
        print('SETTING geoname', self.geoname)

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
        for val in ['psqnum', 'hour']:
            if val in df.columns.values:
                df = df.drop([val], axis=1)
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

    def nowarning_plot_ts(self, save=False, quiet=False):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.plot_ts(save, quiet)

    def plot_ts(self, save=False, quiet=False):
        if self.df.empty: return -1
        sns.set()
        slist = self.get_sites()
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
            ax2.plot(wdir, 'b.', markersize=2)
            ax1.plot(so2, '-k')

            ax1.set_ylabel('so2 (ppb)')
            ax2.set_ylabel('Wind direction (degrees)')
            plt.title(str(site))
            plt.tight_layout() 
            if not quiet:
                plt.show()
            if save:
                tag = self.tag
                if not tag: tag = ''
                plt.savefig(tag + str(site) + '.met_ts.jpg')
            plt.close() 

    def date2hour(self):
        def process_date(dt):
            return dt.hour
        self.df['hour'] = self.df.apply(lambda row: process_date(row['time']), axis=1)

    def PSQ2NUM(self):
        if not 'PSQ' in self.df.columns.values: 
           return False

        def process_psq(psq):
            if psq=='A': return 1
            elif psq=='B': return 2
            elif psq=='C': return 3
            elif psq=='D': return 4
            elif psq=='E': return 5
            elif psq=='F': return 6
            elif psq=='G': return 7
            else: return 8
        self.df['psqnum'] = self.df.apply(lambda row: process_psq(row['PSQ']), axis=1)
        return True


    def conditional(self, save=False, quiet=False):
        slist = self.get_sites()
        sz = [10,5]
        for site in slist:
            sns.set()
            sns.set_style('whitegrid')
            fig = plt.figure(self.fignum)
            fig.set_size_inches(sz[0],sz[1])
            ax = fig.add_subplot(1,1,1)
            df = self.df[self.df['siteid'] == site]
            v1, x1 =  self.conditional_sub(df, ax, site, pval=[0.99,1],
                                           color='r')    
            v2, x2 =  self.conditional_sub(df, ax, site, pval=[0.95,1],    
                                           color='b')    
            v3, x3 =  self.conditional_sub(df, ax, site, pval=[0,0.2],    
                                           color='g')    
            #self.conditional_sub(df, ax, site, pval=[0.2,0.95])    
            addplants(site, ax, ymax=0.01, geoname=self.geoname)
            ax.set_xlabel('Wind Direction (degrees)')
            ax.set_ylabel('Probability')  
            plt.title(str(site))
            plt.tight_layout()
            plt.savefig(str(site) + 'cpdf.jpg')
            plt.show() 
 
    def conditional_sub(self,df, ax, site, pval, label=None, color='b'): 
        var1='SO2'
        var2='WDIR'

        mdl=2
        ra = df[var1].tolist()
        valA = statmain.probof(ra, pval[0]) 
        valB = statmain.probof(ra, pval[1]) 
        #print('VALA, VALB', valA, valB)
        #if valB < 0.2: valB = 0.25
             
        tdf = df[df[var1] >= valA]          
        tdf = tdf[tdf[var1] <= valB]          
        #print(tdf.columns.values) 
        tdf = tdf.set_index('time')
        hhh = tdf[var2]
        hhh = hhh.fillna(0)
        if not label: 
           label = "{0:2.2f}".format(valA)  
           label += ' to '
           label += "{0:2.2f}".format(valB)  
           label += ' ppb'
        myhist(hhh.values,ax, bins=36, label=label, color=color)
        return valA, valB

    def plothexbin(self, save=True, quiet=True): 
        # 2d histograms of obs and wind speed
        # 2d histogram of obs and wind direction.
        if self.df.empty: return -1
        slist = self.get_sites()
        nnn=2
        aaa=1
        sz=(10,5)
        psqplot = self.PSQ2NUM()
        if psqplot: 
           nnn=2
           aaa=2
           sz=(10,10)
           self.date2hour()

        for site in slist:
            sns.set()
            sns.set_style('whitegrid')
            fig = plt.figure(self.fignum)
            fig.set_size_inches(sz[0],sz[1])
            # re-using these axis produces a warning.
            ax1 = fig.add_subplot(aaa,nnn,1)
            ax2 = fig.add_subplot(aaa,nnn,2)
            if psqplot:
                ax3 = fig.add_subplot(aaa,nnn,3)
                ax4 = fig.add_subplot(nnn,nnn,4)

            df = self.df[self.df['siteid'] == site]
            #print('HEXBIN for site ' , site) 
            #print(df[0:10])
            #df.columns = self.met_header(df.columns)
            #print(df.columns.values)
            #xtest = df[("WD", "Degrees Compass")]
       
            xtest = df["WDIR"]
            ytest = df["WS"]
            ztest = df["SO2"]
            if psqplot:
               ptest = df['psqnum']       
               htest = df['hour']
 
            if np.isnan(xtest).all():
                print('No data WDIR', site)
                continue
            if np.isnan(ztest).all():
                print('No data so2', site)
                continue
            cbar=False 
            hexbin(xtest, ztest, ax1, cbar=cbar)  
            ymax = np.max(ztest)
            addplants(site, ax1, ymax=ymax, geoname=self.geoname)
            hexbin(ytest, ztest, ax2, cbar=cbar) 
            if psqplot:
               hexbin(ptest, ztest, ax3, cbar=cbar)
               hexbin(htest, ptest, ax4, cbar=cbar)
            ax1.set_xlabel('Wind Direction ')
            ax2.set_xlabel('Wind Speed ')
            ax1.set_ylabel('SO2 (ppb)')
            if psqplot:
               ax3.set_xlabel('PSQ')
               ax4.set_xlabel('time')
               ax4.set_ylabel('PSQ')
            ax1.set_title(str(site))
            plt.tight_layout() 
            if save:
                tag = self.tag
                if not tag: tag = ''
                plt.savefig(tag + str(site) + '.met_dist.jpg')
            self.fignum +=1
            #if not quiet:
            #    plt.show()
            # clearing the axes does not
            # get rid of warning.
            #plt.cla()
            #plt.clf()
            #plt.close()  

