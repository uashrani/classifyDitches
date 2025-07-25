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
tmpFiles = 'tempFiles2/'

ditchPrefix='BRR'

#%% Layers/files that will be created automatically

vecLines1 = ditchPrefix + '_lines_rmdangle'
vecLines2 = ditchPrefix + '_lines_namelessTemp'
vecLines3 = ditchPrefix + '_lines_renamedTemp'
vecLines4 = ditchPrefix + '_lines_nameless'
vecLines5 = ditchPrefix + '_lines_renamed'

# Create before splitting and breaking category numbers
allNodes = ditchPrefix + '_nodesTemp'

# Start and end points, and duplicates
startNodes1 = ditchPrefix + '_startsTemp'
endNodes1 = ditchPrefix + '_endsTemp'

# Removing even more duplicates
duplicTable1 = ditchPrefix + '_startsToStarts'
duplicFile1 = tmpFiles + duplicTable1 + '.txt'
duplicTable2 = ditchPrefix + '_endsToStarts'
duplicFile2 = tmpFiles + duplicTable2 + '.txt'
sparsePts = ditchPrefix + '_sparseProfile'
sparseFile = tmpFiles + sparsePts + '.txt'
sparsePts2 = ditchPrefix + '_sparseProfile2'

# Final start and 
startNodes2 = ditchPrefix + '_startsTemp2'
endNodes2 = ditchPrefix + '_endsTemp2'
chainFile= tmpFiles + ditchPrefix + '_streamChains.txt'

# Layers/files for the along profile - use it to take cross sections later
profilePts=ditchPrefix + '_profilePts'  # GRASS layer
alongFile=tmpFiles + ditchPrefix + '_alongPts.txt'  # output file

#%% Function definition

def split_nodesIntersects(nodeFile, linesLayer):
    """ Breaks lines at nodes """
    
    nodesDf = pd.read_csv(nodeFile)
    
    # Find whether any lines are doubled up, and get their midpoint
    starts, mids, ends = nodesDf.iloc[::3].reset_index(drop=True), \
        nodesDf.iloc[1::3].reset_index(drop=True), nodesDf.iloc[2::3].reset_index(drop=True)
    nodes = pd.concat((starts,ends), ignore_index=True)
    dists = np.sqrt((ends['x']-starts['x'])**2 + (ends['y']-starts['y'])**2)
    
    toSplit = mids[dists<1]
    
    # Split at midpoints of doubled-up lines
    for i in range(len(toSplit)):
        x,y=toSplit['x'].iloc[i],toSplit['y'].iloc[i]
        gs.run_command('v.edit', map_=vecLines1, tool='break', coords=[x,y])
    
    haveSplit = pd.DataFrame(columns=['x', 'y'])
    for i in range(len(nodes)):
        x,y=nodes['x'].iloc[i],nodes['y'].iloc[i] #,breakDf['thresh'].iloc[i]
        dists = np.sqrt((haveSplit['x']-x)**2 + (haveSplit['y']-y)**2)

        if i==0 or len(np.where(dists < 1)[0]) == 0:
            gs.run_command('v.edit', map_=linesLayer, tool='break', coords=[x,y], threshold=1)
            haveSplit = pd.concat((haveSplit,pd.DataFrame({'x': [x], 'y': [y]})), ignore_index=True)
            
