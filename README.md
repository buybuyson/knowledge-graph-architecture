# Hierarchical Knowledge Graph Architecture for LLMs — V1.2

> A concept for organizing knowledge so LLMs can retrieve it more efficiently — with a partial PoC extracted from a real codebase **and a multi-AI blind benchmark measuring token cost against three baselines (flat RAG, ToC RAG, GraphRAG).**
> **Status: Concept + Partial PoC (B1→B2) + preliminary evidence that structured retrieval beats flat RAG. Honest caveat: the graph does not beat a plain hierarchy on absolute token_in for this linear codebase — see benchmark. B3/O(1) not yet benchmarked. This is a serious hypothesis — testing and rebuttal are welcome.**

**Author:** Pham Nguyen Son

---

## The Problem

As a system grows — more documents, more modules, more context — getting an LLM to retrieve the right information becomes expensive and inaccurate. The common approaches today (stuffing context, flat RAG) waste tokens and frequently miss.

This repo presents a different way to organize knowledge: a **hierarchical knowledge graph**, where knowledge is arranged into a Hub/Leaf structure, every edge carries verifiable information, and queries follow a "fewest steps to an answer" principle instead of scanning everything.

### Why context stuffing fails — the mechanism

A common misunderstanding: that "1M tokens" is capacity the model *sets aside to read* your documents, so you may as well stuff everything in. In reality that number is a **shared budget for both input and output in a single call** — tokens fed in and tokens generated out are drawn from the same pool.

In a multi-turn conversation, because the model **does not remember between calls**, each turn must resend the entire prior history — including the answer the model just produced. History therefore **accumulates turn over turn**, eating into the shared budget. The consequence is not merely "forgetting the middle" (an attention problem); it is a concrete operational chain: by turn N, the budget left for output is squeezed — the effective room left for reasoning and output shrinks, often resulting in shorter, degraded, or compressed answers — or the system **compresses/cuts history** to fit, and the model answers on a *degraded* context, producing **inaccuracy**.

Long context does not only increase memory cost. It also competes with the model's effective reasoning bandwidth. As more tokens occupy the context window, attention becomes increasingly diluted across retrieved documents, prior conversation history, tool traces, intermediate reasoning, and output generation. The result is that larger context windows do not necessarily improve reasoning quality — in many cases, retrieval locality and signal density matter more than raw context size.

This is the real reason answer quality degrades across long conversations — a layer of problem distinct from "lost in the middle," and one that flat context-stuffing has no escape from. This architecture attacks exactly this: instead of resending raw text each turn, history is **graphed into a compact signature**, aiming to keep token growth sublinear across long interactions rather than linearly accumulating. (Full mechanism in `docs/`, section 1.1.1.)

## What's New in V1.2

The three benchmark problem sets were re-run with **two stronger baselines** added, to test a fair critique: that graph-walk beat flat RAG only because building a graph pre-organizes knowledge, not because the edges carry value.

1. **Method C — ToC RAG** (a plain hierarchical table of contents) and **Method D — GraphRAG** (Microsoft-style communities) added to all three problem files, both handed to the AIs ready-made.
2. **Honest headline:** structured retrieval beats flat RAG robustly (now shown for three structures, not just the graph) — but the graph does **not** beat a plain Table of Contents on absolute token_in for this codebase. The graph's defensible win is multi-turn *growth rate*, not absolute savings. Recorded against the architecture's own framing. See [`benchmark/RESULTS.md`](benchmark/RESULTS.md).

## What's New in V1.0

This version builds on concept v1.32 with three additions, keeping the original's honesty discipline (see `CHANGELOG.md`):

1. **Fixed 2 data errors** found when re-checking the graph against real code: removed a mis-extracted edge (`diarize→audio`, actually a misread of `pyannote.audio`), and added the `download_models` node that had been omitted.
2. **Upgraded the edge role** in the data_flow graph: an edge is a *path to an answer*, not *the answer*. Data characteristics live in the node; the edge carries only sequence + direction + routing label. Includes an `edge_index` for fast query filtering before opening nodes.
3. **Multi-AI blind benchmark** (`benchmark/`): the first token-cost measurements from multiple independent LLMs, not just argument.

## Core Principle About Edges (clarified in V1.0)

Edges do **not** carry the answer. The answer lives in the node. An edge holds just enough raw information to let a query *route* — which direction to go, whether this branch is worth taking. If many edges carry near-identical information, that is a sign of **poor node decomposition**, not a flaw to patch by stuffing more metadata into the edge.

## Try It in 2 Minutes

Open the PoC files in a browser (no install needed):

- [`poc/pipeline_v11_graph_viewer.html`](poc/pipeline_v11_graph_viewer.html) — view three graphs (code dependency, data flow, concepts) extracted from a real STT codebase (Pipeline V11). The "Data flow" tab now uses the V1.0 edge architecture: each edge shows `seq · route`, click a node to see its data characteristics, and the sidebar has the `edge_index` table.
- [`poc/poc_graph_query.html`](poc/poc_graph_query.html) — simulates the alarm-by-family mechanism → activating conditional edges → cross-check jump.

## Empirical Evidence

Read [`benchmark/RESULTS.md`](benchmark/RESULTS.md) for details. Honest summary:

**Supported signal (robust):**
- **Structured retrieval loads far fewer input tokens than flat RAG** for structural-lookup questions — and this holds not just for the graph but for three different structures (graph-walk, a plain Table of Contents, and GraphRAG), across all rounds and every reliable AI, with no accuracy loss. Flat RAG is typically 2–6× heavier. This is the solid, repeatable result.
- **Multi-turn growth stays sublinear:** in the 4-turn chain (Round 3), every compact-history method keeps token_in growth far below flat accumulation (which grows ~190–400% turn-over-turn). The graph signature grows the *slowest* of the three in a majority of reliable AIs — node-ids are shorter than ToC entries, so the graph compresses best as history accumulates. This is the graph's narrower, defensible niche.

