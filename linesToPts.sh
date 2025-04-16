#!/bin/bash

vecLines='drainage_centerlines'   # name of ditch layer in Grass, already imported
vecPoints='ditch_nodes'            # name of start/end points, will be created from line data

combTable='ditchCombinations'     # distances between points and lines, can find distances between every pair of ditches

combFile='ditchCombinations.txt'
ptFile='ditchNodes.txt'

# Extract start and end points from ditch lines
v.to.points input=$vecLines output=$vecPoints use='node' --overwrite
# Get xy coordinates of the points
v.to.db map=$vecPoints layer=2 option='coor' columns='x','y' --overwrite

### In addition to start and end points, we also want to know intersections with other ditches

# Get distances from nodes to all nearby lines, and save in table
v.distance -a from=$vecPoints from_layer=2 to=$vecLines dmax=1 upload='dist','cat' table=$combTable --overwrite
# Export the table to a text file, and do the same for the ditch node attribute table
db.select table=$combTable output=$combFile --overwrite
v.db.select map=$vecPoints format='csv' file=$ptFile --overwrite

# Now the Python script will deal with these text files
python3 classifyDitches.py