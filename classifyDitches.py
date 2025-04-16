import grass.script as gs 

vecLines = 'drainage_centerlines'   # name of ditch layer in Grass, already imported
vecPoints = 'ditch_nodes'            # name of start/end points, will be created from line data

combTable = 'ditchCombinations'     # distances between points and lines, can find distances between every pair of ditches

combFile = 'ditchCombinations.txt'
ptFile = 'ditchNodes.txt'

# Extract start and end points from ditch lines
gs.run_command('v.to.points', input=vecLines, output=vecPoints, use='node', overwrite=True)
# Get xy coordinates of the points
gs.run_command('v.to.db', map=vecPoints, layer=2, option='coor', columns=['x', 'y'], overwrite=True)

### In addition to start and end points, we also want to know intersections with other ditches

# Get distances from nodes to all nearby lines, and save in table
gs.run_command('v.distance', vecPoints, from_layer=2, to=vecLines, dmax=1, upload=['dist', 'cat'], table=combTable, flags='a', overwrite=True)
# Export the table to a text file
gs.run_command('db.select', table=combTable, output=combFile, overwrite=True)
gs.run_command('v.db.select', map=vecPoints, format='csv', file=ptFile, overwrite=True)


