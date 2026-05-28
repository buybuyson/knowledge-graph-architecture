import ast, os, json, sys
from collections import defaultdict

SRC = sys.argv[1]
# Thu thập mọi function/method làm node, mọi lời gọi làm cạnh
funcs = {}          # qualified_name -> {file, line, calls:set}
name_to_qual = defaultdict(set)  # short name -> set of qualified names (để resolve call)

class Collector(ast.NodeVisitor):
    def __init__(self, file, module):
        self.file = file; self.module = module; self.stack = []
    def qual(self, name):
        return ".".join([self.module] + self.stack + [name])
    def visit_ClassDef(self, node):
        self.stack.append(node.name); self.generic_visit(node); self.stack.pop()
    def _func(self, node):
        q = self.qual(node.name)
        funcs[q] = {"file": self.file, "line": node.lineno, "calls": set(), "short": node.name}
        name_to_qual[node.name].add(q)
        self.stack.append(node.name)
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                f = child.func
                if isinstance(f, ast.Name): funcs[q]["calls"].add(f.id)
                elif isinstance(f, ast.Attribute): funcs[q]["calls"].add(f.attr)
        self.generic_visit(node); self.stack.pop()
    def visit_FunctionDef(self, node): self._func(node)
    def visit_AsyncFunctionDef(self, node): self._func(node)

for root,_,files in os.walk(SRC):
    for fn in files:
        if not fn.endswith(".py"): continue
        path = os.path.join(root,fn)
        mod = os.path.relpath(path, SRC).replace("/",".")[:-3]
        try:
            tree = ast.parse(open(path,encoding="utf-8").read())
        except: continue
        Collector(path, mod).visit(tree)

# Resolve cạnh: chỉ giữ cạnh trỏ tới function nội bộ (intra-repo)
edges = []
for q, info in funcs.items():
    targets = set()
    for c in info["calls"]:
        for tgt in name_to_qual.get(c, []):
            if tgt != q:
                targets.add(tgt)
    for t in targets:
        edges.append((q, t))

print(f"NODES (functions): {len(funcs)}")
print(f"EDGES (internal calls): {len(edges)}")
json.dump({"nodes":{k:{kk:vv for kk,vv in v.items() if kk!='calls'} for k,v in funcs.items()},
           "edges":edges}, open("raw_graph.json","w"), indent=1)
