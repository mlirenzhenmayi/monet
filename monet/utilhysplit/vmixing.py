#!/n-home/alicec/anaconda/bin/python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import numpy as np
import string
import datetime
import subprocess
from os import path
import pandas as pd
from monet.utilhysplit.hcontrol import HycsControl

"""
PRGMMR: Alice Crawford  ORG: ARL  
PYTHON 2.7
This code written at the NOAA  Air Resources Laboratory
UID: r102
CTYPE: source code
ABSTRACT: manages the xtrct_stn program and outputs.

CLASSES


"""

class VmixingRun:
        
    def __init__(self, fname, cname='CONTROL', cdir='./',  pid=None,
                 kbls=1, kblt=2, cameo=2, tkemin=None, verbose=True):
        self.control = HycsControl(fname=cname, rtype='vmixing')
        self.pid = self.control.replace('CONTROL.','')
        self.kbls = kbls #1 fluxes  #2 wind/temp profile
        self.kblt = kblt #1 BJ #2 KC #3 TKE.
        self.cameo= cameo #0 no #1 yes #2 yes + wdir
        self.tkemin = tkemin 
        self.woption = woption #output extra file
        self.cdir = cdir

    def readcontrol(self):
        self.control.read()

    def writecontrol(self, cname=None, cdir=None):
        if not cdir: cdir = self.cdir
        if cname:
            self.control.rename(cname, working_directory=cdir)
        self.control.write()

    def assign_pid(self, pid):
        self.pid = pid
        self.control.rename('CONTROL.' + str(pid))
        return -1

    def make_runstr(self, hdir):
        rstr = hdir
        if rstr[-1] != '/': rstr.append('/')
        rstr += 'vmixing '
        if self.pid:
            rstr += '-p' + str(self.pid)
            rstr +=  '-s' + str(self.kbls)
            rstr +=  '-t' + str(self.kblt)
            rstr +=  '-a' + str(self.cameo)
            if tkemin: 
               rstr +=  '-m' + str(self.tkemin)
            rstr +=  '-w' + str(self.woption)
        return rstr


class VmixingData:
    """ 
        add_data
        make_dummies (NOT FUNCTIONAL)
        readfile  
    """
    def __init__(self,  century=2000, verbose=True):
        """fname : name of file output by xtrct_stn
           valra : list of values that are in fname
           century : fname lists year by last two digits only. century is needed to process date.
           """
        self.units = None
        self.df = pd.DataFrame()

    def add_data(self, fname,  vdir='./', century=2000, verbose=True):
            df = self.readfile(fname, vdir, century, verbose)   
            if self.df.empty:
               self.df = df
            else:
               self.df = pd.concat([self.df, df], axis=0)
            return self.df

    def make_dummies(self, data_ra=[-999]):
        """instead of running,  write a dummy file like the one vmixing would write.
           Used for testing.
        """    
        #sdate = datetime.datetime()
        #dt = datetime.timedelta(hour=1)
        #iii=1
        #with open(self.fname) as fid:
        #     fid.write(str(iii) + sdate.strftime(" %y %m %d %h"))
        #     iii+=1 
        return -1

    def get_location(self, head1):
        temp1 = head1.split()
        lat = float(temp1[0])
        lon = float(temp1[1])
        met = temp1[2]
        return lat, lon, met

    def parse_header(self, head2, head3):
        temp2 = head2.split()
        temp3 = head3.split()
        cols = ['date']
        units = ['utc']
        cols.extend(temp2[6:])
        if 'Total' in cols and 'Cld' in cols:
            cols.remove('Total')
        units.extend(temp3)
        return cols, units

    def readfile(self,  fname, vdir='./', century=2000, verbose=False):
        """Reads file and returns True if the file exists.
           returns False if file is not found"""
        if path.isfile(vdir + fname):
            data = []
            with open(vdir + fname, "r") as fid:
                 head1 = fid.readline()
                 head2 = fid.readline()
                 head3 = fid.readline()
                 lat, lon, met = self.get_location(head1)
                 cols, units = self.parse_header(head2,head3)
                 for line in fid.readlines():
                     # get the date for the line
                     try:
                        vals = [self.line2date(line, century)]
                     except:
                        return False
                     temp = line.split()
                     vals.extend(temp[6:]) 
                     data.append(vals) 
        df = pd.DataFrame.from_records(data)
        df.columns = cols
        df['latitude'] = lat
        df['longitude'] = lon
        df['met'] = met
        self.units = zip(cols, units)
        return df

    def line2date(self, line, century):
        """get date from a line in the xtrct_stn output and return datetime object"""
        temp = line.strip().split()
        year = int(temp[1]) + century
        month = int(temp[2])
        day =   int(temp[3])
        hour =  int(temp[4])
        minute = int(temp[5])
        vdate = datetime.datetime(year, month, day , hour, minute)
        return vdate

class Script:

    def mksh(self, coord, xname, mdir, metname, interpolate=False,  multra=[], runsh=False, verbose=False,
             hysplitdir = '-99'):
        """writes shell script which will run xtrct_stn
           coord is lat lon in string format e.g. '34 -119'
           mdir is the directory of the meteorological file.
           metname is the name of the meteorological file."""
       
        valra = list(zip(*self.valra))[0]
        levra = list(zip(*self.valra))[1]
        if interpolate:
           interp = '1 \n'
        else:
           interp = '0 \n'
        if hysplitdir == '-99':
           hysplitdir = ''
        elif hysplitdir[-1] != '/':
           hysplitdir += '/'
        with open(xname, 'w') as fid:
             if verbose: print('writing to ', xname)
             fid.write(hysplitdir + 'xtrct_stn -i << EOF \n')
             fid.write(mdir + '\n')
             fid.write(metname + '\n')
             fid.write(str(len(valra)) + '\n')
             if len(levra) != len(valra):
                levra = ['01'] * len(valra)
             if multra==[]:
                ##this block will pick the amount to multiply the value by. 
                for zval in valra:
                    if zval in  ['U10M', 'V10M', 'T02M', 'PRSS','PBLH','SHGT','PRECIP','LHTF','DSWF','LHTF']:
                        multra.append('1')
                    elif zval in ['USTR']:  
                        multra.append('100')
                    elif zval in ['SPHU']:  
                        multra.append('1000')
                    elif zval in ['TPP1', 'TPPT', 'TPP6', 'DIFR']:
                        ##this will put precip in um
                        multra.append('1000000')
                    else:
                        multra.append('1')
                    #print zval, multra
             outra = list(zip(valra, levra, multra))
             for val in outra:
                 fid.write(val[0].strip() + ' ' + val[1].strip() + ' ' + val[2].strip() + '\n')
             fid.write(coord + '\n')
             fid.write(interp)
             fid.write(self.fname + '\n')
             fid.write('1\n')          #record number to start with
             fid.write('99999\n')      #record number to end with
             fid.write('EOF')
        if runsh:
           callstr = "chmod u+x " + './' + xname
           if verbose: print('CALLING', callstr)
           subprocess.call(callstr, shell=True) 

           callstr = './' + xname
           if verbose: print(callstr)
           subprocess.call(callstr, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return callstr            
 

