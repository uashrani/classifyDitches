# -*- coding: utf-8 -*-
"""
Created on Fri Aug  1 15:00:51 2025

@author: swimm
"""

import grass.script as gs
import grass.grassdb.data as gdb
import pandas as pd
import os

import transect

tmpFiles = 'tempFiles/'
hucPrefix = 'testDEM3'
ditchPrefix='BRR'

# This is just to tell us what lcats are in the region
newElevFile = tmpFiles + hucPrefix + '_elevProfile_shiftedDitches.txt'
vecLines = hucPrefix + '_lines_final'

toFill = [245,246]

#%% To be created
transectFile = tmpFiles + hucPrefix + '_downstreamTransects.txt'
dsPoints = hucPrefix + '_downstreamPts'
dsFile = tmpFiles + dsPoints + '.txt'
dsTransects = hucPrefix + '_downstreamTransects'

dsBuffers = hucPrefix + '_downstreamBuffers'

#%% 
### Create transects near downstream ends of ditches for infilling location
if not gdb.map_exists(dsPoints, 'vector'):
    p = pd.read_csv(newElevFile)
    lcats=sorted(set(p['lcat']))
    
    f=open(transectFile, 'a')
    ptID = 1
    for lcat in lcats:
        # Start with two points along the line, and get slope between them
        fillLoc = -50
        for dsLen in [fillLoc+0.5, fillLoc-0.5]:
            f.write('P ' + str(ptID) + ' ' + str(lcat) + ' ' + str(dsLen) + '\n')
            ptID += 1
    f.close()
    
    gs.run_command('v.segment', input_=vecLines, output=dsPoints, rules=transectFile)
    gs.run_command('v.db.addtable', map_=dsPoints)
    
    gs.run_command('v.db.addcolumn', map_=dsPoints, columns='lcat int')
    gs.run_command('v.what.vect', map_=dsPoints, column='lcat', query_map=vecLines, \
                   query_column='cat', dmax=0.01)
    gs.run_command('v.to.db', map_=dsPoints, option='coor', columns=['x', 'y'])
    gs.run_command('v.db.select', map_=dsPoints, format_='csv', file=dsFile, overwrite=True)

dsDf = pd.read_csv(dsFile)
lcats=sorted(set(dsDf['lcat']))

if not gdb.map_exists(dsTransects, 'vector'):
    os.remove(transectFile)
    f=open(transectFile, 'a')
    
    for lcat in lcats:
        x1,x2,y1,y2,f1,f2,f3,f4 = transect.transect(dsDf, lcat, 15)
        x1=x1.iloc[0]; x2=x2.iloc[0]; y1=y1.iloc[0]; y2=y2.iloc[0]
        
        f.write('L  2 1\n')
        f.write(' ' + str(x1) + ' ' + str(y1) + '\n')
        f.write(' ' + str(x2) + ' ' + str(y2) + '\n')
        f.write(' 1 ' + str(lcat))
        if lcat != lcats[-1]:
            f.write('\n')
        
    f.close()
    gs.run_command('v.edit', map_=dsTransects, type_='line', tool='create', overwrite=True)
    gs.run_command('v.edit', flags='n', map_=dsTransects, tool='add', \
                   input_=transectFile)

# Create a new layer that buffers the transects only for the selected ditches
gs.run_command('v.buffer', flags='c', input_=dsTransects, cats=toFill, type_='line', \
               output=dsBuffers, distance=10)
    

        

        
