# -*- coding: utf-8 -*-
"""
Created on Thu Jul 31 13:20:51 2025

@author: swimm
"""

import pandas as pd

def findStreamChains(graph, lcats):
    """ Find 'single chains' (ie where 1 segment flows into 1 segment w/o forks/branches)
    Takes a networkx directed graph, and a list of lcats """
    
    chainDf = pd.DataFrame({'root': lcats})
    chainDf['chain']=''
    
    for lcat in lcats:
        currentChain = chainDf['chain'][chainDf['root']==lcat].iloc[0]
        
        if currentChain == '':
            if graph.has_node(lcat)==False: 
                chain=[int(lcat)] 
            else:
                prevLcats = list(graph.predecessors(lcat))
                
                # If it has exactly one predecessor and no siblings, it's part of another chain
                # If it has 0 or 2+ predecessors, start a new chain
                if len(prevLcats) != 1 or (len(prevLcats)==1 and len(list(graph.successors(prevLcats[0])))!=1):
                    chain=[int(lcat)]
                    
                    nextLcats=list(graph.successors(lcat))
                    
                    # If a segment has 0 or 2+ successors, end the chain here
                    if len(nextLcats) != 1:
                        nextLcat=0 
                    else:
                        nextLcat=nextLcats[0]
                    
                    # Check to make sure the successor isn't receiving flow from another segment
                    while nextLcat != 0 and len(list(graph.predecessors(nextLcat)))==1:
                        chain+=[int(nextLcat)]
                        
                        nextLcats = list(graph.successors(nextLcat))
                        if len(nextLcats) != 1:
                            nextLcat=0
                        else:
                            nextLcat=nextLcats[0]
        
            for segment in chain:
                chainDf.loc[segment-1, 'chain']=str(chain)
        
    return chainDf
    
    