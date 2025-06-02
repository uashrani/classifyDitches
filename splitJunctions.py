""" 
Author: Uma
"""

#%% Prerequisite modules, data, and folders

import grass.script as gs
import grass.grassdb.data as gdb
import pandas as pd
import numpy as np
import networkx as nx

vecLines0='drainage_centerlines'   # name of ditch layer in Grass, already imported

tmpFiles = 'tempFiles/'

ditchPrefix='BRR'

#%% Layers/files that will be created automatically

vecLines1=vecLines0 + '_modifiable'
vecLines2=ditchPrefix + '_lines_nameless'
vecLines3=ditchPrefix + '_lines_renamed'
vecLines=ditchPrefix + '_lines_final'

vecPoints1=ditchPrefix + '_nodes_old'  

intersectTable = ditchPrefix + '_intersections'

# Names of files to export from Grass
ptFileTemp=tmpFiles + ditchPrefix + '_nodes.txt'
intersectFileTemp=tmpFiles + ditchPrefix + '_intersections.txt'

# Start and end points
startNodes = ditchPrefix + '_starts'
endNodes = ditchPrefix + '_ends'

mergeFile=tmpFiles + 'mergeLines.txt'
chainFile= tmpFiles + ditchPrefix + '_streamChains.txt'

# Layers/files for the along profile
profilePts=ditchPrefix + '_profilePts'  # GRASS layer
alongFile=tmpFiles + ditchPrefix + '_alongPts.txt'  # output file

#%% Function definitions

def split_nodesIntersects(ptFile, intersectFile, linesLayer):
    """ Takes two csv's, one containing nodes and one containing line intersections.
    Creates a set with the xy coordinates along which to break the line vectors. 
    Breaks lines along these xy coordinates. """

    pts = pd.read_csv(ptFile)
    intersects = pd.read_csv(intersectFile)
    intersects.rename(columns={'to_x': 'x', 'to_y': 'y'}, inplace=True)

    ptsXY=pts[['x', 'y']]
    intersectsXY=intersects[['x', 'y']]
    breakDf = pd.concat((ptsXY, intersectsXY))

    for col in ['x', 'y']:
        breakDf[col] = breakDf[col].round(1)

    breakDf['tuple'] = '(' + breakDf['x'].astype('str') + ',' + breakDf['y'].astype('str') + ')'

    tupleSet = sorted(set(breakDf['tuple']))

    for elt in tupleSet:
        elt = elt.strip('()')
        x, y = tuple(map(float,elt.split(',')))

        gs.run_command('v.edit', map_=linesLayer, tool='break', coords=[x,y], threshold=1)

#%% Actual code

# Temporary: drop table because overwrite doesn't work
#gs.run_command('db.droptable', flags='f', table=intersectTable)

gs.run_command('g.region', vector=vecLines0)

if not gdb.map_exists(vecLines, 'vector'):
    gs.run_command('g.copy', vector=[vecLines0, vecLines1])
    
# Get list of all nodes and their xy coordinates, will split lines at these points
    gs.run_command('v.to.points', input_=vecLines1, output=vecPoints1, use='node', overwrite=True)
    gs.run_command('v.to.db', map_=vecPoints1, layer=2, option='coor', columns=['x', 'y'], overwrite=True)
    # Export attribute table of these points
    gs.run_command('v.db.select', map_=vecPoints1, layer=2, format_='csv', file=ptFileTemp, overwrite=True)
    
    # Also get intersections between lines, since there is not always a node at the intersection
    gs.run_command('v.distance', flags='a', from_=vecLines1, to=vecLines1, dmax=1, \
        upload=['to_x', 'to_y', 'cat'], table=intersectTable, overwrite=True)
    gs.run_command('db.select', table=intersectTable, separator='comma', output=intersectFileTemp, overwrite=True)
    
    split_nodesIntersects(ptFileTemp, intersectFileTemp, vecLines1)
    
    ### When we split lines into segments, their category number didn't change (only feature ID did)
    ### Create new attribute table so every segment has unique category number
    # Delete old category numbers and assign new category number to each segment
    gs.run_command('v.category', flags='t', input_=vecLines1, output=vecLines2, option='del', cat=-1, overwrite=True)
    gs.run_command('v.category', input_=vecLines2, output=vecLines3, option='add', overwrite=True)
    
    # Disconnect from old attribute table and create new one
    gs.run_command('v.db.connect', flags='d', map_=vecLines3, layer=1)
    gs.run_command('v.db.addtable', map_=vecLines3)

    gs.run_command('v.to.db', map_=vecLines3, option='length', columns=['len'])
    gs.run_command('v.db.droprow', input_=vecLines3, where="len < 0.1", output=vecLines, overwrite=True)


