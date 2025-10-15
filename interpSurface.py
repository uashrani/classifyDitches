# -*- coding: utf-8 -*-
"""
Created on Wed May 21 11:03:19 2025

@author: Uma
"""

# we need the lines, cats, buffer width,  

def interpSurface(tmpFiles, layerPrefix, lineSep, lineSegments, bufferWidth, demForBurn, \
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
    
    import transect
    
    # Define layer names first, will be created later

    lineEndpts = layerPrefix + '_endpoints'
    endptFile = tmpFiles + 'endptDef.txt'
    interpLines = layerPrefix + '_interpLines'
    interpLineFile = tmpFiles + 'interpLineDef.txt'
    
    linesBuffered = layerPrefix + '_buffered'
    
    interpPts = layerPrefix + '_interpPts'
    interpSurf = layerPrefix + '_interpSurf'
     
    demNull = layerPrefix + '_wNulls'
    demBurned = layerPrefix + '_interpDEM'
    
    if cats == []:
        allCats = gs.read_command('v.category', input_=lineSegments, option='print').split(lineSep)
        cats=list(map(int,allCats[:-1]))
    
    ### Create lines perpendicular to those inputted, will use for interpolation pts
    if not gdb.map_exists(linesBuffered, 'vector'):
        if os.path.exists(endptFile):
            os.remove(endptFile)
        f=open(endptFile, 'a')
        
        ptID = 1
        for lcat in cats:
            # Start with two points along the line, and get slope between them
            for sign in ['','-']:
                for dsLen in [0, 0.1]:
                    f.write('P ' + str(ptID) + ' ' + str(lcat) + ' ' + sign + \
                            str(dsLen) + '\n')
                    ptID += 1
        f.close()
        
        # These are points that lie along the line, near the endpoints
        gs.run_command('v.segment', input_=lineSegments, output=lineEndpts, rules=endptFile)
        gs.run_command('v.db.addtable', map_=lineEndpts)
        gs.run_command('v.to.db', map_=lineEndpts, option='coor', columns=['x','y'])
        gs.run_command('v.db.select', map_=lineEndpts, format_='csv', file=endptFile, overwrite=True)
        
        endptDf = pd.read_csv(endptFile)
        endptDf['lcat']=(endptDf['cat']-1)//2 + 1
        
        # Now use the points to get the xy slope of the line, and create perpendicular lines
        if os.path.exists(interpLineFile):
            os.remove(interpLineFile)
        f=open(interpLineFile, 'a')
        
        for i in range(1, len(endptDf) // 2 + 1):
            trX1, trX2, trY1, trY2, x_ms, y_ms, cosines, sines, angles = transect.transect(endptDf, i, bufferWidth/2)
    
            f.write('L  2 1\n')
            f.write(' ' + str(trX1.iloc[0]) + ' ' + str(trY1.iloc[0]) + '\n')
            f.write(' ' + str(trX2.iloc[0]) + ' ' + str(trY2.iloc[0]) + '\n')
            f.write(' 1 ' + str(i))
            if i != len(endptDf) // 2:
                f.write('\n')
                
        f.close()
        
        gs.run_command('v.edit', map_=interpLines, tool='create', \
                            type_='line')
        gs.run_command('v.edit', flags='n', map_=interpLines, tool='add', \
                            input_=interpLineFile)  
            
        # Get points along the newly created lines to use for interpolation
        gs.run_command('v.to.points', input_=interpLines, type_='line', \
                       output=interpPts, dmax=1)
     
        # Now buffer the original lines to create interpolation surfaces
        gs.run_command('v.buffer', flags='c', input_=lineSegments, type_='line', output=linesBuffered, \
                        distance=bufferWidth, cats=cats) 

    ### Create the interpolated DEM (either burned or plugged)
    if not gdb.map_exists(demBurned, 'raster'):
            
        gs.run_command('v.what.rast', map_=interpPts, raster=demForBurn, column='elev', \
                        layer=2)
        gs.run_command('r.mask', vector=linesBuffered)
        gs.run_command('v.surf.idw', input_=interpPts, layer=2, column='elev', \
                        output=interpSurf)
            
        # Kind of dangerous maybe but deleting r.mask doesn't work
        #path=gs.read_command('g.gisenv', get=['GISDBASE','LOCATION_NAME','MAPSET'],\
        #                      sep='/').replace('\\', '/')
        #path=path.strip()+'/cell_misc/MASK'
        #os.chmod(path,0o777)
        #shutil.rmtree(path)
        
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

 


