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
hucPrefix = 'testDEM1'
ditchPrefix = 'BRR'

origCatFile = tmpFiles + ditchPrefix + '_origCats.txt'
chainFile = tmpFiles + ditchPrefix + '_streamChains.txt'
newElevFile = tmpFiles + hucPrefix + '_elevProfile_shiftedDitches.txt'

definedLine = hucPrefix + '_shiftedDitches_notCleaned'

demBurned = hucPrefix + '_interpDEM'

# For splitting lines with differing slopes
vecLines3 = ditchPrefix + '_lines_rmdupl2'
nodesFile = tmpFiles + ditchPrefix + '_nodesTemp.txt'

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

#%% Actual code   
gs.run_command('g.region', vector=definedLine)

chainDf = pd.read_csv(chainFile)   
df = pd.read_csv(newElevFile)
df2 = df

lcats=sorted(set(df['lcat']))

unmappedCulverts = pd.DataFrame({'x': [], 'y': []})

newChainDf = chainDf.copy()

dropFids, origCats = [], []

if not gdb.map_exists(vecLines7, 'vector'):
    gs.run_command('g.copy', vector=[definedLine, vecLines7])

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
            ## Chain some lines together based on the definitions in the file
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
            
            linreg = sp.stats.linregress(along, elev)
            r2 = linreg.rvalue**2
            
        x, y = thisDitch['x'], thisDitch['y']
        linElev = linreg.slope * along + linreg.intercept  
        
        # Calculate the absolute value of error 
        absErr = np.absolute(elev - linElev)
        rmse = np.sqrt(np.mean((elev - linElev)**2))
        prom=min([1,rmse*4])
        
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
            
        allPeaks = pd.concat((pd.Series(peakInds), pd.Series(peakIndsEP))).reset_index(drop=True)
        dropInds = []
        
        for ind in allPeaks:
            unmappedCulverts = pd.concat((unmappedCulverts, \
                                          pd.DataFrame({'x': [x.iloc[ind]], 'y': [y.iloc[ind]]})))
            dropInds += range(ind-25,ind+26)
            
        dropInds=pd.Series(dropInds)
        dropInds = dropInds[dropInds < len(elev)]
        
        filtDf = thisDitch.drop(thisDitch.index[dropInds])
        filtAlong, filtElev = filtDf['along'], filtDf['elev']
        
        linreg = sp.stats.linregress(filtAlong, filtElev)
        r2 = linreg.rvalue**2
                
        #print(lcat,linreg.slope)
            
        if r2 >= 0.4 and linreg.slope > 0:
            gs.run_command('v.edit', map_=vecLines7, tool='flip', cats=lcat)
            df2=pd.concat((df2.iloc[:thisDitch_index[0]], thisDitch_wnans.iloc[::-1], df2.iloc[thisDitch_index[-1]+1:]), ignore_index=True)
        if r2 < 0.4:
            a,b,c = np.polyfit(filtAlong,filtElev,2)
            polyMin = -b / (2*a)
            
            if polyMin > 0 and polyMin < np.max(filtAlong):
                #filtDf = pd.DataFrame({'along': filtAlong, 'elev':filtElev})
                ditch1 = filtDf[filtDf['along'] <= polyMin]
                ditch2 = filtDf[filtDf['along'] > polyMin]
                
                linreg1 = sp.stats.linregress(ditch1['along'], ditch1['elev'])
                linreg2 = sp.stats.linregress(ditch2['along'], ditch2['elev'])
            
                rsq1, rsq2 =linreg1.rvalue**2, linreg2.rvalue**2
                slope1, slope2 = linreg1.slope, linreg2.slope
                
                if rsq1 >= 0.4 and rsq2 >= 0.4:
                    distFromSplit = np.abs(filtAlong - polyMin)
                    toSplit = filtDf[distFromSplit==min(distFromSplit)].iloc[0]
                    
                    midpoint1=ditch1.iloc[len(ditch1)//2]
                    midpoint2=ditch2.iloc[len(ditch2)//2]
                    
                    x1, y1 = midpoint1['x'], midpoint1['y']
                    x2, y2 = midpoint2['x'], midpoint2['y']
                    
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
                    # find the closest original node
                    if oc1 != oc2:
                        nodesDf=pd.read_csv(nodesFile)
                        starts, ends = nodesDf.iloc[::3].reset_index(drop=True), \
                            nodesDf.iloc[2::3].reset_index(drop=True)
                        nodesDf = pd.concat((starts,ends), ignore_index=True)
                        nodesDf=nodesDf[(nodesDf['lcat']==oc1)|(nodesDf['lcat']==oc2)]
                        nodesDf.loc[:,'dist']=np.sqrt((nodesDf['x']-toSplit['x'])**2+(nodesDf['y']-toSplit['y'])**2)
                        toSplit = nodesDf[nodesDf['dist']==min(nodesDf['dist'])].iloc[0]
                    
                    # Read file with original category numbers
                    origDf = pd.read_csv(origCatFile)
                    
                    gs.run_command('v.edit', map_=vecLines7, tool='break', coords=[toSplit['x'],toSplit['y']], threshold=10)
                    
                    fid1=gs.read_command('v.edit', map_=vecLines7, tool='select', bbox=[x1-0.1,y1-0.1,x1+0.1,y1+0.1])
                    fid1 = int(fid1.split('\n')[0])
                    fid2=gs.read_command('v.edit', map_=vecLines7, tool='select', bbox=[x2-0.1,y2-0.1,x2+0.1,y2+0.1])
                    fid2 = int(fid2.split('\n')[0])
                    
                    if slope1 > 0: gs.run_command('v.edit', map_=vecLines7, tool='flip', ids=fid1)
                    if slope2 > 0: gs.run_command('v.edit', map_=vecLines7, tool='flip', ids=fid2)
                    
                    dropFids += [fid1]
                    origCats += [oc1]
                    
                    origDf.loc[(origDf['cat']==lcat), 'orig_cat'] = oc2
                    
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
                    output=culvertBuffers, distance=25)
        
if not gdb.map_exists(culvertLines, 'raster'):
    # Find segments of ditches that pass through culverts
    gs.run_command('v.overlay', ainput=vecLines8, atype='line', binput=culvertBuffers, \
                    operator='and', output=culvertLines)
        
    demBurned2, demNull = interpSurface.interpSurface(tmpFiles, hucPrefix+'_v2', \
                                                  culvertLines, 3, demBurned)
    
