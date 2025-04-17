import pandas as pd

# Names of files exported from Grass
combFile='ditchCombinations.txt'        # has distances from points to lines
ptFile='ditchNodes.txt'                 # has point attributes like elevation and xy coords

ditchCombs = pd.read_csv(combFile)
ditchNodes = pd.read_csv(ptFile)

ditchCombs = ditchCombs.rename(columns={'from_cat': 'fromPt', 'cat': 'toLine'})

print(ditchNodes)

#fromLines = []
ditchCombs['junction']=False

for i in range(len(ditchCombs)):
    fromPt = ditchCombs['fromPt'].iloc[i]

    # Find the corresponding entry in ditchNodes with that point number
    nodesEntry = ditchNodes[ditchNodes['cat']==fromPt].iloc[0]

    fromLine = nodesEntry['lcat']
    #fromLines += [fromLine]

    if fromLine != ditchCombs['toLine'].iloc[i]:
        ditchCombs.loc[i, 'junction'] = True

        ### Verify that junction is downstream end of ditch
        
        # Get the points that lie along the same line
        siblingPts = ditchNodes[ditchNodes['lcat']==fromLine]
        minElev = min(siblingPts['elev'])
        if nodesEntry['elev'] > minElev:
            print(str(fromPt) + '\tJunction is not downstream end of incoming ditch')
        else:
            print(str(fromPt) + '\tMin elev of line ' + str(fromLine) + ' is ' + str(minElev))

    #nodesEntry['elev']

#ditchCombs['fromLine']=fromLines
#ditchCombs['junction']=(ditchCombs['fromLine']!=ditchCombs['toLine'])

ditchJuncs = ditchCombs[ditchCombs['junction']==True]

#print(ditchJuncs)




