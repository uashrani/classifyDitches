# -*- coding: utf-8 -*-
"""
Created on Wed May 21 16:09:13 2025

@author: swimm
"""

#%% Prerequisites 

import pandas as pd
import matplotlib.pyplot as plt
import scipy as sp
import numpy as np
import math

tmpFiles = 'tempFiles/'
hucPrefix = 'testDEM1'
ditchPrefix = 'BRR'

chainFile = tmpFiles + ditchPrefix + '_streamChains.txt'
newElevFile = tmpFiles + hucPrefix + '_elevProfile_shiftedDitches.txt'

newLine = hucPrefix + '_shiftedDitches'

#%% Actual code 
chainDf = pd.read_csv(chainFile)   
df = pd.read_csv(newElevFile)

lcats=sorted(set(df['lcat']))

### Make plots and do linear regression

fig,axs=plt.subplots(3, 3, figsize=(18, 10))
plt.subplots_adjust(hspace=0.3)
ax = axs.flat

i=0
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
        # Concatenate the elevation profiles from different segments into one
        for (j,link) in enumerate(chain):
            thisDitch = df[df['lcat']==link]
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
        
        ax[i].plot(along, elev, 'lightsteelblue', ls='', marker='.') 
        ax[i].plot(filtAlong, filtElev, 'xkcd:purplish brown', ls='', marker='.') 
        ax[i].plot(along, linreg.slope * along + linreg.intercept, 'k')
        
        ax[i].set_title('Ditch ' + str(strpChain))
        
        annotation='m='+str(round(linreg.slope, 6)) + \
            '\nr$^2$='+str(round(linreg.rvalue**2, 3))
            
        if linreg.slope < 0:
            xy=(.62, .78) 
        else:
            xy=(.03, .78)
            
        ax[i].annotate(annotation, xy=xy, xycoords='axes fraction', fontweight='bold', \
                       bbox={'facecolor': 'xkcd:light mint green', 'alpha': 0.3})
            
        i += 1    
        
ax[0].annotate('Along [m]', xy=(0.45, 0.03), xycoords='figure fraction', \
               fontweight='bold', fontsize=15)
ax[0].annotate('Elevation [m]', xy=(0.04, 0.4), xycoords='figure fraction', \
               fontweight='bold', fontsize=15, rotation=90)
fig.suptitle('Ditch Segment Long-Profiles (Shifted Ditches)', y=0.96, fontweight='bold', fontsize=16)        



