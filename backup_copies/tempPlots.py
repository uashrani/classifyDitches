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
hucPrefix = 'HUC_0902010402'
ditchPrefix = 'BRR'

chainFile = tmpFiles + ditchPrefix + '_streamChains.txt'
newElevFile = tmpFiles + hucPrefix + '_elevProfile_shiftedDitches.txt'

newLine = hucPrefix + '_shiftedDitches'

#%% Actual code 
chainDf = pd.read_csv(chainFile)   
df = pd.read_csv(newElevFile)

lcats=sorted(set(df['lcat']))

unmappedCulverts = pd.DataFrame({'x': [], 'y': []})

### Make plots and do linear regression
fig,ax=plt.subplots(figsize=(9,6)) #6, 6, figsize=(20, 14))
#plt.subplots_adjust(hspace=0.3)
#ax = axs.flat

i=0
for lcat in [53]: #lcats: #[32:48]:
    #if lcat==259: continue
    
    strpChain = ''
    
    thisDitch = df[(df['lcat']==lcat) & (np.isnan(df['elev'])==False)]
    filtProfile = thisDitch[np.isnan(thisDitch['elev'])==False]
    along, elev = filtProfile['along'], filtProfile['elev']
    
    # Try linear regression with just a single ditch segment,
    if len(along) >= 2:
        linreg = sp.stats.linregress(along, elev)  
        r2=linreg.rvalue**2
    
    # Concatenate segments for linreg if r2 is too low
    if len(along) < 2 or r2 < 0.4:
        ## Chain some lines together based on the definitions in the file
        strChain = chainDf['chain'][chainDf['root']==lcat].iloc[0]
        strpChain=strChain.strip('[]')
        chain = list(map(int,strpChain.split(', ')))
            
        for (j, segment) in enumerate(chain):
            thisDitch = df[df['lcat']==segment]
            if j==0:
                concatDf = thisDitch.reset_index(drop=True)
            else:
                if len(concatDf) > 0: thisDitch.loc[:, 'along']=thisDitch['along'] + concatDf['along'].iloc[-1]
                concatDf = pd.concat((concatDf, thisDitch)).reset_index(drop=True)
                
        filtProfile = concatDf[np.isnan(concatDf['elev'])==False]
        along, elev = filtProfile['along'], filtProfile['elev']
        
        # if len(along) == 0:
        #     continue
        linreg = sp.stats.linregress(along, elev)
        
    x, y = filtProfile['x'], filtProfile['y']
    linElev = linreg.slope * along + linreg.intercept
    
    # Calculate the absolute value of error 
    absErr = np.absolute(elev - linElev)
    rmse = np.sqrt(np.mean((elev - linElev)**2))
    prom=min([1,rmse*4])
    
    # scipy find_peaks doesn't catch peaks at the endpoints
    # Check where slope is different from rest of profile?
    ditchSlope = np.diff(elev) / np.diff(along)
    peakIndsEP = []
    
    if np.max(along) > 50:
        start25, end25 = np.where(along>25)[0][0], np.where(along+25<along.iloc[-1])[0][-1]
        startSlope = (elev.iloc[start25] - elev.iloc[0]) / (along.iloc[start25] - along.iloc[0])
        endSlope = (elev.iloc[-1] - elev.iloc[end25]) / (along.iloc[-1] - along.iloc[end25])
    
    
        if (np.abs(startSlope) > np.abs(linreg.slope) * 20) and np.max((elev-linElev).iloc[:start25]) > prom:
            peakIndsEP += [0] 
            unmappedCulverts = pd.concat((unmappedCulverts, \
                                          pd.DataFrame({'x': [x.iloc[0]], 'y': [y.iloc[0]]})))
                                         
        if np.abs(endSlope) > np.abs(linreg.slope) * 20 and np.max((elev-linElev).iloc[end25:]) > prom:
            lastInd = len(along)-1
            peakIndsEP += [len(along)-1]
            unmappedCulverts = pd.concat((unmappedCulverts, \
                                          pd.DataFrame({'x': [x.iloc[lastInd]], 'y': [y.iloc[lastInd]]})))
    
    #peakIndsEP = np.where((np.abs(ditchSlope) > 3*np.abs(linreg.slope)) & ((truncAlong < 25) | (truncAlong + 25 > along.iloc[-1])))
    
    ### Still have to filter out culverts from unmapped roads, etc.
    peakInds, props = sp.signal.find_peaks(elev, prominence=prom, width=[1,50])
        
    lefts, rights = props['left_ips'], props['right_ips']
        
    allPeaks = []
    for (k, ind) in enumerate(peakInds):
        l=math.floor(lefts[k])
        r=math.ceil(rights[k])
        allPeaks += range(l, r+1)
        unmappedCulverts = pd.concat((unmappedCulverts, \
                                      pd.DataFrame({'x': [x.iloc[ind]], 'y': [y.iloc[ind]]})))
        
    filtElev=elev.drop(elev.index[allPeaks])
    filtAlong=along.drop(along.index[allPeaks])
    
    linreg = sp.stats.linregress(filtAlong, filtElev)
    r2 = linreg.rvalue**2
    
    if r2 < 0.4:
        # Maybe this line should be two lines with opposite flow directions
        a,b,c = np.polyfit(filtAlong,filtElev,2)
        polyMin = -b / (2*a)
        
        # Check if splitting actually makes it better
        if polyMin > 0 and polyMin < np.max(filtAlong):
            filtDf = pd.DataFrame({'along': filtAlong, 'elev':filtElev})
            ditch1 = filtDf[filtDf['along'] <= polyMin]
            ditch2 = filtDf[filtDf['along'] > polyMin]
            
            linreg1 = sp.stats.linregress(ditch1['along'], ditch1['elev'])
            linreg2 = sp.stats.linregress(ditch2['along'], ditch2['elev'])
        
            rsq1=linreg1.rvalue**2
            rsq2=linreg2.rvalue**2
            
            print(lcat,rsq1,rsq2)
        
        
    #print(lcat,polyfit)
    
    #ax[i].plot(filtAlong.iloc[:-1], deriv, 'darkgray', ls='', marker='.')
    
    #ax[i].plot(filtAlong, [0]*len(filtAlong))
        
    # ax[i].plot(filtAlong.iloc[:-1], deriv, 'darkgray', ls='', marker='.')
    # ax[i].plot(filtAlong, 10*derivReg.slope*filtAlong+derivReg.intercept, 'k')
    # ax[i].plot(filtAlong, [0]*len(filtAlong))
    ax.plot(along, elev, 'lightsteelblue', ls='', marker='.') 
    ax.plot(filtAlong, filtElev, 'xkcd:purplish brown', ls='', marker='.') 
    # ax[i].plot(along, linElev, 'k')
    # ax[i].plot(along.iloc[peakIndsEP], elev.iloc[peakIndsEP], 'r', ls='', marker='x', markersize=10, mew=4)
    
    # ax[i].plot(filtAlong, a*filtAlong**2+b*filtAlong+c, 'k')
    # ax[i].plot([polyMin,polyMin],[np.min(filtElev),np.max(filtElev)])
    
    # deriv = np.diff(filtElev) / np.diff(filtAlong)
    # derivReg = sp.stats.linregress(filtAlong[:-1], deriv)
    
    # xIntercept = -derivReg.intercept/derivReg.slope
    
    # ax[i].plot([xIntercept,xIntercept], [np.min(filtElev),np.max(filtElev)])
        
    ax.set_title('Ditch ' + str(lcat)) # + ' (' + strpChain + ')')
    
    annotation='m='+str(round(linreg.slope, 6)) + \
        '\nr$^2$='+str(round(linreg.rvalue**2, 3))
        
    if linreg.slope < 0:
        xy=(.62, .78) 
    else:
        xy=(.03, .78)
        
    #ax.annotate(annotation, xy=xy, xycoords='axes fraction', fontweight='bold', \
    #               bbox={'facecolor': 'xkcd:light mint green', 'alpha': 0.3})
        
    i += 1    
        
ax.annotate('Along [m]', xy=(0.45, 0.03), xycoords='figure fraction', \
               fontweight='bold', fontsize=15)
ax.annotate('Elevation [m]', xy=(0.04, 0.4), xycoords='figure fraction', \
               fontweight='bold', fontsize=15, rotation=90)
fig.suptitle('Ditch Segment Long-Profiles (Shifted Ditches)', y=0.96, fontweight='bold', fontsize=16)        



