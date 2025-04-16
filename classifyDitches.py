import pandas as pd

# Names of files exported from Grass
combFile='ditchCombinations.txt'
ptFile='ditchNodes.txt'

ditchCombs = pd.read_csv(combFile)
ditchNodes = pd.read_csv(ptFile)

ditchCombs = ditchCombs.rename(columns={'from_cat': 'fromPt', 'cat': 'toLine'})

fromLines = []

for i in range(len(ditchCombs)):
    fromPt = ditchCombs['fromPt'].iloc[i]

    # Find the corresponding entry in ditchNodes with that point number
    nodesEntry = ditchNodes[ditchNodes['cat']==fromPt]

    fromLine = nodesEntry['lcat'].iloc[0]
    fromLines += [fromLine]

ditchCombs['fromLine']=fromLines
ditchCombs['junction']=(ditchCombs['fromLine']!=ditchCombs['toLine'])

ditchJuncs = ditchCombs[ditchCombs['junction']==True]

print(ditchJuncs)


