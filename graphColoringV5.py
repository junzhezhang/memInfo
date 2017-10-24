import numpy as np
from datetime import datetime

class Vertex:
    def __init__(self, name, s,r,d):
        self.name = name
        self.size = s
        self.r = r # arrive
        self.d = d # depart
        self.colorOccupied = []
        self.colorFlag = 0
        self.colorRange = [] # a list of min and max

def memInfo_2_sortedDict(fileName):
    '''
    process memInfo: Malloc and Free sequences into sorted dictionary.
    sorted with size only
    taked care of duplicate addresses, meaning the case where each address
    has been used multiple times.
    assume no no-free conditions, as the memInfo shows
    '''
    f = open(fileName)
    l =[]
    i= 0
    for row in f:
        item =row.split()
        item.append(i)
        i+=1
        swapped_item =[]
        if item[0]=='Malloc':
            swapped_item = [item[1],int(item[2]),1, item[3]]
        else:
            swapped_item = [item[1],-1,-1, item[2]] #-1 means no info of size
        l.append(tuple(swapped_item))

    l2 =sorted(l) #sorted with address
    l6 = sorted(list(set(np.array(l2)[:,0])))  #distinct addresses

    itemList =[]
    itemFlatList =[]
    i=0
    for addr in l6:
        i+=1
        item =[]
        while ((addr ==l2[0][0])&(len(l2)>1)):
            item.append(l2[0])
            l2 = l2[1:]
        if ((addr ==l2[0][0])&(len(l2)==1)):
            item.append(l2[0])
        item =sorted(item, key=lambda x:x[3])
        itemList.append(item)
        itemFlatList +=item

        if len(set(np.array(item)[:,0]))!=1:
            #print(item)
            #print(set(np.array(item)[:,0]))
            print('sth wrong with the same addr grouping!')
    # use Flat list instead:
    rawList = itemFlatList

    raw ={} # dict
    # maxTime is optional as there is no non-free items.
    maxTime = max(np.array(np.array(rawList)[:,3],dtype=int))

    while len(rawList)>0:
        twoItems = rawList[0:2]
        rawList = rawList[2:]
        if (twoItems[0][0]!=twoItems[1][0])or(twoItems[0][2]*twoItems[1][2]!=-1)or(twoItems[0][3]>=twoItems[1][3]):
            print("sth wrong with the raw data pairing")
        if twoItems[0][0]==twoItems[1][0]:
            #print(twoItems)
            raw.update({twoItems[0][0]+'_%d'%twoItems[0][3]:[twoItems[0][1],twoItems[0][3],twoItems[1][3]]})
        else:
            print('sth wrong with the memInfo, sort of Malloc or Free info!')

    raw3 = list(raw.items())
    sortedDict = dict(sorted(raw3,key=lambda x: x[1],reverse=True ))
    #print('no issue')
    return sortedDict

def maxLoad(dictItems):
    '''
    get max load. improved version, reduced from time 45s to 3s for Alexnet
    time complexity reduced from O(n^2) to O(n)
    '''

    tic =datetime.now()

    A = np.array(list(dictItems.values()))
    loadTable =[]
    length =2*len(A)

    for t in range(length):
        B = list(set(np.where(A[:,1]<=t)[0])& set(np.where(t<A[:,2])[0]))
        #same as below
        #C = list(set(np.where(A[:,1]<=t)[0]).intersection(set(np.where(t<A[:,2])[0])))
        loadTable.append(np.sum(A[B,0]))

    maxload = max(loadTable)
    toc = datetime.now()
    print("time spent for maxLoad is %s s"%str(toc-tic))

    return maxload

def mergeSeg (A):
    temp =sorted(A)
    if len(temp)>1:
        m=0
        while m  <len(temp)-2:
            #print('new iteration')
            #print('item%d'%temp[m][1])
            #print(temp[m][1]-temp[m+1][0])
            if temp[m][1]-temp[m+1][0]>=-1:
                tempItem=[temp[m][0],max(temp[m+1][1],temp[m][1])]
                temp =temp[:m]+[tempItem]+temp[m+2:]
            else:
                m+=1
            #print('item%d'%temp[m][1])
        if temp[-2][1]-temp[-1][0]>=-1:
            temp =temp[:-2]+[[temp[-2][0],max(temp[-2][1],temp[-1][1])]]
    output =[]
    for item in temp: #convert to list
        output.append(list(item))
    return output
