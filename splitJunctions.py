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

duplThresh = 3      # lines that are near-duplicates (within 3m of each other)
dangleThresh = 25   # remove dangles less than this length
connectThresh = 10  # connect endpoints within this distance of each other

#%% Layers/files that will be created automatically
vecLines1 = ditchPrefix + '_lines_rmdangle'
vecLines2 = ditchPrefix + '_lines_rmdupl'
vecLines3 = ditchPrefix + '_lines_rmdupl2'
vecLines4 = ditchPrefix + '_lines_poly'
vecLines5 = ditchPrefix + '_lines_nameless'
vecLines6 = ditchPrefix + '_lines_renamed'

# Use these to split at intersections and (if needed) midpoints
allNodes = ditchPrefix + '_nodesTemp'
nodesFile = tmpFiles + allNodes + '.txt'

# Start and end points
startNodes = ditchPrefix + '_startsTemp'
endNodes = ditchPrefix + '_endsTemp'
flowTable = ditchPrefix + '_flowConnections'
flowFile = tmpFiles + flowTable + '.txt'

origCatFile = tmpFiles + ditchPrefix + '_origCats.txt'
chainFile= tmpFiles + ditchPrefix + '_streamChains.txt'

# Layers/files for the along profile - use it to take cross sections later
profilePts=ditchPrefix + '_profilePts'  # GRASS layer
alongFile=tmpFiles + ditchPrefix + '_alongPts.txt'  # output file

#%% Function definition

def split_nodesIntersects(nodeFile, linesLayer):
    """ Breaks lines at nodes; also breaks at midpoints if doubled up 
    nodeFile: has xy coords of line nodes and midpoints
    linesLayer: vector layer to split """
    
    nodesDf = pd.read_csv(nodeFile)
    
    # Find whether any lines are doubled up, and get their midpoint
    starts, mids, ends = nodesDf.iloc[::3].reset_index(drop=True), \
        nodesDf.iloc[1::3].reset_index(drop=True), nodesDf.iloc[2::3].reset_index(drop=True)
    nodes = pd.concat((starts,ends), ignore_index=True)
    dists = np.sqrt((ends['x']-starts['x'])**2 + (ends['y']-starts['y'])**2)
    
    toSplit = mids[dists<duplThresh]
    
    # Split at midpoints of doubled-up lines
    for i in range(len(toSplit)):
        x,y=toSplit['x'].iloc[i],toSplit['y'].iloc[i]
        gs.run_command('v.edit', map_=vecLines1, tool='break', coords=[x,y])
    
    haveSplit = pd.DataFrame(columns=['x', 'y'])
    for i in range(len(nodes)):
        x,y=nodes['x'].iloc[i],nodes['y'].iloc[i] #,breakDf['thresh'].iloc[i]
        dists = np.sqrt((haveSplit['x']-x)**2 + (haveSplit['y']-y)**2)

        if len(haveSplit)==0 or len(np.where(dists < 1)[0]) == 0:
            gs.run_command('v.edit', map_=linesLayer, tool='break', coords=[x,y], threshold=1)
            haveSplit = pd.concat((haveSplit,pd.DataFrame({'x': [x], 'y': [y]})), ignore_index=True)
            
def findStreamChains(graph, lcats):
    """ Find 'single chains' with same original cats
    (ie where 1 segment flows into 1 segment w/o forks/branches)
    Takes a networkx directed graph, and a list of lcats """
    
    chainDf = pd.DataFrame({'root': lcats})
    chainDf['chain']=''
    
    for lcat in lcats:
        currentChain = chainDf['chain'][chainDf['root']==lcat].iloc[0]
        
        if currentChain == '':
            if graph.has_node(lcat)==False: 
                chain=[int(lcat)] 
            else:
                prevLcats = list(graph.predecessors(lcat))
                
                # If it has exactly one predecessor and no siblings, it's part of another chain
                # If it has 0 or 2+ predecessors, start a new chain
                if len(prevLcats) != 1 or (len(prevLcats)==1 and len(list(graph.successors(prevLcats[0])))!=1):
                    chain=[int(lcat)]
                    
                    nextLcats=list(graph.successors(lcat))
                    
                    # If a segment has 0 or 2+ successors, end the chain here
                    if len(nextLcats) != 1:
                        nextLcat=0 
                    else:
                        nextLcat=nextLcats[0]
                    
                    # Check to make sure the successor isn't receiving flow from another segment
                    while nextLcat != 0 and len(list(graph.predecessors(nextLcat)))==1:
                        chain+=[int(nextLcat)]
                        
                        nextLcats = list(graph.successors(nextLcat))
                        if len(nextLcats) != 1:
                            nextLcat=0
                        else:
                            nextLcat=nextLcats[0]
        
            for segment in chain:
                chainDf.loc[chainDf['root']==segment, 'chain']=str(chain)
        
    return chainDf

#%% Split lines at intersections, and on nodes along line

gs.run_command('g.region', vector=vecLines0)

