# -*- coding: utf-8 -*-
"""
Created on Wed May 21 11:03:19 2025

@author: Uma
"""

def removeCulverts(tmpFiles, layerPrefix, hucPrefix, \
                   culvertBuffers, ditchLines, demForNull, demForBurn):
    """ Takes two file prefixes: tmpFiles, layerPrefix, hucPrefix
        Also takes GIS layer names
            - culvertBuffers: vector areas showing radius around culverts
            - ditchLines: vector lines showing ditches
            - demForNull: raster to set areas to null
            - demForBurn: raster to burn drainage into
        Creates layer showing portions of ditches that pass through culverts,
        interpolates surfaces in these areas, 
        and replaces original raster with burned drainage
        """
        
    import grass.script as gs
    import grass.grassdb.data as gdb
    
    # Define layer names first, will be created later
    
    culvertLines = layerPrefix + '_culvertLines' # segment of ditch that passes through culvert
    culvertEndpts = layerPrefix + '_culvertEndpoints'
    culvertMask = layerPrefix + '_culvertMask'
    culvertRaster = layerPrefix + '_culvertSurf'
     
    demNull = layerPrefix + '_wNulls'
    demBurned = layerPrefix + '_burned'
    
    # newPts has the hucPrefix because we only need to create it once 
    # across multiple iterations
    newPts = hucPrefix + '_shiftedVertices'
    newElevFile = tmpFiles + layerPrefix + '_elevProfile_shiftedDitches.txt'
    
    if not gdb.map_exists(demBurned, 'raster'):
        gs.run_command('g.region', raster=demForNull)
        
        # Find where buffers intersect the ditch lines
        gs.run_command('v.overlay', ainput=ditchLines, atype='line', binput=culvertBuffers, \
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
        gs.run_command('v.what.rast', map_=culvertEndpts, raster=demForBurn, column='elev', layer=2, overwrite=True)
        # Interpolate a surface from these points
        gs.run_command('v.surf.rst', input_=culvertEndpts, zcolumn='elev', \
                        elevation=culvertRaster, mask=culvertMask, layer=2)
        # Now patch the interpolated section with the original DEM,
        # using the interpolated part as the primary raster
        gs.run_command('r.patch', input_=[culvertRaster,demForBurn], output=demBurned, overwrite=True)
    
        ### Create null regions where the culvert regions are
        expr=demNull + '=if(isnull('+ culvertMask+ '),' + demForNull + ', 0)'
        gs.run_command('r.mapcalc', expression=expr)
        gs.run_command('r.null', map_=demNull, setnull=0)
        
    if not gdb.map_exists(newPts, 'vector'):
        gs.run_command('v.to.points', input_=ditchLines, dmax=1, output=newPts)
        gs.run_command('v.to.db', map_=newPts, layer=2, option='coor', columns=['x', 'y'])
        
    gs.run_command('v.what.rast', map_=newPts, raster=demNull, column='elev', layer=2)
    gs.run_command('v.db.select', map_=newPts, layer=2, format_='csv', file=newElevFile, overwrite=True)


 


