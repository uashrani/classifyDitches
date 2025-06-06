# -*- coding: utf-8 -*-
"""
Created on Wed May 21 11:03:19 2025

@author: Uma
"""

#%% Prerequisite modules, data, and folders

import grass.script as gs
import grass.grassdb.data as gdb
import pandas as pd

# Folder names
tmpFiles = 'tempFiles/'

hucPrefix='testDEM2' # use for operations that need the DEM
ditchPrefix='BRR' # use for operations involving the entire ditch layer

# We need roads vector data, ditch vector data, and elevation raster data
roads = 'gis_osm_roads_free_1'
railroads = 'rail_lines'
bridges = 'Bridge_locations_in_Minnesota'
airports = 'Airport_Runways_in_Minnesota'
ditches = ditchPrefix + '_lines_filtered'
dem = 'ambigDEM2'
#%% Layers/files that will be created automatically

intersectTable = ditchPrefix + '_intersect'

pointDefFile = tmpFiles + ditchPrefix + '_culvertPtDefs.txt'   # file that GRASS will read from 

culvertPts = ditchPrefix + '_culvertPoints'   # points layer of culvert locations
culvertBuffers = ditchPrefix + '_culvertBuffers'  # vector layer containing circles around the culvert points
culvertLines = ditchPrefix + '_culvertLines'    # segment of ditch that passes through culvert
culvertEndpts = ditchPrefix + '_culvertEndpoints' 

culvertMask = ditchPrefix + '_culvertMask'
nullMask = ditchPrefix + '_culvertMaskWide'

culvertRaster = hucPrefix + '_culvertSurf'

demBurned = hucPrefix + '_burned'
demNull = hucPrefix + '_wNulls'

#%% Actual code

gs.run_command('g.region', vector=ditches)

### Start by finding intersection points between roads and ditches, & create vector layer
if not gdb.map_exists(culvertLines, 'vector'):
    layers=[roads, railroads, bridges, airports]
    suffix = ['Roads', 'Railroads', 'Bridges', 'Airports']
    dmax = [0, 0, 75, 100]  # max distance between ditches and this layer
    buffers = [25, 50, 25, 25]  # width of the culvert
    
    for (i,layer) in enumerate(layers):
        tabName = intersectTable+suffix[i]
        fileName = tmpFiles + tabName + '.txt'
        
        # Temporary: drop table because overwrite doesn't work
        gs.run_command('db.droptable', flags='f', table=tabName)
        gs.run_command('v.distance', flags='a', from_=ditches, to=layer, upload=['to_x', 'to_y'], \
                       dmax=dmax[i], table=tabName)
        gs.run_command('db.select', table=tabName, separator='comma', output=fileName, overwrite=True) 
        
        df = pd.read_csv(fileName)
        df['buffer']=buffers[i]
        
        if i==0:
            intersectDf = df
        else:
            intersectDf = pd.concat((intersectDf, df)).reset_index(drop=True) 
           
    intersectDf.to_csv(pointDefFile, index=False, columns=['to_x', 'to_y', 'buffer'], header=False)
    
    # Create a points layer based on this file
    gs.run_command('v.in.ascii', input_=pointDefFile, output=culvertPts, \
                   separator='comma', columns=['x double precision', 'y double precision', 'buffer int'])
    
    ### Now find portions of ditches that go through a culvert
    # Buffer the culvert points
    gs.run_command('v.buffer', input_=culvertPts, type_='point', \
                    output=culvertBuffers, column='buffer', layer=1)
    # Then find where these buffers intersect the ditch lines
    gs.run_command('v.overlay', ainput=ditches, atype='line', binput=culvertBuffers, \
                    operator='and', output=culvertLines)

    # First find the endpoints of each culvert segment
    gs.run_command('v.to.points', input_=culvertLines, output=culvertEndpts, use='node', overwrite=True)
    
    # Also, we need a narrow mask (for burning drainage), only in regions where culverts are
    gs.run_command('v.buffer', flags='c', input_=culvertLines, type_='line', output=culvertMask, \
                    distance=3) 
    # Above is a vector, but we need a raster mask
    gs.run_command('v.to.rast', input_=culvertMask, type_='area', output=culvertMask, use='value')
    
    # Do the same but for a wide mask (for setting nulls)
    gs.run_command('v.buffer', flags='c', input_=culvertLines, type_='line', output=nullMask, \
                    distance=10) 
    gs.run_command('v.to.rast', input_=nullMask, type_='area', output=nullMask, use='value')
    
### Create interpolated surfaces where the culvert regions are
gs.run_command('g.region', raster=dem)

# Get elevation values at endpoints of culvert segments
gs.run_command('v.what.rast', map_=culvertEndpts, raster=dem, column='elev', layer=2, overwrite=True)
# Interpolate a surface from these points
gs.run_command('v.surf.rst', input_=culvertEndpts, zcolumn='elev', \
                elevation=culvertRaster, mask=culvertMask, layer=2)
# Now patch the interpolated section with the original DEM,
# using the interpolated part as the primary raster
gs.run_command('r.patch', input_=[culvertRaster,dem], output=demBurned)

### Create null regions where the culvert regions are
expr=demNull + '=if(isnull('+ nullMask+ '),' + dem + ', 0)'
gs.run_command('r.mapcalc', expression=expr)
gs.run_command('r.null', map_=demNull, setnull=0)


 


