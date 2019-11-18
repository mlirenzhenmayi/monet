import pandas as pd
import numpy as np
import matplotlib
#matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import datetime
#import sys
import seaborn as sns
import warnings
from monet.utilhysplit import statmain
import pylab as pl
# from arlhysplit.models.datem import mk_datem_pkl
#from monet.obs.epa_util import convert_epa_unit
from monet.util import tools
from monet.util import ptools
from monet.util.svan1 import geometry2hash
from matplotlib.ticker import MultipleLocator
import matplotlib.colors as colors


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

        # we are mergint this left onto the obs.
        # what happens if the obs are missing?
        # seems like we should fill in missing values for the obs.

        # use an outer join because vmix will have data for every hour.
        # this should put Nan values in missing obs sites.
        dfnew = pd.merge(obs,
                         vmix,
                         how='outer',
                         left_on=['date','sid'],
                         right_on=['date','sid']
                         )
        dfnew = dfnew.drop_duplicates()
        dfnew.fillna({'so2':-9}, inplace=True)
        print('vmix2obs---', dfnew[-10:])
        met.from_vmix(dfnew)
    return met

def heatmap(x,y, ax, bins=(50,50)):
    heatmap, xedges, yedges = np.histogram2d(x,y, bins=(bins[0],bins[1]))
    extent = [xedges[0], xedges[-1], yedges[0], yedges[-1]]
    cb = ax.imshow(heatmap, extent=extent)

def hexbin(x,y,ax,sz=[23,15],mincnt=1, cbar=True):
    #cm='Paired'
    x = list(x) 
    y = list(y) 
    print('TYPE', type(x), '---', type(y))
    cm=sns.cubehelix_palette(8, start=0.5, rot=-0.75, as_cmap=True,
                             reverse=False, light=0.70)
    #cm = sns.color_palette("Blues")
  
    print('max', np.max(x)) 
    print('min', np.min(x)) 
    r1 = [0,360]
    r2 = [0,15]
    r3 = [0,24]
 
    cb = ax.hist2d(x,y, norm=colors.LogNorm(), cmap=cm, bins=[23,15], 
                                              range=[r3, [-2,200]])
    #heatmap, xedges, yedges = np.histogram2d(x,y, bins=(sz[0],sz[1]),
    #                                          range=[[0,360], [-2,200]])
    #extent = [xedges[0], xedges[-1], yedges[0], yedges[-1]]
    #cb = ax.imshow(heatmap, extent=extent)
    #cb = ax.hist2d(x,y, cmap=cm)
    if cbar: 
       bar = plt.colorbar(cb[3], ax=ax)
       bar.ax.tick_params(labelsize=15)    

    
def hexbinb(x,y,ax,sz=[23,15],mincnt=1, cbar=True):
    #cm='Paired'
    cm=sns.cubehelix_palette(8, start=0.5, rot=-0.75, as_cmap=True,
                             reverse=False, light=0.70)
    #cm = sns.color_palette("Blues")
    cb = ax.hexbin(x,y, gridsize=sz, bins='log', cmap=cm, mincnt=mincnt)
    if cbar: 
       bar = plt.colorbar(cb, ax=ax)
       bar.ax.tick_params(labelsize=15)    

def myhistA(hhh, ax, bins=None, label=None):
    # same as myhist except use snsdistplot
    if not bins:
        sns.distplot(hhh, label=label)
    else:
        sns.distplot(hhh, bins=bins, label=label)
    plt.legend()

def myhist(hhh, ax, bins, label=None, color='b', step=False, density=True):
    # hist works better than sns.distplot.
    #if not bins:
    #    sns.distplot(hhh, label=label)
    #else:
    if not step:
        nnn, rbins, patches = ax.hist(hhh, density=True, bins=bins, label=label, color=color,
                alpha=0.5 )
    else:
        nnn, rbins, patches = ax.hist(hhh, density=True, bins=bins, label=label, color=color,
                histtype='step')
    plt.legend()
    return nnn, rbins

def get_line_width(eis, neidf ):
    # The initial EIS locations come from the geometry.csv file which is setup
    # using under options_obs.csv.
    # So if the CONFIG.NEI file changes between when that was done and here,
    # values may not match.
       #return 1, 'r', 'unknown'
    return 3, sns.xkcd_rgb['magenta'], 'unknown'
    if neidf.empty:
       #return 1, 'r', 'unknown'
       return 4, sns.xkcd_rgb['magenta'], 'unknown'
    df = neidf[neidf['EIS_ID'].str.contains(eis.replace('EIS',''))]  
    if df.empty:
       #print(eis, ' empty')
       return 1, '-c', 'unknown'
    tp = df.iloc[0]['naics']
    facility=df.iloc[0]['facility']
    return 4, sns.xkcd_rgb['magenta'], facility



    if tp.strip() == '221112':
        clr = 'm'
    elif 'LLC' in tp:
        clr = 'g'
    else:
        clr = 'b'
    mass = df.iloc[0]['SO2_kgph']
    if mass < 1: linewidth=1
    elif mass < 10: linewidth=2
    elif mass < 100: linewidth=3
    elif mass < 500: linewidth=4
    else: linewidth=5
    return linewidth , clr, facility

def get_height(ymax, dthresh, dist):
    if ymax== -99: return 1
    bbb = np.ceil(dthresh)
    incr = dthresh / bbb
    aaa = np.arange(0,bbb+1) * incr 
    ccc = np.arange(0,bbb+1) * ymax / (bbb+1)
    ccc = np.flip(ccc)
    iii=0
    for val in aaa:
        if dist < val: break
        iii +=1
    return ccc[iii]

def addplants_subA(site, geoname, dthresh):
    # returns list of tuples
    # (distance, oris(or EIS), direction)
    disthash, dirhash = geometry2hash(site, fname=geoname)
    iii=0
    tlist = [] # list of tuples, oris, distance, direction
    orislist = []
    for oris in dirhash.keys():
        try:
            distance = float(disthash[oris])
        except:
            print('FAILED at', oris, site, disthash[oris])
            continue

        if distance < dthresh:
            try:
                direction = float(dirhash[oris])
            except:
                print('FAILED at', oris, site, dirhash[oris])
                continue
            tlist.append((distance, oris, direction))
    # sort according to distance from site.
    tlist.sort()
    nlen = len(tlist)
    return tlist, nlen

def addplants_subB(tlist, ymax, neidf, dthresh):
    iii=0
    textra = []
    orislist = []
    for val in tlist:
            facility = 'unknown'
            oris = val[1]
            xxx = val[2]
            dist = val[0]
            if 'EIS' in oris:
                clr= 'b'
                lbl = str(int(dist)) + 'km'
                linewidth, clr, facility =get_line_width(oris, neidf)
                #if facility == 'unknown' and dist > 10:
                #   continue
            else:
                clr = 'k'
                lbl = str(oris) + ' ' + str(int(dist)) + 'km'
                linewidth=5
                orislist.append([str(oris), str(int(dist))])
            #print(xxx, oris, site)
            ty = get_height(ymax, dthresh, dist)  
            yyy = [0,ty] 
           
            #try:
            #    ax.plot([xxx,xxx],yyy,clr, linewidth=linewidth)
            #except:
            #    print('FAILED at', xxx, oris, site)
            textra.append([xxx, ty, lbl, facility, linewidth, clr])
            iii+=1
    if textra: textra = manage_text(textra, ymax)
    return orislist, textra 

