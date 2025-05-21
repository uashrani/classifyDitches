# -*- coding: utf-8 -*-
"""
Created on Wed May 21 11:03:19 2025

@author: Uma
"""

import grass.script as gs
import grass.grassdb.data as gdb
import pandas as pd

# We need roads vector data, ditch vector data, and elevation raster data
roads = 'gis_osm_roads_free_1'
ditches = 'drainage_centerlines'
dem = 'ambigDEM2'

# Folder names
tmpFiles = 'tempFiles/'

# Names of files/layers to be created
intersectTable = 'culvertLocs2'    # table of road-ditch intersections
intersectFile = tmpFiles + intersectTable + '.txt'
pointDefFile = tmpFiles + 'culvertPtDefs.txt'   # file that GRASS will read from 
intersectionPts = 'intersectionPoints'    # points layer of road-ditch intersections
culvertBuffers = 'bufferedPoints'   # vector layer containing circles around the culvert points
culvertLines = 'culvertLines'
culvertEndpts = 'culvertEndpoints'
culvertProfPts = 'culvertProfilePts'

### ---------------------------------------------------------------

### Start by finding intersection points between roads and ditches, & create vector layer
if not gdb.map_exists(intersectionPts, 'vector'):
    # Temporary: drop table because overwrite doesn't work
    #gs.run_command('db.droptable', flags='f', table=intersectTable)
    
    # Find all intersections and add these to table
    gs.run_command('v.distance', flags='a', from_=ditches, to=roads, upload=['to_x', 'to_y'], \
                   dmax=0, table=intersectTable)
    gs.run_command('db.select', table=intersectTable, separator='comma', output=intersectFile, overwrite=True)
    # Write these points to a file so GRASS can create vector layer from it
    df=pd.read_csv(intersectFile)
    xyFmt = ' ' + df['to_x'].astype('str') + ' ' + df['to_y'].astype('str')
    #df.to_csv(pointDefFile, columns=['xyFmt'], index=False, header=[])
    
    f=open(pointDefFile, 'a')
    for (i,row) in enumerate(xyFmt):
        f.write('P  1 1' + '\n')
        f.write(row + '\n')
        f.write(' 1 ' + str(i+1) + '\n')
    f.close()
    
    # Create a points layer based on this file
    gs.run_command('v.edit', map_=intersectionPts, type_='point', tool='create', overwrite=True)
    gs.run_command('v.edit', flags='n', map_=intersectionPts, tool='add', input_=pointDefFile)
    
### Now find portions of ditches that go through a culvert
# First buffer the intersection points by a 25m radius
gs.run_command('v.buffer', input_=intersectionPts, type_='point', \
               output=culvertBuffers, distance=25)
# Then find where these buffers intersect the ditch lines
gs.run_command('v.overlay', ainput=ditches, atype='line', binput=culvertBuffers, \
               operator='and', output=culvertLines)

### Now interpolate an elevation profile along culvert segments
# First find the endpoints of each culvert segment
gs.run_command('v.to.points', input_=culvertLines, output=culvertEndpts, use='node')
# Now get elevation values at these endpoints
gs.run_command('v.what.rast', map_=culvertEndpts, raster=dem, column='elev')

# Now we need the points that run all along the culvert segments 
gs.run_command('v.to.points', input_=culvertLines, output=culvertProfPts, dmax=1)
gs.run_command('v.db.addcolumn', map_=culvertProfPts, layer=2, columns=['elev double precision'])

# We chose a wide buffer distance for the culverts,
# so we can assume the endpoints are in the actual ditch and not on the bridge.
# We can interpolate between them to fill in the missing data under the culvert






 


