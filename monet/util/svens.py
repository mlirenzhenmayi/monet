# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import numpy as np
import datetime
import time
import os
from os import path, chdir
from subprocess import call
import pandas as pd
import sys
# from arlhysplit.process import is_process_running
# from arlhysplit.process import ProcessList
from monet.util import svhy
from monet.util.svhy import create_runlist
from monet.util.svhy import RunScript
from monet.util.svhy import DatemScript


# The ensembles are generally handled by creating their own subdirectory named
# by the ensemble suffix.
# memberlist is a function which creates list of member suffixes (specifically
# for sref so far.
# dirnamelist then creates and returns the list of subdirectories.
# the dirnamelist can then be used 



# individual classes  mainly differ in how they create their member list.
# TO DO switch over to using these classes so can create different ensemblees.
# base class.
class SVEnsemble:

    def __init__(self):
        self.memberlist = self.create_member_list 

    def create_member_list(self, inputlist):
        self.memberlist = inputlist

    def add_member(self, member):
        self.memberlist.append(member)
        # remove duplicates.
        self.memberlist = list(set(self.memberlist))
              
class SV_SREF(SVEnsemble):

    def create_member_list(self):
        memberlist = []
        for zzz in ['nmb','arw']:
            for iii in range(1,7):
                memberlist.append(zzz + '.n' + str(iii))
                memberlist.append(zzz + '.p' + str(iii))
            memberlist.append(zzz + '.ctl')
        return memberlist

    


def create_ens_dfile(obs, d1, source_chunks, run_duration, tdir):
    memberlist = create_member_list_sref()
    dirnamelist = make_ens_dirs(tdir, memberlist)
    for edir in dirnamelist:
        obs.obs2datem(d1, ochunks=(source_chunks, run_duration), tdir=edir) 


def create_ensemble_datem_scripts(options, d1, d2, source_chunks):
    memberlist = create_member_list_sref()
    dirnamelist = make_ens_dirs(options.tdir, memberlist)
    iii=0
    for edir in dirnamelist:
        print('TDIR', options.tdir)
        tdir = path.join(options.tdir, edir)
        runlist = create_runlist(tdir, options.hdir, d1, d2, source_chunks)
        rs = DatemScript("p1datem_" + options.tag + memberlist[iii] + '.sh', 
                       runlist,
                       tdir,
                       options.cunits, 
                       poll=1)
        iii+=1
    return rs



def create_ensemble_scripts(options, d1, d2, source_chunks, check):
    memberlist = create_member_list_sref()
    dirnamelist = make_ens_dirs(options.tdir, memberlist)
    iii=0
    for edir in dirnamelist:
        print('TDIR', options.tdir)
        tdir = path.join(options.tdir, edir)
        runlist = create_runlist(tdir, options.hdir, d1, d2, source_chunks)
        rs = RunScript(options.tag + memberlist[iii] + '.sh', runlist,
                       tdir,
                       check)
        iii+=1
    return rs


def ensemble_defaults(tdir):
    # simply copy the SETUP.0 and CONTROL.0 in the top directory
    # to the ensemble directories.
    memberlist = create_member_list_sref()
    dirnamelist = make_ens_dirs(tdir, memberlist)
    for edir in dirnamelist:
        if not os.path.isfile(os.path.join(edir, 'CONTROL.0')):
            callstr = 'cp ' + os.path.join(tdir, 'CONTROL.0')
            callstr +=  ' ' + edir + '/'
            call(callstr, shell=True)      
        if not os.path.isfile(os.path.join(edir, 'SETUP.0')):
            callstr = 'cp ' + os.path.join(tdir, 'SETUP.0')
            callstr +=  ' ' + edir + '/'
            call(callstr, shell=True)      


def ensemble_emitimes(options, metfmt, ef, source_chunks):
    # ef is an SEmissions object.
    memberlist = create_member_list_sref()
    iii = 0
    fhour=""
    # create directories for ensemble members.
    tdirpath = options.tdir
    dirnamelist = make_ens_dirs(tdirpath, memberlist)
    for sref in generate_sref_ens(metfmt, fhour, memberlist):
        tdir = tdirpath + dirnamelist[iii]
        # create emittimes files
        ef.create_emitimes(
            ef.d1,
            schunks=source_chunks,
            tdir=tdir,
            unit=options.byunit,
            heat=options.heat,
            emit_area=options.emit_area,
        )
        iii+=1 


def create_nei_ensemble_controls(tdirpath, hdirpath, neidf, sdate, edate, timechunks, metfmt, units="ppb",
                    tcm=False, orislist=None):

    fhour=''               #pick the forecast hour to use
    memberlist = create_member_list_sref()
    iii = 0
    # create directories for ensemble members.
    dirnamelist = make_ens_dirs(tdirpath, memberlist)
    for sref in generate_sref_ens(metfmt, fhour, memberlist):
        tdir = tdirpath + dirnamelist[iii]
        
        runlist = svhy.create_controls(tdir, options.hdir, d1, d2, source_chunks,
                                  sref, options.cunits, tcm, orislist) 
        iii+=1 

def create_ensemble_controls(tdirpath, hdir, d1, d2, source_chunks, metfmt, units="ppb",
                    tcm=False, orislist=None):

    fhour=''               #pick the forecast hour to use
    memberlist = create_member_list_sref()
    iii = 0
    # create directories for ensemble members.
    dirnamelist = make_ens_dirs(tdirpath, memberlist)
    for sref in generate_sref_ens(metfmt, fhour, memberlist):
        tdir = tdirpath + dirnamelist[iii]
        #print('ENSEMBLE', tdir)
        runlist = svhy.create_controls(tdir, hdir, d1, d2, source_chunks,
                                  sref, units, tcm, orislist, moffset=24)
        iii+=1 

def make_ens_dirs(tdirpath, memberlist):
    chkdir=True
    dirnamelist = []
    for member in memberlist:
        dname = member.replace('.', '_')
        dirnamelist.append(dname)
        finaldir = os.path.join(tdirpath, dname)
        if not path.isdir(finaldir) and chkdir:
            print('creating directory: ' , finaldir)
            callstr = 'mkdir -p ' +   finaldir
            call(callstr, shell=True)      
        #make directory for the ensemble member.
    return dirnamelist     

def generate_sref_ens(metfmt, fhour, memberlist):
    for member in memberlist:
        rval = metfmt + fhour + member    
        yield rval 


def create_member_list_sref():
    memberlist = []
    for zzz in ['nmb','arw']:
        for iii in range(1,7):
            memberlist.append(zzz + '.n' + str(iii))
            memberlist.append(zzz + '.p' + str(iii))
        memberlist.append(zzz + '.ctl')
    return memberlist


def create_member_list_srefA():
    memberlist = []
    for zzz in ['nmb','arw']:
        for iii in range(1,7):
            memberlist.append(zzz + '_n' + str(iii))
            memberlist.append(zzz + '_p' + str(iii))
        memberlist.append(zzz + '_ctl')
    return memberlist

