# -*- coding: utf-8 -*-
"""
Created on Wed May 21 11:03:19 2025

@author: Uma
"""

# we need the lines, cats, buffer width,  

def interpSurface(tmpFiles, layerPrefix, lineSegments, bufferWidth, demForBurn, \
                   demForNull='', cats=[]):
    """ Prefixes
            - tmpFiles: folder to save temporary files to
            - layerPrefix: the burned DEM will have this in the name
        GIS Layers
            - lineSegments: either a line perpendicular to the ditch (used for 
                infilling ditches), or the segment of the ditch that passes 
                through a culvert
            - demForBurn: name of DEM to copy and burn drainage into 
            - demForNull: name of DEM to copy and set null regions
        Other parameters
            - bufferWidth: width in m to buffer the line
            - cats: which ditches to infill (leave blank if removing culverts) """
        
    import grass.script as gs
    import grass.grassdb.data as gdb
    import pandas as pd
    import os
    import shutil
    
    # Define layer names first, will be created later
    linesBuffered = lineSegments + '_buffered'
    boundaries = lineSegments + '_boundaries'
    vertices = lineSegments + '_vertices'
    vertexFile = tmpFiles + vertices + '.txt'
    boundaryCats = boundaries + 'Cats'
    
    interpPts = layerPrefix + '_interpPts'
    interpSurf = layerPrefix + '_interpSurf'
     
    demNull = layerPrefix + '_wNulls'
    demBurned = layerPrefix + '_interpDEM'
    
    if not gdb.map_exists(boundaryCats, 'vector'):
        gs.run_command('g.region', raster=demForBurn)
        
        gs.run_command('v.buffer', flags='c', input_=lineSegments, type_='line', output=linesBuffered, \
                        distance=bufferWidth) 
        gs.run_command('v.type', input_=linesBuffered, output=boundaries, \
                       from_type='boundary', to_type='line')
            
        gs.run_command('v.to.points', input_=boundaries, output=vertices, use='vertex', \
                       layer=-1)
        gs.run_command('v.to.db', map_=vertices, option='coor', columns=['x', 'y'], layer=2)
        gs.run_command('v.db.select', map_=vertices, layer=2, format_='csv', \
                       file=vertexFile, overwrite=True)

        cornerDf = pd.read_csv(vertexFile)
        cornerDf = cornerDf[cornerDf['along']!=0]
        
        for i in range(len(cornerDf)):
            x,y=cornerDf['x'].iloc[i],cornerDf['y'].iloc[i]
            gs.run_command('v.edit', map_=boundaries, type_='line', tool='break', \
                           coords=[x,y])
                
        gs.run_command('v.edit', map_=boundaries, tool='delete', \
                        type_='line', query='length', threshold=[-1,0,-0.1])
        gs.run_command('v.category', input_=boundaries, output_=boundaryCats, \
                       type_='line', option='add')
        gs.run_command('v.db.addtable', map_=boundaryCats)
        gs.run_command('v.db.addcolumn', map_=boundaryCats, columns='to_cat int')
        gs.run_command('v.distance', from_=boundaryCats, to=lineSegments, dmax=0.1, \
                       upload='cat', column='to_cat')
        gs.run_command('v.edit', map_=boundaryCats, tool='delete', \
                       where='to_cat is null')
     
    if cats != [] and not gdb.map_exists(layerPrefix + '_linesBuffered', 'vector'):
        linesBuffered = layerPrefix + '_linesBuffered'
        boundaryCats2 = layerPrefix + '_boundariesCats'
        
        expr = 'to_cat in ' + str(cats).replace('[','(').replace(']',')')
    
        # We want the polygons and the lines on either side of the surface
        gs.run_command('v.extract', input_=boundaryCats, where=expr, \
                       output=boundaryCats2)
        gs.run_command('v.buffer', flags='c', input_=lineSegments, type_='line', output=linesBuffered, \
                        distance=bufferWidth, cats=cats) 
        
        boundaryCats=boundaryCats2

    if not gdb.map_exists(demBurned, 'raster'):
        gs.run_command('v.to.points', input_=boundaryCats, type_='line', \
                        output=interpPts, dmax=1, layer=-1)
            
        gs.run_command('v.what.rast', map_=interpPts, raster=demForBurn, column='elev', \
                        layer=2)
        gs.run_command('r.mask', vector=linesBuffered)
        gs.run_command('v.surf.idw', input_=interpPts, layer=2, column='elev', \
                        output=interpSurf)
            
        # Kind of dangerous maybe but deleting r.mask doesn't work
        path=gs.read_command('g.gisenv', get=['GISDBASE','LOCATION_NAME','MAPSET'],\
                              sep='/').replace('\\', '/')
        path=path.strip()+'/cell_misc/MASK'
        os.chmod(path,0o777)
        shutil.rmtree(path)
        
        gs.run_command('r.mask', flags='r')
        gs.run_command('r.patch', input_=[interpSurf,demForBurn], output=demBurned)
     
    if demForNull != '' and not gdb.map_exists(demNull, 'raster'):
        ### Create null regions where the culvert regions are
        gs.run_command('v.to.rast', input_=linesBuffered, type_='area', \
                       output=linesBuffered, use='value')
        expr=demNull + '=if(isnull('+linesBuffered+ '),' + demForNull + ', 0)'
        gs.run_command('r.mapcalc', expression=expr)
        gs.run_command('r.null', map_=demNull, setnull=0)
        
    return(demBurned,demNull)

 


