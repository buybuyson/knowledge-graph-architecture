import json
d = json.load(open("experiment_graph.json"))
nodes = {n["id"]:n for n in d["nodes"]}
edges = d["edges"]

# ===== VIEW 1: FLAT — moi node 1 dong, khong cau truc, khong quan he =====
flat_lines=[]
for nid,n in nodes.items():
    flat_lines.append(f"{nid} {n['name']} ({n['evidence']})")
flat = "\n".join(flat_lines)

# ===== VIEW 2: ToC — phan cap theo FILE (module), giu node, BO canh quan he =====
from collections import defaultdict
byfile=defaultdict(list)
for nid,n in nodes.items():
    f = n["evidence"].split(":")[0]
    byfile[f].append((nid,n["name"]))
toc_lines=[]
for f in sorted(byfile):
    toc_lines.append(f"## {f}")
    for nid,name in sorted(byfile[f]):
        toc_lines.append(f"  - {nid} {name}")
toc = "\n".join(toc_lines)

# ===== VIEW 3: GRAPH — node + canh (adjacency) =====
adj=defaultdict(list)
for e in edges: adj[e["from"]].append(e["to"])
g_lines=["NODES:"]
for nid,n in nodes.items():
    g_lines.append(f"{nid} {n['name']}")
g_lines.append("EDGES (caller -> callee):")
for nid in nodes:
    if adj[nid]:
        g_lines.append(f"{nid} -> {','.join(sorted(adj[nid]))}")
graph = "\n".join(g_lines)

open("view_flat.txt","w").write(flat)
open("view_toc.txt","w").write(toc)
open("view_graph.txt","w").write(graph)

# Dem token tho (xap xi GPT: ~4  char/token)
def tok(s): return len(s)//4
print(f"FLAT : {len(flat):6d} chars  ~{tok(flat):5d} tok")
print(f"ToC  : {len(toc):6d} chars  ~{tok(toc):5d} tok  ({len(byfile)} module)")
print(f"GRAPH: {len(graph):6d} chars  ~{tok(graph):5d} tok")
print(f"\nCung 1 bo {len(nodes)} node cho ca 3 view. Khac biet duy nhat: ToC bo canh, Graph giu canh.")
