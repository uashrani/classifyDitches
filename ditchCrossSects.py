# -*- coding: utf-8 -*-
"""
Created on Fri Apr 25 13:50:10 2025

@author: Uma
"""

#%% Prerequisite modules, data, and folders

import pandas as pd
import numpy as np
import grass.script as gs
import grass.grassdb.data as gdb

tmpFiles = 'tempFiles/'
hucPrefix = 'testDEM2'
ditchPrefix = 'BRR'

demNull = hucPrefix + '_wNulls' 

vecLines1='drainage_centerlines'
#%% Layers/files that will be created automatically

vecLines2=ditchPrefix + '_lines_nameless'
vecLines3=ditchPrefix + '_lines_renamed'

alongFile=tmpFiles + ditchPrefix + '_alongPts_unbroken.txt'
profilePts=ditchPrefix + '_profilePts'  # GRASS layer

lineDefFile= tmpFiles + hucPrefix + '_shiftedLineDefs.txt'
tmpFile = tmpFiles + 'tmpProfile.txt'

# Shifted lines, and points that line along the shifted line
newLine = hucPrefix + '_shiftedDitches_unbroken'
newPts = hucPrefix + '_shiftedVertices_unbroken'

# Elevation profile from the shifted points
newElevFile = tmpFiles + hucPrefix + '_elevProfile_shiftedDitches.txt'

#%% Actual code

### Rename category values so features don't share a cat number
if not gdb.map_exists(profilePts, 'vector'):
    gs.run_command('v.category', input_=vecLines1, output=vecLines2, option='del', cat=-1, overwrite=True)
    gs.run_command('v.category', input_=vecLines2, output=vecLines3, option='add', overwrite=True)
    
    # Disconnect from old attribute table and create new one
    gs.run_command('db.droptable', flags='f', table=vecLines3)
    gs.run_command('v.db.connect', flags='d', map_=vecLines3, layer=1)
    gs.run_command('v.db.addtable', map_=vecLines3)
    
    # Get points along line, and their xy coordinates
    gs.run_command('v.to.points', input_=vecLines3, output=profilePts, dmax=1)
    gs.run_command('v.to.db', map_=profilePts, layer=2, option='coor', columns=['x', 'y'])
    gs.run_command('v.db.select', map_=profilePts, layer=2, format_='csv', file=alongFile, overwrite=True)

### Read the points
df = pd.read_csv(alongFile) 

# Later will be region of the HUC, get from the bounding box file
#n, s, e, w = 5217318, 5212652, 274769, 269803   # test region 1
n, s, e, w = 5202318, 5191400, 220687, 212912   # test region 2

# Get all points whose coordinates are in the DEM region
dfInRegion = df[((df['y']>=s)&(df['y']<=n))&((df['x']>=w)&(df['x']<=e))]

# Temporary: also filter out the ones that are <1m 
dfInRegion = dfInRegion[dfInRegion['along']>=1]

lcats=sorted(set(dfInRegion['lcat']))

# Create empty vector map for new lines, and empty file to add coords
gs.run_command('v.edit', map_=newLine, type_='line', tool='create', overwrite=True)
fLine=open(lineDefFile, 'a')

for lcat in lcats:
    profilePts = df[df['lcat']==lcat]
    x, y = profilePts['x'], profilePts['y']
    
    tangentSlopes=np.diff(y) / np.diff(x)  
    normalSlopes = - 1 / tangentSlopes
    
    # we just calculated the normal line's y/x change, aka the tangent
    # which angle is associated with this tangent?
    angles=np.arctan(normalSlopes)
    sines=np.sin(angles)
    cosines=np.cos(angles)
    
    # How far to take the profile on each side, in m
    halfDist = 7.5    # slightly smaller than the null width
    
    # Get the midpoints of all 1-m line segments
    x_m = (x[1:].reset_index(drop=True) +x[:-1].reset_index(drop=True)) / 2
    y_m = (y[1:].reset_index(drop=True) +y[:-1].reset_index(drop=True)) / 2
    
    trX1 = x_m - halfDist*cosines
    trX2 = x_m + halfDist*cosines
    trY1 = y_m - halfDist*sines
    trY2 = y_m + halfDist*sines
    
    ncoords = len(x_m)
    coordsToAdd = list(range(0,ncoords,5))+[ncoords-1]  # go every 5m but include end
    fLine.write('L  ' + str(len(coordsToAdd)) + ' 1\n')
    
    # Get profile across these endpoints
    for i in coordsToAdd:
        
        x1,y1,x2,y2=trX1.iloc[i],trY1.iloc[i],trX2.iloc[i],trY2.iloc[i]
        cos,sin=cosines[i], sines[i]
        
        gs.run_command('r.profile', input_=demNull, output=tmpFile, \
                        coordinates=[x1,y1,x2,y2], overwrite=True)
    
        profile=pd.read_csv(tmpFile, sep='\s+', names=['across', 'elev'], na_values='*')
        crossElev=profile['elev']
        minElev=np.min(crossElev)
        
        if np.isnan(minElev):
            newX, newY = x_m.iloc[i], y_m.iloc[i]
        else:
            minAcross = profile[crossElev==minElev].iloc[0]
            across=minAcross['across']
            
            newX, newY = x1 + across*cos, y1 + across*sin
        
        fLine.write(' ' + str(newX) + ' ' + str(newY) + '\n')
        
    fLine.write(' 1 ' + str(lcat))
    if lcat!=lcats[-1]:
        fLine.write('\n')
    
fLine.close()
        
gs.run_command('v.edit', flags='n', map_=newLine, tool='add', input_=lineDefFile)

# Now compute the elevations at the newly-created points
#gs.run_command('v.to.points', input_=newLine, use='vertex', output=newPts)
gs.run_command('v.to.points', input_=newLine, dmax=1, output=newPts)
gs.run_command('v.what.rast', map_=newPts, raster=demNull, column='elev', layer=2)
gs.run_command('v.db.select', map_=newPts, layer=2, format_='csv', file=newElevFile)
        
    
    