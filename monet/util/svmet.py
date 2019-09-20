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
from monet.util import ptools
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
        print('vmix2obs---', dfnew[-10:])
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

    if neidf.empty:
       return 1, '-r', 'unknown'
    df = neidf[neidf['EIS_ID'].str.contains(eis.replace('EIS',''))]  
    if df.empty:
       #print(eis, ' empty')
       return 1, '-c', 'unknown'
    tp = df.iloc[0]['naics']
    facility=df.iloc[0]['facility']
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
                if facility == 'unknown' and dist > 10:
                   continue
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
    add_text=True 
    # tlist is list of tuples with information on each source.
    tlist, nlen = addplants_subA(site, geoname, dthresh)
    orislist, textra = addplants_subB(tlist, ymax, neidf, dthresh)
    for  val in textra:     
         #print(val)
         ax.plot([val[0], val[0]], [0,val[1]], linewidth=val[4], color=val[5])
         if add_text:
             ax.text(val[0]+1, val[1], val[2],fontsize=8, color="blue")
    return orislist

def addplants_horizontal(site, ax, xr, dthresh=150, add_text=True,
              geoname='geometry.csv', neidf=pd.DataFrame()):
    # add horizontal lines with direction to power plants to the
    # time series.
    tlist, nlen = addplants_subA(site, geoname, dthresh)
    orislist, textra = addplants_subB(tlist, ymax, neidf)
    for  val in textra:   
         # height is the wind direction.
         pnt1 = [xr[0], val[0]]
         pnt2 = [xr[1], val[0]] 
         # still use linewidth to indicate source strength 
         ax.plot(pnt1, pnt2,  linewidth=val[4], alpha=0.5)
         if add_text:
             ax.text(xr[0], val[0]+1, val[2],fontsize=8, color="blue")
    return orislist


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

        self.cemslist = []  #list of column names representing cems data.
        self.model_list = [] #list of columnnames representing model data

        self.neidf = pd.DataFrame()
        self.empty = self.isempty()

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

    def add_model(self, mdf, verbose=True):
        # RIGHT NOW - must add model after creating from vmixing data.
        # or from_vmix will overwrite the self.df
        # add model output to the main dataframe.
        # use the 
     
        # instead of merging the model data to the dataframe.
        # might be best to simply add the model object.
        # and produce time series from it as needed to be merged.

        self.model_list = list(mdf.columns.values)
        print(self.model_list)
        if 'time' in self.model_list: self.model_list.remove('time')
        if 'siteid' in self.model_list: self.model_list.remove('siteid')
        self.model_columns = mdf.columns.values

        if self.df.empty:
           self.df = mdf
        else:
            metobscol = ['time']
            modelcol = ['time'] 
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


    def add_model_object(self, model):
        self.model = model

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
        
          

    def add_cems(self, cemsdf, verbose=True):
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
        if verbose: print('CEMSLIST', self.cemslist)
        if 'time' in self.cemslist:
           self.cemslist.remove('time')

        if self.df.empty:
           self.df = cemsdf
        else:
           self.df = pd.merge(self.df, cemsdf, how='left', left_on=grouplist,
                               right_on=grouplist) 
        if verbose: print('CEMSLIST', self.cemslist)
        self.isempty()

    def from_vmix(self,df):
        # Currenlty this overwrites anything that used to be in self.df
        self.df = df
        self.columns_original = self.df.columns.values
        self.rename_columns()
        self.isempty()      
 
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
           self.df = self.df.dropna(axis=0, how='all', subset=overlap)
        self.isempty()      

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
            #ax3 = fig.add_subplot(2,1,2)
            ax3 = ax1.twinx()

            df = self.df[self.df['siteid'] == site]
            df = df.set_index('time')
            so2 = df['SO2']
            wdir = df['WDIR']
            ax2.plot(wdir, 'b.', markersize=2)
            ax1.plot(so2, '-k')
            for model in self.model_list:
                if model[1] == site:
                    print('PLOTTING', model)
                    mso2 = df[model]
                    ax1.plot(mso2, 'm.')
            # ax2 is for wind direction.
            #orislist = addplants(site, ax2, ymax=np.max(nnn1), geoname=self.geoname, neidf=self.neidf)
            ax1.set_ylabel('so2 (ppb)')
            ax2.set_ylabel('Wind direction (degrees)')
            #for oris in self.cemslist:
            #    print('ORIS', oris, self.cemslist, df.columns.values)
            #    cems = df[oris]
            #    ax3.plot(cems, '-r.')

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
    


    def conditional(self, save=False, quiet=False, varlist=['SO2', 'model']):
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
                plt.tight_layout(rect=[0,0,0.75,1])
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
        nnn=2
        aaa=1
        sz=(10,5)
        psqplot = self.PSQ2NUM()
        if psqplot: 
           nnn=2
           aaa=3
           sz=(10,15)
           self.date2hour()

        for site in slist:
            sns.set()
            sns.set_style('whitegrid')
            fig = plt.figure(self.fignum)
            fig.set_size_inches(sz[0],sz[1])
            fig2 = plt.figure(self.fignum+1)
            fig2.set_size_inches(sz[0],sz[1])
            # re-using these axis produces a warning.
            ax1 = fig.add_subplot(aaa,nnn,1)
            ax2 = fig.add_subplot(aaa,nnn,2)
            if psqplot:
                ax3 = fig.add_subplot(aaa,nnn,3)
                ax4 = fig.add_subplot(aaa,nnn,4)
                ax5 = fig.add_subplot(aaa,nnn,5)
                ax6 = fig.add_subplot(aaa,nnn,6)

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
               hexbin(p2test, ztest, ax3, cbar=cbar)
               hexbin(htest, p1test, ax4, cbar=cbar)
               hexbin(ztest, pbl, ax5, cbar=cbar) 
               hexbin(p2test,pbl,  ax6, cbar=cbar) 
            ax1.set_xlabel('Wind Direction ')
            ax2.set_xlabel('Wind Speed ')
            ax1.set_ylabel('SO2 (ppb)')
            if psqplot:
               ax3.set_xlabel('PSQ')
               ax4.set_xlabel('time')
               ax4.set_ylabel('PSQ')
               ax5.set_ylabel('PBL height ')
               ax5.set_xlabel('SO2')
               ax6.set_ylabel('PBL height ')
               ax6.set_xlabel('Stability')
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

