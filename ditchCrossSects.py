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

import interpSurface
import transect

tmpFiles = 'tempFiles/BlueEarth/'
hucPrefix = 'HUC_0702000709'
ditchPrefix = 'BluEr'

dem = hucPrefix

alongFile=tmpFiles + ditchPrefix + '_alongPts.txt'  


halfDist = 10       # how far to take the profile on each side, in m
profSpacing = 10    # longitudinal spacing between cross-sections
sharpAngle = 20     # what is considered a sharp angle along a line, in degrees

nearDist = 20       # how far to smooth near intersections, in meters 
snapThresh = 10     # snapping threshold for intersections, in meters
snapPerp = 2.5      # maximum perpendicular distance to shift line when snapping

burnWidth = 3

lineSep='\n'

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
culvertLines = hucPrefix + '_culvertLines'
newPts = hucPrefix + '_shiftedVertices'
newElevFile = tmpFiles + hucPrefix + '_elevProfile_shiftedDitches.txt'
#%% Actual code

region = gs.read_command('g.region', flags='gp', raster=dem)

if not gdb.map_exists(definedLine, 'vector'):
    rgn = region.split(lineSep)
    rgnDict = {}
    for entry in rgn[:-1]: 
        keyVal = entry.split('=')
        rgnDict[keyVal[0]] = int(keyVal[1])
    n, s, e, w = rgnDict['n'], rgnDict['s'], rgnDict['e'], rgnDict['w']
    
    ### Read the points
    df = pd.read_csv(alongFile) 
    
    # Get all points whose coordinates are in the DEM region
    dfInRegion = df[((df['y']>=s)&(df['y']<=n))&((df['x']>=w)&(df['x']<=e))]
    lcats=sorted(set(dfInRegion['lcat']))
    
    # Open the culvert definition file so we can check which points are near culvert
    culvertPts = pd.read_csv(culvertDefFile, names=['x', 'y', 'buffer'])
    
    newPtsDf = pd.DataFrame()
    gs.run_command('v.edit', map_=definedLine, type_='line', tool='create') #, overwrite=True)
    
    for lcat in lcats:
        # Get coordinates for cross sections at each point
        trX1, trX2, trY1, trY2, x_ms, y_ms, cosines, sines, angles = transect.transect(df, lcat, halfDist)
        # Find where line angle (relative to E) changes abruptly, take cross-sections here
        angles=pd.Series(angles*180/np.pi)+90
        angleDiff = np.abs(np.diff(angles))
        sharps = angles[:-1].index[angleDiff > sharpAngle]
        sharps2 = sharps+1
        #moreCoords = list(set(list(sharps)+list(sharps2)))
        moreCoords = list(set(sharps))
        
        # Also take cross-sections at least every 10m (or whatever profSpacing is)
        ncoords = len(x_ms)
        coordsToAdd = list(range(0,ncoords,profSpacing)) + [ncoords-1]
        coordsToAdd = sorted(coordsToAdd + moreCoords)
        
        prevAcross = halfDist
        
        # Get profile across these endpoints
        for i in coordsToAdd:
            
            # Make sure to take an actual cross-section at curved parts of the line
            # rather than projecting, even if the point is near an intersection
            ovw = 0
            if i in moreCoords: ovw = 1
            
            # Assume the point is in a culvert, change these variables later if it's not
            across = prevAcross
            culvert=1
            
            x_m, y_m = x_ms.iloc[i], y_ms.iloc[i]
            x1,y1,x2,y2=trX1.iloc[i],trY1.iloc[i],trX2.iloc[i],trY2.iloc[i]
            cos,sin,angle=cosines[i], sines[i], angles[i]
            
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
                    minAcross = profile[crossElev==minElev].iloc[0]
                    across=minAcross['across']
            else:
                ovw=0
            
            prevAcross = across

            # Convert the 'across' distance into xy coordinates
            newX, newY = x1 + across*cos, y1 + across*sin
            
            newRow = pd.DataFrame({'lcat': [lcat], 'along': [i], 'x': [newX], 'y': [newY], \
                                   'across': [across], 'x1': [x1], 'y1': [y1], \
                                       'cos': [cos], 'sin': [sin], 'angle': [angle], \
                                           'culvert': [culvert], 'overwrite': [ovw]})
            newPtsDf = pd.concat((newPtsDf, newRow))
       
    newPtsDf.to_csv(tmpFiles + hucPrefix + '_newPtsDf.txt', index=False)
    newPtsDf = pd.read_csv(tmpFiles + hucPrefix + '_newPtsDf.txt')
    newPtsDf2 = pd.DataFrame()
    
    #%% Smooth most lines near intersections
    ### Smoothing means to shift the lines by an assumed distance rather than 
            # using the actual cross section
    
    # Get preliminary nodes to know if near an intersection
    nodeInds=pd.Series(newPtsDf.index[newPtsDf['along']==0])
    nodes=newPtsDf.iloc[pd.concat((nodeInds,nodeInds-1))]
    nodes=nodes[['lcat','x','y','along']] 
    
    for lcat in lcats:
        
        linePts = newPtsDf[newPtsDf['lcat']==lcat].reset_index(drop=True)
        lineLen = np.max(linePts['along'])
        
        # Check whether it's near other nodes (meaning an intersection)
        startX, startY = linePts['x'].iloc[0], linePts['y'].iloc[0]
        endX, endY = linePts['x'].iloc[-1], linePts['y'].iloc[-1]
        
        nodes.loc[:,'startDist'] = np.sqrt((nodes['x']-startX)**2+(nodes['y']-startY)**2)
        nodes.loc[:,'endDist'] = np.sqrt((nodes['x']-endX)**2+(nodes['y']-endY)**2)
        
        nearStart=nodes[nodes['startDist']<snapThresh]
        nearEnd=nodes[nodes['endDist']<snapThresh]
        
        # If it's not near an intersection, don't smooth
        if len(nearStart) <= 1:
            toOverwrite = (linePts['along']<=nearDist) & (linePts['culvert']==0)
            linePts.loc[toOverwrite, 'overwrite']=1
        if len(nearEnd) <= 1:
            toOverwrite = (linePts['along']+nearDist>=lineLen) & (linePts['culvert']==0)
            linePts.loc[toOverwrite, 'overwrite']=1
        
        # List of index positions to smooth at
        editStart = list(linePts.index[(linePts['overwrite']==0) & \
                                    (linePts['along']<=nearDist)])
        editEnd = list(linePts.index[(linePts['overwrite']==0) & \
                                    (linePts['along']+nearDist>=lineLen)])
        editNodes = []
        
        # Find the first vertex that is not near an intersection, 
        # and see how much it was shifted by. 
        if len(editStart) > 0:
            outsideStart = linePts[(linePts['culvert']==0) & (linePts['along']>nearDist)]
            if len(outsideStart)>0:
                editStart += range(editStart[-1]+1, outsideStart.index[0])
                
                localAcross = outsideStart['across'].iloc[0]
                linePts.loc[editStart,'across']=localAcross
            editNodes += editStart
         
        # Repeat for end nodes
        if len(editEnd) > 0:
            outsideEnd = linePts[(linePts['culvert']==0) & (linePts['along']+nearDist<lineLen)]
            if len(outsideEnd)>0:
                localAcross = outsideEnd['across'].iloc[-1]
                linePts.loc[editEnd, 'across']=localAcross
            editNodes += editEnd
         
        # Convert the 'across' distance into xy coordinates
        if len(editNodes) > 0:
            x1s, y1s = linePts['x1'].iloc[editNodes], linePts['y1'].iloc[editNodes]
            acrosses = linePts['across'].iloc[editNodes]
            cosinez, sinez = linePts['cos'].iloc[editNodes], linePts['sin'].iloc[editNodes]
            
            # Update shifted x and y values
            linePts.loc[editNodes, 'x'] =  x1s + acrosses*cosinez
            linePts.loc[editNodes, 'y'] =  y1s + acrosses*sinez
            
        newPtsDf2 = pd.concat((newPtsDf2,linePts),ignore_index=True)
        
    #%% Snap lines at intersections
        
    # Get xy coords of new nodes, since we smoothed them
    newPtsDf = newPtsDf2
    nodeInds=pd.Series(newPtsDf.index[newPtsDf['along']==0])
    nodes=newPtsDf.iloc[pd.concat((nodeInds,nodeInds-1))]
    nodes=nodes[['lcat','x','y','along']] 
    
    if os.path.exists(lineDefFile):
        os.remove(lineDefFile)
    fLine=open(lineDefFile, 'a')

    for lcat in lcats:
        linePts = newPtsDf[newPtsDf['lcat']==lcat].reset_index(drop=True)
        
        startX, startY = linePts['x'].iloc[0], linePts['y'].iloc[0]
        endX, endY = linePts['x'].iloc[-1], linePts['y'].iloc[-1]
        
        nodes.loc[:,'startDist'] = np.sqrt((nodes['x']-startX)**2+(nodes['y']-startY)**2)
        nodes.loc[:,'endDist'] = np.sqrt((nodes['x']-endX)**2+(nodes['y']-endY)**2)
        
        nearStart=nodes[nodes['startDist']<snapThresh]
        nearEnd=nodes[nodes['endDist']<snapThresh]
        
        # If near other nodes, snap to the average xy position
        avgStartX,avgStartY = np.mean(nearStart['x']), np.mean(nearStart['y'])
        avgEndX,avgEndY = np.mean(nearEnd['x']), np.mean(nearEnd['y'])
        
        # Usually we overwrite the end node with the averaged one,
        # but check if we creatd a sharp angle by snapping 
        # (in this case don't overwrite it)
        if len(nearStart)>1:
            # Angle relative to E of the segment connecting the end node to the averaged one
            snapAngle1 = np.arctan2(startY - avgStartY, startX-avgStartX)*180/np.pi
            # Angle relative to E of the end portion of the original line
            startAngle = linePts['angle'].iloc[0]
            if startAngle > 180: startAngle = startAngle - 360
            
            # Find angle and distance between original line and the snapped segment
            angleDiff1 = np.abs((startAngle - snapAngle1 + 180) % 360 - 180)
            snapDist1 = np.sqrt((startX-avgStartX)**2+(startY-avgStartY)**2)
            
            # If we created a significant perpendicular segment, 
            # keep the original end node
            if np.sin(angleDiff1*np.pi/180)*snapDist1 > snapPerp:
                newCoords = pd.DataFrame({'x': [avgStartX], 'y': [avgStartY], 'lcat': [lcat]})
                linePts = pd.concat((newCoords, linePts), ignore_index=True) 
            else:
                linePts.loc[0,'x']=avgStartX; linePts.loc[0,'y']=avgStartY
            
        if len(nearEnd)>1:
            snapAngle2 = np.arctan2(avgEndY - endY, avgEndX - endX)*180/np.pi
            endAngle = linePts['angle'].iloc[-1]
            if endAngle > 180: endAngle = endAngle - 360
            angleDiff2 = np.abs((snapAngle2 - endAngle+180) % 360 - 180)
            snapDist2 = np.sqrt((endX-avgEndX)**2+(endY-avgEndY)**2)
            
            if np.sin(angleDiff2*np.pi/180)*snapDist2 > snapPerp:
                newCoords = pd.DataFrame({'x': [avgEndX], 'y': [avgEndY], 'lcat': [lcat]})
                linePts = pd.concat((linePts,newCoords), ignore_index=True) 
            else:
                linePts.loc[len(linePts)-1,'x']=avgEndX; linePts.loc[len(linePts)-1,'y']=avgEndY
            
        nPts = len(linePts)
        
        # Write to file that will define the line vertices
        fLine.write('L  ' + str(nPts) + ' 1\n')
        
        for i in range(nPts):
            newX, newY = linePts['x'].iloc[i], linePts['y'].iloc[i]
            fLine.write(' ' + str(newX) + ' ' + str(newY) + '\n')
        fLine.write(' 1 ' + str(lcat))
        if lcat != lcats[-1]:
            fLine.write('\n')
            
    fLine.close()
            
    gs.run_command('v.edit', flags='n', map_=definedLine, tool='add', \
                        input_=lineDefFile)
    # Build polylines for any lines that v.edit missed in splitJunctions
    gs.run_command('v.build.polylines', input_=definedLine, output=newLine, \
                    type_='line', cats='first')

if not gdb.map_exists(newPts, 'vector'):
    # Find portion of ditches that pass through culverts
    gs.run_command('v.overlay', ainput=newLine, atype='line', binput=culvertBuffers, \
                    operator='and', output=culvertLines)
        
    # Create a burned DEM and one with culvert areas set to null
    filler, demNull = interpSurface.interpSurface(tmpFiles, hucPrefix, lineSep, culvertLines, burnWidth, dem, \
                                demForNull=dem)
    
    # Get elevation profile for shifted ditches
    gs.run_command('v.to.points', input_=newLine, dmax=1, output=newPts)
    gs.run_command('v.to.db', map_=newPts, layer=2, option='coor', columns=['x', 'y'])
    gs.run_command('v.what.rast', map_=newPts, raster=demNull, column='elev', layer=2)
    gs.run_command('v.db.select', map_=newPts, layer=2, format_='csv', file=newElevFile, overwrite=True)
    
    