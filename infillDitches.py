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
hucPrefix = 'testDEM3'
ditchPrefix='BRR'

# This is just to tell us what lcats are in the region
newElevFile = tmpFiles + hucPrefix + '_elevProfile_shiftedDitches.txt'

dem=hucPrefix + '_v2_burned'

toFill = [247,298]
layerPrefix = hucPrefix + '_combo4'

#%% To be created
dsTransects = hucPrefix + '_perpendicular'
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
        
interpSurface.interpSurface(tmpFiles, layerPrefix, dsTransects, 10, dem, cats=toFill)

        
    # # Create a new layer that buffers the transects only for the selected ditches
    # gs.run_command('v.buffer', flags='c', input_=dsTransects, type_='line', \
    #                 output=dsBuffers, distance=10, cats=toFill, layer=1)
    # gs.run_command('v.type', input_=dsBuffers, output=dsBoundaries, \
    #                from_type='boundary', to_type='line')
        
    # gs.run_command('v.to.points', input_=dsBoundaries, output=polyCorners, use='vertex', \
    #                layer=-1)
    # gs.run_command('v.to.db', map_=polyCorners, option='coor', columns=['x', 'y'], layer=2)
    # gs.run_command('v.db.select', map_=polyCorners, layer=2, format_='csv', \
    #                file=cornerFile, overwrite=True)

    # cornerDf = pd.read_csv(cornerFile)
    # cornerDf = cornerDf[cornerDf['along']!=0]
    
    # for i in range(len(cornerDf)):
    #     x,y=cornerDf['x'].iloc[i],cornerDf['y'].iloc[i]
    #     gs.run_command('v.edit', map_=dsBoundaries, type_='line', tool='break', \
    #                    coords=[x,y])
            
    # # Segments running parallel to ditch are 20m, perpendicular are 30m
    # # gs.run_command('v.edit', map_=dsBoundaries, tool='delete', \
    # #                type_='line', query='length', threshold=[-1,0,29])
    # gs.run_command('v.edit', map_=dsBoundaries, tool='delete', \
    #                 type_='line', query='length', threshold=[-1,0,-0.1])
    # gs.run_command('v.category', input_=dsBoundaries, output_=dsBdryCats, \
    #                type_='line', option='add')
    # gs.run_command('v.db.addtable', map_=dsBdryCats)
    # gs.run_command('v.db.addcolumn', map_=dsBdryCats, columns='to_cat int')
    # gs.run_command('v.distance', from_=dsBdryCats, to=dsTransects, dmax=0.01, \
    #                upload='cat', column='to_cat')
        
        
    # gs.run_command('v.to.points', input_=dsBoundaries, type_='line', \
    #                 output=bankPts, dmax=1, layer=-1)
        
    # gs.run_command('v.what.rast', map_=bankPts, raster=dem, column='elev', \
    #                 layer=2)
    # gs.run_command('r.mask', vector=dsBuffers)
    # gs.run_command('v.surf.idw', input_=bankPts, layer=2, column='elev', \
    #                 output=pluggedSurf)
        
    # # Kind of dangerous maybe but deleting r.mask doesn't work
    # path=gs.read_command('g.gisenv', get=['GISDBASE','LOCATION_NAME','MAPSET'],\
    #                       sep='/').replace('\\', '/')
    # os.remove(path.strip()+'/cell_misc/MASK')
    
    # gs.run_command('r.mask', flags='r')
    # gs.run_command('r.patch', input_=[pluggedSurf,dem], output=pluggedDEM)
    

    

        

        
