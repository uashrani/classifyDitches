# -*- coding: utf-8 -*-
"""
Created on Tue Apr 22 09:54:26 2025

@author: swimm
"""

import pandas as pd
import numpy as np
import scipy as sp
import grass.script as gs
import math
import matplotlib.pyplot as plt

file = 'linRegPts.txt'

df = pd.read_csv(file) 
df['elev']=df['elev'] / 100

dfWithElevs = df[np.isnan(df['elev'])==False]

lcats = sorted(set(dfWithElevs['lcat']))
#lcats = [35, 42, 126, 148, 631, 632]

fig,axs=plt.subplots(2, 3, figsize=(14, 6))
plt.subplots_adjust(hspace=0.3)
ax = axs.flat

i=0
for lcat in lcats:
    profilePts = dfWithElevs[dfWithElevs['lcat']==lcat]
    
    if profilePts['along'].iloc[-1] > .1:    
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
        
        # ax[i].plot(along, elev, 'lightsteelblue', ls='', marker='.') 
        # ax[i].plot(filtAlong, filtElev,'xkcd:purplish brown', ls='',marker='.')
        # ax[i].plot(along, linreg.slope * along + linreg.intercept, 'k')
        
        # ax[i].set_title('Ditch ' + str(lcat))
        
        annotation='m='+str(round(linreg.slope, 6)) + \
            '\nr$^2$='+str(round(linreg.rvalue**2, 3)) # + \
                #    '\nm_err='+str(round(linreg.stderr,6))
      
        if linreg.slope < 0:
            xy=(.62, .78) 
        else:
            xy=(.03, .78) # Changes plot display
            # CHANGE IN FINAL VERSION
            gs.run_command('v.edit', map_='ditch_lines_renamed', tool='flip', cats=lcat)
      
        #ax[i].annotate(annotation, xy=xy, xycoords='axes fraction', fontweight='bold', \
        #               bbox={'facecolor': 'xkcd:light mint green', 'alpha': 0.3})
    
        i+=1
        
#ax[0].annotate('Along [m]', xy=(0.45, 0.03), xycoords='figure fraction', \
               #fontweight='bold', fontsize=15)
#ax[0].annotate('Elevation [m]', xy=(0.04, 0.4), xycoords='figure fraction', \
               #fontweight='bold', fontsize=15, rotation=90)
#fig.suptitle('Ditch Segment Long-Profiles', y=0.96, fontweight='bold', fontsize=16)        





# fig, ax = plt.subplots(figsize=(10,8))
# profilePts = dfWithElevs[dfWithElevs['lcat']==27]
# adjustedDf = pd.read_csv('shiftedDitch27.txt')

# ax.plot(profilePts['along'], profilePts['elev'], 'gray', ls='', marker='.', label='original')
# ax.plot(adjustedDf['along'], adjustedDf['elev'], 'cornflowerblue', ls='', marker='.', label='adjusted')

# plt.legend()

# ax.set_xlabel('Along [m]')
# ax.set_ylabel('Elevation [m]')
# ax.set_title('Ditch 27')