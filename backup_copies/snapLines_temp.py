# -*- coding: utf-8 -*-
"""
Created on Wed Jul  9 13:51:26 2025

@author: swimm
"""

import pandas as pd
import numpy as np

df = pd.read_csv('whereToSnap.txt')

df = df[(df['from_cat']!=df['cat']) & (df['dist'] > 0)]
#dfCopy = df.copy()

l = len(df)
i = 0
while i < l:
    f_cat, t_cat = df['from_cat'].iloc[i], df['cat'].iloc[i]
    df = df[(df['from_cat']!=t_cat) | (df['cat']!=f_cat)]
    
    l = len(df)
    i += 1
    
#%%

### Read the points
df2 = pd.read_csv('endptCoors.txt') 
    
lcats = sorted(set(df2['lcat']))

for lcat in lcats:
    profilePts = df2[df2['lcat']==lcat]
    snaps = df[df['from_cat']==lcat]
    
    # Check which are near the end point, and which are near start point

    for pos in [0, -1]:
        x1, y1 = profilePts['x'].iloc[pos], profilePts['y'].iloc[pos]
        
        snapsDist = np.sqrt((snaps['to_x']-x1)**2+(snaps['to_y']-y1)**2)
        linesNearby = np.where(snapsDist < 10)[0]
        nearestXY = snaps.iloc[linesNearby]
        
        if len(linesNearby) > 1:
            nearestXY = snaps[snapsDist == np.min(snapsDist)].iloc[0]
            
        if profilePts['along'].iloc[-1] > 10 and len(linesNearby) > 0:
            newRow = pd.DataFrame({'cat': [np.nan], 'lcat': [lcat], 'along': [np.nan], \
                                   'x': [nearestXY['to_x']], 'y':nearestXY['to_y']})
            if pos == 0:
                profilePts = pd.concat((newRow,profilePts)).reset_index(drop=True)
            else:
                profilePts = pd.concat((profilePts,newRow)).reset_index(drop=True)
                
    print(profilePts)
    
        # if len(linesNearby) > 1 and profilePts['along'].iloc[-1] > 10:
        #     print(profilePts)
        #     print(snaps.iloc[linesNearby])
        #     print()
    
        
#         # Sometimes v.edit adds a 'toe' to a segment
#         # you can tell if two subsequent points have identical xy coords
#         xDiff, yDiff = np.diff(profilePts['x']), np.diff(profilePts['y'])
#         whereExtra = np.where((xDiff == 0) & (yDiff == 0))[0]+1
#         if len(whereExtra) > 0:
#             # Keep the longest segment and filter out the toe
#             segEndpts = [0] + list(whereExtra) + [len(profilePts)]
#             lenSegments=np.diff(segEndpts)
#             k = np.where(lenSegments==np.max(lenSegments))[0][0]
#             profilePts = profilePts.iloc[segEndpts[k]:segEndpts[k+1]]
#             print(str(lcat) + ' had a toe added by v.edit')
        
#         x, y = profilePts['x'], profilePts['y']
        
#         tangentSlopes=np.diff(y) / np.diff(x)  
#         normalSlopes = - 1 / tangentSlopes
        
#         # we just calculated the normal line's y/x change, aka the tangent
#         # which angle is associated with this tangent?
#         angles=np.arctan(normalSlopes)
#         sines=np.sin(angles)
#         cosines=np.cos(angles)
        
#         # Get the midpoints of all 1-m line segments
#         x_ms = (x[1:].reset_index(drop=True) +x[:-1].reset_index(drop=True)) / 2
#         y_ms = (y[1:].reset_index(drop=True) +y[:-1].reset_index(drop=True)) / 2
        
#         trX1 = x_ms - halfDist*cosines
#         trX2 = x_ms + halfDist*cosines
#         trY1 = y_ms - halfDist*sines
#         trY2 = y_ms + halfDist*sines
        
#         ncoords = len(x_ms)
#         coordsToAdd = list(range(0,ncoords,10))+[ncoords-1]  # go every 10m but include end
        
#         prevAcross = halfDist
        
