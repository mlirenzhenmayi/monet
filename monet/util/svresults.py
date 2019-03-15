# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import numpy as np
import datetime
import time
import os
from os import path, chdir
from subprocess import call
import pandas as pd
from monet.verification.statmain import MatchedData
import seaborn as sns
"""
"""

def results(dfile, runlist):
    from monet.util.datem import read_dataA
    from monet.util.datem import frame2datem
    import matplotlib.pyplot as plt
    df = pd.DataFrame()
    nnn=0
    for run in runlist:
        fname = run.directory + '/dataA.txt'
        print(fname)
        tempdf = read_dataA(fname)
        if nnn==0 and not tempdf.empty:
           df = tempdf.copy()
           nnn+=1
        elif not tempdf.empty:
           df = pd.merge(df, tempdf, how='outer')
        elif tempdf.empty:
           print('-----------------------------')
           print('WARNING: svhy.py results method empty dataframe')
           print(fname)
           print('-----------------------------')
    df['duration'] = "0100"
    df['altitude'] = 20
    #print(df[0:10])
    #frame2datem(dfile, df, cnames=['date','duration','lat', 'lon',
    #                        'obs','model','sid','altitude'] )
       
    df['obs'].fillna(0, inplace=True)
    df['model'].fillna(0, inplace=True)
    df2 = df.set_index('date') 
    mdata = MatchedData(df2['obs'], df2['model'])
    print('*ALL*')
    #print(df2[0:10])
    print(mdata.find_stats()) 
    sns.set()
    for site in df['sid'].unique():
        dfile2 = str(site) + '.' + dfile 
        dftemp = df[df['sid']==site]
        dftemp.set_index('date', inplace=True)
        dftemp = dftemp.resample('H').asfreq()
        dftemp['obs'].fillna(0, inplace=True)
        dftemp['model'].fillna(0, inplace=True)
        dftemp['duration'].fillna(method='bfill', inplace=True)
        dftemp['lat'].fillna(method='bfill', inplace=True)
        dftemp['lon'].fillna(method='bfill', inplace=True)
        dftemp['sid'].fillna(method='bfill', inplace=True)
        dftemp['altitude'].fillna(method='bfill', inplace=True)
        dftemp.reset_index(inplace=True)
        #print(dftemp[0:10])
        #frame2datem(dfile2, dftemp, cnames=['date','duration','lat', 'lon',
        #                    'obs','model','sid','altitude'] )
         
        dftemp.set_index('date', inplace=True)
        obs= dftemp['obs']
        model = dftemp['model']
        msitedata = MatchedData(obs, model)
        dhash = msitedata.find_stats()
        print(str(site))
        print('RMSE', str(dhash['rmse']))
        print('NMSE', str(dhash['nmse']))
        #plt.plot(obs,'--r')
        #plt.plot(model,'--k')
        obs.plot()
        model.plot()
        plt.title(str(site))
        plt.show()


