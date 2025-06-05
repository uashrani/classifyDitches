# -*- coding: utf-8 -*-
"""
Created on Wed May 21 16:09:13 2025

@author: swimm
"""

#%% Prerequisites 

import pandas as pd
import scipy as sp
import numpy as np
import math
import grass.script as gs
import grass.grassdb.data as gdb

tmpFiles = 'tempFiles/'
hucPrefix = 'testDEM2'
ditchPrefix = 'BRR'

alongFile = tmpFiles + ditchPrefix + '_alongPts.txt'    # before shifting. used for determining lcats bc attribute table has xy column
chainFile = tmpFiles + ditchPrefix + '_streamChains.txt'
newElevFile = tmpFiles + hucPrefix + '_elevProfile_shiftedDitches.txt'

vecLines4 = ditchPrefix + '_lines_filtered'

#df = pd.read_csv('tempFiles/BRR_elevProfile_origDitches.txt')

# Later will be region of the HUC, get from the bounding box file
#n, s, e, w = 5217318, 5212652, 274769, 269803   # test region 1
n, s, e, w = 5202318, 5191400, 220687, 212912   # test region 2

#%% To be created

vecLines = ditchPrefix + '_lines_final'

#%% Actual code 
origDf = pd.read_csv(alongFile)    
chainDf = pd.read_csv(chainFile)   
df = pd.read_csv(newElevFile)

# Get all points whose coordinates are in the DEM region
dfInRegion = origDf[((origDf['y']>=s)&(origDf['y']<=n))&((origDf['x']>=w)&(origDf['x']<=e))]

# Temporary: also filter out the ones that are <1m 
dfInRegion = dfInRegion[dfInRegion['along']>=1]

lcats=sorted(set(dfInRegion['lcat']))

chainDf['us_chain']=''
chainDf['us_len']=''

if not gdb.map_exists(vecLines, 'vector'):
    gs.run_command('g.copy', vector=[vecLines4, vecLines])

    ### Do linear regression and flip vector directions if needed
    for lcat in lcats:
        thisDitch = df[df['lcat']==lcat]
        filtProfile = thisDitch[np.isnan(thisDitch['elev'])==False]
        
        ## Chain some lines together based on the definitions in the file
        strChain = chainDf['chain'][chainDf['root']==lcat].iloc[0]
        
        strpChain=strChain.strip('[]')
        if strpChain != '': 
            chain = list(map(int,strpChain.split(', ')))
        else:
            chain=[]
            
        if len(chain) > 0:
            lens = []
            
            # Concatenate the elevation profiles from different segments into one
            for (j,link) in enumerate(chain):
                thisDitch = df[df['lcat']==link]
                
                lens += [thisDitch['along'].iloc[-1]]
                if j==0:
                    concatDf = thisDitch.reset_index(drop=True)
                else:
                    thisDitch.loc[:, 'along']=thisDitch['along'] + concatDf['along'].iloc[-1]
                    concatDf = pd.concat((concatDf, thisDitch)).reset_index(drop=True)
                    
            filtProfile = concatDf[np.isnan(concatDf['elev'])==False]
            along, elev = filtProfile['along'], filtProfile['elev']
        
            ### Still have to filter out peaks even after culvert removal
            peakInds, props = sp.signal.find_peaks(elev, prominence=1, width=[1,250])
            
            lefts, rights = props['left_ips'], props['right_ips']
            
            allPeaks = []
            for (k, ind) in enumerate(peakInds):
                l=math.floor(lefts[k])
                r=math.ceil(rights[k])
                allPeaks += range(l, r+1)
                
            filtElev=elev.drop(elev.index[allPeaks])
            filtAlong=along.drop(along.index[allPeaks])
            
            linreg = sp.stats.linregress(filtAlong, filtElev)   
            
            r2=linreg.rvalue**2
            
            if linreg.slope > 0:
                gs.run_command('v.edit', map_=vecLines, tool='flip', cats=chain)
                chain = chain[::-1]
                newRoot = chain[0]
                chainDf.loc[lcat-1, 'chain']='[]'
                chainDf.loc[newRoot-1, 'chain']=str(chain)
            if r2 < 0.25:
                print('Warning: Ditch ' + strpChain + 'has r2 value less than 0.25.')
                
            for (i,segment) in enumerate(chain):
                us_chain = chain[:i+1]
                us_len = sum(lens[:i+1])
                chainDf.loc[segment-1, 'us_chain']=str(us_chain)
                chainDf.loc[segment-1, 'us_len']=us_len          

chainDf.to_csv(chainFile, index=False)