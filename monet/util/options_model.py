import matplotlib.pyplot as plt
import pandas as pd
from monet.util.svresults3 import DatemOutput
from monet.util.svcems import SourceSummary
from monet.util.svcems import CEMScsv
from monet.util.svens import create_member_list_srefA
from os import path
import sys
##------------------------------------------------------##
#vmet is a MetObs object.
#vmetdf is the dataframe associated with that.
#vmetdf = pd.DataFrame()

# Step1: vmet needs to already exist.

# Step2: create DatemOuptut object.  

# Step3: add this object to the svmet object.


def options_model_ts(options, d1, d2, vmet, logfile, model_list=None):
    print('MODEL TS')
    model_list  = get_model_list(1)
    model_list = ['F2hrrr', 'B4nam12', 'B4wrf','B17nam12', 'Bnam12']
    
    levlist = [[1,2]]
    #levlist = [[4,5]]
    sss = SourceSummary(fname = options.tag + '.source_summary.csv')
    orislist = sss.check_oris(10)
    for model in model_list:
        tdir = path.join(options.tdir + model)
        print('TDIR', tdir)
        options_model_sub(vmet, tdir, orislist, [d1,d2], model)
    vmet.plot_ts(levlist=levlist) 
    #vmet.plot_autocorr(levlist=levlist) 
    #vmet.plot_spag(levlist=levlist) 
    #vmet.plot_model_hex(levlist=levlist, tag=model_list[0]) 
    #vmet.plot_cdf(levlist=levlist) 
    plt.show()

def get_model_list(number):
    model_list = []
    if number == 1: 
        model_list = ['B4nam12', 'B17nam12','Bnam12','F2hrrr','B4wrf']
    elif number == 2: 
        # uses Beljaar holstead for the low plume rise nam
        model_list = ['B17nam12', 'B4nam12','Enam12','F2hrrr','B4wrf']
    return model_list

def options_model_main(options, d1, d2, vmet,
                      logfile, model_list=None):

    print('IN OPTIONS MODEL MAIN')
    #vmet.plot_all_winds()
    #sys.exit()
     
    # used for plotting the time series.
    options_model_ts(options, d1, d2, vmet, logfile, model_list=None)
    sys.exit()

    model_list = get_model_list(1)
    #model_list = ['Bwrf']
    options_model_prob(options, d1, d2, vmet, logfile, model_list=model_list)

def options_model_prob(options, d1, d2, vmet,
                      logfile, model_list=None):
   """
   code for 
   """
   print('Model list', model_list)

   #levlist = [[4,5]]
   levlist = [[1]]
   with open(logfile, 'a') as fid:
     fid.write('Running options.datem\n')
   sss = SourceSummary(fname = options.tag + '.source_summary.csv')
   orislist = sss.check_oris(10)
   for model in model_list:
       tdir = path.join(options.tdir + model)
       options_model_sub(vmet, tdir, orislist, [d1,d2], model)
   #vmet.plot_ts(levlist=levlist) 
   vmet.plot_prob(levlist=levlist) 
   plt.show()

def options_model_sub(vmet, tdir, orislist, daterange, name):
   print('ADDING model ', name)
   svr = DatemOutput(tdir, orislist=orislist, daterange=daterange)
   flist = svr.find_files()
   svr.create_df(flist)
   svr.writedatemall(name + '.datem.txt')
   #svr.plotall()
   if not vmet.isempty():
       #datemdf = svr.get_pivot()
       vmet.add_model_object(name=name, model=svr)
       #vmet.add_model_all(datemdf)
       #vmet.conditional_model(varlist=['SO2', 'model'])
       #vmet.add_model(datemdf, verbose=True)
       #vmet.plot_ts() 
       #plt.show() 
   else:
       print('VMET IS EMPTY')
