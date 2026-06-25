# -*- coding:utf-8 -*-
"""
Created on Sun Dec  7 20:13:00 2025

@author:swimm
"""

import pandas as pd
import grass.script as gs

cropsLayer = 'minneopa_polygons'
attrFile = 'cropAttrs.txt'

colorFile = 'croplandColorTable.txt'

#%% 
df = pd.read_csv(attrFile)

categories = sorted(set(df['b_Class_Name']))

cFile=open(colorFile, 'a')

colorTable = {'Alfalfa':'255:165:226', \
              'Apples':'37:150:190', \
              'Barley':'226:0:124', \
              'Barren':'204:191:163', \
              'Buckwheat':'214:158:188', \
              'Clover/Wildflowers':'232:191:255', \
              'Corn':'255:211:0', \
              'Deciduous Forest':'147:204:147', \
              'Developed/High Intensity':'154:154:154', \
              'Developed/Low Intensity':'154:154:154', \
              'Developed/Med Intensity':'154:154:154', \
              'Developed/Open Space':'154:154:154', \
              'Evergreen Forest':'147:204:147', \
              'Fallow/Idle Cropland':'0:175:75', \
              'Grapes':'112:68:137', \
              'Grassland/Pasture':'232:255:191', \
              'Herbaceous Wetlands':'126:177:177', \
              'Millet':'112:0:73', \
              'Misc Vegs & Fruits':'255:102:102', \
              'Mixed Forest':'147:204:147', \
              'Oats':'160:89:137', \
              'Open Water':'75:112:163', \
              'Other Crops':'0:175:75', \
              'Other Hay/Non Alfalfa':'165:242:140', \
              'Other Tree Crops':'177:154:112', \
              'Peas':'84:255:0', \
              'Potatoes':'112:38:0', \
              'Pumpkins':'255:102:102', \
              'Rye':'172:0:124', \
              'Shrubland':'198:214:158', \
              'Sod/Grass Seed':'175:255:221', \
              'Sorghum':'255:158:11', \
              'Soybeans':'38:112:0', \
              'Spring Wheat':'216:181:107', \
              'Squash':'255:102:102', \
              'Sugarbeets':'168:0:228', \
              'Sunflower':'255:255:0', \
              'Sweet Corn':'221:165:11', \
              'Switchgrass':'0:175:75', \
              'Tomatoes':'242:163:119', \
              'Triticale':'214:158:188', \
              'Winter Wheat':'165:112:0', \
              'Woody Wetlands':'126:177:177', }

for (i, c) in enumerate(categories):
    gs.run_command('v.db.update',map_=cropsLayer,layer=1,column='landType',\
                  value=i,where="Class_Name = '" + c + "'")
        
    clr = colorTable[c]
        
    cFile.write(str(i) + ' ' + clr + '\n')
    
cFile.close()


    
    
    