# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
from os import path, chdir
import datetime
from subprocess import call
#import numpy as np
#import time
#import os

"""
NAME: ashfall_base.py
UID: r100
PRGMMR: Alice Crawford  ORG: ARL  
This code written at the NOAA  Air Resources Laboratory
ABSTRACT: This code manages HYSPLIT runs for Hanford resuspension project.
CTYPE: source code

List of classes and functions in this file:
-------------------------------------------------------------------------------
functions to create directory tree based on date and to get directory from date.
-------------------------------------------------------------------------------
function get_vlist
function date2dir
function dirtree (generator function)

function make_sourceid - creates string from lat lon point. 
-------------------------------------------------------------------------------


"""

##------------------------------------------------------------------------------------##
##------------------------------------------------------------------------------------##
#####get_vlist date2dir and dirtree are functions to create directory tree based on date and
#####to get directory from date.
##------------------------------------------------------------------------------------##
##------------------------------------------------------------------------------------##

def get_vlist(sdate, dhour):
       """This function is called by the dirtree generator to help generate a directory
       tree based on date.
       Input 
          sdate: datetime object 
          dhour: integer specifying how many directories per hour in the tree).
       If dhour = -1 then directory tree only goes down to month.
       output
          
       """
       if dhour < 24:
            list1 = [sdate.year, sdate.month, sdate.day, sdate.hour]
            list2 = ['y', 'm', 'd', 'h']
            list3 = [4,2,2,2] #this tells how many spaces to take up.
            vlist = list(zip(list1, list2, list3))
       elif dhour >= 24:
            list1 = [sdate.year, sdate.month, sdate.day]
            list2 = ['y', 'm', 'd']
            list3 = [4,2,2]
            vlist = list(zip(list1, list2, list3))
       elif dhour == -1:
            list1 = [sdate.year, sdate.month]
            list2 = ['y', 'm']
            list3 = [4,2]
            vlist = list(zip(list1, list2, list3))
       return vlist

def date2dir(topdirpath, sdate, dhour=1, chkdir=False):
    """given a topdirpath(string), run_num (integer), sdate (datetime) 
       and dhour(int) returns directory"""
    finaldir = topdirpath
    if not path.isdir(finaldir) and chkdir:
        print('creating directory: ' , finaldir)
        callstr = 'mkdir -p ' +   finaldir
        call(callstr, shell=True)      
    for val in get_vlist(sdate, dhour):
        finaldir  += val[1] + str(val[0]).zfill(val[2]) + '/'
    if not path.isdir(finaldir) and chkdir:
        callstr = 'mkdir -p ' +   finaldir
        call(callstr, shell=True)      
    return finaldir


def dirtree(topdirpath,  sdate, edate,
            chkdir=True, verbose = True, maxiter=1e6, dhour = 1):
    """A generator function which generates the directories for the HYSPLIT output.
       A generator function (which uses yield instead of return) can be iterated over.
       If chkdir=True then will create day level directory if it does not exist already.
       Directory is topdirpath / y(year) / m(month) / d(day) / h(hour)/
       Starts creating directories at input sdate and  creates new directory for every date spaced
       by hours specified in dhour until reach edate or maxiter.
       The topdirpath should already exist
    """
    dt = datetime.timedelta(seconds = 60*60*dhour)
    done = False
    zzz = 0
    while not done:
        finaldir = topdirpath
        for val in get_vlist(sdate, dhour):
            finaldir  += val[1] + str(val[0]).zfill(val[2]) + '/'
            if not path.isdir(finaldir) and chkdir:
                callstr = 'mkdir -p ' +   finaldir
                call(callstr, shell=True)      
        zzz+=1
        sdate += dt
        if sdate > edate or zzz> maxiter:
           done = True
        yield finaldir    

##------------------------------------------------------------------------------------##
##------------------------------------------------------------------------------------##
###The following functions and classes define the sources used  
## make_sourceid, Source, source_generator 
##source_generator can easily be modified to produce different sources.
##------------------------------------------------------------------------------------##
##------------------------------------------------------------------------------------##


def make_sourceid(lat, lon):
        """Returns string for identifying lat lon point"""
        latstr = str(abs(int(round(lat*100))))
        lonstr = str(abs(int(round(lon*100))))
        return latstr + '_' + lonstr


