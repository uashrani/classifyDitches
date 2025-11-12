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

tmpFiles = 'tempFiles/BlueEarth2/'
hucPrefix = 'HUC_0702000709'
ditchPrefix='BluEr'

outDir = '/media/uashrani/topobathy-ditch/HUC_0702000709/'

# This is just to tell us what lcats are in the region
newElevFile = tmpFiles + hucPrefix + '_elevProfile_flippedDitches.txt'

dem=hucPrefix + '_v2_interpDEM'

# exclude 15, 100, 104
#fillCombos = [[15], [32], [38], [40], [41], [42], [43], [44], [46], [47], [48], [67], [68], [77], [86], \
#[90], [92], [93], [94], [96], [100], [103], [104], [107], [108], [113], [119], [132], [134], [143]]
fillCombos = [[107], [108], [113], [119], [132], [134], [143]]
#layerPrefix = hucPrefix + '_fill102'

fillLoc = 50        # downstream location
fillWidth = 12.5      # half the width of the plug
fillLen = 10        # half the length of the plug

lineSep='\n'

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
        x1,x2,y1,y2,f1,f2,f3,f4,f5 = transect.transect(profilePts, lcat, fillWidth)
        
        if len(x1) > fillLoc+fillLen:
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


for toFill in fillCombos:
    layerPrefix = hucPrefix + '_fill' + str(toFill[0])
    gs.run_command('g.region', raster=dem)
        
    pluggedDEM, filler = interpSurface.interpSurface(tmpFiles, layerPrefix, lineSep, \
                                                    dsTransects, fillLen, dem, cats=toFill)

    intName = pluggedDEM + '_int'
    # Pseudocode: intName = round((DEM - 100) * 100)
    expression = intName + ' = ' + 'round((' + pluggedDEM + '-100)*100)'
    gs.run_command('r.mapcalc', expression=expression, overwrite=True)

    # Grow the region by 1, which creates a buffer of NaNs around the edge
    gs.run_command('g.region', grow=1)

    # Output the new lake-subtracted DEM for that region
    gs.run_command('r.out.gdal', flags='f', input=intName, output=outDir + layerPrefix+'.tif', \
                    format='GTiff', createopt="COMPRESS=LZW,BIGTIFF=YES", type='UInt16', nodata=0)
    

    

        

        
