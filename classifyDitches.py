import grass.script as gs
import grass.grassdb.data as gdb
import pandas as pd

vecLines1='drainage_centerlines'   # name of ditch layer in Grass, already imported
vecLines2='ditch_lines_nameless'
vecLines='ditch_lines_renamed'
vecPoints='ditch_nodes'

combTable='ditchCombinations'     # distances between points and lines, can find distances between every pair of ditches

# Names of files to export from Grass
combFile='ditchCombinations.txt'        # has distances from points to lines
ptFile='ditchNodes.txt'                 # has point attributes like elevation and xy coords

# External link to data
dem='mnDEM'

### Lines were split at points when imported, but their category number didn't change (only feature ID did)
### Create new attribute table so every segment has unique category number

# Delete old category numbers and assign new category number to each segment
gs.run_command('v.category', input=vecLines1, output=vecLines2, option='del', cat=-1, overwrite=True)
gs.run_command('v.category', input=vecLines2, output=vecLines, option='add', overwrite=True)

# Disconnect from old attribute table and create new one
gs.run_command('db.droptable', flags='f', table=vecLines)
gs.run_command('v.db.connect', flags='d', map=vecLines, layer=1)
gs.run_command('v.db.addtable', map=vecLines)

### Extract start and end point numbers, their xy coordinates, and their elevations
gs.run_command('v.to.points', input=vecLines, output=vecPoints, use='node', overwrite=True)
gs.run_command('v.to.db', map=vecPoints, layer=2, option='coor', columns=['x', 'y'], overwrite=True)
gs.run_command('v.what.rast', map=vecPoints, layer=2, raster=dem, column=['elev'])
 
### Find intersections with other ditches

# Get distances from nodes to all nearby lines, and save in table
gs.run_command('v.distance', flags='a', from_=vecPoints, from_layer=2, to=vecPoints, to_layer=2, dmax=1, \
upload=['dist', 'cat'], table=combTable, overwrite=True)
# Export to csv
gs.run_command('db.select', table=combTable, output=combFile, separator='comma', overwrite=True)
#gs.run_command('v.distance', flags='a', _from=vecPoints, from_layer=2, to=vecLines, dmax=1, upload=['dist', 'cat'], table=combTable)

### -------------------------------------------
# ditchCombs = pd.read_csv(combFile)
# ditchNodes = pd.read_csv(ptFile)

# ditchCombs = ditchCombs.rename(columns={'from_cat': 'fromPt', 'cat': 'toLine'})

# print(ditchNodes)

# #fromLines = []
# ditchCombs['junction']=False

# for i in range(len(ditchCombs)):
#     fromPt = ditchCombs['fromPt'].iloc[i]

#     # Find the corresponding entry in ditchNodes with that point number
#     nodesEntry = ditchNodes[ditchNodes['cat']==fromPt].iloc[0]

#     fromLine = nodesEntry['lcat']
#     #fromLines += [fromLine]

#     if fromLine != ditchCombs['toLine'].iloc[i]:
#         ditchCombs.loc[i, 'junction'] = True

#         ### Verify that junction is downstream end of ditch
        
#         # Get the points that lie along the same line
#         siblingPts = ditchNodes[ditchNodes['lcat']==fromLine]
#         minElev = min(siblingPts['elev'])
#         if nodesEntry['elev'] > minElev:
#             print(str(fromPt) + '\tJunction is not downstream end of incoming ditch')
#         else:
#             print(str(fromPt) + '\tMin elev of line ' + str(fromLine) + ' is ' + str(minElev))

#     #nodesEntry['elev']

# #ditchCombs['fromLine']=fromLines
# #ditchCombs['junction']=(ditchCombs['fromLine']!=ditchCombs['toLine'])

# ditchJuncs = ditchCombs[ditchCombs['junction']==True]

# #print(ditchJuncs)