def findDuplics(vecLines, profPts, duplicFile1, duplicFile2):
    """ Finds lines that partially or completely overlap, 
    and deletes the lower cat value 
    
    duplicFile1 is starts-->starts, duplicFile2 is ends-->starts
    """
    
    gs.run_command('v.to.points', flags='p', input_=vecLines, output=profPts, dmax=51)
    gs.run_command('v.to.db', map_=profPts, layer=2, option='coor', columns=['x', 'y'])
    gs.run_command('v.db.select', map_=profPts, layer=2, format_='csv', file=sparseFile, overwrite=True)
    
    profDf = pd.read_csv(sparseFile)
    duplics = []

    for file in [duplicFile1, duplicFile2]:

        sameStarts = pd.read_csv(file)
        sameStarts = sameStarts[sameStarts['from_cat']!=sameStarts['cat']]

        # duplicFile2 is where start-->start
        if file==duplicFile1:
        # Each row is being double-counted, so delete half
            origLen = len(sameStarts)
            i=0
            while len(sameStarts) > origLen/2:
                f_cat, t_cat = sameStarts['from_cat'].iloc[i], sameStarts['cat'].iloc[i]
                sameStarts = sameStarts[(sameStarts['from_cat']!=t_cat) | (sameStarts['cat']!=f_cat)]
                i += 1
            sameStarts.reset_index(drop=True, inplace=True)

        for i in range(len(sameStarts)):
            cat1, cat2 = sameStarts['from_cat'].iloc[i], sameStarts['cat'].iloc[i]
            prof1, prof2 = profDf[profDf['lcat']==cat1].reset_index(drop=True), \
                profDf[profDf['lcat']==cat2].reset_index(drop=True)
            
            # Read one profile backwards if going from ends to starts
            if file==duplicFile2: 
                prof1 = prof1.iloc[::-1].reset_index(drop=True)
                prof1['along'] = prof1['along'].iloc[::-1].reset_index(drop=True)
            
            x1, y1 = prof1['x'], prof1['y']
            x2, y2 = prof2['x'], prof2['y']
            
            dists = np.sqrt((x2-x1)**2 + (y2-y1)**2)
            if np.mean(dists) < 1: 
                toDrop=min([cat1,cat2])
                duplics += [toDrop]
                
                #profDf = profDf[profDf['lcat']!=toDrop]        
                
    duplics=list(sorted(set(duplics)))
    for duplic in duplics:
        profDf = profDf[profDf['lcat']!=duplic]
        sameStarts = sameStarts[(sameStarts['from_cat']!=duplic) & (sameStarts['cat']!=duplic)]
    
    return(duplics, sameStarts) #, profDf)
    

#%% Split lines at intersections, and on nodes along line

gs.run_command('g.region', vector=vecLines0)

if not gdb.map_exists(vecLines3, 'vector'):
    
    gs.run_command('v.clean', input_=vecLines0, type_='line', output=vecLines1,\
                   tool='rmdangle', threshold=25)
    
    # Very specific but some lines are "doubled up" (like a U-turn), split these midway
    gs.run_command('v.to.points', flags='p', input_=vecLines1, output=allNodes, dmax=51)
    gs.run_command('v.to.db', map_=allNodes, layer=2, option='coor', columns=['x', 'y'])
    gs.run_command('v.db.select', map_=allNodes, layer=2, format_='csv', file=sparseFile, overwrite=True)
    
    split_nodesIntersects(sparseFile, vecLines1)
    
    # Update category numbers temporarily (will update a second time)
    gs.run_command('v.category', flags='t', input_=vecLines1, output=vecLines2, option='del', cat=-1, overwrite=True)
    gs.run_command('v.category', input_=vecLines2, output=vecLines3, option='add', overwrite=True)

    # Delete very short line segments
    gs.run_command('v.edit', map_=vecLines3, tool='delete', query='length', threshold=[-1,0,-0.1], type_='line')

### Get points that help identify duplicates
if not gdb.map_exists(endNodes1, 'vector'):
    # Create layers for start and end points
    gs.run_command('v.to.points', input_=vecLines3, output=startNodes1, use='start', overwrite=True)
    gs.run_command('v.to.points', input_=vecLines3, output=endNodes1, use='end', overwrite=True)
    
    # Find lines with matching starts
    gs.run_command('v.distance', flags='a', from_=startNodes1, to=startNodes1, from_layer=1, to_layer=1, \
                    dmax=1, upload='cat', table= duplicTable1, overwrite=True)
    gs.run_command('db.select', table=duplicTable1, separator='comma', output=duplicFile1, overwrite=True)
    
    # Direction may be wrong, so also find where the end of one line is near the start of another
    gs.run_command('v.distance', flags='a', from_=endNodes1, to=startNodes1, from_layer=1, to_layer=1, \
                    dmax=1, upload='cat', table=duplicTable2, overwrite=True)
    gs.run_command('db.select', table=duplicTable2, separator='comma', output=duplicFile2, overwrite=True)
    
