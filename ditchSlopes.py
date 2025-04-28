# -*- coding: utf-8 -*-
"""
Created on Tue Apr 22 09:54:26 2025

@author: swimm
"""

import pandas as pd
import numpy as np
import scipy as sp
import math
import matplotlib.pyplot as plt

file = 'linRegPts.txt'

df = pd.read_csv(file) 

dfWithElevs = df[np.isnan(df['elev'])==False]

lcats = sorted(set(dfWithElevs['lcat']))

fig,axs=plt.subplots(4, 4, figsize=(20, 16))
plt.subplots_adjust(wspace=0.3)
ax = axs.flat

i=0
for lcat in lcats:
    profilePts = dfWithElevs[dfWithElevs['lcat']==lcat]
    
    if profilePts['along'].iloc[-1] > 0.01:    
        elev=profilePts['elev']
        along=profilePts['along']
        
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
        
        ax[i].plot(along, elev, 'lightgray', ls='', marker='.') 
        ax[i].plot(filtAlong, filtElev,'gray', ls='',marker='.')
        ax[i].plot(along, linreg.slope * along + linreg.intercept, 'k')
        
        ax[i].set_title('Ditch ' + str(lcat))
        
        annotation='m='+str(round(linreg.slope, 6)) + \
            '\nr$^2$='+str(round(linreg.rvalue**2, 3)) + \
                    '\nm_err='+str(round(linreg.stderr,6))
      
        if linreg.slope < 0:
            xy=(.62, .75)
        else:
            xy=(.03, .75)
      
        ax[i].annotate(annotation, xy=xy, xycoords='axes fraction', fontweight='bold', \
                       bbox={'facecolor': 'wheat', 'alpha': 0.3})
    
        i+=1
        
fig, ax = plt.subplots(figsize=(10,8))
profilePts = dfWithElevs[dfWithElevs['lcat']==27]
adjustedDf = pd.read_csv('shiftedDitch27.txt')

ax.plot(profilePts['along'], profilePts['elev'], 'gray', ls='', marker='.', label='original')
ax.plot(adjustedDf['along'], adjustedDf['elev'], 'cornflowerblue', ls='', marker='.', label='adjusted')

plt.legend()

ax.set_xlabel('Along [m]')
ax.set_ylabel('Elevation [m]')
ax.set_title('Ditch 27')