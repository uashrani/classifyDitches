# -*- coding: utf-8 -*-
"""
Created on Mon Jun  9 16:50:14 2025

@author: swimm
"""

#%% Prerequisite modules, data, and folders

import grass.script as gs
import grass.grassdb.data as gdb
import pandas as pd

# Folder names
tmpFiles = 'tempFiles2/'

ditchPrefix='BRR' # use for operations involving the entire ditch layer

# We need roads vector data, ditch vector data, and elevation raster data
roads = 'gis_osm_roads_free_1'
ctyRoads = ['roads_beckerCounty', 'roads_clayCounty', 'roads_wilkinCounty']     # list of TIGER county roads
railroads = 'rail_lines'
bridges = 'Bridge_locations_in_Minnesota'
airports = 'Airport_Runways_in_Minnesota'
ditches = ditchPrefix + '_lines_snapped'

#%% Layers/files that will be created automatically

roads2 = ditchPrefix + '_ctyRoads'

intersectTable = ditchPrefix + '_intersect'

culvertDefFile = tmpFiles + ditchPrefix + '_culvertPtDefs.txt'   # file that GRASS will read from 

ditchBuffers = ditchPrefix + '_lineBuffers'

culvertPts = ditchPrefix + '_culvertPoints'   # points layer of culvert locations
culvertBuffers = ditchPrefix + '_culvertBuffers'  # vector layer containing circles around the culvert points

#%% Actual code

gs.run_command('g.region', vector=ditches)

### Patch together the county roads into one layer
if len(ctyRoads) > 1:
    gs.run_command('v.patch', input_=ctyRoads, output=roads2)
else: 
    roads2 = ctyRoads[0]

### Start by finding intersection points between roads and ditches, & create vector layer
if not gdb.map_exists(culvertBuffers, 'vector'):
    ### A single road can loop back around and intersect the same ditch twice,
    ### but v.distance only recognizes this as one intersection.
    ### Use v.overlay in places where dmax=0, then get the center of the line? 
    gs.run_command('v.buffer', input_=ditches, type_='line', \
                   output=ditchBuffers, distance=0.01)
    
    layers=[roads, roads2, railroads, bridges, airports]
    suffixs = ['Roads', 'Roads2', 'Railroads', 'Bridges', 'Airports']
    dmaxs = [0, 0, 0, 60, 100]  # max distance between ditches and this layer
    buffers = [25, 25, 50, 50, 75]  # width of the culvert
    
    for (i, layer) in enumerate(layers):
        dmax, buffer, suffix = dmaxs[i], buffers[i], suffixs[i]
        tabName = intersectTable+suffix
        fileName = tmpFiles + tabName + '.txt'

        # Temporary: drop table because overwrite doesn't work
        if dmax > 0:
            gs.run_command('db.droptable', flags='f', table=tabName)
            gs.run_command('v.distance', flags='a', from_=layer, to=ditches, upload=['to_x', 'to_y', 'dist'], \
                           dmax=dmax, table=tabName)
            gs.run_command('db.select', table=tabName, separator='comma', output=fileName, overwrite=True) 
        else:
            gs.run_command('db.droptable', flags='f', table=tabName)
            gs.run_command('v.overlay', ainput=layer, atype='line', binput=ditchBuffers, \
                            operator='and', output=tabName)
            gs.run_command('v.to.db', map_=tabName, option='start', columns=['to_x', 'to_y'])
            gs.run_command('v.db.select', map_=tabName, format_='csv', file=fileName, overwrite=True)
        
        df = pd.read_csv(fileName)
        if suffix=='Bridges':
            df['buffer']=buffer + df['dist']
            df.loc[df['buffer']>100, 'buffer']=100
        else:
            df['buffer']=buffer
        
        if i==0:
            intersectDf = df
        else:
            intersectDf = pd.concat((intersectDf, df)).reset_index(drop=True) 
           
    intersectDf.to_csv(culvertDefFile, index=False, columns=['to_x', 'to_y', 'buffer'], header=False)
    
    # Create a points layer based on this file
    gs.run_command('v.in.ascii', input_=culvertDefFile, output=culvertPts, \
                   separator='comma', columns=['x double precision', 'y double precision', 'buffer double precision'])
    
    # Buffer the culvert points
    gs.run_command('v.buffer', input_=culvertPts, type_='point', \
                    output=culvertBuffers, column='buffer', layer=1)