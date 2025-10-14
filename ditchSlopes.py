# -*- coding: utf-8 -*-
"""
Created on Wed May 21 16:09:13 2025

@author: swimm
"""

#%% Prerequisites 

import grass.script as gs
import grass.grassdb.data as gdb
import pandas as pd
import scipy as sp
import numpy as np

import interpSurface

tmpFiles = 'tempFiles/'
hucPrefix = 'HUC_0902010402'
ditchPrefix = 'BRR'

origCatFile = tmpFiles + ditchPrefix + '_origCats.txt'
chainFile = tmpFiles + ditchPrefix + '_streamChains.txt'
elevFile = tmpFiles + hucPrefix + '_elevProfile_shiftedDitches.txt'

newLine = hucPrefix + '_shiftedDitches'

demBurned = hucPrefix + '_interpDEM'

lineSep='\n'

# For splitting lines with differing slopes
vecLines3 = ditchPrefix + '_lines_rmdupl2'
nodesFile = tmpFiles + ditchPrefix + '_nodesTemp.txt'

peakThresh = 1      # What counts as a peak in the elevation profile
burnWidth = 3
unmappedBuffer = 25

#%% To be created
vecLines7 = hucPrefix + '_lines_flowDirTemp'

culvertDefFile = tmpFiles + hucPrefix + '_culvertPtDefs.txt'   # file that GRASS will read from 

culvertPts = hucPrefix + '_culvertPoints'   # points layer of culvert locations
culvertBuffers = hucPrefix + '_culvertBuffers'  # vector layer containing circles around the culvert points

# Temp layers if we are splitting 
tempSplit1 = hucPrefix + '_tempSplit1'
splitPts = hucPrefix + '_splitPts'

vecLines8 = hucPrefix + '_lines_flowDir'

# Culvert removal
culvertLines = hucPrefix + '_v2_culvertLines'

# Elevation file with accurate ditch directions
newElevFile = tmpFiles + hucPrefix + '_elevProfile_flippedDitches.txt'

#%% Actual code   
gs.run_command('g.region', raster=demBurned)

chainDf = pd.read_csv(chainFile)   
df = pd.read_csv(elevFile)
df2 = pd.DataFrame()

lcats=sorted(set(df['lcat']))

unmappedCulverts = pd.DataFrame({'x': [], 'y': []})

dropFids, origCats = [], []

