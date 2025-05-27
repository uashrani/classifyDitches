# -*- coding: utf-8 -*-
"""
Created on Fri Apr 25 13:50:10 2025

@author: Uma
"""

import pandas as pd
import numpy as np
import grass.script as gs

file = 'tempFiles/linRegPts.txt'
demNull='DEMwNulls'     # DEM used to take elevation profile along shifted lines. Has nulls

df = pd.read_csv(file) 
dfWithElevs = df[np.isnan(df['elev'])==False]

lcats = sorted(set(dfWithElevs['lcat']))
lcats=[27, 36, 37, 251, 274, 414, 415, 420, 421, 428, 467, 564]

lineDefFile='tempFiles/lineDefs_culvertsRemoved.txt'
tmpFile = 'tempFiles/tmpProfile.txt'

newLine = 'shiftedDitches'
newPts = 'shiftedVertices'

newElevFile = 'tempFiles/elevProfile_shiftedDitches.txt'

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
    halfDist = 7.5
    
    # Get the midpoints of all 1-m line segments
    x_m = (x[1:].reset_index(drop=True) +x[:-1].reset_index(drop=True)) / 2
    y_m = (y[1:].reset_index(drop=True) +y[:-1].reset_index(drop=True)) / 2
    
    trX1 = x_m - halfDist*cosines
    trX2 = x_m + halfDist*cosines
    trY1 = y_m - halfDist*sines
    trY2 = y_m + halfDist*sines
    
    ncoords = len(x_m)
    coordsToAdd = range(0,ncoords)
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
        
        if minElev==np.nan:
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
gs.run_command('v.to.points', input_=newLine, use='vertex', output=newPts)
gs.run_command('v.what.rast', map_=newPts, raster=demNull, column='elev', layer=2)
gs.run_command('v.db.select', map_=newPts, layer=2, format_='csv', file=newElevFile)
        
    
    