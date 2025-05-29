""" 
Author: Uma
"""

#%% Prerequisite modules, data, and folders

import grass.script as gs
import pandas as pd

vecLines1='drainage_centerlines'   # name of ditch layer in Grass, already imported

tmpFiles = 'tempFiles/'

ditchPrefix='BRR'

#%% Layers/files that will be created automatically

vecLines2=ditchPrefix + '_lines_nameless'
vecLines3=ditchPrefix + '_lines_renamed'
vecLines=ditchPrefix + '_lines_final'

vecPoints1=ditchPrefix + '_nodes_old'  

intersectTable = ditchPrefix + '_intersections'

# Names of files to export from Grass
ptFileTemp=tmpFiles + ditchPrefix + '_nodes.txt'
intersectFileTemp=tmpFiles + ditchPrefix + '_intersections.txt'

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
        breakDf[col] = breakDf[col].round(2)

    breakDf['tuple'] = '(' + breakDf['x'].astype('str') + ',' + breakDf['y'].astype('str') + ')'

    tupleSet = sorted(set(breakDf['tuple']))

    for elt in tupleSet:
        elt = elt.strip('()')
        x, y = tuple(map(float,elt.split(',')))

        gs.run_command('v.edit', map_=linesLayer, tool='break', coords=[x,y], threshold=1)

#%% Actual code

# Temporary: drop table because overwrite doesn't work
#gs.run_command('db.droptable', flags='f', table=intersectTable)

gs.run_command('g.region', vector=vecLines1)

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
#gs.run_command('v.db.droprow', input_=vecLines3, where="len<0.01", output=vecLines, overwrite=True)

# Keep track of original category numbers
gs.run_command('v.db.addcolumn', map_=vecLines3, columns='orig_cat int')
gs.run_command('v.distance', from_=vecLines3, to=vecLines1, upload='cat', column='orig_cat')

### Next create layers for start and end points, and find connections where 1 lcat --> 1 lcat and both are from same original line



### Get points spaced 1m apart along the new lines, will be used for transects
gs.run_command('v.to.points', input_=vecLines3, output=profilePts, dmax=1)
gs.run_command('v.to.db', map_=profilePts, layer=2, option='coor', columns=['x', 'y'])
gs.run_command('v.db.select', map_=profilePts, layer=2, format_='csv', file=alongFile, overwrite=True)

