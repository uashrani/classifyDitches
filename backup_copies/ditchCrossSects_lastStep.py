# -*- coding: utf-8 -*-
"""
Created on Fri Apr 25 13:50:10 2025

@author: Uma
"""

#%% Prerequisite modules, data, and folders

import grass.script as gs
import grass.grassdb.data as gdb
import pandas as pd
import numpy as np
import os

#import removeCulverts

tmpFiles = 'tempFiles2/'
hucPrefix = 'testDEM2'
ditchPrefix = 'BRR'

dem = hucPrefix

alongFile=tmpFiles + ditchPrefix + '_alongPts.txt'  

culvertDefFile = tmpFiles + ditchPrefix + '_culvertPtDefs.txt'
chainFile = tmpFiles + ditchPrefix + '_streamChains.txt'
#snapDefFile = tmpFiles + ditchPrefix + '_whereToSnap.txt'

# How far to take the profile on each side, in m
halfDist = 10   

#%% Layers/files that will be created automatically

lineDefFile = tmpFiles + 'shiftedLineDef.txt'
#tmpFiles + hucPrefix + '_shiftedLineDefs.txt'
tmpFile = tmpFiles + 'tmpProfile.txt'

# Shifted lines
definedLine = hucPrefix + '_sd_nc'
newLine = hucPrefix + '_sd'

# Stuff needed to remove culverts
# culvertBuffers = ditchPrefix + '_culvertBuffers'
# demNull = hucPrefix + '_wNulls'
# demBurned = hucPrefix + '_burned'
#%% Actual code
       
newPtsDf = pd.read_csv(tmpFiles + hucPrefix + '_newPtsDf.txt')
lcats=sorted(set(newPtsDf['lcat']))
# Now write to a file since we know how many points are in each line

chainDf = pd.read_csv(chainFile)
gs.run_command('v.edit', map_=definedLine, type_='line', tool='create', overwrite=True)

for lcat in lcats:
    if os.path.exists(lineDefFile):
        os.remove(lineDefFile)
    fLine=open(lineDefFile, 'a')
    
    linePts = newPtsDf[newPtsDf['lcat']==lcat].reset_index(drop=True)
    
    strChain = chainDf['chain'][chainDf['root']==lcat].iloc[0]
    strpChain=strChain.strip('[]')
    chain = np.array(list(map(int,strpChain.split(', '))))
    chainPos = np.where(chain==lcat)[0][0]
    if chainPos + 1 < len(chain):
        nextSeg = chain[chainPos+1]
        nextSegPts = newPtsDf[newPtsDf['lcat']==nextSeg]
        
        if len(nextSegPts) > 0:
        
            newAlong = np.sqrt((linePts['x'].iloc[-1] - nextSegPts['x'].iloc[0])**2 + \
                               (linePts['y'].iloc[-1] - nextSegPts['y'].iloc[0])**2)
            if newAlong < 10: 
                linePts = pd.concat((linePts, nextSegPts.iloc[0:1])).reset_index(drop=True)
            else:
                newAlong = np.sqrt((linePts['x'].iloc[-1] - nextSegPts['x'].iloc[-1])**2 + \
                                   (linePts['y'].iloc[-1] - nextSegPts['y'].iloc[-1])**2)
                if newAlong < 10:
                    linePts = pd.concat((linePts, nextSegPts.iloc[-1:])).reset_index(drop=True)
                else:
                    newAlong = 0
            
            linePts.loc[len(linePts)-1, 'along'] = linePts['along'].iloc[-2]+newAlong
    
    ### Fill in any start points that were in a culvert
    earlyCuls = list(linePts.index[(linePts['culvert']==1) & (linePts['along']<=10)])
    if len(earlyCuls) > 0:
        # Get the index of the first non-culvert point, edit preceding across values
        nonCuls = linePts[(linePts['culvert']==0) & (linePts['along']>10)]
        if len(nonCuls) > 0:
            earlyCuls += range(earlyCuls[-1]+1, nonCuls.index[0])
            localAcross = nonCuls['across'].iloc[0]
            linePts.loc[earlyCuls, 'across']=localAcross
        
        # These are just for the start points in a culvert
        x1s, y1s = linePts['x1'].iloc[earlyCuls], linePts['y1'].iloc[earlyCuls]
        acrosses = linePts['across'].iloc[earlyCuls]
        cosinez, sinez = linePts['cos'].iloc[earlyCuls], linePts['sin'].iloc[earlyCuls]
        
        # Update shifted x and y values
        linePts.loc[earlyCuls, 'x'] =  x1s + acrosses*cosinez
        linePts.loc[earlyCuls, 'y'] =  y1s + acrosses*sinez
        
    nPts = len(linePts)
    
    fLine.write('L  ' + str(nPts) + ' 1\n')

    for i in range(nPts):
        newX, newY = linePts['x'].iloc[i], linePts['y'].iloc[i]
        fLine.write(' ' + str(newX) + ' ' + str(newY) + '\n')
    fLine.write(' 1 ' + str(lcat))
        
    fLine.close()
        
    gs.run_command('v.edit', flags='n', map_=definedLine, tool='add', \
                   input_=lineDefFile, snap='node', threshold=10)
        
gs.run_command('v.clean', input_=definedLine, output=newLine, tool='snap', threshold=2.5)

#gs.run_command('v.edit', map_=definedLine, type_='line', tool='snap', threshold=5, cats=1-1000)
    #gs.run_command('v.clean', input_=definedLine, output=newLine, tool='snap', threshold=10)

# Later make a mega program that calls all functions, but for now do it here
#removeCulverts.removeCulverts(tmpFiles, hucPrefix, hucPrefix, \
#                             culvertBuffers, definedLine, dem, dem)
    
    