### Build network (make sure it's cleaned, connected, etc.)
if not gdb.map_exists(vecLines6, 'vector'):
    
    # Remove dangles < 25m (short segments not connected to any other line)
    gs.run_command('v.clean', input_=vecLines0, type_='line', output=vecLines1,\
                   tool='rmdangle', threshold=dangleThresh, overwrite=True)
    
    # Very specific but some lines are "doubled up" (like a U-turn) 
    # these points help determine if they are
    gs.run_command('v.to.points', flags='p', input_=vecLines1, output=allNodes, dmax=51)
    gs.run_command('v.to.db', map_=allNodes, layer=2, option='coor', columns=['x', 'y'])
    gs.run_command('v.db.select', map_=allNodes, layer=2, format_='csv', file=nodesFile, overwrite=True)
    
    # Split doubled-up lines at midpoints, and split all lines at nodes
    split_nodesIntersects(nodesFile, vecLines1)
    
    # We use tool=snap, but this really removes duplicates
    gs.run_command('v.edit', map_=vecLines1, tool='delete', query='length', threshold=[-1,0,-0], type_='line')
    gs.run_command('v.clean', flags='c', input_=vecLines1, output_=vecLines2, \
                   tool='snap', threshold=duplThresh)
    
    # Connect all lines within 10m of each other
    gs.run_command('v.edit', map_=vecLines2, tool='connect', threshold=connectThresh, ids='1-1000')
    # Snap lines again to delete any short duplicate segments created by v.edit
    gs.run_command('v.clean', flags='c', input_=vecLines2, output_=vecLines3, \
                   tool='snap', threshold=duplThresh)
    
    # Build polylines
    gs.run_command('v.build.polylines', input_=vecLines3, output_=vecLines4, \
                   type_='line', cats='first')
    # Get the original category of the polylines
    orig_cats = gs.read_command('v.category', input_=vecLines4, option='print')
    ls_orig_cats = orig_cats.split('\r\n')
    ls_orig_cats = pd.Series(ls_orig_cats[:-1]).astype('int')
    fIDs = np.arange(1, len(ls_orig_cats)+1)
    dfOrig = pd.DataFrame({'cat': fIDs, 'orig_cat': ls_orig_cats})
    dfOrig.to_csv(origCatFile, index=False)
    
    # Rename categories (some have multiple features)
    gs.run_command('v.category', flags='t', input_=vecLines4, output=vecLines5, option='del', cat=-1, overwrite=True)
    gs.run_command('v.category', input_=vecLines5, output=vecLines6, option='add', overwrite=True)
    gs.run_command('v.db.connect', flags='d', map_=vecLines6, layer=1)
    gs.run_command('v.db.addtable', map_=vecLines6)
    
    # Get updated start and end nodes and find connections between them
    gs.run_command('v.to.points', input_=vecLines6, output=startNodes, use='start', overwrite=True)
    gs.run_command('v.to.points', input_=vecLines6, output=endNodes, use='end', overwrite=True)
    gs.run_command('v.distance', flags='a', from_=endNodes, to=startNodes, from_layer=1, to_layer=1, \
                         dmax=1, upload='cat', table=flowTable, overwrite=True)
    gs.run_command('db.select', table=flowTable, separator='comma', output=flowFile, overwrite=True)             

### Get points spaced 1m apart along the new lines
### Will be used to take cross-sectional profiles
if not gdb.map_exists(profilePts, 'vector'):
    gs.run_command('v.to.points', input_=vecLines6, output=profilePts, dmax=1)
    gs.run_command('v.to.db', map_=profilePts, layer=2, option='coor', columns=['x', 'y'])
    gs.run_command('v.db.select', map_=profilePts, layer=2, format_='csv', file=alongFile, overwrite=True)

#%% Find which segments originally connected to each other (even if not actual flow dir)

dfEnds = pd.read_csv(flowFile)
dfEnds=dfEnds[dfEnds['from_cat']!=dfEnds['cat']].reset_index(drop=True)

dfOrig = pd.read_csv(origCatFile)
fIDs=dfOrig['cat']
### We have a table showing all connections, 
### but we narrow this down to connections b/w segments that had same original cat
from_cats, to_cats=[], []

for i in range(len(dfEnds)):
    row=dfEnds.iloc[i]
    
    # These are their cat numbers in the renamed layer
    f_cat, t_cat=row['from_cat'], row['cat']
    
    # These are their cat numbers from the original layer
    f_orig=dfOrig['orig_cat'][dfOrig['cat']==f_cat].iloc[0]
    t_orig=dfOrig['orig_cat'][dfOrig['cat']==t_cat].iloc[0]
    
    # If they came from the same original cat, add them to the to/from columns
    if f_orig==t_orig: 
        from_cats+=[f_cat]
        to_cats+=[t_cat]
        
# Create a directed graph of segments that came from the same original lines
mergedLines=pd.DataFrame({'from':from_cats, 'to':to_cats})
graph = nx.from_pandas_edgelist(mergedLines, source='from', target='to', create_using=nx.DiGraph)  

# Find single chains and save to file
chainDf = findStreamChains(graph, fIDs)
chainDf.to_csv(chainFile, index=False)



