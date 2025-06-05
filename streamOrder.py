# -*- coding: utf-8 -*-
"""
Created on Sun May  4 20:48:37 2025

@author: Uma
"""
import grass.script as gs
import pandas as pd
import networkx as nx
import numpy as np
import math

tmpFiles = 'tempFiles/'
ditchPrefix='BRR'

vecLines = ditchPrefix + '_lines_final'
chainFile = tmpFiles + ditchPrefix + '_streamChains.txt'

# Later will be region of the HUC, get from the bounding box file
#n, s, e, w = 5217318, 5212652, 274769, 269803   # test region 1
n, s, e, w = 5202318, 5191400, 220687, 212912   # test region 2

#%% To be created

startNodes = ditchPrefix + '_starts'
endNodes = ditchPrefix + '_ends'

connectTable = ditchPrefix + '_flowConnections'
duplicTable = ditchPrefix + '_duplicateStarts'

duplicFile=tmpFiles + 'maybeDuplicates.txt'
connectFile=tmpFiles + 'mergeLines.txt'

sparseProfilePts = ditchPrefix + '_sparseProfile'
sparseFile = tmpFiles + ditchPrefix + '_sparsePts.txt'

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
#gs.run_command('g.remove', flags='f', type_='vector', name=[startNodes, endNodes])
gs.run_command('v.to.points', input_=vecLines, output=startNodes, use='start', overwrite=True)
gs.run_command('v.to.points', input_=vecLines, output=endNodes, use='end', overwrite=True)

# Find where the end of one segment flows into the start of another
gs.run_command('db.droptable', flags='f', table=connectTable)
gs.run_command('v.distance', flags='a', from_=endNodes, to=startNodes, from_layer=1, to_layer=1, \
                dmax=0.2, upload='cat', table= connectTable, overwrite=True)
# But also find where the start points of two segments are nearby
gs.run_command('v.distance', flags='a', from_=startNodes, to=startNodes, from_layer=1, to_layer=1, \
                dmax=1, upload='cat', table= duplicTable, overwrite=True)

gs.run_command('db.select', table=connectTable, separator='comma', output=connectFile, overwrite=True)
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

# # The starts are the same, but check points along the entire profile
profDf = pd.read_csv(sparseFile)   

for i in range(len(sameStarts)):
    cat1, cat2 = sameStarts['from_cat'].iloc[i], sameStarts['cat'].iloc[i]
    prof1, prof2 = profDf[profDf['lcat']==cat1], profDf[profDf['lcat']==cat2]
    
    x1, y1 = prof1['x'].iloc[-1], prof1['y'].iloc[-1]
    x2, y2 = prof2['x'].iloc[-1], prof2['y'].iloc[-1]
    
    # First check distance between endpoints, if they are far then stop
    endDist=math.sqrt((x2-x1)**2 + (y2-y1)**2)
    
    if endDist < 1:
        print(cat1, cat2)
        # Check 10 evenly spaced points along profile to make sure they're same
        nPts = min([len(prof1), len(prof2)])
        dists = []
        for j in range(1, nPts-1):
            x1, y1 = prof1['x'].iloc[j], prof1['y'].iloc[j]
            x2, y2 = prof2['x'].iloc[j], prof2['y'].iloc[j]
            
            dists += [math.sqrt((x2-x1)**2 + (y2-y1)**2)]
        if np.mean(dists) < 1:
            
            chain1 = chainDf['chain'][chainDf['root']==cat1].iloc[0]
            chain2 = chainDf['chain'][chainDf['root']==cat2].iloc[0]
            
            # Delete the one that is an isolate, or the shorter one
            if chain1 == '[]' and chain2 != '[]':
                gs.run_command('v.edit', map_=vecLines, tool='delete', cats=cat2)
            elif chain2 == '[]':
                gs.run_command('v.edit', map_=vecLines, tool='delete', cats=cat1)
            else:
                len1, len2 = prof1['along'].iloc[-1], prof2['along'].iloc[-1]
                if len1 < len2: 
                    gs.run_command('v.edit', map_=vecLines, tool='delete', cats=cat1)
                else: 
                    gs.run_command('v.edit', map_=vecLines, tool='delete', cats=cat2)
                
            

#%% Find stream orders

dfInRegion = profDf[((profDf['y']>=s)&(profDf['y']<=n))&((profDf['x']>=w)&(profDf['x']<=e))]

# Temporary: also filter out the ones that are <1m 
dfInRegion = dfInRegion[dfInRegion['along']>=1]

lcats=sorted(set(dfInRegion['lcat']))

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





# #gs.run_command('v.edit', map_='order1', type_='line', tool='create', overwrite=True)
# #gs.run_command('v.edit', map_='order2', type_='line', tool='create', overwrite=True)
# gs.run_command('v.db.addcolumn', map_='ditch_lines_renamed', columns='order int')

# Next pass: 
for lcat in lcats:
    order, orderDf = findOrder(lcat, orderDf)
    print(lcat, order)
            
#         if order==1:
#             gs.run_command('v.edit', map_='order1', tool='copy', bgmap='ditch_lines_renamed', cat=lcat, overwrite=True)
#         if order==2: 
#             gs.run_command('v.edit', map_='order2', tool='copy', bgmap='ditch_lines_renamed', cat=lcat, overwrite=True)
    
        #gs.run_command('v.db.update', map_='ditch_lines_renamed', column='order', value=order, where="cat="+str(lcat))

#ditchCombs.to_csv('final_' + combFile, index=False, sep='\t', float_format='%.3f')