## Next create layers for start and end points
if not gdb.map_exists(endNodes, 'vector'):
    gs.run_command('v.to.points', input_=vecLines, output=startNodes, use='start', overwrite=True)
    gs.run_command('v.to.points', input_=vecLines, output=endNodes, use='end', overwrite=True)
    # Find which segments are connected
    gs.run_command('v.db.addcolumn', map_=endNodes, layer=2, columns=['to_lcat int'])
    gs.run_command('v.distance', from_=endNodes, to=startNodes, from_layer=2, to_layer=2, \
                    dmax=1, upload='to_attr', to_column='lcat', \
                        column='to_lcat', overwrite=True)
    gs.run_command('v.db.select', map_=endNodes, layer=2, format_='csv', file=mergeFile, overwrite=True)

dfEnds=pd.read_csv(mergeFile)
dfEnds=dfEnds[(dfEnds['lcat']!=dfEnds['to_lcat']) & (np.isnan(dfEnds['to_lcat'])==False)].reset_index(drop=True)
# Keep track of original category numbers
orig_cats = gs.read_command('v.category', input_=vecLines1, option='print')
ls_orig_cats = orig_cats.split('\r\n')
ls_orig_cats = pd.Series(ls_orig_cats[:-1]).astype('int')
fIDs = np.arange(1, len(ls_orig_cats)+1)

dfOrig = pd.DataFrame({'cat': fIDs, 'orig_cat': ls_orig_cats})

from_cats, to_cats=[], []

# Get connections b/w segments that were originally part of same line
for i in range(len(dfEnds)):
    row=dfEnds.iloc[i]
    f_cat, t_cat=row['lcat'], row['to_lcat']
    
    f_orig=dfOrig['orig_cat'][dfOrig['cat']==f_cat].iloc[0]
    t_orig=dfOrig['orig_cat'][dfOrig['cat']==t_cat].iloc[0]
    
    if f_orig==t_orig: 
        from_cats+=[f_cat]
        to_cats+=[t_cat]
        
mergedLines=pd.DataFrame({'from':from_cats, 'to':to_cats})

graph = nx.from_pandas_edgelist(mergedLines, source='from', target='to', create_using=nx.DiGraph)  

dfOrig['nPrev']=0
dfOrig['nNext']=0

for i in range(len(dfOrig)):
    lcat=dfOrig['cat'].iloc[i]
    
    if graph.has_node(lcat):
        nPrev = len(list(graph.predecessors(lcat)))
        nNext = len(list(graph.successors(lcat)))
        
        dfOrig.loc[i, 'nPrev'] = nPrev
        dfOrig.loc[i, 'nNext'] = nNext
       
# To merge a segment, we want the number of its successors and predecessors to be 1
singleChains=dfOrig[(dfOrig['nPrev']<=1) & (dfOrig['nNext']<=1) & ((dfOrig['nPrev'] + dfOrig['nNext']) > 0)]
# Start at roots
rootLcats=singleChains['cat'][singleChains['nPrev']==0]

chainCol = []
rootCol = []

for lcat in fIDs:
    if graph.has_node(lcat)==False or len(list(graph.predecessors(lcat))) == 0:
           chain=[int(lcat)]
    else: 
        chain=[]
    if lcat in list(rootLcats):
        
        nextLcats=list(graph.successors(lcat))
        
        if len(nextLcats) > 0: 
            nextLcat=nextLcats[0] 
        else: 
            nextLcat=0
        
        while nextLcat in list(singleChains['cat']):
            chain+=[int(nextLcat)]
            
            nextLcats=list(graph.successors(nextLcat))
            if len(nextLcats) > 0: 
                nextLcat=nextLcats[0]
            else: 
                nextLcat=0
            
    chainCol += [str(chain)]
    
chainDf = pd.DataFrame({'root': fIDs, 'chain': chainCol})
chainDf.to_csv(chainFile, index=False)
        
### Get points spaced 1m apart along the new lines, will be used for transects
if not gdb.map_exists(profilePts, 'vector'):
    gs.run_command('v.to.points', input_=vecLines, output=profilePts, dmax=1)
    gs.run_command('v.to.db', map_=profilePts, layer=2, option='coor', columns=['x', 'y'])
    gs.run_command('v.db.select', map_=profilePts, layer=2, format_='csv', file=alongFile, overwrite=True)

