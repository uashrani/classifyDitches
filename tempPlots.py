# -*- coding: utf-8 -*-
"""
Created on Wed May 21 16:09:13 2025

@author: swimm
"""

import pandas as pd
import matplotlib.pyplot as plt
import scipy as sp
import numpy as np

df = pd.read_csv('tempFiles/elevProfile_421shifted.txt')

fig,axs=plt.subplots(3, 4, figsize=(18, 10))
plt.subplots_adjust(hspace=0.3)
ax = axs.flat

lcats=[27, 36, 37, 251, 274, 414, 415, 420, 421, 428, 467, 564]
lcats=[421]

for (i,lcat) in enumerate(lcats):
    thisDitch = df[df['lcat']==lcat]
    filtDitch = thisDitch[np.isnan(thisDitch['elev'])==False]
    along, elev = filtDitch['along'], filtDitch['elev']
    
    linreg = sp.stats.linregress(along, elev) 

    ax[i].plot(along, elev, 'xkcd:purplish brown', ls='', marker='.') 
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
        
    if lcat==421:
        print(linreg)
        
ax[0].annotate('Along [m]', xy=(0.45, 0.03), xycoords='figure fraction', \
               fontweight='bold', fontsize=15)
ax[0].annotate('Elevation [m]', xy=(0.04, 0.4), xycoords='figure fraction', \
               fontweight='bold', fontsize=15, rotation=90)
fig.suptitle('Ditch Segment Long-Profiles', y=0.96, fontweight='bold', fontsize=16)        