def addplants(site, ax, ymax=20, dthresh=150, add_text=True,
              geoname='geometry.csv', neidf=pd.DataFrame()):
    # add vertical lines with direction to power plants to the
    # 2d histogram of so2 concentration vs. wind speed.
    #add_text=True 
    # tlist is list of tuples with information on each source.
    tlist, nlen = addplants_subA(site, geoname, dthresh)
    orislist, textra = addplants_subB(tlist, ymax, neidf, dthresh)
    for  val in textra:     
         print(val)
         ax.plot([val[0], val[0]], [0,val[1]], linewidth=val[4], color=val[5])
         if add_text:
             ax.text(val[0]+1, val[1], val[2],fontsize=8, color="blue")
    return orislist

def addplants_horizontal(site, ax, xr, dthresh=150, add_text=True,
              geoname='geometry.csv', neidf=pd.DataFrame()):
    # add horizontal lines with direction to power plants to the
    # time series.
    # xr should be daterange.
    tlist, nlen = addplants_subA(site, geoname, dthresh)
    # -99 means that the height of the line will just be returned as 1. val[1]
    orislist, textra = addplants_subB(tlist, -99, neidf, dthresh)
    iii=0
    for  val in textra:   
         print('adding plant lines', val)
         # height is the wind direction.
         pnt1 = [xr[0], xr[1]]
         pnt2 = [val[0], val[0]] 
         print('PNT1', pnt1)
         print('PNT2', pnt2)
         dt = (xr[1] - xr[0]) / 10.0
         if iii==0: xtext = xr[0]-dt
         # still use linewidth to indicate source strength 
         try:
             ax.plot(pnt1, pnt2,  linewidth=val[4], alpha=0.5, color=val[5])
         except:
             return orislist
         if add_text:
             ax.text(xtext, val[0]+1, val[2],fontsize=8, color="blue")
             xtext += dt
             if xtext > xr[1]: xtext = xr[0]
             print('XTEXT', xtext, dt)
         iii+=1
    return orislist

def color_wdir(wdir, 
              geoname='geometry.csv', neidf=pd.DataFrame()):
    return -1

def manage_text(textra, ymax,  xinc=50):
    # sort by the x position of the text.
    yinc = ymax / 10.0
    prev_xpos = textra[0][0]
    iii=0
    newra = []
    textra.sort()
    for tx in textra:
        if iii==0 : 
           newra. append([tx[0], tx[1], tx[2], tx[3], tx[4], tx[5]])
           prev_xpos = tx[0]
           prev_ypos = ymax
        else:
           xpos = tx[0]
           ypos = tx[1]
           label = tx[2]
           if (xpos - prev_xpos) < xinc:
              if np.abs((ypos - prev_ypos)) < yinc:    
                 temp = label.split(' ')
                 if len(temp) <= 1:
                     label = ''
                 #ypos = prev_ypos - yinc 
                 #if ypos < 0: ypos = ymax
           #else:
           #   ypos = ymax
           newra.append([xpos, ypos, label, tx[3], tx[4], tx[5]])
           prev_xpos = tx[0]
           prev_ypos = ypos
        iii+=1
    return newra


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

        m1temp = m1temp.sort_values(by=['time'], axis=0, inplace=False)
        m2temp = m2temp.sort_values(by=['time'], axis=0, inplace=False)
        #m1temp['dup'] = m1temp.duplicated(subset=['time'], keep=False)
        #m2temp['dup'] = m2temp.duplicated(subset=['time'], keep=False)


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
  
class Reliability(object):

    def __init__(self, num_models):
        return -1   

    def reliability_init(self):
        num = self.get_num_models()
        self.binlist = list(np.arange(0,1, 1.0/num) + 1.0/(num*10))
        self.binlist.append(1)
        print('BINLIST', self.binlist)
        #self.binlist = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]
        self.yeshash = {}
        self.nohash = {}
        for binval in self.binlist:
            self.yeshash[binval] = 0
            self.nohash[binval] = 0
        self.thresh = 2.5

    def reliability_add(self, obs, prob):
        df = pd.concat([obs, prob], axis=1)
        df.dropna(axis=0, inplace=True)
        cols = ['obs','prob']
        df.columns = cols
        #print(type(df))
        #print(df[0:10])
        for index, row in df.iterrows():
            prob = row['prob'] 
            for pbin in self.binlist:
                #print(prob, pbin)
                if prob <= pbin: 
                   binval = pbin
                   print('break', binval, prob)
                   break 
            if row['obs'] >= self.thresh:
               self.yeshash[binval] += 1
            else:
               self.nohash[binval] += 1

    def reliability_plot(self):
        xxx = []
        yyy = []
        nnn = []
        yesval = []
        noval = []
        for binval in self.binlist:
            x = binval
            # total number of counts.
            n = self.yeshash[binval] + self.nohash[binval]
            if n != 0:
                noval.append(self.nohash[binval])
                yesval.append(self.yeshash[binval])
                y = self.yeshash[binval] / n
                xxx.append(x)
                yyy.append(y)
                nnn.append(n)
        fig = plt.figure(1)
        ax1 = fig.add_subplot(2,1,1)
        ax2 = fig.add_subplot(2,1,2)   
        ax1.plot(xxx,yyy, '-g.')
        ax1.plot([0,1], [0,1], '-k')
        ax2.plot(xxx, nnn, '-b.')
        ax2.set_yscale('log')
        #ax1.set_ylim(bottom=1)  
        plt.savefig('reliability.jpg')
 
        fig2 = plt.figure(2)
        ax3 = fig2.add_subplot(1,1,1)
        print('MEAS > thresh', yesval)
        print('MEAS < thresh', noval)
        plt.plot(xxx, yesval, '-g.')
        plt.plot(xxx, noval, '-r.')
        plt.show()

    


