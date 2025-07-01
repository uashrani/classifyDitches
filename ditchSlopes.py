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

tmpFiles = 'tempFiles/'
hucPrefix = 'testDEM3'
ditchPrefix = 'BRR'

chainFile = tmpFiles + ditchPrefix + '_streamChains.txt'
newElevFile = tmpFiles + hucPrefix + '_elevProfile_shiftedDitches.txt'

newLine = hucPrefix + '_shiftedDitches'

#%% To be created
vecLines = hucPrefix + '_lines_final'

culvertDefFile = tmpFiles + hucPrefix + '_culvertPtDefs.txt'   # file that GRASS will read from 

culvertPts = hucPrefix + '_culvertPoints'   # points layer of culvert locations
culvertBuffers = hucPrefix + '_culvertBuffers'  # vector layer containing circles around the culvert points

#%% Actual code   
gs.run_command('g.region', vector=newLine)

chainDf = pd.read_csv(chainFile)   
df = pd.read_csv(newElevFile)

lcats=sorted(set(df['lcat']))

unmappedCulverts = pd.DataFrame({'x': [], 'y': []})

newChainDf = chainDf.copy()

if not gdb.map_exists(vecLines, 'vector'):
    gs.run_command('g.copy', vector=[newLine, vecLines])

    ### Do linear regression and flip vector directions if needed
    for lcat in lcats:
        chain=[lcat]
        
        # temporary
        if lcat == 259: continue
    
        thisDitch = df[df['lcat']==lcat]
        filtProfile = thisDitch[np.isnan(thisDitch['elev'])==False]
        along, elev = filtProfile['along'], filtProfile['elev']
        
        # Try linear regression with just a single ditch segment first
        linreg = sp.stats.linregress(along, elev)  
        r2=linreg.rvalue**2
        
        # Concatenate segments for linreg if r2 is too low
        if r2 < 0.4: 
            ## Chain some lines together based on the definitions in the file
            strChain = chainDf['chain'][chainDf['root']==lcat].iloc[0]
            strpChain=strChain.strip('[]')
            chain = list(map(int,strpChain.split(', ')))
            
            print('Ditch ' + str(lcat) + ' has r2 value less than 0.4. Concatenating with ' + \
                  strpChain)
                
            for (j, segment) in enumerate(chain):
                thisDitch = df[df['lcat']==segment]
                if j==0:
                    concatDf = thisDitch.reset_index(drop=True)
                else:
                    if len(concatDf) > 0: thisDitch.loc[:, 'along']=thisDitch['along'] + concatDf['along'].iloc[-1]
                    concatDf = pd.concat((concatDf, thisDitch)).reset_index(drop=True)
                    
            filtProfile = concatDf[np.isnan(concatDf['elev'])==False]
            along, elev = filtProfile['along'], filtProfile['elev']
            
            linreg = sp.stats.linregress(along, elev)
            r2 = linreg.rvalue**2
            
        x, y = filtProfile['x'], filtProfile['y']
        linElev = linreg.slope * along + linreg.intercept  
        
        # Calculate the absolute value of error 
        absErr = np.absolute(elev - linElev)
        rmse = np.sqrt(np.mean((elev - linElev)**2))
        prom=min([1,rmse*4])
        
        # scipy find_peaks doesn't catch peaks at the endpoints
        # Check where slope is different from rest of profile?
        ditchSlope = np.diff(elev) / np.diff(along)
        start25, end25 = np.where(along>25)[0][0], np.where(along+25<along.iloc[-1])[0][-1]
        
        startSlope = (elev.iloc[start25] - elev.iloc[0]) / (along.iloc[start25] - along.iloc[0])
        endSlope = (elev.iloc[-1] - elev.iloc[end25]) / (along.iloc[-1] - along.iloc[end25])
        
        peakIndsEP = []
        if (np.abs(startSlope) > np.abs(linreg.slope) * 20) and np.max((elev-linElev).iloc[:start25]) > prom:
            peakIndsEP += [0] 
        if np.abs(endSlope) > np.abs(linreg.slope) * 20 and np.max((elev-linElev).iloc[end25:]) > prom:
            peakIndsEP += [len(along)-1]
                
        peakInds, props = sp.signal.find_peaks(elev, prominence=prom, width=[1,50])
            
        allPeaks = pd.concat((pd.Series(peakInds), pd.Series(peakIndsEP))).reset_index(drop=True)
        for ind in allPeaks:
            unmappedCulverts = pd.concat((unmappedCulverts, \
                                          pd.DataFrame({'x': [x.iloc[ind]], 'y': [y.iloc[ind]]})))
            
        if linreg.slope > 0:
            gs.run_command('v.edit', map_=vecLines, tool='flip', cats=lcat)
            chain = chain[::-1]
            newRoot = chain[0]
            #newChainDf.loc[lcat-1, 'chain']='[]'
            newChainDf.loc[lcat-1, 'chain']=str(chain)
        if r2 < 0.4:
            print('Warning: Ditch ' + str(lcat) + ' still has r2 < 0.4 even after concatenating profiles.')
                
            # for (i,segment) in enumerate(chain):
            #     us_chain = chain[:i+1]
            #     us_len = sum(lens[:i+1])
            #     newChainDf.loc[segment-1, 'us_chain']=str(us_chain)
            #     newChainDf.loc[segment-1, 'us_len']=us_len          

newChainDf.to_csv(chainFile, index=False)
unmappedCulverts.to_csv(culvertDefFile, index=False, header=False)

# Create points layer with unmapped culvert locations
gs.run_command('v.in.ascii', input_=culvertDefFile, output=culvertPts, \
               separator='comma', columns=['x double precision', 'y double precision'])
    
# Buffer the culvert points
gs.run_command('v.buffer', input_=culvertPts, type_='point', \
                output=culvertBuffers, distance=25)