#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 31 17:16:51 2018

@author: romie
"""
#Hello Git

import numpy as np
import pandas as pd 
import json
import itertools


def flatten(A): #flattens a nested list
        
        if A == []: return A
        if type(A[0]) == list:
            return flatten(A[0]) + flatten(A[1:])
        else: return [A[0]] + flatten(A[1:])
        

def cart(A,B): # cartesian product of two lists
   
    if A == []: return B
    elif B == []: return A
    else: return [flatten([x,y]) for x in A for y in B]


def most_common(A): #Find most common element
    df = pd.DataFrame({"A":A})
    return df.mode().values.tolist()[0]



class k_Nerve():

    def __init__(self, n_components = None, clusterer_params = (0.1, 5), covering_size = 200, overlap = 2):

        self.n_components = n_components
        self.covering_size = covering_size
        self.clusterer_params = clusterer_params
        self.overlap = overlap
        
    def project_data(self,data,labels):
        
        # ---------dimension of the projected data -----------------------------------------------------

        k = self.n_components 
        
        #------------data frame to record data and the projection to lower dimensional space-------------------
        
        frame = pd.DataFrame({"data":data, "labels":labels})

        from sklearn.decomposition import PCA
        pca = PCA(n_components = k)
        frame["proj"] = pca.fit_transform(data).tolist()
        return frame

    def make_covering(self,data,labels):

        print("building cover ....")

        frame = self.project_data(data,labels)

        covering_size = self.covering_size

        #-------------- N = lattic length ---------------------------

        N = int(np.exp(np.log(covering_size)/self.n_components))
        

        # -----------Determine the range of projection map------------------------------------------------
        Y = []
        for i in range(self.n_components):
            Y.append(np.array(self.project_data(data,labels)["proj"].values.tolist())[:,i])

        r_max = []
        r_min = []
        for i in range(self.n_components):
            r_max.append(np.amax(Y[i]))
            r_min.append(np.amin(Y[i]))

        
        # ------------------------- Make lattice inside projected data -----------------------------------

        sub_intervals = []
        for i in range(self.n_components):
            sub_intervals.append([r_min[i] + (r_max[i] - r_min[i])*j/N for j in range(N)] + [r_max[i]])

        #print(sub_intervals)

        LATTICE = []
        for k in range(len(sub_intervals)):
            LATTICE = cart(LATTICE, sub_intervals[k])


        # ----------cover projected data with k-balls centered around the lattice points----------------------

        R = []
        for  i in range(self.n_components):
            R.append((r_max[i] - r_min[i])/N)
        overlap = self.overlap
        ball_radius = overlap*np.amax(R)
        
        from sklearn.metrics.pairwise import euclidean_distances as ED
        k_balls_covering_frames = [None]*((N+1)**(self.n_components ))


        #-----------cover original data using pullback of k-balls covering along the projection map----------------

        covering_frames = [None]*((N+1)**(self.n_components))

        for i in range((N+1)**(self.n_components)):
           covering_frames[i] = frame[ ED( frame["proj"].values.tolist(), [LATTICE[i]] ) < ball_radius] 

        covering_frames_sorted = sorted(covering_frames, key = lambda x:x['labels'].max(axis = 0))

        #return covering_frames_sorted


        return [list(group)[0] for _,group in itertools.groupby(covering_frames_sorted, key = lambda x:x["data"].values.tolist())]



    def cluster(self,data,labels):
        
        #------------Get connected components of each pullback cover-----------
        
        covering = self.make_covering(data, labels)

        print("clustering covers by connected components ......")

        cluster_frames = [[]]*len(covering)
        index = [[]]*len(covering)

        #--------------Use clusterer DBSCAN to get connected components------------------
        
        from sklearn.cluster import DBSCAN

        eps, min_samples = self.clusterer_params #------set DBSCAN parameters-------------

        
        for i in range(len(covering)): 
            C = covering[i]["data"].values.tolist()

            if C != []:
                dbscan = DBSCAN(eps = eps, min_samples = min_samples).fit(C)
                covering[i]["cluster"] = dbscan.labels_
                cluster_frames[i] = [covering[i][covering[i]["cluster"] == label] for label in set(dbscan.labels_)]
                index[i] = [str(i) + "," + str(j) + "," + str(len(cluster_frames[i][j])) + "," + str(cluster_frames[i][j]["labels"].mode().values[0]) for j in range(len(set(dbscan.labels_)))]
        
        return cluster_frames, index


    def fit(self,data, labels):


        #------ make (two-dim) nerve of covering----------------------------------

        cluster_frames, index = self.cluster(data, labels)

        print("building nerve .......")

        #------- vertices = clusters ------------------

        print(" making vertices ....")
        V = flatten(index)
        

        #-------- edges = cluster pairs with nonempty intersection -------------------------
        
        print(" making edges .....")
        pairs = [(x,y) for x in V for y in V if V.index(x) < V.index(y)] # edges are non-degenerate
        
        E = [(x, y) for (x,y) in pairs if [a for a in cluster_frames[int(x.split(",")[0])][int(x.split(",")[1])]["data"].values.tolist() if a in cluster_frames[int(y.split(",")[0])][int(y.split(",")[1])]["data"].values.tolist()] != []]
        

        #---------- faces = cluster triples with nonempty intersection -----------------------

        print(" making faces ......")
        triples = [(x,y,z) for x in V for y in V for z in V if V.index(x) < V.index(y) and V.index(y) < V.index(z)] #faces are non-degenerate

        F = [(x,y,z) for (x,y,z) in triples if [a for a in cluster_frames[int(x.split(",")[0])][int(x.split(",")[1])]["data"].values.tolist() if a in cluster_frames[int(y.split(",")[0])][int(y.split(",")[1])]["data"].values.tolist() if a in cluster_frames[int(z.split(",")[0])][int(z.split(",")[1])]["data"].values.tolist()] != []]


        return V,E,F

        
    def draw(self,data,labels):

        V, E, F = self.fit(data,labels)

        #------------ encode nerve simplicial complex in json ---------------------

        print("building json data..........")
        if [int(v.split(",")[2]) for v in V] != []:
            max_weight = max([int(v.split(",")[2]) for v in V])
        else: max_weight = 0

        LABELS = set(labels)


        nodes = [{"id": v, "weight": int(v.split(",")[2]), "label": int(v.split(",")[3])} for v in V]
        links = [{"source": V.index(link[0]), "target": V.index(link[1]), "value": 1} for link in E]
        paths = [{ "vertices":[{"node": V.index(node[0]) }, {"node": V.index(node[1])}, {"node": V.index(node[2])}] , "label": most_common([int(node[0].split(",")[3]), int(node[1].split(",")[3]), int(node[2].split(",")[3])] ) } for node in F]


        
        viz = {"max_weight": max_weight, "labels_size": len(LABELS), "nodes":nodes, "links": links, "paths": paths}

        viz_json = json.dumps(viz)

        file = open("kNerve.json", 'w')
        file.write(viz_json)
        file.close()
        print("DONE!!")

        
    












        
        
        
        