class MetObs(object):
    """
    creates plots of Meteorology and observations.
    1. time series plot
    2. hexbin plot (2d histogram of obs and wind speed/ wind direction)  
    """

    def __init__(self, tag=None, geoname='geometry.csv'):
        """
        The dataframe is structured in the following way.
       
        COLUMNS
          'time'
          'siteid'
          'wdir'
          'ws'
          'SO2'  gives observations of SO2.

        'time' and 'siteid' could be turned into row indices.
   
        Currently the meteorological data can either come from observations or
        from the vmixing output but not both. This should be changed so we can
        get all the data into one frame.
 
        Model data may be added with the add_model_all method. 
        This will add extra columns which have a hierarchical index 
        (source, pollnum, stype).
        e.g. (8042, 1, ORIS)
        e.g. (11529,1, EIS)
        source is either the ORIS code or EIS_ID (from nei dataset)
        pollnum gives the species number (usually 1 so far).
        stype indicates whether the source is from CEMS with known hourly
        emissions or if emissions were estimated from the NEI data.

        CEMS data may be added.  However, CEMS data is not specific to a siteid.
        Therefore the cems data must be repeated if it is merged into the main
        dataframe.

        self.geoname gives a geometry.csv file associated with the data. This
        file provides important information on the distance and direction
        between measurement sites and sources.

        """
        self.df = pd.DataFrame()
        self.columns_original = []
        self.fignum = 1
        self.tag = tag
       
        self.geoname = geoname

        self.cemslist = []  #list of column names representing cems data.
        self.model_list = [] #list of columnnames representing model data

        self.neidf = pd.DataFrame()
        self.empty = self.isempty()
        #self.model = pd.DataFrame()
        self.model =  {}  #dictionary of DataFrames

    def isempty(self):
        if self.df.empty: 
           self.empty=True
           return True
        else: 
           self.empty=False
           return False


    def add_nei_data(self, df):
        self.neidf = df

    def set_geoname(self, name):
        """
         name of geometry.csv file to use.
         this is needed to plot direction of power plants
        """
        self.geoname = name
        print('SETTING geoname', self.geoname)

    def add_model_all(self, mdf, verbose=True):
        # This adds the model data to the dataframe.
        # 

        # RIGHT NOW - must add model after creating from vmixing data.
        # or from_vmix will overwrite the self.df
        # add model output to the main dataframe.
        # use the 
 
        # instead of merging the model data to the dataframe.
        # might be best to simply add the model object.
        # and produce time series from it as needed to be merged.

        self.model_list = list(mdf.columns.values)
        print('adding model list', self.model_list)
        if 'time' in self.model_list: self.model_list.remove('time')
        if 'siteid' in self.model_list: self.model_list.remove('siteid')
        self.model_columns = mdf.columns.values

        if self.df.empty:
           self.df = mdf
        else:
            metobscol = ['time', 'siteid']
            modelcol = ['date', 'sid'] 
            newdf = pd.merge(self.df,
                             mdf,
                             how='left',
                             left_on = metobscol,
                             right_on =modelcol 
                             )
            self.df = newdf
            print(newdf[0:10])
            print(self.df.columns.values)
            print(self.model_list)
        self.isempty()
        return  self.df


    def add_model_object(self,name, model):
        self.model[name] = model

    #def add_model(self):
       

    def conditional_model(self):
        original_df = self.df.copy()
        mdf = self.model.group() 
        mdf = mdf.drop(['lat', 'lon', 'obs'], axis=1) 
        metobscol = ['time', 'siteid']
        modelcol = ['date', 'sid'] 
        newdf = pd.merge(self.df,
                         mdf,
                         how='left',
                         left_on = metobscol,
                         right_on =modelcol 
                         )
        newdf = newdf.fillna(0)
        print('NEWDF', newdf.columns.values)
        print(newdf[0:10])
        self.df = newdf
        self.conditional(varlist=['SO2', 'model']) 
        
          

    def add_cems(self, cemsdf, verbose=False):
        """
        adds the following colummns to the dataframe 
        """
       
        grouplist = ['time']
        if verbose:
            print('ADDING CEMS ')
            print(cemsdf.dtypes)
            print(self.df.dtypes)
            print(list(cemsdf.columns.values))
            #print(self.df.columns.values)
        #self.cemslist.extend(cemsdf.columns.values)
        self.cemslist = list(cemsdf.columns.values)
        if 'time' in self.cemslist:
           self.cemslist.remove('time')

        if self.df.empty:
           self.df = cemsdf
        else:
           self.df = pd.merge(self.df, 
                              cemsdf, 
                              how='left', 
                              left_on=grouplist,
                              right_on=grouplist) 
        if verbose: print('CEMSLIST', self.cemslist)
        self.isempty()

    def from_vmix(self,df):
        # Currenlty this overwrites anything that used to be in self.df
        self.df = df
        self.columns_original = self.df.columns.values
        self.rename_columns()
        self.isempty()      


    def add_obs(self, obs):
        df = tools.long_to_wideB(obs)
        self.rename_columns()
        testcols = ['WD','RH','TEMP','WS']
        overlap = [x for x in testcols if x in self.df.columns.values]
 
    def from_obs(self, obs):
        # Currenlty this overwrites anything that used to be in self.df
        # only keep rows (sites) which have Met data.
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
           # drop rows which have all NANs in the columns which give
           # metdata (WD, RH, TEMP, WS)
           self.df = self.df.dropna(axis=0, how='all', subset=overlap)
        self.isempty()      

    def to_csv(self,tdir, csvfile=None):
        if self.df.empty: return -1
        if not csvfile: csvfile = ''
        df = self.df.copy()
        for val in ['psqnum', 'hour']:
            if val in df.columns.values:
                df = df.drop([val], axis=1)
        print(self.columns_original)
        print(df.columns.values)
        try:
            df.columns = self.columns_original
        except:
            print('WARNING columns not matching', df.columns.values,
                   self.columns_original)
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
   
    def rename_columns(self, df=pd.DataFrame()):
        #if df.empty
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

    def get_num_models(self):
        model_list = self.model.keys()
        return len(model_list)      

    def add_model_ts(self, sid, tp='ORIS', model_list=None, levlist=None ):
        if not model_list:
           model_list = self.model.keys()
        for mmm in model_list:
            model = self.model[mmm]
            elist, slist = model.sourcelist()
            model_ts = model.group(sid, stypelist=[tp], levlist=levlist)
            model_ts.set_index('date', inplace=True)
            rval = model_ts['model']
            # the dataA files don't include 0,0 pairs so fill in missing with 0.
            rval = rval.resample("H").asfreq(fill_value=0)
            yield mmm, rval

    def clustering_csv(self,tdir):
        slist = self.get_sites()
        for site in slist:
            df = self.df[self.df['siteid'] == site]
            df = df[['time','SO2','WDIR','WS']]
            df = df.set_index('time')
            df.to_csv(tdir + str(site) + "met.csv",  header=True, float_format="%g")

    def plot_cdf(self, levlist=None, save=True, quiet=False, thresh=2.5):
        from monet.utilhysplit import statmain
        if self.df.empty: return -1
        sns.set()
        sns.set_style('whitegrid')
        slist = self.get_sites()
        for site in slist:
            fig = plt.figure(self.fignum)
            fig.set_size_inches(15,5)
            # re-using these axis produces a warning.
            ax1 = fig.add_subplot(1,1,1)
            #ax2 = ax1.twinx()
            df = self.df[self.df['siteid'] == site]
            df = df.set_index('time')
            so2 = df['SO2']
           
            iii=0
            jjj=0
            clrs = ['-g','-m', '-r','-c','-b','-y'] 
            #df = pd.DataFrame()
            #cols=[]
            ktest = []
            for lev in levlist:
                df = pd.DataFrame()
                cols=[]
                for name, oris_ts in self.add_model_ts(site, tp='ORIS',
                                                        levlist=lev):
                    print(type(oris_ts))
                    mcdf,y = statmain.cdf(oris_ts)
                    ax1.step(mcdf, y, '-r')
                    ktest.append(statmain.kstest_answer(so2, oris_ts))
            obs_cdf, obsy = statmain.cdf(so2)
            ax1.step(obs_cdf, obsy, '-k')
            ax1.set_xscale('log')
            ax1.set_xlim(left=1)
            plt.title(str(site))
            plt.show()
            plt.plot(ktest, 'b.')
            plt.show()


    def plot_spag(self, levlist=None, save=True, quiet=False, thresh=2.5):
        if self.df.empty: return -1
        sns.set()
        sns.set_style('whitegrid')
        slist = self.get_sites()
        for site in slist:
            fig = plt.figure(self.fignum)
            fig.set_size_inches(15,5)
            # re-using these axis produces a warning.
            ax1 = fig.add_subplot(1,1,1)
            #ax2 = ax1.twinx()
            df = self.df[self.df['siteid'] == site]
            df = df.set_index('time')
            so2 = df['SO2']
            iii=0
            jjj=0
            clrs = ['-g','-m', '-r','-c','-b','-y'] 
            #df = pd.DataFrame()
            #cols=[]
            for lev in levlist:
                df = pd.DataFrame()
                cols=[]
                for name, oris_ts in self.add_model_ts(site, tp='ORIS',
                                                        levlist=lev):
                    #ocolor = sns.xkcd_rgb['grey']
                    #ax1.plot(oris_ts, ocolor, linewidth=1 )  
                    if jjj==0: 
                       df = pd.DataFrame(oris_ts)
                    else:
                       df = pd.concat([df, oris_ts], axis=1) 
                    jjj+=1
                    cols.append(name)
                print(df[0:5])
                print(cols)
                df.columns = cols
                df2 = df.copy()
                df['mean'] = df.mean(axis=1)
                df['max'] = df.max(axis=1) 
                df['min'] = df.min(axis=1) 
                df2 = df2.T
                vals = (df2[df2 > thresh].count()) /len(cols)
                print('PROBS', len(cols), vals)
                #ax2.plot(vals, clrs[iii], linewidth=1) 
                yval = df['mean'].values 
                xval = df.index.tolist()
                maxval = df['max'].values
                minval = df['min'].values
                ocolor = sns.xkcd_rgb['magenta']
                ocolor = sns.xkcd_rgb['cerulean']
                ocolor = sns.xkcd_rgb['ocean blue']
                #ocolor = sns.xkcd_rgb['darker pink']
                ax1.plot(xval, yval, ocolor, linewidth=3)
                ax1.set_yscale('log')
                ax1.set_ylim(bottom=1)
                ax1.fill_between(xval, minval, maxval, alpha=0.4,\
                                 #facecolor=clrs[iii].replace('-','')) 
                                 facecolor=ocolor) 
                iii+=1
            ax1.plot(so2.sort_index(), '-k', linewidth=2)
            ax1.set_ylabel('so2 (ppb)')
            #ax2.set_ylabel('Wind direction (degrees)')
            #ax2.grid(False, which='both')
            ptools.set_date_ticksB(ax1)
            ax1.grid(True, which='both')
            plt.title(str(site))
            fig.autofmt_xdate()
            tag = self.tag
            if not tag: tag = ''
            plt.savefig(tag + str(site) + '.spag.jpg')
            plt.show()

    def plot_hist(self, levlist, save=True, quiet=False, thresh=2.5):
        model_list = self.model.keys()
        if self.df.empty: return -1
        sns.set()
        sns.set_style('whitegrid')
        slist = self.get_sites()
        self.date2hour()

        self.reliability_init(thresh=thresh)
        for model in model_list:
          for site in slist:
            fig = plt.figure(self.fignum)
            fig.set_size_inches(15,5)
            # re-using these axis produces a warning.
            ax1 = fig.add_subplot(1,1,1)
            ax2 = ax1.twinx()
            #ax3 = fig.add_subplot(2,1,2)
            #ax3 = ax1.twinx()
            df = self.df[self.df['siteid'] == site]

            #df = df[df['hour'] <= 21]
            #df = df[df['hour'] >= 12]
            df = df[df['WS'] < 5]
            df = df[df['WS'] >= 2]
            df = df.set_index('time')
            so2 = df['SO2']
            print(df.columns.values)
            mval = 'MixHgt'
            wdir = df[mval]
            #ax2.plot(wdir, 'b.', markersize=4)
            #ax1.plot(so2, '-k')
            #print('MODEL LIST', self.model_list)
            iii=0
            jjj=0
            clrs = ['-g','-m', '-r','-c','-b','-y'] 
            clrs = [sns.xkcd_rgb['brownish yellow']]
            for name, oris_ts in self.add_model_ts(site, tp='ORIS',
                                                        levlist=lev):
                    if jjj==0: 
                       df = pd.DataFrame(oris_ts)
                    else:
                       df = pd.concat([df, oris_ts], axis=1) 
                    jjj+=1
                    cols.append(name)
        


    def plot_prob(self, levlist=None, save=True, quiet=False, thresh=2.5):
        if self.df.empty: return -1
        sns.set()
        sns.set_style('whitegrid')
        slist = self.get_sites()
        self.date2hour()

        for site in slist:
            fig = plt.figure(self.fignum)
            fig.set_size_inches(15,5)
            # re-using these axis produces a warning.
            ax1 = fig.add_subplot(1,1,1)
            ax2 = ax1.twinx()
            #ax3 = fig.add_subplot(2,1,2)
            #ax3 = ax1.twinx()
            df = self.df[self.df['siteid'] == site]

            #df = df[df['hour'] <= 21]
            #df = df[df['hour'] >= 12]
            #df = df[df['WS'] < 5]
            #df = df[df['WS'] < 2]
            df = df.set_index('time')
            so2 = df['SO2']
            vpi = so2==-9
            so2[vpi] = float('Nan') 
            print(df.columns.values)
            mval = 'MixHgt'
            wdir = df[mval]
            #ax2.plot(wdir, 'b.', markersize=4)
            #ax1.plot(so2, '-k')
            #print('MODEL LIST', self.model_list)
            iii=0
            jjj=0
            clrs = ['-g','-m', '-r','-c','-b','-y'] 
            clrs = [sns.xkcd_rgb['grass green']]
            #df = pd.DataFrame()
            #cols=[]
            self.reliability_init(thresh=thresh)
            for lev in levlist:
                df = pd.DataFrame()
                cols=[]
                for name, oris_ts in self.add_model_ts(site, tp='ORIS',
                                                        levlist=lev):
                    if jjj==0: 
                       df = pd.DataFrame(oris_ts)
                    else:
                       df = pd.concat([df, oris_ts], axis=1) 
                    jjj+=1
                    cols.append(name)
                print(df[0:5])
                print(cols)
                df.columns = cols
                df2 = df.copy()
                df['mean'] = df.mean(axis=1)
                df['max'] = df.max(axis=1) 
                df['min'] = df.min(axis=1) 
                df2 = df2.T
                vals = (df2[df2 > thresh].count()) /len(cols)
                #ax1.plot(oris_ts, clrs[iii], label=name)  
                ax2.plot(vals, clrs[iii], linewidth=2, alpha=0.7) 
                ax2.set_yticks([0,0.2,0.4,0.6,0.8,1.0])
                ax2.set_yticklabels(['0','1','2','3','4','5'])
                ax2.tick_params(axis='y', which='major', labelsize=20)
                ax2.grid(b=None, which='major', axis='y')
                yval = df['mean'].values 
                xval = df.index.tolist()
                maxval = df['max'].values
                minval = df['min'].values
                #ax1.plot(xval, yval, clrs[iii], linewidth=2)
                #ax1.fill_between(xval, minval, maxval, alpha=0.4,\
                #                 facecolor=clrs[iii].replace('-','')) 
                iii+=1
            #for name, eis_ts in self.add_model_ts(site, tp='NEI'):
            #    ax1.plot(eis_ts, '-g.', label=name)  
            ax1.plot(so2.sort_index(), '-k', linewidth=2)
            #ax1.set_ylabel('SO2 (ppb)')
            #ax2.set_ylabel('Wind direction (degrees)')
            #ax2.set_ylabel('Probability of C > 2.5 ppb')
            #ax2.grid(False, which='both')

            xdata = so2.index.tolist()
            dt = datetime.timedelta(hours=5*24)
            right = xdata[-1] -dt
            right = datetime.datetime(2018,6,10,0)
            #ax2.set_xlim(left = xdata[0], right=right)  
            ptools.set_date_ticksC(ax1)
            #ax1.set_xlim(left = xdata[0], right=right)  
            ax1.grid(True, which='both')
            #plt.title(str(site))
            fig.autofmt_xdate()
            tag = self.tag
            if not tag: tag = ''
            plt.savefig(tag + str(site) + '.prob.jpg')
            plt.show()
            plt.close()
            self.reliability_add(so2, vals)
        self.reliability_plot()

            
    def reliability_init(self, thresh):
        num = self.get_num_models()
        self.binlist = list(np.arange(0,1, 1.0/num) + 1.0/(num*10))
        self.binlist.append(1)
        #self.binlist = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]
        self.yeshash = {}
        self.nohash = {}
        for binval in self.binlist:
            self.yeshash[binval] = 0
            self.nohash[binval] = 0
        self.thresh = thresh

    def reliability_add(self, obs, prob):
        df = pd.concat([obs, prob], axis=1)
        df.dropna(axis=0, inplace=True)
        cols = ['obs','prob']
        df.columns = cols
        #print(type(df))
        #print(df[0:10])
        for index, row in df.iterrows():
            prob = row['prob'] 
            for pbin in self.binlist:
                if prob <= pbin: 
                   binval = pbin
                   #print('break', binval)
                   break 
            if row['obs'] >= self.thresh:
               self.yeshash[binval] += 1
            else:
               self.nohash[binval] += 1

    def reliability_plot(self):
        xxx = []
        yyy = []
        nnn = []
        yesval = []
        noval = []
        for binval in self.binlist:
            x = binval
            n = self.yeshash[binval] + self.nohash[binval]
            if n != 0:
                noval.append(self.nohash[binval])
                yesval.append(self.yeshash[binval])
                y = self.yeshash[binval] / n
                xxx.append(x)
                yyy.append(y)
                nnn.append(n)
        fig = plt.figure(1)
        ax1 = fig.add_subplot(2,1,1)
        ax2 = fig.add_subplot(2,1,2)   
        ax1.plot(xxx,yyy, '-g.')
        ax1.plot([0,1], [0,1], '-k')
        ax2.plot(xxx, nnn)
        ax2.set_yscale('log')
        plt.savefig('reliability.jpg')
        fig2 = plt.figure(2)
        ax3 = fig2.add_subplot(1,1,1)
        #with open('reliability.txt', 'w') as fid:
        #    fid.write(yesval)
        #    print(noval)
        print('meas > thresh', yesval)
        print('meas < thresh', noval)
        plt.plot(xxx, yesval, '-g.')
        plt.plot(xxx, noval, '-r.')
        plt.show()
        plt.show()

    def plot_all_winds(self):
        # check the relationship  between winds at different sites
        if self.df.empty: return -1
        sns.set()
        sns.set_style('whitegrid')
        slist = self.get_sites()
        self.date2hour()
        fig2 = plt.figure(self.fignum+1)
        fig2.set_size_inches(20,5)
        axh1 = fig2.add_subplot(1,3,1)
        wlist = {}

        df = self.df.copy()
        print(df[0:10])
        #df = df[df['hour'] > 12]
        #df = df[df['hour'] > 21]
        #df = df[df['WS'] >=  2 ]
        # this would result in looking only at times they both had
        # concentrations greater than this.
        #df = df[df['SO2'] >=  2.5 ]
        print(df[0:10])
        df = pd.pivot_table(df, values=['WDIR'], columns=['siteid'],
                            index='time')
        df.dropna(axis=0, inplace=True)

        a = sns.PairGrid(df)
        a.map_diag(sns.distplot)
        a.map_offdiag(sns.jointplot, kind='hex')
        plt.show()
        #c = df.columns.values
        #df['diff'] = df.apply(lambda row: degdiff(row[c[0]], row[c 


    def plot_model_hex(self, levlist=None, save=True, quiet=False, tag=None):

        if self.df.empty: return -1
        sns.set()
        sns.set_style('whitegrid')
        slist = self.get_sites()
        self.date2hour()
        for site in slist:

            fig2 = plt.figure(self.fignum+1)
            fig2.set_size_inches(20,5)
            axh1 = fig2.add_subplot(1,3,1)
            axh2 = fig2.add_subplot(1,3,2)
            axh3 = fig2.add_subplot(1,3,3)

            df = self.df[self.df['siteid'] == site]
            df = df.set_index('time')
            so2 = df['SO2']
            mval = 'WDIR'
            print(df.columns.values)
            wdir = df['WDIR']
            wspd = df['WS']
            hour = df['hour']


            iii=0
            for lev in levlist:
                for name, oris_ts in self.add_model_ts(site, tp='ORIS',
                                                     levlist=lev):

                    cat = pd.concat([oris_ts, wdir], axis=1) 
                    cat = cat.dropna(axis=0)
                    print(cat[0:10])
                    hexbin(cat['WDIR'], cat['model'], axh1)            
                    cat = pd.concat([oris_ts, wspd], axis=1) 
                    hexbin(cat['WS'], cat['model'], axh2)            
                    cat = pd.concat([oris_ts, hour], axis=1) 
                    hexbin(cat['hour'], cat['model'], axh3)            
                    #hexbin(wspd,so2, axh2)            
                    #hexbin(hour,so2, axh3)       
                    ymax = np.max(cat['model'])   
                    ymax = 90
                    orislist = addplants(site, axh1, ymax=ymax,
                                 geoname=self.geoname, add_text=False)
                    axh1.set_xticks([0,45,90,135, 180,225,270,315])
                    axh1.set_xticklabels(['0','','90','', '180','','270',''],fontsize=15)
                    axh2.set_xticks([0,2.5,5,7.5,10])
                    axh2.set_xticklabels(['0','','5','', '10'],fontsize=15)
                    axh3.set_xticks([0,3,6,9,12,15,18,21])
                    axh3.set_xticklabels(['0','','6','', '12','','18',''],fontsize=15)
                    axh1.yaxis.set_major_locator(MultipleLocator(20))
                    axh1.yaxis.set_minor_locator(MultipleLocator(10))
                    axh1.set_ylim(0,ymax+2)  
                    axh1.tick_params(labelsize=15, which='both')
                    axh2.yaxis.set_major_locator(MultipleLocator(20))
                    axh2.yaxis.set_minor_locator(MultipleLocator(10))
                    #axh2.set_xlim(0,15)  
                    axh2.set_ylim(0,ymax+2)  
                    axh2.tick_params(labelsize=15, which='both')
                    axh3.yaxis.set_major_locator(MultipleLocator(20))
                    axh3.yaxis.set_minor_locator(MultipleLocator(10))
                    axh3.set_ylim(0,ymax+2)  
                    axh3.tick_params(labelsize=15,which='both')
                    plt.tight_layout() 
                    if not tag: tag = self.tag
                    plt.savefig(tag + str(site) + '.model_hex.jpg')
                    plt.show() 
                    iii+=1


    def plot_autocorr(self, levlist=None, save=True, quiet=False):
         
        sns.set()
        sns.set_style('whitegrid')
        slist = self.get_sites()
        print('SLIST', slist)
        #self.date2hour()
        for site in slist:
            fig = plt.figure(self.fignum)
            fig.set_size_inches(15,5)


            # re-using these axis produces a warning.
            ax1 = fig.add_subplot(1,1,1)
            #ax2 = ax1.twinx()
            #ax3 = fig.add_subplot(2,1,2)
            #ax3 = ax1.twinx()

            df = self.df[self.df['siteid'] == site]
            df = df.set_index('time')
            so2 = df['SO2']
            mval = 'WDIR'
            wdir = df['WDIR']
            wspd = df['WS']
            #hour = df['hour']
            nlist = np.arange(0,72) 
            wdir_auto = statmain.autocorr(wdir, nlist)
            wspd_auto = statmain.autocorr(wspd, nlist)
 
            wdir.to_csv(str(site) + '.wdir.csv', header=True)
            vpi = so2==-9
            so2[vpi] = float('Nan') 
            #so2_auto = statmain.autocorr(so2, nlist)
            vpi = so2<1
            so2[vpi] =  0
            so2_auto = statmain.autocorr(so2, nlist)

            #ax2.plot(wdir, 'b.', markersize=2)
            #ax2.plot(wdir, '--b.', markersize=2)
            iii=0
            for lev in levlist:
                for name, oris_ts in self.add_model_ts(site, tp='ORIS',
                                                     levlist=lev):
                    acorr = statmain.autocorr(oris_ts, nlist)
                    ax1.plot(nlist, acorr, '-b')
                    iii+=1
            ax1.plot(nlist, so2_auto, '-ko')
            ax1.plot(nlist, wdir_auto, '--r')
            ax1.plot(nlist, wspd_auto, '--g')
            plt.title(str(site))
            plt.savefig(str(site) + 'autocorr.jpg')
            plt.show() 

    def plot_ts(self, levlist=None, save=True, quiet=False):

        # levlist should be a list of lists.
        # for instance [[1],[2],[3]]
        # will plot levels 1,2,3 seperately.
        # [[1,2],[3]]
        # will plot levels 1&2 averaged together and then 3 separately. 
        print('PLOT TS')
        if self.df.empty: return -1
        sns.set()
        sns.set_style('whitegrid')
        slist = self.get_sites()
        self.date2hour()
        for site in slist:
            fig = plt.figure(self.fignum)
            fig.set_size_inches(15,5)


            # re-using these axis produces a warning.
            ax1 = fig.add_subplot(1,1,1)
            #ax2 = ax1.twinx()
            #ax3 = fig.add_subplot(2,1,2)
            #ax3 = ax1.twinx()

            df = self.df[self.df['siteid'] == site]
            df = df.set_index('time')
            so2 = df['SO2']
            mval = 'WDIR'
            wdir = df['WDIR']
            wspd = df['WS']
            hour = df['hour']
            
            wdir.to_csv(str(site) + '.wdir.csv', header=True)
            vpi = so2==-9
            so2[vpi] = float('Nan') 

            #ax2.plot(wdir, 'b.', markersize=2)
            #ax2.plot(wdir, '--b.', markersize=2)
            ax1.plot(so2.sort_index(), '-k', linewidth=3)
            #print('MODEL LIST', self.model_list)
            iii=0
            plume='hrrr'
            plume='hrrrA'
            if plume == 'nam':
                #clrs = [sns.xkcd_rgb['magenta']]
                #clrs.append(sns.xkcd_rgb['rose'])
                #clrs.append(sns.xkcd_rgb['pink'])
                clrs = [sns.xkcd_rgb['scarlet']]
                clrs.append(sns.xkcd_rgb['pale red'])
                clrs.append(sns.xkcd_rgb['salmon'])
                clrs.append(sns.xkcd_rgb['grey'])
                clrs.append(sns.xkcd_rgb['grey'])
                alpha = [1,0.5,0.5,0.5,0.5]
            elif plume == 'hrrr':
                clrs = [sns.xkcd_rgb['grey']]
                clrs.append(sns.xkcd_rgb['grey'])
                clrs.append(sns.xkcd_rgb['grey'])
                clrs.append(sns.xkcd_rgb['bright blue'])
                clrs.append(sns.xkcd_rgb['grey'])
                alpha = [0.5,0.5,0.5,1.0,0.5]
            elif plume == 'hrrrA':
                clrs = [sns.xkcd_rgb['bright blue']]
                clrs.append(sns.xkcd_rgb['grey'])
                clrs.append(sns.xkcd_rgb['light grey'])
                clrs.append(sns.xkcd_rgb['grey'])
                clrs.append(sns.xkcd_rgb['grey'])
                clrs.append(sns.xkcd_rgb['grey'])
                alpha = [0.8,0.4,0.4,0.4,0.4]
            elif plume == 'wrf':
                clrs = [sns.xkcd_rgb['grey']]
                clrs.append(sns.xkcd_rgb['grey'])
                clrs.append(sns.xkcd_rgb['grey'])
                clrs.append(sns.xkcd_rgb['grey'])
                clrs.append(sns.xkcd_rgb['kelly green'])
                alpha = [0.5,0.5,0.5,0.5,1.0]
            else:
                clrs = [sns.xkcd_rgb['magenta']]
                clrs.append(sns.xkcd_rgb['rose'])
                clrs.append(sns.xkcd_rgb['pink'])
                clrs.append(sns.xkcd_rgb['bright blue'])
                clrs.append(sns.xkcd_rgb['kelly green'])
                alpha = [0.5,0.5,0.5,0.5,0.5]


            for lev in levlist:
                for name, oris_ts in self.add_model_ts(site, tp='ORIS',
                                                     levlist=lev):

                    #ax1.plot(oris_ts, clrs[iii], label=name)  
                    ax1.plot(oris_ts, clrs[iii],  label=name, linewidth=2,
                             alpha=alpha[iii])  
                    iii+=1
            #for name, eis_ts in self.add_model_ts(site, tp='NEI'):
            #    ax1.plot(eis_ts, '-g.', label=name)  
            #for model in self.model_list:
                #if model[1] == site:
           #         print('PLOTTING', model)
           #         mso2 = df[model]
           #         ax1.plot(mso2, 'm.')
            # ax2 is for wind direction.
            dlist = oris_ts.index.tolist()
            #daterange = (dlist[0], dlist[-1])
            #orislist = addplants_horizontal(site, ax2, daterange, geoname=self.geoname, neidf=self.neidf)
            #ax1.set_ylabel('so2 (ppb)')
            #ax1.set_yscale('log')
            #ax1.set_ylim(bottom=0.1)  
            ax1.set_ylim(top=60)  
            #ax2.set_ylabel('Wind direction (degrees)')
            #ax2.set_ylabel('Mixing Height')
            #for oris in self.cemslist:
            #    print('ORIS', oris, self.cemslist, df.columns.values)
            #    cems = df[oris]
            #    ax3.plot(cems, '-r.')
            xdata = dlist
            dt = datetime.timedelta(hours=5*24)
            #ax2.set_xlim(left = xdata[0], right=xdata[-1]-dt)  
            ax1.set_xlim(left = xdata[0], right=xdata[-1]-dt)  
          
            #ax2.spines["right"].set_position(("axes", 1.1))
            #ptools.make_patch_spines_invisible(ax2)
            #ax2.spines["right"].set_visible(True)
            #ax2.grid(False, which='both')
            ptools.set_date_ticksD(ax1)
            ax1.grid(True, which='both')
            #plt.title(str(site))
            fig.autofmt_xdate()
            ax = plt.gca()
            handles, labels = ax.get_legend_handles_labels()
            #ax.legend(handles, labels)
            plt.tight_layout() 
            save=True
            if save:
                tag = self.tag
                if not tag: tag = ''
                print('SAVING', plume+str(site) + '.met_ts.jpg')
                plt.savefig(plume + str(site) + '.met_ts.jpg')
            if not quiet:
                plt.show()
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
            else:
                return 8
        print(self.df['PSQ'])
        print('---------------------')
        self.df['psqnum'] = self.df.apply(lambda row: process_psq(row['PSQ']), axis=1)
        self.isempty()      
        return True


    def conditionalB(self, save=False, quiet=True):
        # looks at probability of wind direction for top 5% of SO2 values for
        # all measurements
        # when CEMS above a threshold
        # when CEMS below a threshold.

        # Looking to see if power plant being on or off makes a big difference.
        # 
        slist = self.get_sites()
        sz = [10,5]
        for site in slist:
            sns.set()
            sns.set_style('whitegrid')
            fig = plt.figure(self.fignum)
            fig.set_size_inches(sz[0],sz[1])
            ax = fig.add_subplot(1,1,1)
            df = self.df[self.df['siteid'] == site]
            v1, x1, nnn1 =  self.conditional_sub(df, ax, site, pval=[0.99,1],
                                           color='r', limit=True)    
            orislist = addplants(site, ax, ymax=np.max(nnn1), geoname=self.geoname, neidf=self.neidf)
            plt.close()
            for oris in orislist:
                sns.set()
                sns.set_style('whitegrid')
                fig = plt.figure(self.fignum)
                fig.set_size_inches(sz[0],sz[1])
                ax = fig.add_subplot(1,1,1)
                df = self.df[self.df['siteid'] == site]
                v1, x1, nnn1 =  self.conditional_sub(df, ax, site, pval=[0.99,1],
                                               color='r', limit=True,
                                               density=False)    
                orislist = addplants(site, ax, ymax=np.max(nnn1), geoname=self.geoname, neidf=self.neidf)

                print('Adding step for ', oris)
                self.add_more(oris, df, site, ax)
                ax.set_xlabel('Wind Direction (degrees)')
                ax.set_ylabel('Probability')  
                ptools.set_legend(ax, bw=0.60)
                plt.title(str(site) + ' ORIS: ' + str(oris[0]))
                plt.tight_layout(rect=[0,0,0.75,1])
                plt.savefig(str(site) + 'cpdf.jpg')
                plt.show() 
    


    def conditional(self, save=False, quiet=False, varlist=['SO2']):
        slist = self.get_sites()
        sz = [10,5]
        for site in slist:
            for var1 in varlist:
                sns.set()
                sns.set_style('whitegrid')
                fig = plt.figure(self.fignum)
                fig.set_size_inches(sz[0],sz[1])
                ax = fig.add_subplot(1,1,1)
                df = self.df[self.df['siteid'] == site]


                v1, x1, nnn1 =  self.conditional_sub(df, ax, site, pval=[0.99,1],
                                               color='r', limit=True, var1=var1)    
                # lower limit should not be less than mdl
                v2, x2, nnn2 =  self.conditional_sub(df, ax, site, pval=[0.95,0.99],    
                                               color='b', limit=True, var1=var1)    
               
                v3, x3, nnn3  =  self.conditional_sub(df, ax, site, pval=[0,0.2],    
                                               color='g', limit=False, var1=var1)    
                #if upper limit of green < lower limit of blue
                # and lower limit of blue is greater than 5
                # then add a fourth distribution.
                #if x3 < v2 and v2 > 5:
                #   v4, x4, nnn4 =  self.conditional_sub(df, ax, site, pval=[0.2,0.95],    
                #                               color='c', limit=True)    
                ymax = 0.90 * np.max([np.max(nnn1), np.max(nnn2), np.max(nnn3)])
                orislist = addplants(site, ax, ymax=ymax, geoname=self.geoname, neidf=self.neidf)
                #for oris in [orislist[0]]:
                #    print('Adding step for ', oris)
                #    self.add_more(oris, df, site, ax)

                ax.set_xlabel('Wind Direction (degrees)')
                ax.set_ylabel('Probability')  
                ptools.set_legend(ax, bw=0.60)
                plt.title(str(site) + str(var1))
                #plt.tight_layout(rect=[0,0,0.75,1])
                plt.savefig(str(site) + 'cpdf.jpg')
                self.fignum +=1
            plt.show() 


    def add_more(self, orisinfo, indf, site, ax):
        df = indf.copy()
        oris  = orisinfo[0]
        distance = orisinfo[1]
        roll=12
        thresh = 50 * roll
        print('dfroll--------')
        # want to take into account emission during the previous 12
        # hours
        df['roll'] = df[oris].rolling(roll).sum()
        #df = dfroll.copy()
        #print('df--------')
        #print(df[0:36])
        # only take values where cems is above threshold.
        #df = df[df[oris] >= thresh]
        df2 = df[df['roll'] >= thresh]
        print('ON size', df2.size)
        v1, x1, nnn1 =  self.conditional_sub(df2, ax, site, pval=[0.95,1],
                                             color='r', limit=True, step=True,
                                             density=False)    
        # only take values where cems is below threshold.
        #df = indf.copy()
        df2 = df[df['roll'] < thresh]
        print('off size', df2.size)
        #df = dfroll.copy()
        #df = df[df[oris] < thresh]
        v1, x1, nnn1 =  self.conditional_sub(df2, ax, site, pval=[0.95,1],
                                             color='k', limit=True, step=True)    


    def conditionalA(self, distrange=5, roll=12):
        # roll gives how many hours of emission to take into account.
        # sums the previous roll (default 12)  hours.

        # for each site.
        # for each ORIS code.
        # find wdir to that ORIS code from the site.
        # keep only points within 5 degrees of that wdir.
        # look at SO2 values when CEMS are high
        # look at SO2 values when CEMS are low.
        # plot together.
        slist = self.get_sites()
        sz = [10,5]
        sns.set()
        sns.set_style('whitegrid')
        if 'time' in self.cemslist:
            self.cemslist.remove('time')
        fignum = 1
        maxdist = 100
        for site in slist:
            fig = plt.figure(fignum)
            sitedf = self.df[self.df['siteid'] == site]
            disthash, dirhash = geometry2hash(site, fname=self.geoname)
            nnn=0
            for key in disthash.keys():
                if disthash[key] < maxdist: 
                  nnn+=1
            nnn=1
            sz = [10,5*nnn]
            print(str(site), str(nnn)) 
            fig.set_size_inches(sz[0],sz[1])
            iii = 1
            for oris in self.cemslist:
                direction = dirhash[oris]
                distance  = disthash[oris]
                if distance > maxdist: continue
                print('ORIS', oris, direction, distance)
                df = sitedf.copy()
                valA = direction + distrange
                if valA > 360: valA = 360-valA
                valB = direction - distrange
                if valB < 0: valB = 360+ valB
                print('between ', str(valB), str(valA))
                df = df[df['WDIR']<=valA]
                df = df[df['WDIR']>=valB]
                df.dropna(axis=0, inplace=True)
                print(df)
                if df.empty: continue 
                fig = plt.figure(fignum)
                fig.set_size_inches(sz[0],sz[1])
                ax = fig.add_subplot(1,1,1)
                dfroll = df[oris]
                # want to take into account emission during the previous 12
                # hours
                #dfroll = dfroll.rolling(roll).sum()
               
                
                hexbin(df['SO2'], dfroll, ax, cbar=True)  
                iii += 1
                ax.set_title(str(site) + ' ' + str(oris) ) 
                #if iii > 2: break
                plt.show() 

    def conditional_sub(self,df, ax, site, pval, label=None, color='b',
                       var1='SO2', limit=True, step=False, density=True): 
        #var1='SO2'
        df = df.fillna(0)
        var2='WDIR'
        mdl=df['mdl'].unique()
        ra = df[var1].tolist()
        valA = statmain.probof(ra, pval[0]) 
        valB = statmain.probof(ra, pval[1]) 
        #print('VALA, VALB', valA, valB)
        #if valB < 0.2: valB = 0.25
        #print('MDL', mdl)
        try:
             if mdl:
                if valA <= mdl[0] and limit: valA = mdl[0] 
        except:
             print('MDL not valid', mdl)
        
        if valA > valB: 
           return valA, valB, 0


        tdf = df[df[var1] >= valA]          
        tdf = tdf[tdf[var1] <= valB]          
        #print(tdf.columns.values) 
        tdf = tdf.set_index('time')
        hhh = tdf[var2]
        #print('SIZE', tdf.size)
        # do not use values with NAN
        hhh = hhh.fillna(-10)
        #hhh = hhh[hhh != -9]
        if not label: 
           label = "{0:2.2f}".format(valA)  
           label += ' to '
           label += "{0:2.2f}".format(valB)  
           label += ' ppb'
        bins = np.arange(0,365,5)
        nnn, rbins = myhist(hhh.values,ax, bins=bins, label=label, color=color,
                            step=step, density=density)
        return valA, valB, nnn

    def plothexbin(self, save=True, quiet=True): 
        # 2d histograms of obs and wind speed
        # 2d histogram of obs and wind direction.
        if self.df.empty: return -1
        slist = self.get_sites()
        nnn=3
        aaa=1
        sz=(20,5)
        sz1=(10,15)
        psqplot = self.PSQ2NUM()
        self.date2hour()
        if psqplot: 
           nnn=2
           aaa=3
           bbb=1
           sz=(15,10)
           sz1=(10,15)

        for site in slist:
            sns.set()
            sns.set_style('whitegrid')
            sns.set_context('talk', font_scale=1.2)
            fig = plt.figure(1)
            #fig1 = plt.figure(self.fignum+1)
            #fig2 = plt.figure(self.fignum+1)
            #axts = fig2.add_subplot(1,1,1)
            #fig2 = plt.figure(self.fignum+1)
            #fig3 = plt.figure(self.fignum+2)
            #fig4 = plt.figure(self.fignum+3)
            #fig5 = plt.figure(self.fignum+4)
            #fig6 = plt.figure(self.fignum+5)
            fig.set_size_inches(sz[0],sz[1])
            #fig1.set_size_inches(sz1[0],sz1[1])
            #fig2 = plt.figure(self.fignum+1)
            #fig2.set_size_inches(sz[0],sz[1])
            # re-using these axis produces a warning.
            ax1 = fig.add_subplot(aaa,nnn,1)
            ax2 = fig.add_subplot(aaa,nnn,2)
            ax3 = fig.add_subplot(aaa,nnn,3)
            if psqplot:
                #ax3 = fig.add_subplot(aaa,nnn,3)
                ax5 = fig.add_subplot(aaa,nnn,4)
                ax4 = fig1.add_subplot(aaa,bbb,1)
                ax6 = fig1.add_subplot(aaa,bbb,2)
                ax7 = fig1.add_subplot(aaa,bbb,3)

            df = self.df[self.df['siteid'] == site]
            print('HEXBIN for site ' , site) 
            print(df[0:10])
            #df.columns = self.met_header(df.columns)
            #print(df.columns.values)
            #xtest = df[("WD", "Degrees Compass")]
            # remove missing measurements.
            df = df[df["SO2"] != -9]      
            #df = df[df["SO2"] >= 1]      
 
            xtest = df["WDIR"]
            ytest = df["WS"]
            ztest = df["SO2"]
            htest = df['hour']
            #axts.plot(df['time'], xtest, '-b.') 
            if psqplot:
               # do not include Nans in the distributions.
               dftemp = df[df['psqnum']<8] 
               p1test = dftemp['psqnum']       
               p2test = dftemp['psqnum']       
               htest = dftemp['hour']

               xtest = dftemp["WDIR"]
               ytest = dftemp["WS"]
               ztest = dftemp["SO2"]
               print(dftemp.columns.values) 
               pbl = dftemp['MixHgt']
               print(dftemp[dftemp['MixHgt'] < 150])
 
            if np.isnan(xtest).all():
                print('No data WDIR', site)
                continue
            if np.isnan(ztest).all():
                print('No data so2', site)
                continue
            cbar= True
            hexbin(xtest, ztest, ax1, cbar=cbar)  
            ymax = np.max(ztest)
            addplants(site, ax1, ymax=ymax, dthresh=50,  geoname=self.geoname,
                      add_text=False)
            #hexbin(htest, ztest, ax2, cbar=cbar) 
            hexbin(ytest, ztest, ax2, cbar=cbar) 
            hexbin(htest, ztest, ax3, cbar=cbar)
            if psqplot:
               hexbin(htest, p2test, ax4, cbar=cbar)
               hexbin(p2test, ztest, ax7, cbar=cbar)
               hexbin(pbl, ztest,  ax5, cbar=cbar) 
               hexbin(p2test,pbl,  ax6, cbar=cbar) 
            #ax1.set_xlabel('Wind Direction ')
            #ax2.set_xlabel('Wind Speed ')
            #ax2.set_xlabel('Hour of day (UTC)')
            #ax1.set_ylabel('SO2 (ppb)')
            ax1.set_xticks([0,45,90,135, 180,225,270,315])
            ax1.set_xticklabels(['0','','90','', '180','','270',''],fontsize=15)
            ax2.set_xticks([0,2.5,5,7.5,10])
            ax2.set_xticklabels(['0','','5','', '10'],fontsize=15)
            ax3.set_xticks([0,3,6,9,12,15,18,21])
            ax3.set_xticklabels(['0','','6','', '12','','18',''],fontsize=15)

            ax1.yaxis.set_major_locator(MultipleLocator(10))
            ax1.yaxis.set_minor_locator(MultipleLocator(5))
            ax1.set_ylim(0,ymax+2)  
            ax1.tick_params(labelsize=15, which='both')
            ax2.yaxis.set_major_locator(MultipleLocator(10))
            ax2.yaxis.set_minor_locator(MultipleLocator(5))
            ax2.set_xlim(0,15)  
            ax2.set_ylim(0,ymax+2)  
            ax2.tick_params(labelsize=15, which='both')
            ax3.yaxis.set_major_locator(MultipleLocator(10))
            ax3.yaxis.set_minor_locator(MultipleLocator(5))
            ax3.set_ylim(0,ymax+2)  
            ax3.tick_params(labelsize=15,which='both')
            #yt = np.arange(0,ymax,5)
            #ax1.tick_params(labelsize=15)
            #ax2.tick_params(labelsize=15)
            #ax3.tick_params(labelsize=15)
            #ax1.set_yticks(yt)
            #ax2.set_yticks(yt)
            #ax3.set_yticks(yt)

            #ax1.set_ylim(0,ymax+2)  
            #ax2.set_ylim(0,ymax+2)  
            #ax3.set_ylim(0,ymax+2)  

            plt.tight_layout() 
            if psqplot:
               ax7.set_xlabel('PSQ')
               ax7.set_ylabel('SO2 (ppb)')
               ax7.set_xticks([1,2,3,4,5,6,7])
               ax7.set_xticklabels(['A','B','C','D','E','F','G'])

               ax4.set_xlabel('time')
               ax4.set_ylabel('PSQ')
               ax4.set_yticks([1,2,3,4,5,6,7])
               ax4.set_yticklabels(['A','B','C','D','E','F','G'])
               ax5.set_xlabel('PBL height (m) ')
               ax6.set_ylabel('PBL height ')
               ax6.set_xlabel('Stability')
               ax6.set_xticks([1,2,3,4,5,6,7])
               ax6.set_xticklabels(['A','B','C','D','E','F','G'])
            #ax1.set_title(str(site))
            plt.tight_layout() 
            if save:
                tag = self.tag
                if not tag: tag = ''
                plt.sca(ax1)
                plt.savefig(tag + str(site) + '.met_distA.jpg')
                if psqplot:
                   plt.sca(ax4)
                   plt.savefig(tag + str(site) + '.met_distB.jpg')
            #self.fignum +=1
            if not quiet:
                plt.show()
            # clearing the axes does not
            # get rid of warning.
            plt.cla()
            plt.clf()
            plt.close()  

