# -*- coding: utf-8 -*-
"""
Created on Wed May 21 16:09:13 2025

@author: swimm
"""

import pandas as pd
import matplotlib.pyplot as plt
import scipy as sp
import numpy as np
import math

df = pd.read_csv('tempFiles/testDEM1_elevProfile_shiftedDitches.txt')
#df = pd.read_csv('tempFiles/BRR_elevProfile_origDitches.txt')

fig,axs=plt.subplots(3, 4, figsize=(18, 10))
plt.subplots_adjust(hspace=0.3)
ax = axs.flat

lcats=[73, 238, 298, 1097, 1099, 2680]
#lcats=[27, 36, 37, 206, 267, 296, 314, 376, 407, 408, 663, 2242]

for (i,lcat) in enumerate(lcats):
    thisDitch = df[df['lcat']==lcat]
    filtDitch = thisDitch[np.isnan(thisDitch['elev'])==False]
    along, elev = filtDitch['along'], filtDitch['elev']
    
    ### Still have to filter out peaks even after culvert removal
    peakInds, props = sp.signal.find_peaks(elev, prominence=1, width=[1,250])
    
    lefts, rights = props['left_ips'], props['right_ips']
    
    allPeaks = []
    for (j, ind) in enumerate(peakInds):
        l=math.floor(lefts[j])
        r=math.ceil(rights[j])
        allPeaks += range(l, r+1)
        
    filtElev=elev.drop(elev.index[allPeaks])
    filtAlong=along.drop(along.index[allPeaks])
    
    linreg = sp.stats.linregress(filtAlong, filtElev)   
    
    ax[i].plot(along, elev, 'lightsteelblue', ls='', marker='.') 
    ax[i].plot(filtAlong, filtElev, 'xkcd:purplish brown', ls='', marker='.') 
    ax[i].plot(along, linreg.slope * along + linreg.intercept, 'k')
    
    ax[i].set_title('Ditch ' + str(lcat))
    
    annotation='m='+str(round(linreg.slope, 6)) + \
        '\nr$^2$='+str(round(linreg.rvalue**2, 3))
        
    if linreg.slope < 0:
        xy=(.62, .78) 
    else:
        xy=(.03, .78)
        
    ax[i].annotate(annotation, xy=xy, xycoords='axes fraction', fontweight='bold', \
                   bbox={'facecolor': 'xkcd:light mint green', 'alpha': 0.3})
        
        
ax[0].annotate('Along [m]', xy=(0.45, 0.03), xycoords='figure fraction', \
               fontweight='bold', fontsize=15)
ax[0].annotate('Elevation [m]', xy=(0.04, 0.4), xycoords='figure fraction', \
               fontweight='bold', fontsize=15, rotation=90)
fig.suptitle('Ditch Segment Long-Profiles (Shifted Ditches)', y=0.96, fontweight='bold', fontsize=16)        



