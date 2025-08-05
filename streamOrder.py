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
hucPrefix = 'testDEM3'
ditchPrefix='BRR'

vecLines8 = hucPrefix + '_lines_flowDir'

# This is just to tell us what lcats are in the region
newElevFile = tmpFiles + hucPrefix + '_elevProfile_shiftedDitches.txt'

#%% To be created

#vecLines = hucPrefix + '_lines_final'

startNodes = hucPrefix + '_starts'
endNodes = hucPrefix + '_ends'

connectTable = hucPrefix + '_endsToStarts'
connectFile = tmpFiles + connectTable + '.txt'

#%% 

def findOrder(lcat, orderDf):
    thisRow = orderDf[orderDf['cat']==lcat].iloc[0]
    order = thisRow['order']
    strParents = thisRow['parents']
    strpParents=strParents.strip('[]')
    if strpParents != '': 
        parents = list(map(int,strpParents.split(', ')))
    else:
        parents=[]
    
    if order > 0:
        return(order, orderDf)
    else:
        parentOrders = []
        parentBraids = []
        for parent in parents:
            #if parent in list(ditchLines['cat']):
            parentOrder, orderDf = findOrder(parent, orderDf)
            parentOrders += [parentOrder]   
            parentBraid = orderDf['braid'][orderDf['cat']==parent].iloc[0]
            parentBraids += [parentBraid]
            
        parentDf1 = pd.DataFrame({'cat': parents, 'order': parentOrders, \
                                 'braid': parentBraids})
        
        parentDf = parentDf1.copy()
        
        # Make sure this is not a braided stream with the same origin
        for i in range(len(parentDf1)):
            braid = parentDf1['braid'].iloc[i]
            if braid != '':
                matchBraid = parentDf1.index[parentDf1['braid']==braid]
                parentDf.drop(index=matchBraid[matchBraid < i], inplace=True)
        
        maxOrder = max(parentDf['order'])
        nmax = len(parentDf[parentDf['order']==maxOrder])

        # If it has a non-empty value for braided, it shares the exact same parents with another segment
        if nmax > 1 and thisRow['braid']=='':
            order = maxOrder + 1 
        else:
            order = maxOrder
            if len(parentDf) == 1 and parentDf['braid'].iloc[0] != '':
                orderDf.loc[orderDf['cat']==lcat, 'braid'] = parentDf['braid'].iloc[0]
        
        orderDf.loc[orderDf['cat']==lcat, 'order'] = order
        
        return(order, orderDf)

#%% Find stream orders
### Build polylines and find where end of one segment flows into start of another
if not gdb.map_exists(endNodes, 'vector'):
    #gs.run_command('v.build.polylines', input_=vecLines6, output=vecLines, cats='first', type_='line')
    #gs.run_command('v.db.droptable', flags='f', map_=vecLines)
    #gs.run_command('v.db.addtable', map_=vecLines)
    gs.run_command('v.to.points', input_=vecLines8, output=startNodes, use='start', overwrite=True)
    gs.run_command('v.to.points', input_=vecLines8, output=endNodes, use='end', overwrite=True)
    
    #gs.run_command('db.droptable', flags='f', table=connectTable)
    gs.run_command('v.distance', flags='a', from_=endNodes, to=startNodes, from_layer=1, to_layer=1, \
                    dmax=10, upload=['cat','dist'], table= connectTable, overwrite=True)
    gs.run_command('db.select', table=connectTable, separator='comma', output=connectFile, overwrite=True)

p = pd.read_csv(newElevFile)
lcats=sorted(set(p['lcat']))

connectDf = pd.read_csv(connectFile)
connectDf = connectDf[connectDf['from_cat']!=connectDf['cat']]

graph = nx.from_pandas_edgelist(connectDf, source='from_cat', target='cat', create_using=nx.DiGraph)

# Go through all lines for upstream neighbors & stream order
# orderDf = pd.DataFrame({'cat': lcats})

# orderDf['parents']=''
# orderDf['order']=0
# orderDf['braid']=''

# # First pass: note parents of each ditch
# for i in range(len(orderDf)):
#     lcat = orderDf['cat'].iloc[i]
    
#     # Find upstream neighbors/parents
#     if graph.has_node(lcat):
#         parents = str(list(graph.predecessors(lcat)))
        
#         sameParents = orderDf.index[orderDf['parents']==parents]
#         if len(sameParents) > 0 and parents != '[]':
#             orderDf.loc[i, 'braid'] = parents
#             orderDf.loc[sameParents, 'braid'] = parents
#     else:
#         parents = '[]'
        
#     orderDf.loc[i, 'parents'] = parents
    
# orderDf.loc[orderDf['parents'] == '[]', 'order'] = 1

# if not gdb.map_exists(ditchPrefix + '_order1', 'vector'):
#     for ordr in range(1,5):
#         mapName = ditchPrefix + '_order' + str(ordr)
#         gs.run_command('v.edit', map_=mapName, type_='line', tool='create', overwrite=True)

# #gs.run_command('v.db.addcolumn', map_=vecLines, columns='order int')

# # Next pass: 
# for lcat in lcats:
#     order, orderDf = findOrder(lcat, orderDf)
#     mapName = ditchPrefix + '_order' + str(order)
#     print(lcat, order)
    #gs.run_command('v.edit', map_=mapName, tool='copy', bgmap=vecLines, cat=lcat)
    
    #gs.run_command('v.db.update', map_=vecLines, column='order', value=order, where="cat = "+str(lcat))

#ditchCombs.to_csv('final_' + combFile, index=False, sep='\t', float_format='%.3f')


