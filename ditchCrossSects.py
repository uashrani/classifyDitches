# -*- coding: utf-8 -*-
"""
Created on Fri Apr 25 13:50:10 2025

@author: swimm
"""

import pandas as pd
import numpy as np
import grass.script as gs

file = 'linRegPts.txt'

dem='ambigDEM2'

df = pd.read_csv(file) 

dfWithElevs = df[np.isnan(df['elev'])==False]

lcats = sorted(set(dfWithElevs['lcat']))

lcats=[27]

for lcat in lcats:
    profilePts = dfWithElevs[dfWithElevs['lcat']==lcat]
    x, y = profilePts['x'], profilePts['y']
    
    tangentSlopes=np.diff(x) / np.diff(y)  
    normalSlopes = - 1 / tangentSlopes
    
    # we just calculated the normal line's y/x change, aka the tangent
    # which angle is associated with this tangent?
    angles=np.arctan(normalSlopes)
    sines=np.sin(angles)
    cosines=np.cos(angles)
    
    # How far to take the profile on each side, in m
    halfDist = 20
    
    # Get the midpoints of all 1-m line segments
    x_m = (x[1:].reset_index(drop=True) +x[:-1].reset_index(drop=True)) / 2
    y_m = (y[1:].reset_index(drop=True) +y[:-1].reset_index(drop=True)) / 2
    
    trX1 = x_m - halfDist*cosines
    trX2 = x_m + halfDist*cosines
    trY1 = y_m - halfDist*sines
    trY2 = y_m + halfDist*sines
    
    # Get profile across these endpoints
    for i in range(5): #len(trX1)):
        gs.run_command('r.profile', input_=dem, output='tmpProfile.txt', \
                       coordinates=[trX1.iloc[i],trY1.iloc[i],trX2.iloc[i],trY2.iloc[i]])
    
    
    
    
    