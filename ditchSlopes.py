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
ax = axs.flat

i=0
for lcat in lcats:
    profilePts = dfWithElevs[dfWithElevs['lcat']==lcat]
    
    if profilePts['along'].iloc[-1] > 0.01:
        
        elev=profilePts['elev']
        along=profilePts['along']
        
        # Outlier analysis
        # avg, std =np.mean(elev), np.std(elev)
        # zOutliers = [avg + 3*std, avg - 3*std]
        
        # q1, q3=np.percentile(elev, 25), np.percentile(elev,75)
        # iqr=q3-q1
        # iqrOutliers=[q1-1.5*iqr,q3+1.5*iqr]
        
        # for z in zOutliers:
        #     ax[i].plot(along, [z]*len(along), 'k', ls='dashed')
        # for z in iqrOutliers:
        #     ax[i].plot(along, [z]*len(along), 'gold', ls='dashed')
        
        # scipy outlier analysis
        #peakInds, props = sp.signal.find_peaks(elev, width=[10,250])
        #print(props)
        
        ### 
        linreg = sp.stats.linregress(along, elev)
        
        ax[i].plot(along, elev,'gray', ls='',marker='.')
        ax[i].plot(along, linreg.slope * along + linreg.intercept, 'k')
        ax[i].plot(along.iloc[peakInds], elev.iloc[peakInds], 'r', ls='', marker='x')
        
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

