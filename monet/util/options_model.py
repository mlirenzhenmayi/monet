import matplotlib.pyplot as plt
import pandas as pd
from monet.util.svresults3 import DatemOutput
from monet.util.svcems import SourceSummary
from monet.util.svcems import CEMScsv
from os import path

##------------------------------------------------------##
#vmet is a MetObs object.
#vmetdf is the dataframe associated with that.
#vmetdf = pd.DataFrame()

# Step1: vmet needs to already exist.

# Step2: create DatemOuptut object.  

# Step3: add this object to the svmet object.


def options_model_main(options, d1, d2, vmet,
                      logfile, model_list=None):
   """
   code for 
   """
   model_list = ['y2019', 'arw_ctl', 'arw_n1','arw_n2']
   with open(logfile, 'a') as fid:
     fid.write('Running options.datem\n')
   sss = SourceSummary(fname = options.tag + '.source_summary.csv')
   orislist = sss.check_oris(10)
   for model in model_list:
       tdir = path.join(options.tdir + model)
       options_model_sub(vmet, tdir, orislist, [d1,d2], model)
   vmet.plot_ts() 
   plt.show()

def options_model_sub(vmet, tdir, orislist, daterange, name):
   print('ADDING model ', name)
   svr = DatemOutput(tdir, orislist=orislist, daterange=daterange)
   flist = svr.find_files()
   svr.create_df(flist)
   #svr.plotall()
   if not vmet.empty:
       #datemdf = svr.get_pivot()
       vmet.add_model_object(name=name, model=svr)
       #vmet.add_model_all(datemdf)
       #vmet.conditional_model(varlist=['SO2', 'model'])
       #vmet.add_model(datemdf, verbose=True)
       #vmet.plot_ts() 
       #plt.show() 
