# -*- coding: utf-8 -*-
"""
Created on Sun May  4 20:48:37 2025

@author: Uma
"""
import grass.script as gs
import grass.grassdb.data as gdb
import pandas as pd
import networkx as nx
import numpy as np

tmpFiles = 'tempFiles/'
hucPrefix = 'HUC_0902010603'
ditchPrefix='BRR'

vecLines = hucPrefix + '_lines_final'
chainFile = tmpFiles + ditchPrefix + '_streamChains.txt'

#%% To be created

startNodes = hucPrefix + '_starts'
endNodes = hucPrefix + '_ends'

connectTable = hucPrefix + '_flowConnections'
duplicTable = hucPrefix + '_duplicateStarts'
connectFile=tmpFiles + 'mergeLines.txt'
duplicFile=tmpFiles + 'maybeDuplicates.txt'

sparseProfilePts = hucPrefix + '_sparseProfile'
sparseFile = tmpFiles + hucPrefix + '_sparsePts.txt'

linesFile = 'ditchLines.txt'

#%% 

def findOrder(lcat, ditchLines):
    thisRow = ditchLines[ditchLines['cat']==lcat].iloc[0]
    order = thisRow['order']
    strParents = thisRow['parents']
    strpParents=strParents.strip('[]')
    if strpParents != '': 
        parents = list(map(int,strpParents.split(', ')))
    else:
        parents=[]
    
    if order > 0:
        return(order, ditchLines)
    else:
        parentOrders = []
        for parent in parents:
            #if parent in list(ditchLines['cat']):
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

#%%  Create new start and end point layers from correct flow direction
if not gdb.map_exists(sparseProfilePts, 'vector'): 
    gs.run_command('v.to.points', input_=vecLines, output=startNodes, use='start', overwrite=True)
    gs.run_command('v.to.points', input_=vecLines, output=endNodes, use='end', overwrite=True)
    
    # But also find where the start points of two segments are nearby
    gs.run_command('db.droptable', flags='f', table=duplicTable)
    gs.run_command('v.distance', flags='a', from_=startNodes, to=startNodes, from_layer=1, to_layer=1, \
                    dmax=1, upload='cat', table= duplicTable, overwrite=True)
    gs.run_command('db.select', table=duplicTable, separator='comma', output=duplicFile, overwrite=True)
    
    # Also maybe get sparse profile points along ditch (corrected flow dir)
    # just to compare for duplicates
    gs.run_command('v.to.points', flags='p', input_=vecLines, output=sparseProfilePts, dmax=10)
    gs.run_command('v.to.db', map_=sparseProfilePts, layer=2, option='coor', columns=['x', 'y'])
    gs.run_command('v.db.select', map_=sparseProfilePts, layer=2, format_='csv', file=sparseFile, overwrite=True)

#%% Delete duplicates to make stream orders correct

sameStarts = pd.read_csv(duplicFile)
sameStarts = sameStarts[sameStarts['from_cat']!=sameStarts['cat']]

chainDf = pd.read_csv(chainFile)

# # Each row is being double-counted, so delete half
origLen = len(sameStarts)
i=0
while len(sameStarts) > origLen/2:
    f_cat, t_cat = sameStarts['from_cat'].iloc[i], sameStarts['cat'].iloc[i]
    sameStarts = sameStarts[(sameStarts['from_cat']!=t_cat) | (sameStarts['cat']!=f_cat)]
    i += 1
sameStarts.reset_index(drop=True, inplace=True)

# The starts are the same, but check points along the entire profile
profDf = pd.read_csv(sparseFile)   

for i in range(len(sameStarts)):
    cat1, cat2 = sameStarts['from_cat'].iloc[i], sameStarts['cat'].iloc[i]
    prof1, prof2 = profDf[profDf['lcat']==cat1], profDf[profDf['lcat']==cat2]
    
    x1, y1 = prof1['x'], prof1['y']
    x2, y2 = prof2['x'], prof2['y']
    
    dists = np.sqrt((x2-x1)**2 + (y2-y1)**2)
    
    if np.mean(dists) < 1:
        chain1 = chainDf['chain'][chainDf['root']==cat1].iloc[0]
        chain2 = chainDf['chain'][chainDf['root']==cat2].iloc[0]
        len1, len2 = prof1['along'].iloc[-1], prof2['along'].iloc[-1]
        
        # Delete the one that is an isolate, or the shorter one
        toDel=cat1
        if (chain1 == '[]' and chain2 != '[]') or len2 < len1:
            toDel=cat2
        
        for layer in [vecLines, startNodes, endNodes]:
            gs.run_command('v.edit', map_=layer, tool='delete', cats=toDel)

#%% Find stream orders
# Find where the end of one segment flows into the start of another
gs.run_command('db.droptable', flags='f', table=connectTable)
gs.run_command('v.distance', flags='a', from_=endNodes, to=startNodes, from_layer=1, to_layer=1, \
                dmax=10, upload='cat', table= connectTable, overwrite=True)
gs.run_command('db.select', table=connectTable, separator='comma', output=connectFile, overwrite=True)

lcats=sorted(set(profDf['lcat']))

connectDf = pd.read_csv(connectFile)
connectDf = connectDf[connectDf['from_cat']!=connectDf['cat']]

graph = nx.from_pandas_edgelist(connectDf, source='from_cat', target='cat', create_using=nx.DiGraph)

# Go through all lines for upstream neighbors & stream order
orderDf = pd.DataFrame({'cat': chainDf['root']})

orderDf['parents']=''
orderDf['order']=0

# First pass: note parents of each ditch
for i in range(len(orderDf)):
    lcat = orderDf['cat'].iloc[i]
    
    # Find upstream neighbors/parents
    if graph.has_node(lcat):
        prelimParents = list(graph.predecessors(lcat))
        parents=[]
        # A short ditch segment is not really a parent, probably a mapping error
        for parent in prelimParents:
            parentLen = chainDf['us_len'][chainDf['root']==parent].iloc[0]
            if parentLen > 10:
                parents += [parent]
        parents=str(parents)
    else:
        parents = '[]'
    
    orderDf.loc[i, 'parents'] = parents
    
orderDf.loc[orderDf['parents'] == '[]', 'order'] = 1

if not gdb.map_exists(ditchPrefix + '_order1', 'vector'):
    for ordr in range(1,5):
        mapName = ditchPrefix + '_order' + str(ordr)
        gs.run_command('v.edit', map_=mapName, type_='line', tool='create', overwrite=True)

#gs.run_command('v.db.addcolumn', map_=vecLines, columns='order int')

# Next pass: 
for lcat in lcats:
    order, orderDf = findOrder(lcat, orderDf)
    mapName = ditchPrefix + '_order' + str(order)
    print(lcat, order)
    gs.run_command('v.edit', map_=mapName, tool='copy', bgmap=vecLines, cat=lcat)
    
    #gs.run_command('v.db.update', map_=vecLines, column='order', value=order, where="cat = "+str(lcat))

#ditchCombs.to_csv('final_' + combFile, index=False, sep='\t', float_format='%.3f')
