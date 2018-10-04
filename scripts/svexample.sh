#!/bin/bash
#/n-home/alicec/anaconda3/bin/python sverify.py --obs --cems -d2016:6:1:2016:10:1 -and -o/pub/Scratch/alicec/SO2/run3/
#/n-home/alicec/anaconda3/bin/python sverify.py --obs -d2016:1:1:2016:1:16 -and -o/pub/Scratch/alicec/SO2/run3/
#/n-home/alicec/anaconda3/bin/python sverify.py -ydefaults -d2016:1:1:2016:1:16 -and -o/pub/Scratch/alicec/SO2/run3/ --hdir /n-home/alicec/Ahysplit/trunk/

/n-home/alicec/anaconda3/bin/python sverify.py --cems --obs -d2016:10:1:2016:12:31 -and -o/pub/Scratch/alicec/SO2/run4/  --hdir /n-home/alicec/Ahysplit/trunk/
/n-home/alicec/anaconda3/bin/python sverify.py -ydefaults -d2016:6:1:2016:10:1 -and -o/pub/Scratch/alicec/SO2/run3/  --hdir /n-home/alicec/Ahysplit/trunk/
/n-home/alicec/anaconda3/bin/python sverify.py -yrunlist  -d2016:10:1:2016:12:31 -and -o/pub/Scratch/alicec/SO2/run4/  --hdir /n-home/alicec/Ahysplit/trunk/


#/n-home/alicec/anaconda3/bin/python sverify.py -yrunlist -d2016:6:1:2016:10:1 -and -o/pub/Scratch/alicec/SO2/run3/  --hdir /n-home/alicec/Ahysplit/trunk/





