# -*- coding: utf-8 -*-
"""
Created on Fri Aug  1 15:00:51 2025

@author: swimm
"""

import grass.script as gs
import grass.grassdb.data as gdb
import pandas as pd
import os

import transect
import interpSurface

tmpFiles = 'tempFiles/'
hucPrefix = 'testDEM1'
ditchPrefix='BRR'

# This is just to tell us what lcats are in the region
newElevFile = tmpFiles + hucPrefix + '_elevProfile_shiftedDitches.txt'

dem=hucPrefix + '_v2_interpDEM'

toFill = [266,267]
layerPrefix = hucPrefix + '_combo1'

#%% To be created
dsTransects = hucPrefix + '_plugLoc'
transectFile = tmpFiles + dsTransects + '.txt'

#%% 
### Create transects near downstream ends of ditches for infilling location
if not gdb.map_exists(dsTransects, 'vector'):
    if os.path.exists(transectFile):
        os.remove(transectFile)
    f=open(transectFile, 'a')

    profilePts = pd.read_csv(newElevFile)
    lcats=sorted(set(profilePts['lcat']))
    
    for lcat in lcats:
        x1,x2,y1,y2,f1,f2,f3,f4 = transect.transect(profilePts, lcat, 15)
        fillLoc = 50
        
        if len(x1) > fillLoc:
            x1,x2,y1,y2=x1.iloc[-fillLoc],x2.iloc[-fillLoc],\
                y1.iloc[-fillLoc],y2.iloc[-fillLoc]
                
            f.write('L  2 1\n')
            f.write(' ' + str(x1) + ' ' + str(y1) + '\n')
            f.write(' ' + str(x2) + ' ' + str(y2) + '\n')
            f.write(' 1 ' + str(lcat))
            if lcat != lcats[-1]:
                f.write('\n')
            
    f.close()
    gs.run_command('v.edit', map_=dsTransects, type_='line', tool='create', overwrite=True)
    gs.run_command('v.edit', flags='n', map_=dsTransects, tool='add', \
               input_=transectFile)
        
pluggedDEM, filler = interpSurface.interpSurface(tmpFiles, layerPrefix, \
                                                 dsTransects, 10, dem, cats=toFill)
    

    

        

        
