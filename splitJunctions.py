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
vecLines4=ditchPrefix + '_lines_filtered'

vecPoints1=ditchPrefix + '_nodes_old'  

intersectTable = ditchPrefix + '_intersections'

# Names of files to export from Grass
ptFileTemp=tmpFiles + ditchPrefix + '_nodes.txt'
intersectFileTemp=tmpFiles + ditchPrefix + '_intersections.txt'

# Start and end points, and duplicates
startNodes = ditchPrefix + '_startsTemp'
endNodes = ditchPrefix + '_endsTemp'
connectTable = ditchPrefix + '_flowConnections'

connectFile=tmpFiles + 'mergeLines.txt'
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

#%% Split lines at intersections, and on nodes along line

# Temporary: drop table because overwrite doesn't work
#gs.run_command('db.droptable', flags='f', table=intersectTable)

gs.run_command('g.region', vector=vecLines0)

if not gdb.map_exists(vecLines4, 'vector'):
    gs.run_command('g.copy', vector=[vecLines0, vecLines1])
    
    # Get list of all nodes and their xy coordinates, will split lines at these points
    gs.run_command('v.to.points', input_=vecLines1, output=vecPoints1, use='node', overwrite=True)
    gs.run_command('v.to.db', map_=vecPoints1, layer=2, option='coor', columns=['x', 'y'], overwrite=True)
    # Export attribute table of these points
    gs.run_command('v.db.select', map_=vecPoints1, layer=2, format_='csv', file=ptFileTemp, overwrite=True)
    
    # Also get intersections between lines, since there is not always a node at the intersection
    gs.run_command('v.distance', flags='a', from_=vecLines1, to=vecLines1, dmax=10, \
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
    gs.run_command('v.db.droprow', input_=vecLines3, where="len < 0.1", output=vecLines4, overwrite=True)

### Find segments to concatenate
### and identify which lines may be duplicates
if not gdb.map_exists(endNodes, 'vector'):
    # Create layers for start and end points
    gs.run_command('v.to.points', input_=vecLines4, output=startNodes, use='start', overwrite=True)
    gs.run_command('v.to.points', input_=vecLines4, output=endNodes, use='end', overwrite=True)
    # Find where the end of one segment flows into the start of another
    gs.run_command('v.distance', flags='a', from_=endNodes, to=startNodes, from_layer=1, to_layer=2, \
                    dmax=0.2, upload='to_attr', to_column='lcat', column='to_lcat', \
                        table= connectTable, overwrite=True)
    
    gs.run_command('db.select', table=connectTable, separator='comma', output=connectFile, overwrite=True)
    
#%% Find which segments originally connected to each other (even if not actual flow dir)

dfEnds=pd.read_csv(connectFile)
dfEnds=dfEnds[dfEnds['from_cat']!=dfEnds['to_lcat']].reset_index(drop=True)

# Keep track of original category numbers
orig_cats = gs.read_command('v.category', input_=vecLines1, option='print')
ls_orig_cats = orig_cats.split('\r\n')
ls_orig_cats = pd.Series(ls_orig_cats[:-1]).astype('int')
fIDs = np.arange(1, len(ls_orig_cats)+1)

dfOrig = pd.DataFrame({'cat': fIDs, 'orig_cat': ls_orig_cats})
#dfOrig.to_csv(tmpFiles + 'origCats.txt')

### We have a table showing all connections, 
### but we narrow this down to connections b/w segments that had same original cat
from_cats, to_cats=[], []

for i in range(len(dfEnds)):
    row=dfEnds.iloc[i]
    
    # These are their cat numbers in the split layer
    f_cat, t_cat=row['from_cat'], row['to_lcat']
    
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
### Will be used to take transects and check for duplicates
if not gdb.map_exists(profilePts, 'vector'):
    gs.run_command('v.to.points', input_=vecLines4, output=profilePts, dmax=1)
    gs.run_command('v.to.db', map_=profilePts, layer=2, option='coor', columns=['x', 'y'])
    gs.run_command('v.db.select', map_=profilePts, layer=2, format_='csv', file=alongFile, overwrite=True)

