# -*- coding: utf-8 -*-
"""
Created on Fri Apr 25 13:50:10 2025

@author: Uma
"""

#%% Prerequisite modules, data, and folders

import grass.script as gs
import grass.grassdb.data as gdb
import pandas as pd
import numpy as np
import os

import removeCulverts
import transect

tmpFiles = 'tempFiles2/'
hucPrefix = 'testDEM3'
ditchPrefix = 'BRR'

dem = hucPrefix

alongFile=tmpFiles + ditchPrefix + '_alongPts.txt'  

chainFile = tmpFiles + ditchPrefix + '_streamChains.txt'
#snapDefFile = tmpFiles + ditchPrefix + '_whereToSnap.txt'

# How far to take the profile on each side, in m
halfDist = 10   
# Longitudinal spacing between cross-sections
profSpacing = 10

# Need to know where culverts are
culvertDefFile = tmpFiles + ditchPrefix + '_culvertPtDefs.txt'
culvertBuffers = ditchPrefix + '_culvertBuffers'

#%% Layers/files that will be created automatically

lineDefFile= tmpFiles + 'shiftedLineDef.txt'
tmpFile = tmpFiles + 'tmpProfile.txt'

# Shifted lines
definedLine = hucPrefix + '_shiftedDitches_notCleaned'
newLine = hucPrefix + '_shiftedDitches'

# Stuff created after identifying culverts
demNull = hucPrefix + '_wNulls'
demBurned = hucPrefix + '_burned'
#%% Actual code

