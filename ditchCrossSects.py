# -*- coding: utf-8 -*-
"""
Created on Fri Apr 25 13:50:10 2025

@author: Uma
"""

#%% Prerequisite modules, data, and folders

import grass.script as gs
import pandas as pd
import numpy as np

tmpFiles = 'tempFiles/'
hucPrefix = 'testDEM2'
ditchPrefix = 'BRR'

dem = 'ambigDEM2'
#demNull = hucPrefix + '_wNulls' 

alongFile=tmpFiles + ditchPrefix + '_alongPts.txt'  

culvertDefFile = tmpFiles + ditchPrefix + '_culvertPtDefs.txt'

# Later will be region of the HUC, get from the bounding box file or g.region
#n, s, e, w = 5217318, 5212652, 274769, 269803   # test region 1
n, s, e, w = 5202318, 5191400, 220687, 212912   # test region 2

# How far to take the profile on each side, in m
halfDist = 7.5    # slightly smaller than the null width
#%% Layers/files that will be created automatically

lineDefFile= tmpFiles + hucPrefix + '_shiftedLineDefs.txt'
tmpFile = tmpFiles + 'tmpProfile.txt'

# Shifted lines, and points that line along the shifted line
newLine = hucPrefix + '_shiftedDitches'
newPts = hucPrefix + '_shiftedVertices'

# Elevation profile from the shifted points
newElevFile = tmpFiles + hucPrefix + '_elevProfile_shiftedDitches.txt'

#%% Actual code

gs.run_command('g.region', raster=dem)

### Read the points
df = pd.read_csv(alongFile) 

# Get all points whose coordinates are in the DEM region
dfInRegion = df[((df['y']>=s)&(df['y']<=n))&((df['x']>=w)&(df['x']<=e))]

# Temporary: also filter out the ones that are <1m 
dfInRegion = dfInRegion[dfInRegion['along']>=1]
lcats=sorted(set(dfInRegion['lcat']))

# Open the culvert definition file so we can check which points are near culvert
culvertPts = pd.read_csv(culvertDefFile, names=['x', 'y', 'buffer'])

# Create empty vector map for new lines, and empty file to add coords
newPtsDf = pd.DataFrame({'lcat': [], 'x': [], 'y': []})
gs.run_command('v.edit', map_=newLine, type_='line', tool='create', overwrite=True)

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
    
    # Get the midpoints of all 1-m line segments
    x_m = (x[1:].reset_index(drop=True) +x[:-1].reset_index(drop=True)) / 2
    y_m = (y[1:].reset_index(drop=True) +y[:-1].reset_index(drop=True)) / 2
    
    trX1 = x_m - halfDist*cosines
    trX2 = x_m + halfDist*cosines
    trY1 = y_m - halfDist*sines
    trY2 = y_m + halfDist*sines
    
    ncoords = len(x_m)
    coordsToAdd = list(range(0,ncoords,10))+[ncoords-1]  # go every 10m but include end
    
    # Get profile across these endpoints
    for i in coordsToAdd:
        
        x1,y1,x2,y2=trX1.iloc[i],trY1.iloc[i],trX2.iloc[i],trY2.iloc[i]
        cos,sin=cosines[i], sines[i]
        
        gs.run_command('r.profile', input_=dem, output=tmpFile, \
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
            
        # Check if it's near a culvert
        culvertPts['distToPt']=np.sqrt((culvertPts['x']-newX)**2+(culvertPts['y']-newY)**2)
        culvertsNearby =  culvertPts[culvertPts['distToPt'] < culvertPts['buffer']]
        
        # Only include it in the line if it's not near a culvert
        if len(culvertsNearby) == 0:     
            newRow = pd.DataFrame({'lcat': [lcat], 'x': [newX], 'y': [newY]})
            newPtsDf = pd.concat((newPtsDf, newRow))
            
# Now write to a file since we know how many points are in each line
fLine=open(lineDefFile, 'a')

for lcat in lcats:
    linePts = newPtsDf[newPtsDf['lcat']==lcat]
    nPts = len(linePts)
    
    fLine.write('L  ' + str(nPts) + ' 1\n')
    
    for i in range(nPts):
        newX, newY = linePts['x'].iloc[i], linePts['y'].iloc[i]
        fLine.write(' ' + str(newX) + ' ' + str(newY) + '\n')
    fLine.write(' 1 ' + str(lcat))
    
    if lcat!=lcats[-1]:
        fLine.write('\n')
        
fLine.close()
        
gs.run_command('v.edit', flags='n', map_=newLine, tool='add', input_=lineDefFile)
    
    