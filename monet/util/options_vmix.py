import matplotlib.pyplot as plt
from monet.util.svhy import read_vmix
from monet.util.svobs import SObs
from monet.util.svmet import vmixing2metobs
from monet.util.svmet import metobs2matched


##------------------------------------------------------##
#vmet is a MetObs object.
#vmetdf is the dataframe associated with that.
#vmetdf = pd.DataFrame()

def options_vmix_main(options, d1, d2, area, source_chunks,
                      logfile):
   with open(logfile, 'a') as fid:
     fid.write('Running vmix=1 options\n')
   from monet.util.svhy import read_vmix
   from monet.util.svobs import SObs
   from monet.util.svmet import vmixing2metobs

   df = read_vmix(options.tdir, d1, d2, source_chunks, sid=None)
   vmet = vmixing2metobs(df,obs.obs)
   if not df.empty:
      # start getting obs data to compare with.
      obs = SObs([d1, d2], area, tdir=options.tdir)
      obs.find(tdir=options.tdir, test=options.runtest, units=options.cunits)
    
      # outputs a MetObs object. 
      #vmet = vmixing2metobs(df,obs.obs)
      vmet.set_geoname(options.tag + '.geometry.csv')
      sites = vmet.get_sites()
      pstr=''
      for sss in sites:
           pstr += str(sss) + ' ' 
      print('Plotting met data for sites ' + pstr)
      quiet=True
      if options.quiet < 2:
          quiet=False
      #vmet.plot_ts(quiet=quiet, save=True) 
      #vmet.nowarning_plothexbin(quiet=quiet, save=True) 
      vmet.conditional(quiet=quiet, save=True) 
      vmet.to_csv(options.tdir, csvfile = options.tag + '.vmixing.'  + '.csv')
      #vmetdf = vmet.df
   else:
      print('No vmixing data available')
   return vmet

def options_vmix_met(options, vmet, meto, logfile):
    # compare vmixing output with met data from AQS. 
   if not vmet.df.empty and not meto.df.empty:
       with open(logfile, 'a') as fid:
             fid.write('comparing met and vmixing data\n')
       mdlist = metobs2matched(vmet.df, meto.df)
       fignum=10
       for md in mdlist:
           #print('MATCHED DATA CHECK')
           #print(md.stn)
           #print(md.obsra[0:10])
           #print('---------------------')
           
           fig = plt.figure(fignum)
           ax = fig.add_subplot(1,1,1)
           md.plotscatter(ax)
           save_str = str(md.stn[0]) + '_' + str(md.stn[1])
           plt.title(save_str)
           plt.savefig(save_str + '.jpg')
           fignum+=1
           if str(md.stn[1])=='WDIR' or str(md.stn[1])=='WS':
              fig = plt.figure(fignum)
              ax = fig.add_subplot(1,1,1)
              wdir=False
              if md.stn[1] == 'WDIR': wdir=True
              md.plotdiff(ax, wdir=wdir)
              save_str = 'TS_' + str(md.stn[0]) + '_' + str(md.stn[1])
              plt.savefig(save_str + '.jpg')
              fignum+=1
       if options.quiet < 2: 
          plt.show()
       else:
          plt.close()
