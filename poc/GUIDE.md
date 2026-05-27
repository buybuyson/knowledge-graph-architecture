# PoC Usage Guide

## View the ready demo (no install)

Download the repo, open the `.html` files in `poc/` in a browser:

- `poc/poc_graph_query.html` — fire queries at the spherical graph, see the query mechanism
- `poc/pipeline_v11_graph_viewer.html` — browse the three graphs extracted from the codebase

Both run entirely in the browser with embedded data. No server, no internet needed (except the D3 library loaded from a CDN — needs network on first load).

## Graph data structure

The files in `data/` are JSON with this schema:

```
{
  "meta": { "hubs": [...], "schema": {...} },
  "nodes": [ { "id", "type", "label", "families", "is_hub", "in_degree", "multi_family" } ],
  "edges": [ { "source", "target", "type", "evidence", "carries", "minus_class" } ]
}
```

Each edge has `evidence` pointing to a `file:line` of the original codebase — you can verify every relationship back to source.

## Extracting a graph from YOUR codebase

The current PoC uses ready-made Pipeline V11 data. To extract a graph from your own code, you need an AST analysis script (not included in this version — see "Still missing" below). The principle: scan each file, and each `import`/function call/environment-variable read → an edge with evidence.

## Still missing (contributions welcome)

This is a partial PoC. The pieces not yet present:

- A general AST extraction script for any codebase (this version only has the pre-extracted output for V11)
- Real query graphing (the PoC uses pre-written scenario queries)
- An O(1) benchmark as node count grows
- A real lowest-common-ancestor check for the path-independence condition (the PoC only simulates it)

If you want to build these pieces, open an issue to discuss first.
