import grass.script as gs
import grass.grassdb.data as gdb
import pandas as pd

vecLines1='drainage_centerlines'   # name of ditch layer in Grass, already imported
vecLines='ditch_lines_broken'
vecPoints1='ditch_nodes_old'            # name of start/end points, will be created from line data
vecPoints='ditch_nodes'

combTable='ditchCombinations'     # distances between points and lines, can find distances between every pair of ditches

# Names of files exported from Grass
combFile='ditchCombinations.txt'        # has distances from points to lines
ptFile='ditchNodes.txt'                 # has point attributes like elevation and xy coords
ptFileTemp='ditchNodesTemp.txt'

# External link to data
dem='mnDEM'

# Extract start and end points from ditch lines
gs.run_command('v.to.points', input=vecLines1, output=vecPoints1, use='node', overwrite=True)
# Get xy coordinates of the points
gs.run_command('v.to.db', map=vecPoints1, layer=2, option='coor', columns=['x', 'y'], overwrite=True)
# Export attribute table of these points
gs.run_command('v.db.select', map=vecPoints1, layer=2, format='csv', file=ptFileTemp, overwrite=True)

breakPoints = pd.read_csv(ptFileTemp)

if not gdb.map_exists(vecLines, 'vector'):
    gs.run_command('g.copy', vector=[vecLines1, vecLines])
    # Split up the lines at these points. Some have multiple intermediate points
    for i in range(len(breakPoints)):
        breakPt = breakPoints.iloc[i]
        x,y = breakPt['x'], breakPt['y']
        gs.run_command('v.edit', map=vecLines, tool='break', coords=[x, y], threshold=1)

gs.run_command('v.to.points', input=vecLines, output=vecPoints, use='node')
 
### In addition to start and end points, we also want to know intersections with other ditches
 
# Get distances from nodes to all nearby lines, and save in table
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




