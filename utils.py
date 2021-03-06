import networkx as nx
import httplib

def reciprocity(G):
    """Calculate reciprocity of graph, i.e. the ratio of the edges in
    one direction that have and edge going in the other direction."""
    return sum([G.has_edge(e[1], e[0]) 
    for e in G.edges_iter()]) / float(G.number_of_edges())

def short_names(names):
   labels = {}
   for n in names:
      mainlabel = n[0:3]
      if n[2] == '-':
         mainlabel = n[0:2]
      if n[-2:].startswith('w'):
         labels[n] = (mainlabel + n[-1])
      else:
         labels[n] = mainlabel
   return labels

def edge_labels(edges, edgegroups=[], suppress_default=True):
   labels = []

   i = 0

   edgedone = {}
   
   for (u,v,w) in edges:      
      for el, type in edgegroups:
         for (s,t,x) in el:
            if (u,v) == (s,t):
               if not (u,v) in edgedone:
                  metric = int(x['weight'])
                  m = str(metric)
                  if metric == 10 and suppress_default:
                      m = ""
                  if type.endswith("opath") and x['weight'] != w['weight']:
                     m = "%s (%s)" % (str(int(x['weight'])), str(int(w['weight'])))
                  l = (i, m, type.startswith('main'))
                  labels.append((i, m, type.startswith('main')))
                  edgedone[(u,v)] = l
                  i = i + 1
      if (u,v) not in edgedone:
         labels.append((i, "", False))
         i = i + 1

   try:
      assert len(edges) == len(labels)
   except:
      print "Assertion fail: %s != %s" % (len(edges), len(labels))

   return labels


def cap2str(capacity):

    mapping = {  1984    : '2Mbit/s',
                34000    : '34Mbit/s',
                34010    : '34Mbit/s',
                100000   : '100Mbit/s',
                155000   : '155Mbit/s',
                1000000  : '1Gbit/s',
                2488000  : '2.5Gbit/s',
                10000000 : '10Gbit/s'
              }

    if type(capacity) != type(int):
        capacity = int(capacity)
    if not capacity in mapping: return "Unkown"
    return mapping[capacity]
      
def read_linkloads(G, host, url):

    conn = httplib.HTTPConnection(host)
    conn.request("GET", url)
    r1 = conn.getresponse()
    if r1.status != 200:
        conn.close()        
        return {}
    data1 = r1.read()
    if not data1:
        conn.close()        
        return {}
    conn.close()

    loads_by_descr = {}

    retloads = {}

    for line in data1.split('\n'):
        if not line: continue
        tokens = line.split()
        descr = tokens[0].strip()
        avg_in = int(tokens[3].strip())
        avg_out = int(tokens[4].strip())

        loads_by_descr[descr] = (avg_out, avg_in)

    for (u,v,edgedata) in G.edges(data=True):
        if not 'l' in edgedata: continue
        label = edgedata['l']
        if label in loads_by_descr:
            retloads[(u,v)] = loads_by_descr[label]

    sanitized_loads = {}
    for (u,v) in retloads:
        if (v,u) in retloads:
            if retloads[(v,u)][1] > retloads[(u,v)][0]:
                sanitized_loads[(u,v)] = retloads[(v,u)][1]
            else:
                sanitized_loads[(u,v)] = retloads[(u,v)][0]
        else:
            sanitized_loads[(u,v)] = retloads[(u,v)][0]
            sanitized_loads[(v,u)] = retloads[(u,v)][1]

    return sanitized_loads


def calc_ratio(G, loads, u, v, discard_inverse=False, no_diff=False, exclude_edges=[]):
  sum = 0
  totload = loads[(u,v)]
  #for (u1,v1,d) in [(v2, u2, d2) for (u2, v2, d2) in G.edges(data=True) if u2 == u]:
  for neighbor in G[u]:
      if (neighbor,u) in exclude_edges:
          #totload -= loads[(u1,v1)] * calc_ratio(G, loads, u,v)
          continue
      if discard_inverse and (neighbor,u) == (v,u): continue
      if not (neighbor,u) in loads:
          sum += 0.0
      else:
          sum += float(loads[(neighbor,u)])
  ee = []
  #if discard_inverse: ee += [(v,u)]
  ndiff = node_diff_in_out(G, loads, u, False, ee)
  if not no_diff:
      if ndiff < 0:
          sum += -ndiff
  if sum == 0:
     return 0
  ratio = totload / float(sum)
  if ratio < 0:
      print "Assertion failed for ratio (%s, %s): %s" \
          % (u, v, ratio)
  if ratio > 1:
      ratio = 1
  return ratio

def node_diff_in_out(G, loads, node, inverse=False, exclude_edges=[]):
   sum_out = 0
   sum_in = 0

   for neighbor in G[node]:
      if (node,neighbor) not in exclude_edges:
         if (node,neighbor) not in loads:
             sum_out += 0.0
         else:
             sum_out += loads[(node,neighbor)]
      if (neighbor,node) not in exclude_edges:
         if (neighbor,node) not in loads:
             sum_in += 0.0
         else:
             sum_in += loads[(neighbor,node)]

   if inverse:
      return sum_in - sum_out
       
   return sum_out - sum_in

