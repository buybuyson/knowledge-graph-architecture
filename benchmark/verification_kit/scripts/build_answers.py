#!/usr/bin/env python3
"""
build_answers.py  —  TU SINH dap an tu graph tho. KHONG chua dap an viet san.
Bat ky ai chay lai cung ra dung mot ket qua => khong the bia.
Cach chay:  python3 scripts/build_answers.py data/graph.json
Xuat ra:    answer_key.GENERATED.json  (deterministic, hash kem theo)
"""
import json, sys, hashlib
try:
    import networkx as nx
except ImportError:
    sys.exit("Can: pip install networkx")

graph_path = sys.argv[1] if len(sys.argv)>1 else "data/graph.json"
d = json.load(open(graph_path))
nodes = {n["id"]: n for n in d["nodes"]}
name  = {nid: n["name"] for nid, n in nodes.items()}
G = nx.DiGraph(); G.add_nodes_from(nodes)
for e in d["edges"]: G.add_edge(e["from"], e["to"])

# Node tam diem X: chon DETERMINISTIC = fan-out>=3, reach lon nhat, cham vong nhieu nhat,
# tie-break theo id nho nhat. Quy tac co dinh => moi nguoi chay ra cung X.
scc = set()
for c in nx.strongly_connected_components(G):
    if len(c) > 1: scc |= c
def keyf(n):
    return (G.out_degree(n) >= 3, len(nx.descendants(G, n)),
            len(nx.descendants(G, n) & scc), -int(n[1:]))
X = max(nodes, key=keyf)

# 4 cau hoi — dinh nghia bang THUAT TOAN tren graph, khong phai con so
q1 = sorted(G.successors(X))
q2 = sorted([n for n in q1 if G.out_degree(n) >= 2])
q3 = sorted({m for n in q2 for m in (nx.descendants(G, n) & scc)})
q4 = sorted({m for n in q2 for m in G.successors(n)})

ak = {
 "X": X, "X_name": name[X],
 "Q1": {"answer_ids": q1, "answer_names": sorted(set(name[n] for n in q1))},
 "Q2": {"answer_ids": q2, "answer_names": sorted(set(name[n] for n in q2))},
 "Q3": {"answer_ids": q3, "answer_names": sorted(set(name[n] for n in q3))},
 "Q4": {"answer_ids": q4, "answer_names": sorted(set(name[n] for n in q4))},
}
blob = json.dumps(ak, sort_keys=True, ensure_ascii=False).encode()
ak["_integrity_sha256"] = hashlib.sha256(blob).hexdigest()
json.dump(ak, open("answer_key.GENERATED.json","w"), indent=1, ensure_ascii=False)
print("Da sinh answer_key.GENERATED.json")
print("X =", X, "(", name[X], ")")
for q in ["Q1","Q2","Q3","Q4"]:
    print(f"  {q}: {len(ak[q]['answer_ids'])} dap an")
print("Integrity SHA-256:", ak["_integrity_sha256"][:16], "...")
print("\n>> Neu hash nay KHAC voi hash trong EXPECTED_HASH.txt => graph da bi sua, dap an khong dang tin.")
