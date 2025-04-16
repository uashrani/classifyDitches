#!/bin/bash

vecLines = 'drainage_centerlines'   # name of ditch layer in Grass, already imported
vecPoints = 'ditch_nodes'            # name of start/end points, will be created from line data

combTable = 'ditchCombinations'     # distances between points and lines, can find distances between every pair of ditches

combFile = 'ditchCombinations.txt'
ptFile = 'ditchNodes.txt'

v.to.points input=$vecLines output=$vecPoints use='node' --overwrite
v.to.db map=$vecPoints layer=2 option='coor' columns='x','y' --overwrite
v.distance -a from=$vecPoints from_layer=2 to=$vecLines dmax=1 upload='dist','cat' table=$combTable --overwrite
db.select table=$combTable output=$combFile --overwrite
v.db.select map=$vecPoints format='csv' file=$ptFile --overwrite