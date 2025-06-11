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
hucPrefix = 'testDEM1'
ditchPrefix = 'BRR'

chainFile = tmpFiles + ditchPrefix + '_streamChains.txt'
newElevFile = tmpFiles + hucPrefix + '_elevProfile_shiftedDitches.txt'

newLine = hucPrefix + '_shiftedDitches'

#%% To be created

vecLines = hucPrefix + '_lines_final'

newChainFile = tmpFiles + ditchPrefix + '_streamChains_final.txt'

#%% Actual code   
gs.run_command('g.region', vector=newLine)

chainDf = pd.read_csv(chainFile)   
df = pd.read_csv(newElevFile)

lcats=sorted(set(df['lcat']))

newChainDf = chainDf.copy()
newChainDf['us_chain']=''
newChainDf['us_len']=''

if not gdb.map_exists(vecLines, 'vector'):
    gs.run_command('g.copy', vector=[newLine, vecLines])

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
                newChainDf.loc[lcat-1, 'chain']='[]'
                newChainDf.loc[newRoot-1, 'chain']=str(chain)
            if r2 < 0.25:
                print('Warning: Ditch ' + strpChain + ' has r2 value less than 0.25.')
                
            for (i,segment) in enumerate(chain):
                us_chain = chain[:i+1]
                us_len = sum(lens[:i+1])
                newChainDf.loc[segment-1, 'us_chain']=str(us_chain)
                newChainDf.loc[segment-1, 'us_len']=us_len          

newChainDf.to_csv(newChainFile, index=False)