def FFallocation(merged_seg,size):
    '''
    weighted coloring: FF
    '''
    if len(merged_seg)==0:
        #print("case 1")
        return (0,size-1)
    if (len(merged_seg)>0) & (size<(merged_seg[0][0]+1)): #TODO should be a +1
        #print(size)
        #print(merged_seg[0][0]+1)
        #print("case 2")
        return (0,size-1)
    if len(merged_seg)>1:
        location =-1
        n=0
        while n<len(merged_seg)-1: #TODO verify -1 here
            if merged_seg[n+1][0]-merged_seg[n][1]-1>=size:
                #print("case 3")
                location = merged_seg[n][1]+1
                break
            n+=1
        if location == -1:
            #print("case 4")
            location = merged_seg[-1][1]+1
    elif len(merged_seg)==1:
        #print("case 5")
        location = merged_seg[0][1]+1
    return (location,location+size-1)

def run(rawDict):
    '''
    main function, improved coloring section, reduced time from 2min to 1.5s
    '''

    # start to build vertices:
    tic =datetime.now()
    vertices =[]
    for name in rawDict:
        s, r, d = rawDict[name]
        # print("test "+str(s)+str(r)+str(d))
        v = Vertex(name, s, r, d)
        vertices.append(v)
        # print(vertices)
    toc = datetime.now()
    print("time spent for vertices is %s s"%str(toc-tic))

    # build edges:
    tic =datetime.now()
    gvertices = {} # gvertices vs vertices, {} and []
    verticesList=[] #list of names
    edges = [] #matrix
    edge_indices = {}
    idx_to_name={}
    idx = 0
    for vertex in vertices:
        gvertices[vertex.name] = vertex
        edge_indices[vertex.name] = idx
        verticesList.append(vertex.name)
        idx_to_name[idx] = vertex.name
        idx+=1
    edges = np.zeros((idx,idx), dtype=np.int)
    toc = datetime.now()
    print("time spent for edges part 1 is %s s"%str(toc-tic))

    # build edges O(n^2)
    tic =datetime.now()
    for i in range(idx):
        u = gvertices[idx_to_name[i]]
        for j in range (idx):
            v = gvertices[idx_to_name[j]]
            if (max(u.r,v.r)<min(u.d,v.d)):
                edges[i][j]=1
    toc = datetime.now()
    print("time spent for edges part 2 is %s s"%str(toc-tic))
    #print("below shows edges")
    #print(edges)

    i=-1
    highSideColor =[]
    tic = datetime.now()
    for node in verticesList:
        i+=1
        j=0
        idx = list(set(np.where(edges[i,:]==1)[0])-{i})
        colorOccupied_withEmptyList = [gvertices[idx_to_name[x]].colorRange for x in idx]
        colorOccupied = [x for x in colorOccupied_withEmptyList if x != []]
        #note that the colorOccupied is not saved into gvertices object. not needed.
        #merge colorOccupied:
        merged_seg =mergeSeg(colorOccupied)
        # FF over here
        size = gvertices[idx_to_name[i]].size
        gvertices[idx_to_name[i]].colorRange =FFallocation(merged_seg,size)
        highSideColor.append(gvertices[idx_to_name[i]].colorRange[1])
        #print('colorRange '+str(gvertices[idx_to_name[i]].colorRange))

    print('time spent for coloring in all loops is %s s'%str(datetime.now()-toc))
    maxload = maxLoad(rawDict)
    heighestColor = max(highSideColor)+1
    print('maxLoad vs poolSize: '+str(maxload)+' '+str(heighestColor)+' '+str(float(heighestColor/maxload)))
    return maxload,heighestColor, float(heighestColor/maxload)

print('start running')
truePath= '/Users/apple/Dropbox/code2017August/memoryGraphColoring/memInfo/'
fileName = truePath+'memAlex.text'

tic =datetime.now()
sortedDict = memInfo_2_sortedDict(fileName)
toc = datetime.now()
print("time spent for memInfo_2_sorted is %s s"%str(toc-tic))

tic =datetime.now()
run(sortedDict)
print('done coloring')
toc = datetime.now()
print("total time spent is %s s"%str(toc-tic))