if not gdb.map_exists(newLine, 'vector'):
    region = gs.read_command('g.region', flags='gp', raster=dem)
    rgn = region.split('\r\n')
    rgnDict = {}
    for entry in rgn[:-1]: 
        keyVal = entry.split('=')
        rgnDict[keyVal[0]] = int(keyVal[1])
    n, s, e, w = rgnDict['n'], rgnDict['s'], rgnDict['e'], rgnDict['w']
    
    ### Read the points
    df = pd.read_csv(alongFile) 
    
    # Get all points whose coordinates are in the DEM region
    dfInRegion = df[((df['y']>=s)&(df['y']<=n))&((df['x']>=w)&(df['x']<=e))]
    #lcats=sorted(set(dfInRegion['lcat']))
    lcats=[166,167,168,169]
    
    # Open the culvert definition file so we can check which points are near culvert
    culvertPts = pd.read_csv(culvertDefFile, names=['x', 'y', 'buffer'])
    
    # Create empty vector map for new lines, and empty file to add coords
    newPtsDf = pd.DataFrame({'lcat': [], 'x': [], 'y': [], 'across': [], \
                             'x1': [], 'y1': [], 'cos': [], 'sin': [], 'culvert': []})
    gs.run_command('v.edit', map_=definedLine, type_='line', tool='create', overwrite=True)
    
    for lcat in lcats:
        trX1, trX2, trY1, trY2, x_ms, y_ms, cosines, sines = transect.transect(df, lcat, halfDist)
        
        ncoords = len(x_ms)
        if ncoords < 20:
            # Take a cross section every 1m if the segment is short
            coordsToAdd = list(range(0,ncoords,2)) + [ncoords-1]
        else:
            # Otherwise, go every 1m near the endpoints but space out the cross sections in between
            coordsToAdd = list(range(0,10,2)) + list(range(10,ncoords-10,profSpacing)) + \
                list(range(ncoords-10,ncoords,2))
        
        prevAcross = halfDist
        
        # Get profile across these endpoints
        for i in coordsToAdd:
            
            # Assume the point is in a culvert, change these variables later if it's not
            across = prevAcross
            culvert=1
            
            x_m, y_m = x_ms.iloc[i], y_ms.iloc[i]
            x1,y1,x2,y2=trX1.iloc[i],trY1.iloc[i],trX2.iloc[i],trY2.iloc[i]
            cos,sin=cosines[i], sines[i]
            
            # Check if the point is near a culvert
            culvertPts['distToPt']=np.sqrt((culvertPts['x']-x_m)**2+(culvertPts['y']-y_m)**2)
            culvertsNearby =  culvertPts[culvertPts['distToPt'] < culvertPts['buffer']]
            
            # If it's not near a culvert, find the minimum elevation along transect
            if len(culvertsNearby) == 0:     
                culvert=0
    
                gs.run_command('r.profile', input_=dem, output=tmpFile, \
                                coordinates=[x1,y1,x2,y2], overwrite=True)
            
                profile=pd.read_csv(tmpFile, sep='\s+', names=['across', 'elev'], na_values='*')
                crossElev=profile['elev']
                minElev=np.min(crossElev)
                
                if np.isnan(minElev):
                    newX, newY = x_m, y_m
                else:
                    # across gets changed if 
                    minAcross = profile[crossElev==minElev].iloc[0]
                    across=minAcross['across']
            
            prevAcross = across
                
            newX, newY = x1 + across*cos, y1 + across*sin
            
            newRow = pd.DataFrame({'lcat': [lcat], 'along': [i], 'x': [newX], 'y': [newY], \
                                   'across': [across], 'x1': [x1], 'y1': [y1], \
                                       'cos': [cos], 'sin': [sin], 'culvert': [culvert]})
            newPtsDf = pd.concat((newPtsDf, newRow))
       
    newPtsDf.to_csv(tmpFiles + hucPrefix + '_newPtsDf.txt', index=False)
    # Now write to a file since we know how many points are in each line
    chainDf = pd.read_csv(chainFile)
    
    fLine=open(lineDefFile, 'a')
    
    for lcat in lcats:
        #if os.path.exists(lineDefFile):
        #    os.remove(lineDefFile)
        
        linePts = newPtsDf[newPtsDf['lcat']==lcat].reset_index(drop=True)
        
        if max(linePts['along']) < 10: 
            strChain = chainDf['chain'][chainDf['root']==lcat].iloc[0]
            strpChain=strChain.strip('[]')
            chain = np.array(list(map(int,strpChain.split(', '))))
            chainPos = np.where(chain==lcat)[0][0]
            if chainPos + 1 < len(chain):
                nextSeg = chain[chainPos+1]
                nextSegPts = newPtsDf[newPtsDf['lcat']==nextSeg]
                
                if len(nextSegPts) > 0:
                    newAlong = np.sqrt((linePts['x'].iloc[-1] - nextSegPts['x'].iloc[0])**2 + \
                                       (linePts['y'].iloc[-1] - nextSegPts['y'].iloc[0])**2)
                    if newAlong < 10: 
                        linePts = pd.concat((linePts, nextSegPts.iloc[0:1])).reset_index(drop=True)
                    else:
                        newAlong = np.sqrt((linePts['x'].iloc[-1] - nextSegPts['x'].iloc[-1])**2 + \
                                           (linePts['y'].iloc[-1] - nextSegPts['y'].iloc[-1])**2)
                        if newAlong < 10:
                            linePts = pd.concat((linePts, nextSegPts.iloc[-1:])).reset_index(drop=True)
                        else:
                            newAlong = 0
                    
                    linePts.loc[len(linePts)-1, 'along'] = linePts['along'].iloc[-2]+newAlong
        
        ### Fill in any start points that were in a culvert
        earlyCuls = list(linePts.index[(linePts['culvert']==1) & (linePts['along']<=10)])
        if len(earlyCuls) > 0:
            # Get the index of the first non-culvert point, edit preceding across values
            nonCuls = linePts[(linePts['culvert']==0) & (linePts['along']>10)]
            if len(nonCuls) > 0:
                earlyCuls += range(earlyCuls[-1]+1, nonCuls.index[0])
                localAcross = nonCuls['across'].iloc[0]
                linePts.loc[earlyCuls, 'across']=localAcross
            
            # These are just for the start points in a culvert
            x1s, y1s = linePts['x1'].iloc[earlyCuls], linePts['y1'].iloc[earlyCuls]
            acrosses = linePts['across'].iloc[earlyCuls]
            cosinez, sinez = linePts['cos'].iloc[earlyCuls], linePts['sin'].iloc[earlyCuls]
            
            # Update shifted x and y values
            linePts.loc[earlyCuls, 'x'] =  x1s + acrosses*cosinez
            linePts.loc[earlyCuls, 'y'] =  y1s + acrosses*sinez
            
        nPts = len(linePts)
        
        fLine.write('L  ' + str(nPts) + ' 1\n')
    
        for i in range(nPts):
            newX, newY = linePts['x'].iloc[i], linePts['y'].iloc[i]
            fLine.write(' ' + str(newX) + ' ' + str(newY) + '\n')
        fLine.write(' 1 ' + str(lcat))
        if lcat != lcats[-1]:
            fLine.write('\n')
            
    fLine.close()
            
    gs.run_command('v.edit', flags='n', map_=definedLine, tool='add', \
                       input_=lineDefFile) #, snap='node', threshold=10)
    
    gs.run_command('v.clean', input_=definedLine, output=newLine, tool=['snap','rmdupl'], threshold=[10,0])
    

# Later make a mega program that calls all functions, but for now do it here
# removeCulverts.removeCulverts(tmpFiles, hucPrefix, hucPrefix, \
#                             culvertBuffers, newLine, dem, dem)
    
    