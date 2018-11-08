#!/opt/Tools/anaconda3/bin/python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
#from math import *
from optparse import OptionParser
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
#import datetime
#import pandas as pd
#from pylab import matrix
#import io


"""class for Hysplit MESSAGE file.
optionparser input which will plot time steps"""

def color_generator(start):
    done=False 
    clr = ['m','r','g','c','b','k']
    clr.append(sns.xkcd_rgb['royal blue']) 
    while not done:
        start+=1
        if start > len(clr)-1: start=0
        yield clr[start]
     
      


class HysplitMessageFile(object):
    """Class to read the Hysplit Message File.
    Currently looks at how time step evolves over the run"""


    def __init__(self, fname):
        self.fname=fname
        self.hdist = []
        self.read()

    def process_heights(self, oname='heights.jpg'):
        print('Processing height data')
        clr = color_generator(0)
        sns.set()
        sns.set_palette("cubehelix",8)
        iiit=0
        for hdist in self.hdist:
            height = []
            pmass = []
            for line in hdist:
                temp = line.split()
                try:
                    height.append(float(temp[1]))
                    pmass.append(float(temp[2]))
                except:
                    print(temp)
            plt.plot(pmass, height, label=str(iiit))
            ax = plt.gca()
            plt.xlabel('Percent Mass')
            plt.ylabel('Height')
            handles, labels = ax.get_legend_handles_labels()
            iiit +=1
        ax.legend(handles, labels, loc=1)     
        plt.savefig(oname)
        plt.show()             


    def read(self):
        self.flags = []
        self.warning = []
        phour = 0
        nnn = 0

        self.mhash={}
        self.mhash['hour'] = []
        self.mhash['pnum'] = []
        self.mhash['mass'] = []

        thash={}   #key is hour number, value is number of times the hour is printed out
        phash={}   #key is hour number, value is large number of particles in that hour

        iii=0
        get_h=False
        hlist=[]
        with open(self.fname,'r') as fid:
             print('opening file' , self.fname)
             for temp in fid:
                 #print(get_h, temp)
                 if 'str' in temp:
                     break
                 if 'WARNING' in temp:
                    self.warning.append(temp)
                 elif ('NOTICE' in temp) and ('main' in temp):
                    get_h=False
                    if 'number meteo grids and times' in temp:
                        meteogrids = temp
                    elif 'flags' in temp:
                        self.flags.append(temp)
                    elif 'time step' in temp:
                        init_time_step = temp
                    else:
                        temp2 = temp.split()
                        #print temp2
                        hour = int(temp2[2])
                        self.mhash['hour'].append(hour)
                        self.mhash['pnum'].append(int(temp2[4]))
                        self.mhash['mass'].append(float(temp2[5]))
                        if hour != phour:
                           nnn = 1
                        else:
                           nnn +=1
                        phash[hour] = int(temp2[4]) 
                        #print hour , int(temp2[4])
                        thash[hour] = nnn
                        phour = hour
                 elif ('Height' in temp) and ('Mass' in temp):
                    print(temp)
                    get_h=True 
                    if hlist: self.hdist.append(hlist)    
                    hlist = []
                 if get_h: 
                    print(temp)
                    hlist.append(temp) 
                      
        self.timestep = []
        self.pnumber = []
        ##calculate time step for each simulation hour.
        for key in thash:
            tstep = 60.0 / thash[key]
            self.timestep.append((key, tstep))
            self.pnumber.append(np.log10(phash[key]))
            #print key, phash[key] , np.log10(phash[key])


    def print_warnings(self):
        """prints all lines with WARNING in them"""
        for warn in self.warning:
            print(warn)

    def plot_time_step(self):
        """plots the time step as a function of simulation hour"""
        timestep = self.timestep
        fig = plt.figure(1)
        ax = plt.subplot(1,1,1) 
        ax.plot(zip(*timestep)[0],zip(*timestep)[1],  '-b.')
        ax.set_xlabel('Simulation Hour')
        ax.set_ylabel('Average time step in hour (minutes)')
        plt.show()                    




parser = OptionParser()

parser.add_option("-f", type='string', dest='fname', default='MESSAGE',
                 help="Name of HYSPLIT output MESSAGE file. (MESSAGE)")

(options, args) = parser.parse_args()

mfile = HysplitMessageFile(options.fname)     
#mfile.print_warnings()   
#mfile.plot_time_step()
suffix = options.fname.split('.')
try: 
   hname = 'heights.' + suffix[1] + '.jpg'
except:
   hname = 'heights.jpg'
mfile.process_heights(oname=hname)