#         # Get profile across these endpoints
#         for i in coordsToAdd:
            
#             # Assume the point is in a culvert, change these variables later if it's not
#             across = prevAcross
#             culvert=True
            
#             x_m, y_m = x_ms.iloc[i], y_ms.iloc[i]
#             x1,y1,x2,y2=trX1.iloc[i],trY1.iloc[i],trX2.iloc[i],trY2.iloc[i]
#             cos,sin=cosines[i], sines[i]
            
#             # Check if the point is near a culvert
#             culvertPts['distToPt']=np.sqrt((culvertPts['x']-x_m)**2+(culvertPts['y']-y_m)**2)
#             culvertsNearby =  culvertPts[culvertPts['distToPt'] < culvertPts['buffer']]
            
#             # If it's not near a culvert, find the minimum elevation along transect
#             if len(culvertsNearby) == 0:     
#                 culvert=False
    
#                 gs.run_command('r.profile', input_=dem, output=tmpFile, \
#                                 coordinates=[x1,y1,x2,y2], overwrite=True)
            
#                 profile=pd.read_csv(tmpFile, sep='\s+', names=['across', 'elev'], na_values='*')
#                 crossElev=profile['elev']
#                 minElev=np.min(crossElev)
                
#                 if np.isnan(minElev):
#                     newX, newY = x_m, y_m
#                 else:
#                     # across gets changed if 
#                     minAcross = profile[crossElev==minElev].iloc[0]
#                     across=minAcross['across']
            
#             prevAcross = across
                
#             newX, newY = x1 + across*cos, y1 + across*sin
            
#             newRow = pd.DataFrame({'lcat': [lcat], 'x': [newX], 'y': [newY], \
#                                    'across': [across], 'x1': [x1], 'y1': [y1], \
#                                        'cos': [cos], 'sin': [sin], 'culvert': [culvert]})
#             newPtsDf = pd.concat((newPtsDf, newRow))
       
#     #newPtsDf.to_csv(tmpFiles + hucPrefix + '_newPtsDf.csv')
#     # Now write to a file since we know how many points are in each line
#     fLine=open(lineDefFile, 'a')
    
#     for lcat in lcats:
#         linePts = newPtsDf[newPtsDf['lcat']==lcat].reset_index(drop=True)
#         nPts = len(linePts)
        
#         fLine.write('L  ' + str(nPts) + ' 1\n')
        
#         ### Fill in any start points that were in a culvert
        
#         # Get the index of the first non-culvert point, edit preceding across values
#         nonCuls = linePts.index[linePts['culvert']==False]
#         if len(nonCuls) > 0:
#             nonCul = nonCuls[0]
#             linePts.loc[:(nonCul-1), 'across'] = linePts['across'].iloc[nonCul]
            
#             # These are just for the start points in a culvert
#             x1s, y1s = linePts['x1'].iloc[:nonCul], linePts['y1'].iloc[:nonCul]
#             acrosses = linePts['across'].iloc[:nonCul]
#             cosinez, sinez = linePts['cos'].iloc[:nonCul], linePts['sin'].iloc[:nonCul]
            
#             # Update shifted x and y values
#             linePts.loc[:(nonCul-1), 'x'] =  x1s + acrosses*cosinez
#             linePts.loc[:(nonCul-1), 'y'] =  y1s + acrosses*sinez
    
#         for i in range(nPts):
#             newX, newY = linePts['x'].iloc[i], linePts['y'].iloc[i]
#             fLine.write(' ' + str(newX) + ' ' + str(newY) + '\n')
#         fLine.write(' 1 ' + str(lcat))
        
#         if lcat!=lcats[-1]:
#             fLine.write('\n')
            
#     fLine.close()
            
#     gs.run_command('v.edit', flags='n', map_=definedLine, tool='add', input_=lineDefFile)
    
#     gs.run_command('v.clean', input_=definedLine, output=newLine, tool='snap', threshold=10)

# # Later make a mega program that calls all functions, but for now do it here
# removeCulverts.removeCulverts(tmpFiles, hucPrefix, hucPrefix, \
#                               culvertBuffers, newLine, dem, dem)
    
    