if not gdb.map_exists(vecLines7, 'vector'):
    gs.run_command('g.copy', vector=[newLine, vecLines7])

    ### Do linear regression and flip vector directions if needed
    for lcat in lcats:
        
        chain=[lcat]
    
        thisDitch_index = df.index[df['lcat']==lcat]
        thisDitch_wnans = df[df['lcat']==lcat]
        thisDitch = df[(df['lcat']==lcat) & (np.isnan(df['elev'])==False)]
        along, elev = thisDitch['along'], thisDitch['elev']
        
        # Try linear regression with just a single ditch segment first
        if len(along) >= 25: 
            linreg = sp.stats.linregress(along, elev)  
            r2=linreg.rvalue**2
        
        # Concatenate segments for linreg if r2 is too low
        if len(along) < 25 or r2 < 0.4: 
            ## Chain some lines together based on the chain file
            strChain = chainDf['chain'][chainDf['root']==lcat].iloc[0]
            strpChain=strChain.strip('[]')
            chain = list(map(int,strpChain.split(', ')))
            
            print('Ditch ' + str(lcat) + ' is < 25m or has r2 < 0.4. Concatenating with ' + \
                  strpChain)
                
            for (j, segment) in enumerate(chain):
                chainDitch = df[(df['lcat']==segment) & (np.isnan(df['elev'])==False)]
                if j==0:
                    concatDf = chainDitch.reset_index(drop=True)
                else:
                    if len(concatDf) > 0: chainDitch.loc[:, 'along']=chainDitch['along'] + concatDf['along'].iloc[-1]
                    concatDf = pd.concat((concatDf, chainDitch)).reset_index(drop=True)
                 
            thisDitch = concatDf
            along, elev = thisDitch['along'], thisDitch['elev']
            
            # Take elevation profile of concatenated lines
            linreg = sp.stats.linregress(along, elev)
            r2 = linreg.rvalue**2
          
        ### Now find whether there are any unmapped culverts along the profile
        x, y = thisDitch['x'], thisDitch['y']
        linElev = linreg.slope * along + linreg.intercept  
        
        # First define what counts as a significant peak in the profile
        # using RMSE (or just 1m if RMSE is high)
        rmse = np.sqrt(np.mean((elev - linElev)**2))
        prom=min([peakThresh,rmse*4])
        
        # scipy find_peaks doesn't catch peaks at the endpoints
        # Check where slope is different from rest of profile?
        ditchSlope = np.diff(elev) / np.diff(along)
        
        peakIndsEP = []
        
        if np.max(along) > 50:
            start25 = np.where(along>25)[0][0]
            end25 = np.where(along+25<along.iloc[-1])[0][-1]
            startSlope = (elev.iloc[start25] - elev.iloc[0]) / (along.iloc[start25] - along.iloc[0])
            endSlope = (elev.iloc[-1] - elev.iloc[end25]) / (along.iloc[-1] - along.iloc[end25]) 
            
            if (np.abs(startSlope) > np.abs(linreg.slope) * 20) and np.max((elev-linElev).iloc[:start25]) > prom:
                peakIndsEP += [0] 
            if np.abs(endSlope) > np.abs(linreg.slope) * 20 and np.max((elev-linElev).iloc[end25:]) > prom:
                peakIndsEP += [len(along)-1]
                
        peakInds, props = sp.signal.find_peaks(elev, prominence=prom, width=[1,50])
            
        # Now have index positions of all peaks in the elev profile
        allPeaks = pd.concat((pd.Series(peakInds), pd.Series(peakIndsEP))).reset_index(drop=True)
        dropInds = []
        
        # Get the xy coordinates of the unmapped culverts
        for ind in allPeaks:
            unmappedCulverts = pd.concat((unmappedCulverts, \
                                          pd.DataFrame({'x': [x.iloc[ind]], 'y': [y.iloc[ind]]})))
            dropInds += range(ind-25,ind+26)
            
        # Also drop the peaks from the profile and redo the linear regression
        dropInds=pd.Series(dropInds)
        dropInds = dropInds[dropInds < len(elev)]
        
        filtDf = thisDitch.drop(thisDitch.index[dropInds])
        filtAlong, filtElev = filtDf['along'], filtDf['elev']
        
        linreg = sp.stats.linregress(filtAlong, filtElev)
        r2 = linreg.rvalue**2
            
        if r2 >= 0.4 and linreg.slope > 0:
            gs.run_command('v.edit', map_=vecLines7, tool='flip', cats=lcat)
            df2=pd.concat((df2, thisDitch_wnans.iloc[::-1]), ignore_index=True)
        
        # If r2 is low, it's possible that there are two segments with opposite flow dirs
        if r2 < 0.4:
            # Try fitting a quadratic curve
            a,b,c = np.polyfit(filtAlong,filtElev,2)
            polyMin = -b / (2*a)
            
            # See if the quadratic turning point is within the profile
            if polyMin > 0 and polyMin < np.max(filtAlong):
                # Split the ditch based on the x position of quadratic min/max
                ditch1 = filtDf[filtDf['along'] <= polyMin]
                ditch2 = filtDf[filtDf['along'] > polyMin]
                
                # Take linear regression of each segment
                linreg1 = sp.stats.linregress(ditch1['along'], ditch1['elev'])
                linreg2 = sp.stats.linregress(ditch2['along'], ditch2['elev'])
                rsq1, rsq2 = linreg1.rvalue**2, linreg2.rvalue**2
                slope1, slope2 = linreg1.slope, linreg2.slope
                
                # If r2s of each individual segment are both high, split the ditch
                if rsq1 >= 0.4 and rsq2 >= 0.4:
                    distFromSplit = np.abs(filtAlong - polyMin)
                    # This gives xy point on the ditch closest to the quadratic min/max
                    # Previously we just had 'along'
                    toSplit = filtDf[distFromSplit==min(distFromSplit)].iloc[0]
                    
                    # We want to see if these were originally two ditches that got incorrectly merged by build.polylines
                    # Get the midpoint xy of each segment to find original cats
                    midpoint1=ditch1.iloc[len(ditch1)//2]
                    midpoint2=ditch2.iloc[len(ditch2)//2]   
                    x1, y1 = midpoint1['x'], midpoint1['y']
                    x2, y2 = midpoint2['x'], midpoint2['y']
                    
                    # Import the midpoints as a points layer, 
                    # and use v.what.vect to get cats from a previous lines layer
                    midDf = pd.DataFrame({'x':[x1,x2], 'y':[y1,y2]})
                    midDf.to_csv('splitMidpoints.txt', index=False, header=False)
                    gs.run_command('v.in.ascii', input_='splitMidpoints.txt', output=splitPts, \
                                   separator='comma', columns=['x double precision', 'y double precision'])
                    gs.run_command('v.db.addtable', map_=splitPts)
                    gs.run_command('v.db.addcolumn', map_=splitPts, columns='orig_cat int')
                    gs.run_command('v.what.vect', map_=splitPts, column='orig_cat', query_map=vecLines3, query_column='cat', dmax=10)
                    gs.run_command('v.db.select', map_=splitPts, format_='csv', file='split_origcats.txt', overwrite=True)
                    
                    d=pd.read_csv('split_origcats.txt')
                    oc1, oc2 = d['orig_cat'].iloc[0], d['orig_cat'].iloc[1]
                    
                    # If this was originally two lines that shouldn't have been merged,
                    # find the closest original node, and use its xy coords as point to split
                    if oc1 != oc2:
                        nodesDf=pd.read_csv(nodesFile)
                        starts, ends = nodesDf.iloc[::3].reset_index(drop=True), \
                            nodesDf.iloc[2::3].reset_index(drop=True)
                        nodesDf = pd.concat((starts,ends), ignore_index=True)
                        nodesDf=nodesDf[(nodesDf['lcat']==oc1)|(nodesDf['lcat']==oc2)]
                        nodesDf.loc[:,'dist']=np.sqrt((nodesDf['x']-toSplit['x'])**2+(nodesDf['y']-toSplit['y'])**2)
                        toSplit = nodesDf[nodesDf['dist']==min(nodesDf['dist'])].iloc[0]
                    
                    # Split line at the xy point
                    gs.run_command('v.edit', map_=vecLines7, tool='break', coords=[toSplit['x'],toSplit['y']], threshold=10)
                    
                    # Find the feature IDs currently associated with the split ditch
                    fid1=gs.read_command('v.edit', map_=vecLines7, tool='select', bbox=[x1-0.1,y1-0.1,x1+0.1,y1+0.1])
                    fid1 = int(fid1.split('\n')[0])
                    fid2=gs.read_command('v.edit', map_=vecLines7, tool='select', bbox=[x2-0.1,y2-0.1,x2+0.1,y2+0.1])
                    fid2 = int(fid2.split('\n')[0])
                    
                    # One of them will need a new category number, but keep track of original cat
                    dropFids += [fid1]
                    origCats += [oc1]
                    
                    # Update file with original category number for the 2nd segment
                    origDf = pd.read_csv(origCatFile)
                    origDf.loc[(origDf['cat']==lcat), 'orig_cat'] = oc2
                    
                    # Also change the category numbers in the elevation profile
                    # First re-split ditch based on the xy coord
                    thisDitch_wnans.reset_index(inplace=True, drop=True)
                    distFromSplit = np.sqrt((thisDitch_wnans['x']-toSplit['x'])**2 + (thisDitch_wnans['y']-toSplit['y'])**2)
                    splitInd = thisDitch_wnans.index[distFromSplit==min(distFromSplit)][0]
                    
                    ditch1 = thisDitch_wnans.iloc[:splitInd]
                    ditch2 = thisDitch_wnans.iloc[splitInd:]
                    
                    # Flip any segments with a positive slope
                    if slope1 > 0: 
                        gs.run_command('v.edit', map_=vecLines7, tool='flip', ids=fid1)
                        ditch1 = ditch1.iloc[::-1]
                    if slope2 > 0: 
                        gs.run_command('v.edit', map_=vecLines7, tool='flip', ids=fid2)
                        ditch2 = ditch2.iloc[::-1]
                    
                    newCat = max(pd.concat((origDf['cat'], df2['lcat'])))+1
                    ditch1.loc[:, 'lcat']=newCat
                    
                    df2 = pd.concat((df2, ditch1, ditch2), ignore_index=True)
                    
                else:
                    print('Warning: Ditch ' + str(lcat) + ' still has r2 < 0.4 even after concatenating profiles.')

    newCat = max(origDf['cat'])+1
    gs.run_command('v.category', input_=vecLines7, cat=-1, ids=dropFids, option='del', output=tempSplit1)
    gs.run_command('v.category', input_=tempSplit1, option='add', output=vecLines8, cat=newCat)
    
    for (i,thisCat) in enumerate(range(newCat,newCat+len(dropFids))):
        newRow = pd.DataFrame({'cat':[thisCat], 'orig_cat':[origCats[i]]})
        origDf = pd.concat((origDf,newRow),ignore_index=True)
    
    origDf.to_csv(origCatFile, index=False)
    unmappedCulverts.to_csv(culvertDefFile, index=False, header=False)
    df2.to_csv(newElevFile, index=False)
    
    # Create points layer with unmapped culvert locations
    gs.run_command('v.in.ascii', input_=culvertDefFile, output=culvertPts, \
                    separator='comma', columns=['x double precision', 'y double precision'])
        
    # Buffer the culvert points
    gs.run_command('v.buffer', input_=culvertPts, type_='point', \
                    output=culvertBuffers, distance=unmappedBuffer)
        
if not gdb.map_exists(culvertLines, 'raster'):
    # Find segments of ditches that pass through culverts
    gs.run_command('v.overlay', ainput=vecLines8, atype='line', binput=culvertBuffers, \
                    operator='and', output=culvertLines)
        
    demBurned2, demNull = interpSurface.interpSurface(tmpFiles, hucPrefix+'_v2', lineSep, \
                                                  culvertLines, burnWidth, demBurned)
    