if not gdb.map_exists(vecLines5, 'vector'):
# Delete duplicates (first pass, otherwise connecting lines gets messy)
    duplics, filler = findDuplics(vecLines3, sparsePts, duplicFile1, duplicFile2)
    
    # Drop duplicates from the nameless layer using feature IDs
    gs.run_command('v.edit', map_=vecLines1, tool='delete', ids=duplics)
    gs.run_command('v.edit', map_=vecLines1, tool='delete', query='length', threshold=[-1,0,-0.1], type_='line')
    gs.run_command('v.edit', map_=vecLines1, tool='connect', threshold=10, ids='1-1000')
    gs.run_command('v.edit', map_=vecLines1, tool='delete', query='length', threshold=[-1,0,-0.1], type_='line')
    # Now we can break lines at intersections
    gs.run_command('v.edit', map_=vecLines1, tool='break', ids='1-1000')
    gs.run_command('v.edit', map_=vecLines1, tool='delete', query='length', threshold=[-1,0,-1], type_='line')
    
    # Update category numbers
    gs.run_command('v.category', flags='t', input_=vecLines1, output=vecLines4, option='del', cat=-1, overwrite=True)
    gs.run_command('v.category', input_=vecLines4, output=vecLines5, option='add', overwrite=True)
    
    # Disconnect from old attribute table and create new one
    gs.run_command('v.db.connect', flags='d', map_=vecLines5, layer=1)
    gs.run_command('v.db.addtable', map_=vecLines5)
    
    ### Ok now drop any new duplicates that were missed (like they partially overlapped before but now fully overlap)
    gs.run_command('v.to.points', input_=vecLines5, output=startNodes2, use='start', overwrite=True)
    gs.run_command('v.to.points', input_=vecLines5, output=endNodes2, use='end', overwrite=True)
    
    # starts-->starts
    gs.run_command('db.droptable', flags='f', table=duplicTable1)
    gs.run_command('v.distance', flags='a', from_=startNodes2, to=startNodes2, from_layer=1, to_layer=1, \
                    dmax=1, upload='cat', table= duplicTable1, overwrite=True)
    gs.run_command('db.select', table=duplicTable1, separator='comma', output=duplicFile1, overwrite=True)
    
    # Ends-->starts (also used for finding stream chains later)
    gs.run_command('db.droptable', flags='f', table=duplicTable2)
    gs.run_command('v.distance', flags='a', from_=endNodes2, to=startNodes2, from_layer=1, to_layer=1, \
                    dmax=1, upload='cat', table=duplicTable2, overwrite=True)
    gs.run_command('db.select', table=duplicTable2, separator='comma', output=duplicFile2, overwrite=True)
    
    duplics, dfEnds = findDuplics(vecLines5, sparsePts2, duplicFile1, duplicFile2)
    
    gs.run_command('v.edit', map_=vecLines5, tool='delete', cats=duplics)

#%% Find which segments originally connected to each other (even if not actual flow dir)

dfEnds=dfEnds[dfEnds['from_cat']!=dfEnds['cat']].reset_index(drop=True)

# Keep track of original category numbers
orig_cats = gs.read_command('v.category', input_=vecLines1, option='print')
ls_orig_cats = orig_cats.split('\r\n')
ls_orig_cats = pd.Series(ls_orig_cats[:-1]).astype('int')
fIDs = np.arange(1, len(ls_orig_cats)+1)

dfOrig = pd.DataFrame({'cat': fIDs, 'orig_cat': ls_orig_cats})
dfOrig.to_csv(tmpFiles + 'origCats.txt', index=False)

### We have a table showing all connections, 
### but we narrow this down to connections b/w segments that had same original cat
from_cats, to_cats=[], []

for i in range(len(dfEnds)):
    row=dfEnds.iloc[i]
    
    # These are their cat numbers in the split layer
    f_cat, t_cat=row['from_cat'], row['cat']
    
    # These are their cat numbers from the original layer (unbroken)
    f_orig=dfOrig['orig_cat'][dfOrig['cat']==f_cat].iloc[0]
    t_orig=dfOrig['orig_cat'][dfOrig['cat']==t_cat].iloc[0]
    
    # If they came from the same original cat, add them to the to/from columns
    if f_orig==t_orig: 
        from_cats+=[f_cat]
        to_cats+=[t_cat]
        
# Create a directed graph of segments that came from the same original lines
mergedLines=pd.DataFrame({'from':from_cats, 'to':to_cats})
graph = nx.from_pandas_edgelist(mergedLines, source='from', target='to', create_using=nx.DiGraph)  

### We will construct chains of segments, and keep track of the first in the chain
### Chains should have 1 segment feeding into 1, & shouldn't have forks/branches
chainDf = pd.DataFrame({'root': fIDs})
chainDf['chain']=''

for lcat in fIDs:
    # If a segment isn't in the directed graph, it forms its own chain
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
        chainDf.loc[segment-1, 'chain']=str(chain)
    
chainDf['us_chain']=''
chainDf['us_len']=np.nan
chainDf.to_csv(chainFile, index=False)

### Get points spaced 1m apart along the new lines
### Will be used to take cross-sectional profiles
if not gdb.map_exists(profilePts, 'vector'):
    gs.run_command('v.to.points', input_=vecLines5, output=profilePts, dmax=1)
    gs.run_command('v.to.db', map_=profilePts, layer=2, option='coor', columns=['x', 'y'])
    gs.run_command('v.db.select', map_=profilePts, layer=2, format_='csv', file=alongFile, overwrite=True)



