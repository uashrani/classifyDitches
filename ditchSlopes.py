# -*- coding: utf-8 -*-
"""
Created on Tue Apr 22 09:54:26 2025

@author: swimm
"""

import pandas as pd
import numpy as np
import scipy.stats as sp
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
    
        linreg = sp.linregress(profilePts['along'], profilePts['elev'])
        
        ax[i].plot(profilePts['along'], profilePts['elev'],'gray', ls='',marker='.')
        ax[i].plot(profilePts['along'], linreg.slope * profilePts['along'] + linreg.intercept, 'k')
        
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

