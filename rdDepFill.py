import grass.script as gs
import richdem as rd
import numpy as np
import rioxarray
import sys

fillCats = ['103', '109']
# 8, 58, 92, 103, 109, 194, 195, 200

for fillCat in fillCats:

    hucPrefix = 'HUC_0902010402'
    filePath='/media/uashrani/topobathy-ditch/HUC_0902010402/'
    fileName=hucPrefix + '_fill' + fillCat

    #%% 
    filledLayer = fileName + '_rdFilled'
    filledName = filePath+fileName+'_rdFilled.tif'

    #%%
    rdArr = rd.LoadGDAL(filePath+fileName + '.tif', no_data=0)

    rd.FillDepressions(rdArr, epsilon=False, in_place=True)

    rd.SaveGDAL(filledName, rdArr)

    gs.run_command('r.in.gdal', input=filledName, output=filledLayer)

    # Calculate depressions (dammed - not dammed)
    exp = 'deps' + fillCat + ' = (' + filledLayer + ' - ' + fileName + '_interpDEM_int) / 100'
    gs.run_command('r.mapcalc', expression=exp)

    # Calculate difference between these depressions and the base case depressions
    exp = 'change' + fillCat + ' = deps' + fillCat + ' - deps' 
    gs.run_command('r.mapcalc', expression=exp)

    gs.run_command('r.null', map_='change' + fillCat, setnull=0)