**Result against expectation (recorded anyway):**
- **The graph is not the absolute token winner.** A plain Table of Contents ties or *beats* the graph on absolute token_in (unanimous in Round 1, majority in Round 3, split in Round 2). On this small, largely linear codebase, much of the saving comes from **hierarchy**, not from edges. The "graph's edges drive the savings" framing is **not supported here** — recorded honestly. Whether edges pull ahead on a non-linear codebase is the next test.
- The hypothesis "graph resists fabrication better than RAG" **was not supported.** When a model tends to fabricate, it fabricates under all methods. Honesty depends on the model's nature, not the data structure.

**Still hypothesis:**
- The magnitude of token savings is not pinned down — range too wide to state a single number.
- token_out (output) is inconclusive across all rounds.
- Whether edges beat a plain hierarchy on a dense, non-linear codebase is untested.
- Behavior at >100 nodes, and **B3 / semantic jump / bounded traversal depth**, are not yet benchmarked.

## Read the Full Concept

[`docs/Knowledge_Graph_Architecture_v1_32.md`](docs/Knowledge_Graph_Architecture_v1_32.md) — the full concept document (tree B1 → web B2 → space B3, information-carrying edges, multi-family nodes, cross-check jumps, graph lifecycle, with a section honestly recording what is proven vs. still hypothesis).

## Theoretical Foundation — The NLC (Threshold–Quantity–Quality) Framework

This concept does not stand on intuition. It is grounded in the **THRESHOLD–QUANTITY–QUALITY (NLC)** framework, which is used to verify whether a B0 decomposition is "correct." Summary below is self-contained enough to evaluate the architecture; the full foundation is in the book (linked below).

- **THRESHOLD (Ngưỡng):** A boundary where, once crossed, structural constraints lose effect and the system shifts to different logic. Critically, a threshold is *not* a tunable variable — you cannot "raise it" by adding protective layers. In this architecture, the Δ3 schema-breaking point is a threshold in exactly this sense, not a parameter.
- **QUANTITY (Lượng):** Accumulated factors the system has not yet resolved. Quantity does not break constraints by itself, but each unit raises the probability of hitting one. This is why the architecture treats unresolved coupling as measurable load (e.g. in-degree), not as harmless detail.
- **QUALITY (Chất):** The operational role a node actually holds — not a moral attribute, and not freely chosen. A decomposition has correct *quality* when each node genuinely holds its declared role rather than having silently drifted into another.

A key consequence the architecture inherits directly (NLC, Chapter 11, *"Just Add Constraints"*): **constraints are not accessories.** You cannot fix a bad decomposition by piling metadata onto edges — *"Each added constraint creates new threshold."* This is precisely why edges here carry only routing information, and why redundant edge metadata signals a decomposition fault rather than something to patch.

> From the NLC book's final declaration: *"No return to repair → not optimization... Optimization is not belief. Optimization is logical discipline."*

This is also why the architecture differs from GraphRAG at the level of **ideology, not features** (see `docs/` section 8.1): GraphRAG is retrieval-first (build a graph bottom-up to *find* better); this architecture is optimization-first (lock a schema top-down, verified by NLC, where the graph is the *form of an already-optimized decomposition*).

### Books (foundation, not included in repo)

If you want the full foundation — or simply want to pressure-test whether the reasoning holds — the books are available:

- **THRESHOLD–QUANTITY–QUALITY** — the NLC framework: https://nguyenson57.gumroad.com/l/qxbgia
- **Am I Really Optimizing — Or Am I Hurting the System?** — optimization vs. pseudo-optimization, the 6-question validation set, authority vs. responsibility: https://nguyenson57.gumroad.com/l/oczdmd

The companion book *EVO* is referenced in the concept but is not yet published.

> Note: the repo is **self-contained enough to evaluate without buying anything.** The books are for going deeper, not for unlocking the argument.

## Honest Status — Read Before Judging

The repo follows a discipline: **claim nothing beyond what has been demonstrated.**

**Has evidence:**
- A real codebase was extracted into a Hub/Leaf tree (B1), with edges carrying verifiable `file:line` metadata (B2).
- Multi-family nodes, conditional edges, cross-check across two families — these are real phenomena.
- **Structured retrieval beats flat RAG:** across all rounds and three different structures (graph, ToC, GraphRAG), token_in is far lower than flat RAG with no accuracy loss — numbers from a multi-AI blind test (preliminary evidence, not rigorous proof).
- **Multi-turn growth stays sublinear** (Round 3), and the graph signature grows slowest of the three structures in a majority of reliable AIs — the graph's defensible niche.

**Recorded against expectation:**
- The graph does **not** beat a plain Table of Contents on absolute token_in (Round 1 unanimous, Round 3 majority). On this linear codebase, hierarchy explains most of the saving, not edges.

**Still hypothesis:**
- Whether edges beat a plain hierarchy on a dense, non-linear codebase.
- B3 / semantic jump / O(1) — the current PoC is still topology traversal, not teleportation.
- Behavior at >100 nodes.
- Advantage in token_out and in accuracy/anti-fabrication.

## Rebuttal

This is a project open to rebuttal. Finding where it breaks is a contribution. Especially welcome: re-running the blind benchmark (`benchmark/`) on your own codebase with other AIs, and reporting back if results differ.

## License & Citation

See [`LICENSE`](LICENSE) and [`CITATION.cff`](CITATION.cff).