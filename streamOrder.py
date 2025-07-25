# -*- coding: utf-8 -*-
"""
Created on Sun May  4 20:48:37 2025

@author: Uma
"""
import grass.script as gs
import grass.grassdb.data as gdb
import pandas as pd
import networkx as nx

tmpFiles = 'tempFiles2/'
hucPrefix = 'testDEM2'
ditchPrefix='BRR'

vecLines = hucPrefix + '_lines_final'

# This is just to tell us what lcats are in the region
newElevFile = tmpFiles + hucPrefix + '_elevProfile_shiftedDitches.txt'

#%% To be created

startNodes = hucPrefix + '_starts'
endNodes = hucPrefix + '_ends'

connectTable = hucPrefix + '_endsToStarts'
connectFile = tmpFiles + connectTable + '.txt'

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

#%% Find stream orders
# Find where the end of one segment flows into the start of another
if not gdb.map_exists(endNodes, 'vector'):
    gs.run_command('v.to.points', input_=vecLines, output=startNodes, use='start', overwrite=True)
    gs.run_command('v.to.points', input_=vecLines, output=endNodes, use='end', overwrite=True)
    
    #gs.run_command('db.droptable', flags='f', table=connectTable)
    gs.run_command('v.distance', flags='a', from_=endNodes, to=startNodes, from_layer=1, to_layer=1, \
                    dmax=0.1, upload='cat', table= connectTable, overwrite=True)
    gs.run_command('db.select', table=connectTable, separator='comma', output=connectFile, overwrite=True)

p = pd.read_csv(newElevFile)
lcats=sorted(set(p['lcat']))

connectDf = pd.read_csv(connectFile)
connectDf = connectDf[connectDf['from_cat']!=connectDf['cat']]

graph = nx.from_pandas_edgelist(connectDf, source='from_cat', target='cat', create_using=nx.DiGraph)

# Go through all lines for upstream neighbors & stream order
orderDf = pd.DataFrame({'cat': lcats})

orderDf['parents']=''
orderDf['order']=0

# First pass: note parents of each ditch
for i in range(len(orderDf)):
    lcat = orderDf['cat'].iloc[i]
    
    # Find upstream neighbors/parents
    if graph.has_node(lcat):
        parents = str(list(graph.predecessors(lcat)))
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
