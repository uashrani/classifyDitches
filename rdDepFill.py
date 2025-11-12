import grass.script as gs
import richdem as rd
import numpy as np
import rioxarray
import sys

hucPrefix = 'HUC_0702000709'
filePath='/media/uashrani/topobathy-ditch/HUC_0702000709/'

#baseCase = 1        # base case is when none of the ditches are dammed, just getting current water storage

fillCats = ['32', '38', '40', '41', '42', '43', '44', '46', '47', '48', '67', '68', '77', '86', \
'90', '92', '93', '94', '96', '103', '107', '108', '113', '119', '132', '134', '143']

#%% ------------------------- Actual code

for fillCat in fillCats:
    if fillCat == 'Base':
        fileName = hucPrefix 
    else:
        fileName=hucPrefix + '_fill' + fillCat

    pathToFile = filePath + fileName + '.tif'

    filledLayer = fileName + '_rdFilled'        # layer in Grass
    filledName = filePath + filledLayer + '.tif'

    rdArr = rd.LoadGDAL(pathToFile, no_data=0)
    rd.FillDepressions(rdArr, epsilon=False, in_place=True)
    rd.SaveGDAL(filledName, rdArr)

    gs.run_command('r.in.gdal', input=filledName, output=filledLayer)

    # Calculate depressions (dammed - not dammed)
    if fillCat == 'Base':
        expr  = 'deps = (' + filledLayer + ' - ' + fileName + '_v2_interpDEM_int) / 100'
    else:
        expr = 'deps' + fillCat + ' = (' + filledLayer + ' - ' + fileName + '_interpDEM_int) / 100'

    gs.run_command('r.mapcalc', expression=expr)

    # Calculate difference between these depressions and the base-case depressions
    if fillCat != 'Base':
        exp = 'change' + fillCat + ' = deps' + fillCat + ' - deps' 
        gs.run_command('r.mapcalc', expression=exp)

        gs.run_command('r.null', map_='change' + fillCat, setnull=0)



#fillCats = ['103', '109']
# 8, 58, 92, 103, 109, 194, 195, 200

#for fillCat in fillCats:
    
    #fileName=hucPrefix + '_fill' + fillCat

    #%% 
    #filledLayer = fileName + '_rdFilled'
    #filledName = filePath+fileName+'_rdFilled.tif'

    #%%
    #rdArr = rd.LoadGDAL(filePath+fileName + '.tif', no_data=0)

    #rd.FillDepressions(rdArr, epsilon=False, in_place=True)

    #rd.SaveGDAL(filledName, rdArr)

    #gs.run_command('r.in.gdal', input=filledName, output=filledLayer)

    # Calculate depressions (dammed - not dammed)
    #exp = 'deps' + fillCat + ' = (' + filledLayer + ' - ' + fileName + '_interpDEM_int) / 100'
    #gs.run_command('r.mapcalc', expression=exp)

    # Calculate difference between these depressions and the base case depressions
    #exp = 'change' + fillCat + ' = deps' + fillCat + ' - deps' 
    #gs.run_command('r.mapcalc', expression=exp)

    #gs.run_command('r.null', map_='change' + fillCat, setnull=0)





