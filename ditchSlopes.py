# -*- coding: utf-8 -*-
"""
Created on Tue Apr 22 09:54:26 2025

@author: swimm
"""

import pandas as pd
import numpy as np
import scipy as sp
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
        
        # last try: derivatives
        deriv = np.diff(elev) / np.diff(along)
        
        # Outlier analysis
        avg, std =np.mean(deriv), np.std(deriv)
        zOutliers = [avg - 3*std, avg + 3*std]
        locOutliers = np.where((deriv < zOutliers[0]) | (deriv > zOutliers[1]))
        
        
        # for z in zOutliers:
        #     ax[i].plot(along, [z]*len(along), 'k', ls='dashed')
        # for z in iqrOutliers:
        #     ax[i].plot(along, [z]*len(along), 'gold', ls='dashed')
        
        # scipy outlier analysis
        #peakInds, props = sp.signal.find_peaks(elev, width=[10,250])
        #print(props)
        
        ### 
        # Plot derivative
        ax2 = ax[i].twinx()
        #ax2.plot(along[1:], deriv, 'lightgray')
        
        linreg = sp.stats.linregress(along, elev)
        
        ax[i].plot(along, elev,'gray', ls='',marker='.')
        ax[i].plot(along, linreg.slope * along + linreg.intercept, 'k')
        ax[i].plot(along.iloc[locOutliers], elev.iloc[locOutliers], 'r', ls='', marker='x', markersize=5)
        
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

