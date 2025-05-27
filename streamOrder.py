# -*- coding: utf-8 -*-
"""
Created on Sun May  4 20:48:37 2025

@author: Uma
"""

import pandas as pd
import networkx as nx
import numpy as np
import grass.script as gs

combFile = 'ditchCombinations.txt'
startFile = 'ditchStartPts.txt'
endFile = 'ditchEndPts.txt'
linesFile = 'ditchLines.txt'

ditchCombs = pd.read_csv(combFile)
ditchStarts = pd.read_csv(startFile)
ditchEnds = pd.read_csv(endFile)

ditchCombs = ditchCombs.rename(columns={'from_cat': 'fromPt', 'cat': 'toPt'})

def findOrder(lcat, ditchLines):
    order = ditchLines.loc[ditchLines['cat']==lcat, 'order'].iloc[0]
    
    if order > 0:
        return(order, ditchLines)
    else:
        parents = list(graph.predecessors(lcat))
        parentOrders = []
        for parent in parents:
            if parent in list(ditchLines['cat']):
                parentOrder, ditchLines = findOrder(parent, ditchLines)
            
                parentOrders += [parentOrder]            
            
        parentOrders = pd.Series(parentOrders)
        
        # Get the max stream order of the parents 
        maxOrder = max(parentOrders)
        nmax = len(parentOrders[parentOrders==maxOrder])
        
        if nmax > 1:
            order = maxOrder + 1 
        else:
            order = maxOrder
        
        ditchLines.loc[ditchLines['cat']==lcat, 'order'] = order
        
        return(order, ditchLines)

### In ditch combinations csv, find associated line for each point
### and determine flow direction between ditches

ditchCombs['fromLine']=0
ditchCombs['toLine']=0

for i in range(len(ditchCombs)):
    # Read the current row in the "combinations" table
    combEntry = ditchCombs.iloc[i]
    fromPt, toPt = combEntry['fromPt'], combEntry['toPt']
    
    # Find the corresponding rows in the point attribute tables
    # Remember: 'from' is downstream, 'to' is upstream
    fromEntry = ditchEnds[ditchEnds['cat']==fromPt].iloc[0]
    toEntry = ditchStarts[ditchStarts['cat']==toPt].iloc[0]
    
    # Get line numbers associated with points
    fromLine, toLine = fromEntry['lcat'], toEntry['lcat']

    if fromLine != toLine: 
        ditchCombs.loc[i, 'fromLine'] = fromLine
        ditchCombs.loc[i, 'toLine'] = toLine
        
# Go through all lines for upstream neighbors & stream order
ditchLines = pd.read_csv(linesFile)
ditchLines = ditchLines[ditchLines['len'] >= 1].reset_index(drop=True)

ditchLines['parents']=''
ditchLines['order']=0

graph = nx.from_pandas_edgelist(ditchCombs, source='fromLine', target='toLine', create_using=nx.DiGraph)

# First pass: note parents of each ditch
for i in range(len(ditchLines)):
    lcat = ditchLines['cat'].iloc[i]
    
    # Find upstream neighbors/parents
    if graph.has_node(lcat):
        parents = str(list(graph.predecessors(lcat)))
    else:
        parents = '[]'
    
    ditchLines.loc[i, 'parents'] = parents
    
ditchLines.loc[ditchLines['parents'] == '[]', 'order'] = 1

file = 'linRegPts.txt'

df = pd.read_csv(file) 
df['elev']=df['elev'] / 100

dfWithElevs = df[np.isnan(df['elev'])==False]

lcats = sorted(set(dfWithElevs['lcat']))

#gs.run_command('v.edit', map_='order1', type_='line', tool='create', overwrite=True)
#gs.run_command('v.edit', map_='order2', type_='line', tool='create', overwrite=True)
gs.run_command('v.db.addcolumn', map_='ditch_lines_renamed', columns='order int')

for lcat in lcats:
    print(lcat)
    
    if lcat in list(ditchLines['cat']):
        order, ditchLines = findOrder(lcat, ditchLines)
            
        if order==1:
            gs.run_command('v.edit', map_='order1', tool='copy', bgmap='ditch_lines_renamed', cat=lcat, overwrite=True)
        if order==2: 
            gs.run_command('v.edit', map_='order2', tool='copy', bgmap='ditch_lines_renamed', cat=lcat, overwrite=True)
    
        #gs.run_command('v.db.update', map_='ditch_lines_renamed', column='order', value=order, where="cat="+str(lcat))

#ditchCombs.to_csv('final_' + combFile, index=False, sep='\t', float_format='%.3f')
