# -*- coding: utf-8 -*-
"""
Created on Wed May 21 11:03:19 2025

@author: Uma
"""

#%% Prerequisite modules, data, and folders

import grass.script as gs

# Folder names
tmpFiles = 'tempFiles/'
hucPrefix='HUC_0902010603' # use for operations that need the DEM
ditchPrefix='BRR' # use for operations involving the entire ditch layer

# We need roads vector data, ditch vector data, and elevation raster data
ditchesCropped = hucPrefix + '_shiftedDitches'  # only covers extent of DEM
dem = 'HUC_0902010603'

culvertBuffers = ditchPrefix + '_culvertBuffers'  # vector layer containing circles around the culvert points

#%% Layers/files that will be created automatically
culvertLines = hucPrefix + '_culvertLines'    # segment of ditch that passes through culvert
culvertEndpts = hucPrefix + '_culvertEndpoints' 

culvertMask = hucPrefix + '_culvertMask'

culvertRaster = hucPrefix + '_culvertSurf'

demBurned = hucPrefix + '_burned'
demNull = hucPrefix + '_wNulls'

newPts = hucPrefix + '_shiftedVertices'
newElevFile = tmpFiles + hucPrefix + '_elevProfile_shiftedDitches.txt'
       
#%% Need DEM for this part
gs.run_command('g.region', raster=dem)

# Then find where these buffers intersect the ditch lines
gs.run_command('v.overlay', ainput=ditchesCropped, atype='line', binput=culvertBuffers, \
                operator='and', output=culvertLines)

# First find the endpoints of each culvert segment
gs.run_command('v.to.points', input_=culvertLines, output=culvertEndpts, use='node', overwrite=True)

# Also, we need a narrow mask (for burning drainage), only in regions where culverts are
gs.run_command('v.buffer', flags='c', input_=culvertLines, type_='line', output=culvertMask, \
                distance=3) 
# Above is a vector, but we need a raster mask
gs.run_command('v.to.rast', input_=culvertMask, type_='area', output=culvertMask, use='value')
    
### Create interpolated surfaces where the culvert regions are
# Get elevation values at endpoints of culvert segments
gs.run_command('v.what.rast', map_=culvertEndpts, raster=dem, column='elev', layer=2, overwrite=True)
# Interpolate a surface from these points
gs.run_command('v.surf.rst', input_=culvertEndpts, zcolumn='elev', \
                elevation=culvertRaster, mask=culvertMask, layer=2)
# Now patch the interpolated section with the original DEM,
# using the interpolated part as the primary raster
gs.run_command('r.patch', input_=[culvertRaster,dem], output=demBurned)

### Create null regions where the culvert regions are
expr=demNull + '=if(isnull('+ culvertMask+ '),' + dem + ', 0)'
gs.run_command('r.mapcalc', expression=expr)
gs.run_command('r.null', map_=demNull, setnull=0)

gs.run_command('v.to.points', input_=ditchesCropped, dmax=1, output=newPts)
gs.run_command('v.what.rast', map_=newPts, raster=demNull, column='elev', layer=2)
gs.run_command('v.db.select', map_=newPts, layer=2, format_='csv', file=newElevFile, overwrite=True)


 


