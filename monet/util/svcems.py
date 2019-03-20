import os
import sys
import subprocess
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
import seaborn as sns
from monet.obs import cems_mod
import monet.obs.obs_util as obs_util
#from arlhysplit import runh
from monet.util.svdir import date2dir
#from arlhysplit.runh import source_generator
#from arlhysplit.runh import create_plume
#from arlhysplit.tcm import TCM
from monet.utilhysplit import emitimes
#from monet.obs.epa_util import convert_epa_unit

"""
SEmissions class
"""


class SEmissions(object):
    """This class for running the SO2 HYSPLIT verification.
       self.cems is a CEMS object

       methods
       find_emissions
       get_sources
       plot - plots time series of emissions
       map  - plots locations of power plants on map
    """
    def __init__(self, dates, area, states=['nd'], tdir='./'):
        """
        self.sources: pandas dataframe
            sources are created from a CEMSEmissions class object in the get_sources method.

        area: list or tuple of four floats
             (lat, lon, lat, lon) describing lower left and upper right corner
              of area to consider. Note that the user is responsible for
              requestiong all states that may lie within this area. 
        states: list of strings
              list of two letter state abbreviations. Data for all states listed
              will be downloaded and then stations outside of the area requested
              will be pruned.
        """
        ##dates to consider.
        self.d1 = dates[0]
        self.d2 = dates[1]
        self.states=states
        #area to consider
        self.area = area
        self.pfile = './' + 'obs' + self.d1.strftime("%Y%m%d.") + self.d2.strftime("%Y%m%d.") + 'pkl'
        self.tdir = tdir
        self.fignum = 1
        ##self.sources is a DataFrame returned by the CEMS class.
        self.cems= cems_mod.CEMS()
        self.sources = pd.DataFrame()
        self.ethresh = 100 #lbs emittimes only created if max emission over
                           #this.
    
        self.lbs2kg = 0.453592

    def find(self, testcase=False, byunit=False, verbose=False):
        """find emissions using the CEMSEmissions class
           
           prints out list of emissions soures with information about them.

           self.ehash : self.ehash used in 
           self.stackhash : not used anywhere else?
        """
        print("FIND EMISSIONS")
        area = self.area
        if testcase:
            efile = 'emission_02-28-2018_103721604.csv'
            self.cems.load(efile, verbose=verbose)
        else:
            self.cems.add_data([self.d1, self.d2], states=self.states,
                                download=True, verbose=True)
        if area:
            self.cems.df = obs_util.latlonfilter(self.cems.df, (area[0], area[1]), (area[2], area[3]))

        self.ehash = self.cems.create_location_dictionary()
        
        self.stackhash = cems_mod.get_stack_dict(cems_mod.read_stack_height(), orispl=self.ehash.keys())

        #key is the orispl_code and value is (latitude, longitude)
        #print('List of emissions sources found\n', self.ehash)
        #print('----------------')
        namehash = self.cems.create_name_dictionary()
        self.meanhash={}    
        ##This gets a pivot table with rows time.
        ##columns are (orisp, unit_id) or just (orisp)
        data1 = self.cems.cemspivot(('so2_lbs'), daterange=[self.d1, self.d2],
                verbose=True, unitid=byunit)
        badoris=[]
        for oris in data1.columns:
            keep= self.check_oris(data1[oris], oris)
            if not keep: badoris.append(oris)
        self.badoris=badoris
        data1.drop(badoris, inplace=True, axis=1)

        #print('done with pivot----------------')
        #print(self.ehash)
       
        #columns=['ORIS','Name','latlon','Mean (kg)','Max (kg)','Stack']
        columns=['ORIS','Name', 'lat','lon', 'Mean(kg)', 'Max(kg)', \
                 'Stack (id=ht(m)']
        slist = []
        for oris in self.ehash.keys():
            sublist = []
            print('----------------')
            print(namehash[oris])
            print('ORISPL ' + str(oris))
            try:
                #data = data1[loc].sum(axis=1)
                data = data1[oris]
            except: 
                data = pd.Series()
            qmean = data.mean(axis=0)
            qmax = data.max(axis=0) 
            sublist.append(oris) 
            sublist.append(namehash[oris])
            sublist.append(self.ehash[oris][0])  #latlon tuple
            sublist.append(self.ehash[oris][1])  #latlon tuple
            print(self.ehash[oris])
            if not np.isnan(qmean):
                self.meanhash[oris] = qmean * self.lbs2kg
                sublist.append(int(qmean*self.lbs2kg)) #mean emission (kg)
            else: 
                self.meanhash[oris] = -99
                sublist.append(-99) #mean emission (kg)
            if not np.isnan(qmax):
                sublist.append(int(qmax*self.lbs2kg))  #max emission (kg)
            else:  
                sublist.append(-99)  #max emission (kg)

            print('Mean emission (lbs)', qmean)
            print('Maximum emission (lbs)', qmax)
            print('Stack id, Stack height (meters)')
            rstr=''
            if oris in self.stackhash.keys():
                for val in self.stackhash[oris]:
                    rstr += str(val[0]) + ' = ' + str(int(val[1]*0.3048)) + ', '
                    print(str(val[0]) + ',    ' + str(int(val[1]*0.3048)))
            else: 
                print('unknown stack height')
                rstr += '-99'
            sublist.append(rstr)
            slist.append(sublist)
        self.sumdf = pd.DataFrame(slist, columns=columns)
        print(self.sumdf[0:2])

    def print_source_summary(self, tdir, name='source_summary.csv'):
        #from tabulate import tabulate
        #content = tabulate(self.sumdf.tolist(), list(self.sumdf.columns),
        #                   tablefmt="plain")
        fname = tdir + name
        #open(fname, "w").write(content)
        self.sumdf.to_csv(fname) 

    def get_so2(self, unit=False):
        sources = self.get_sources(stype='so2_lbs', unit=unit) 
        sources = sources * self.lbs2kg  #convert from lbs to kg.
        return sources

    def get_heat(self, unit=False):
        """
        return dataframe with heat from the CEMS file
        """
        sources = self.get_sources(stype='heat_input (mmbtu)', unit=unit) 
        mult = 1.055e9 / 3600.0  #mmbtu to watts
        mult=0  ##the heat input from the CEMS files is not the correct value to
                ##use.
        sources = sources * mult
        return sources

    def get_stackvalues(self, unit=False):
        """
        return dataframe with string which has stack diamter, temperature
        velocity  obtained from the ptinv file.
        """
        sources = self.get_sources(stype='stack values', unit=unit) 
        #mult = 1.055e9 / 3600.0  #mmbtu to watts
        #mult=0  ##the heat input from the CEMS files is not the correct value to
                ##use.
        #sources = sources * mult
        return sources

    def check_oris(self, series, oris):
        print(oris , 'CHECK COLUMN---------------------------')
        nanum = series.isna().sum()
        series.dropna(inplace=True)
        maxval = np.max(series)
        print('Number of Nans', nanum)
        print('Max value', maxval)
        rval=False
        if maxval > self.ethresh:
           rval = True
        else:
           print( 'DROPPING')
        return rval
 
    def get_sources(self, stype='so2_lbs', unit=False):
        """ 
        Returns a dataframe with rows indexed by date.
        column has info about lat, lon, 
        stackheight in meters, 
        orisp code
        values are
        if stype=='so2_lbs'  so2 emissions
        if stype='

        self.ehash is constructed in find. 
        """
        #print("GET SOURCES")
        getstackvals=False
        if stype=='stack values': 
           stype='so2_lbs'
           getstackvals=True

        if self.cems.df.empty: self.find()
        ut=unit
        sources = self.cems.cemspivot((stype), daterange=[self.d1, self.d2],
                  verbose=False, unitid=ut)
        ehash = self.cems.create_location_dictionary()
        stackhash = cems_mod.get_stack_dict(cems_mod.read_stack_height(), orispl=self.ehash.keys())
        ##This block replaces ORISP code with (lat, lon) tuple as headers
        cnew = []
        sources.drop(self.badoris, inplace=True, axis=1)
        columns=list(sources.columns.values)
        #print('----columns------')
        #print(columns) #EXTRA
        #print(stackhash)
        #print('----columns------')
        stackdf = sources.copy() 
        ################################################################################
        ################################################################################
        ##original column header contains either just ORIS code or 
        ##(ORIS,UNITID)
        ##This block adds additional information into the COLUMN HEADER.
        for ckey in columns:
            if ut: 
               sid = ckey[1]
               oris = ckey[0]
            else: oris = ckey
            if oris in stackhash.keys():
                bid, ht, diam, temp, vel = zip(*stackhash[oris])
                ht = np.array(ht) * 0.3048  #convert to meters!
                diam = np.array(diam) * 0.3048 #convert to meters
                temp = np.array(temp)  
                kelvin = (temp-32)*(5/9.0) + 273.15 #convert F to K
                vel = np.array(vel) * 0.3048 #convert from ft/s to m/s 
                bhash = dict(zip(bid,ht))   #key is boiler id. value is height. 
                dhash = dict(zip(bid,diam)) #key is boiler id. value is diam 
                thash = dict(zip(bid,kelvin)) #key is boiler id. value is temp. 
                vhash = dict(zip(bid,vel))  #key is boiler id. value is velocity 
                try:
                   ##tuple of diameter, temperature, velocity
                   stackval = ("{:.2f}".format(dhash[sid]),  
                               "{:.2f}".format(thash[sid]), 
                               "{:.2f}".format(vhash[sid]))
                except:
                   stackval = ('-99', '-99', '-99') 
            else:
                sid=-99
                ht = -99
            ##puts the maximum stack height associated with that orispl code.
            if ut:
                try:
                    ht = bhash[sid]
                except:
                    print('WARNING in svcems.py get_sources')
                    print('ORIS '+ str(oris) + ' unitid in CEMS data ' + str(sid))
                    print('No match found in ptinv file')
                    print(stackhash[oris])
                    ht = np.max(ht)
                newcolumn = (ehash[oris][0], ehash[oris][1], ht, oris,
                             sid)
            else:
                newcolumn = (ehash[oris][0], ehash[oris][1], np.max(ht), oris,
                             -99)
            cnew.append(newcolumn)
            ##stackdf is a dataframe with tuple of (stack diameter, temperature
            ##and velocity. These are obtained from the ptinv file.
            ##and so each column will have one value. They are input as a string
            ##so can be written in emitimes file.
            stackdf[ckey] = ' '.join(stackval)
        sources.columns=cnew
        stackdf.columns=cnew
        ################################################################################
        ################################################################################
        if getstackvals:  return stackdf
        #print(sources[0:20])
        return sources


    #def create_heatfile(self,edate, schunks=1000, tdir='./', unit=True):

    def create_emitimes(self, edate, schunks=1000, tdir='./', unit=True):
        """
        create emitimes file for CEMS emissions.
        edate is the date to start the file on.
        Currently, 24 hour cycles are hard-wired.
        """
        df = self.get_so2(unit=unit)
        print(df[0:10])
        dfheat = self.get_heat(unit=unit)
        if unit: dfstack = self.get_stackvalues(unit=unit)
        locs=df.columns.values
        done = False
        iii=0
        d1 = edate
        while not done:
            d2 = d1 + datetime.timedelta(hours=schunks-1)
            dftemp = df.loc[d1:d2]
            hdf = dfheat[d1:d2]
            if unit: sdf = dfstack[d1:d2]
            if dftemp.empty: 
               break
            self.emit_subroutine(dftemp, hdf, d1, schunks, tdir, unit=unit)       
            if unit: self.emit_subroutine(dftemp, sdf, d1, schunks, tdir, unit=unit,
                                 bname='STACKFILE')       
            d1 = d2 + datetime.timedelta(hours=1)
            iii+=1
            if iii > 1000: done=True
            if d1 > self.d2: done=True 
       
    #def emit_subroutine(self, df, dfheat):


    def emit_subroutine(self, df, dfheat,edate, schunks, tdir='./', unit=True,
                        bname='EMIT'):
        """
        create emitimes file for CEMS emissions.
        edate is the date to start the file on.
        Currently, 24 hour cycles are hard-wired.
        """
        #df = self.get_so2()
        #dfheat = self.get_heat()
        locs=df.columns.values
        for hdr in locs:
            #print('HEADER', hdr)
            d1 = edate  #date to start emitimes file.
            dftemp = df[hdr]
            dfh = dfheat[hdr]
            
            oris = hdr[3]
            ename = bname + str(oris) 
            if unit:
               sid = hdr[4]
               ename  += '.' + str(sid)
            height = hdr[2] 
            lat = hdr[0]
            lon = hdr[1]
            ##hardwire 1 hr duraton of emissions.
            record_duration='0100'
            area=1
            ##output directory is determined by tdir and starting date.
            ##chkdir=True means date2dir will create the directory if
            ##it does not exist already.
            odir =  date2dir(tdir, edate, dhour=schunks, chkdir=True)
            ename = odir + ename + '.txt'
            efile = emitimes.EmiTimes(filename=ename)
            if 'STACK' in bname:
                hstring = efile.header.replace('HEAT(w)',
                                'DIAMETER(m) TEMP(K) VELOCITY(m/s)')
                efile.modify_header(hstring)
            ##hardwire 24 hour cycle length
            dt = datetime.timedelta(hours=24)
            efile.add_cycle(d1, "0024")
            for date, rate in dftemp.iteritems():
                if date >= edate:
                    heat=dfh[date]
                    check= efile.add_record(date, record_duration, lat, lon, height,
                                     rate, area, heat)
                    if not check: 
                       d1 = d1 + dt
                       efile.add_cycle(d1, "0024")
                       check2= efile.add_record(date, record_duration, lat, lon, height,
                                     rate, area, heat)
                       if not check2: 
                           print('sverify WARNING: record not added to EmiTimes')
                           print(date.strftime("%Y %m %d %H:%M"))
                           print(str(lat), str(lon), str(rate), str(heat))
                           break
            efile.write_new(ename)
  
    def plot(self, save=True, quiet=True, maxfig=10):
        """plot time series of emissions"""
        if self.cems.df.empty: self.find()
        sns.set()
        namehash = self.cems.create_name_dictionary()
        data1 = self.cems.cemspivot(('so2_lbs'), daterange=[self.d1, self.d2],
                verbose=False, unitid=False)
        print(self.ehash)
        print('*****************')
        print(data1.columns)
        print('*****************')
        for loc in data1.keys():
            print(loc)
            fig = plt.figure(self.fignum)
            ax = fig.add_subplot(1,1,1)
            data = data1[loc] * self.lbs2kg
            ax.plot(data, '--b.')   
            plt.ylabel('SO2 mass kg')
            plt.title(str(loc) + ' ' + namehash[loc])
            if save: 
               figname = self.tdir + '/cems.' + str(loc) + '.jpg'
               plt.savefig(figname)
            if self.fignum > maxfig:
               if not quiet:
                  plt.show()
               plt.close('all')
               self.fignum=0 
            print('plotting cems figure ' + str(self.fignum))
            self.fignum+=1

    def map(self, ax):
        """plot location of emission sources"""
        if self.cems.df.empty: self.find()
        plt.sca(ax)
        #fig = plt.figure(self.fignum)
        for loc in self.ehash:
            lat = self.ehash[loc][0]
            lon = self.ehash[loc][1]
            #print('PLOT', str(lat), str(lon))
            #plt.text(lon, lat, (str(loc) + ' ' + str(self.meanhash[loc])), fontsize=12, color='red')
            pstr = str(loc) + ' \n' + str(int(self.meanhash[loc])) + 'kg'
            if self.meanhash[loc] > 1:
                if loc not in self.badoris:
                    ax.text(lon, lat, pstr, fontsize=12, color='red')
                    ax.plot(lon, lat,  'ko')
                else:
                    ax.text(lon, lat, str(loc), fontsize=8, color='k')
                    ax.plot(lon, lat,  'k.')
    #def testsources(self):
    #    if self.sources.empty: self.get_sources()
    #    sgenerator = source_generator(self.sources)
    #    for src in sgenerator:
    #        print(src)

