#!/opt/Tools/anaconda3/bin/python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
#from math import *
from optparse import OptionParser
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import datetime
#import pandas as pd
#from pylab import matrix
#import io

#TO DO Fix year

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


    def __init__(self, fname, year=2018):
        self.fname=fname
        self.hdist = []
        self.read()
        self.year = year

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

        self.emrise = []
        self.dayhour= []
        self.date = []
        self.edate = []
        self.ehour = []

        self.mhash={}
        self.mhash['hour'] = []
        self.mhash['pnum'] = []
        self.mhash['mass'] = []

        thash={}   #key is hour number, value is number of times the hour is printed out
        phash={}   #key is hour number, value is large number of particles in that hour

        iii=0
        hhh=0
        eee=0
        get_h=False
        hlist=[]
        hour = 2
        emrise=(-1,0,0) 
        with open(self.fname,'r', errors="ignore") as fid:
             print('opening file' , self.fname)
             for temp in fid:
                 #print(get_h, temp)
                 #if 'str' in temp:
                 #    break
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
                 elif ('NOTICE' in temp) and ('emrise' in temp):
                    temp2 = temp.split()
                    #self.emrise.append((hour-1, float(temp2[4]), float(temp2[5])))
                    emrise=(hour-1, float(temp2[4]), float(temp2[5]))
                    #self.edate.append(date)
                    #self.ehour.append(hour)
                    eee+=1
                 elif ('NOTICE' in temp) and ('output' in temp):
                    temp2 = temp.split()
                    hour = int(temp2[7])
                    self.dayhour.append(int(temp2[7]))
                    self.date.append(datetime.datetime(2018, int(temp2[5]),
                                     int(temp2[6]), int(temp2[7])))
                    date = datetime.datetime(2018, int(temp2[5]),
                                     int(temp2[6]), int(temp2[7]))
                    hhh+=1
                    self.emrise.append(emrise)
                    self.edate.append(date)
                    self.ehour.append(hour)
                 elif ('Height' in temp) and ('Mass' in temp):
                    get_h=True 
                    if hlist: self.hdist.append(hlist)    
                    hlist = []
                 if get_h: 
                    hlist.append(temp) 
                 iii+=1
                      
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

    def plot_emrise(self):
        sep = list(zip(*self.emrise))
        print(sep)
        fig = plt.figure(1)
        ax=fig.add_subplot(1,1,1)
        ax.set_xlabel('Simulation Hour')
        ax.set_ylabel('Height')
        ax.plot(sep[0], sep[2], '-b.', label='rise')
        ax.plot(sep[0], sep[1], '-g.', label='kmixd')
        handles, labels = ax.get_legend_handles_labels()
        plt.legend
        plt.show()  
        






