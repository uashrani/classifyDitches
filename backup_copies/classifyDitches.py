import grass.script as gs
import grass.grassdb.data as gdb
import pandas as pd
import numpy as np

vecLines0='drainage_centerlines'
vecLines1='drainage_centerlines_modifiable'   # name of ditch layer in Grass, already imported
vecLines2='ditch_lines_nameless'
vecLines3='ditch_lines_renamed'
vecLines='ditch_lines_final'
vecPoints1='ditch_nodes_old'  
vecPoints='ditch_nodes'

combTable='ditchCombinations'     # distances between points and lines, can find distances between every pair of ditches
intersectTable='ditchIntersections'

# Names of files to export from Grass
combFile='ditchCombinations.txt'        # has distances from points to lines
ptFile='ditchNodes.txt'                 # has point attributes like elevation and xy coords

ptFileTemp='ditchNodesTemp.txt'
intersectFileTemp='ditchIntersections.txt'

# External link to data
dem='mnDEM'
### Function definitions----------------------------------------------------------------------------------

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
        breakDf[col] = breakDf[col].round(2)

    breakDf['tuple'] = '(' + breakDf['x'].astype('str') + ',' + breakDf['y'].astype('str') + ')'

    tupleSet = set(breakDf['tuple'])

    for elt in tupleSet:
        elt = elt.strip('()')
        x, y = tuple(map(float,elt.split(',')))

        gs.run_command('v.edit', map=linesLayer, tool='break', coords=[x,y], threshold=1)

### ------------------------------------------------------------------------------------------------------
# Temporary: drop table because overwrite doesn't work
gs.run_command('db.droptable', flags='f', table=intersectTable)

if not gdb.map_exists(vecLines1, 'vector'):
    gs.run_command('g.copy', vector=[vecLines0, vecLines1])

    # Get list of all nodes and their xy coordinates, will split lines at these points
    gs.run_command('v.to.points', input=vecLines1, output=vecPoints1, use='node', overwrite=True)
    gs.run_command('v.to.db', map=vecPoints1, layer=2, option='coor', columns=['x', 'y'], overwrite=True)
    # Export attribute table of these points
    gs.run_command('v.db.select', map=vecPoints1, layer=2, format='csv', file=ptFileTemp, overwrite=True)
    breakPoints = pd.read_csv(ptFileTemp)

    # Also get intersections between lines, since there is not always a node at the intersection
    gs.run_command('v.distance', flags='a', from_=vecLines1, to=vecLines1, dmax=1, \
        upload=['to_x', 'to_y', 'cat'], table=intersectTable, overwrite=True)
    gs.run_command('db.select', table=intersectTable, separator='comma', output=intersectFileTemp, overwrite=True)

    split_nodesIntersects(ptFileTemp, intersectFileTemp, vecLines1)

    # Split up the lines at these points. Some have multiple intermediate points
    # for i in range(len(breakPoints)):
    #     breakPt = breakPoints.iloc[i]
    #     x,y = breakPt['x'], breakPt['y']
    #     gs.run_command('v.edit', map=vecLines1, tool='break', coords=[x, y], threshold=1)

### When we split lines into segments, their category number didn't change (only feature ID did)
### Create new attribute table so every segment has unique category number

# Delete old category numbers and assign new category number to each segment
gs.run_command('v.category', input=vecLines1, output=vecLines2, option='del', cat=-1, overwrite=True)
gs.run_command('v.category', input=vecLines2, output=vecLines3, option='add', overwrite=True)

# Disconnect from old attribute table and create new one
gs.run_command('db.droptable', flags='f', table=vecLines3)
gs.run_command('v.db.connect', flags='d', map=vecLines3, layer=1)
gs.run_command('v.db.addtable', map=vecLines3)

