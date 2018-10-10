#!/bin/bash

#dr=2016:10:1:2016:12:31
#dr=2016:11:1:2016:11:15
#DATERANGE
dr=2016:6:1:2016:7:21
#OUTPUT DIRECTORY
outdir=/pub/Scratch/alicec/SO2/run4/ 
hdir=/n-home/alicec/Ahysplit/trunk/
#pycall=/n-home/alicec/anaconda3/bin/python
pycall=python
state=nd
bounds=42.7:-107:49:-94

##--cems option finds emissions data.
##--obs option finds observation data
##--def option writes base CONTROL and SETUP.CFG files in outdir.
##--run option writes CONTROL and SETUP files in subdirectories 

$pycall sverify.py --cems --obs -b$bounds -d$dr -a$state -o$outdir -y$hdir
$pycall sverify.py --def -d$dr -a$state -o$outdir -y$hdir
$pycall sverify.py --run test.sh -d$dr -a$state -o$outdir -y$hdir
##run results after running the script created by test.sh
#$pycall sverify.py --results -d$dr -a$state -o$outdir -y$hdir







