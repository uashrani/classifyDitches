# -*- coding: utf-8 -*-
"""
Created on Fri Aug  1 14:28:31 2025

@author: swimm
"""

def transect(df, lcat, halfDist):
    import numpy as np
    
    profilePts = df[df['lcat']==lcat]
    
    x, y = profilePts['x'], profilePts['y']

    # Find the angle of the line perpendicular to the ditch at each point
    angles=np.arctan2(-np.diff(x),np.diff(y))
    sines=np.sin(angles)
    cosines=np.cos(angles)
    
    # Get the midpoints of all 1-m line segments
    x_ms = (x[1:].reset_index(drop=True) +x[:-1].reset_index(drop=True)) / 2
    y_ms = (y[1:].reset_index(drop=True) +y[:-1].reset_index(drop=True)) / 2
    
    trX1 = x_ms - halfDist*cosines
    trX2 = x_ms + halfDist*cosines
    trY1 = y_ms - halfDist*sines
    trY2 = y_ms + halfDist*sines
    
    return trX1, trX2, trY1, trY2, x_ms, y_ms, cosines, sines, angles