# But we still want to keep track of which ditch it originally came from in case we need county info etc.
# gs.run_command('v.db.addcolumn', map=vecLines, columns=['ditch_orig int'])
# for i in range(1, 672):        # fix this later
#     orig_cat = gs.read_command('v.category', input=vecLines1, option='print', ids=i)
#     gs.run_command('v.db.update', map=vecLines, column='ditch_orig', value=4, where='"cat='+str(i)+'"')

gs.run_command('v.to.db', map=vecLines3, option='length', columns=['len'])
gs.run_command('v.db.droprow', input=vecLines3, where="len<0.01", output=vecLines, overwrite=True)

### Extract start and end point numbers, their xy coordinates, and their elevations
gs.run_command('v.to.points', input=vecLines, output=vecPoints, use='node', overwrite=True)
gs.run_command('v.to.db', map=vecPoints, layer=2, option='coor', columns=['x', 'y'], overwrite=True)
gs.run_command('v.what.rast', map=vecPoints, layer=2, raster=dem, column=['elev'])
 
### Find distances to other ditches (doesn't necessarily mean flow is transferred, will process later)

# Temporary: drop table because overwrite doesn't work
gs.run_command('db.droptable', flags='f', table=combTable)

# Get distances from nodes to all nearby lines, and save in table
gs.run_command('v.distance', flags='a', from_=vecPoints, from_layer=2, to=vecPoints, to_layer=2, dmax=1, \
upload=['dist', 'cat'], table=combTable, overwrite=True)
# Export to csv
gs.run_command('db.select', table=combTable, output=combFile, separator='comma', overwrite=True)
gs.run_command('v.db.select', map=vecPoints, layer=2, format='csv', file=ptFile, overwrite=True)

###---------- Process these csv's and find where flow is really being transferred

ditchCombs = pd.read_csv(combFile)
ditchNodes = pd.read_csv(ptFile)

ditchCombs = ditchCombs.rename(columns={'from_cat': 'fromPt', 'cat': 'toPt'})

### First look at the nodes csv, and label each as upstream or downstream

ditchNodes['ds']=False
for i in range(len(ditchNodes)):
    thisEntry=ditchNodes.iloc[i]
    thisPt=thisEntry['cat']
    thisLine=thisEntry['lcat']
    siblingEntry=ditchNodes[(ditchNodes['lcat']==thisLine) & \
        (ditchNodes['cat'] != thisPt)].iloc[0]

    if thisEntry['elev'] < siblingEntry['elev']:
        ditchNodes.loc[i, 'ds'] = True

### In ditch combinations csv, find associated line for each point
### and determine flow direction between ditches

ditchCombs['fromLine']=np.nan
ditchCombs['toLine']=np.nan

for i in range(len(ditchCombs)):
    entry = ditchCombs.iloc[i]
    fromPt, toPt = entry['fromPt'], entry['toPt']

    # v.distance identified a duplicate for each point (e.g. pt 1 intersects pt 1),
    # so skip these as they are not real junctions
    if fromPt != toPt:
        # Find the corresponding lines with those point numbers
        fromEntry_nodes = ditchNodes[ditchNodes['cat']==fromPt].iloc[0]

        toEntry_nodes = ditchNodes[ditchNodes['cat']==toPt].iloc[0]

        # Flow transfer happens when the downstream node of the giving segment
        # intersects the upstream node of the receiving segment
        if (fromEntry_nodes['ds']==True) and (toEntry_nodes['ds']==False):
            # This is a real junction, so get info about the line numbers
            fromLine, toLine = fromEntry_nodes['lcat'], toEntry_nodes['lcat']

            # Enter line numbers into columns
            if fromLine != toLine: 
                ditchCombs.loc[i, 'fromLine'] = fromLine
                ditchCombs.loc[i, 'toLine'] = toLine

ditchNodes.to_csv('final_' + ptFile, index=False, sep='\t', float_format='%.1f')
ditchCombs.to_csv('final_' + combFile, index=False, sep='\t', float_format='%.3f')
