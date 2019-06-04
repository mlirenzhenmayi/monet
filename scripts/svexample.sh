#!/bin/bash

#Date range
year=2016
m1=1
m2=2
dr=$year:$m1:01:$year:$m2:1

#OUTPUT DIRECTORYs
outdir=/pub/ECMWF/SO2/clusters/run1api/ 
hdir=/n-home/alicec/hysplit/trunk/
sdir=/n-home/alicec/MONET/scripts/
pycall=/hysplit-users/alicec/anaconda3/bin/python
pycall=python

# BOUNDS (Lower left lat, lon,  Upper Right lat, lon)
bounds=35.5:-80.5:36.5:-79.5

##--cems option finds emissions data
#        writes emittimes files in subdirectories.
#  default is to write emissions with different MODC flags to different species.
#  using -s will turn this option off and write all emissions to same species regardless of MODC.

##--obs option finds observation data.
#        writes datem.txt files in subdirectories.
#        if cems has been run already, writes a geometry.csv file
#        which gives info on distance and direction to measurement sites.
##--def option writes base CONTROL and SETUP.CFG files in outdir.
#       can edit these files as needed. 
##--run option writes CONTROL and SETUP files in subdirectories.
#       uses CONTROL.0 and SETUP.0 in top level directory.
#       puts in correct met data.
#       reads emittimes files to write correct number of locations and species.
      

#$pycall ${sdir}sverify.py --cems --obs -b$bounds -d$dr  -o$outdir -y$hdir --unit PPB
#$pycall ${sdir}sverify.py -q 2 --obs -b$bounds -d$dr - -o$outdir -y$hdir --unit PPB
#$pycall ${sdir}sverify.py  -q 2 --cems  -b$bounds -d$dr  -o$outdir -y$hdir --unit PPB
#$pycall ${sdir}sverify.py -q 2 --def -d$dr -a$state -b$bounds -o$outdir -y$hdir --unit PPB
#$pycall ${sdir}sverify.py --run ${year}run.sh -d$dr -a$state -o$outdir -y$hdir --unit PPB
##run results after running the script created by test.sh

#dr=2016:1:01:2016:11:30
#$pycall ${sdir}sverify.py --results -d$dr -o$outdir -y$hdir







