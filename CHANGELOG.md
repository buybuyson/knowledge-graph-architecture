# CHANGELOG

## V1.3 — Round 5: the non-linear codebase test (answers the standing open question)

Every prior version closed on the same unanswered question: *do the graph's edges beat a plain Table of Contents on a non-linear codebase with dense cross-dependencies?* Rounds 1–4 could not answer it because they ran on Pipeline V11, a largely linear STT pipeline with no dependency cycles. V1.3 runs the test on a non-linear codebase and records the result against the architecture's own framing.

### Added

- **`benchmark/round5_problem.md`** — self-contained 4-turn cumulative problem set on **Flask core (100 function-level nodes, 178 call edges, 4 dependency cycles)**. The same 100 nodes are presented three ways (Flat / ToC / Graph); the only ToC-vs-Graph difference is the edge list, isolating the value of edges. Questions force relationship-following: Q1 direct lookup (static), Q2 conditional filter, Q3 transitive reach into a cycle, Q4 convergence — each reusing the prior turn's answer.
- **`benchmark/verification_kit/`** — an independent anti-fabrication kit. `build_answers.py` regenerates the ground-truth answers deterministically from the graph and emits a SHA-256 hash (`EXPECTED_HASH.txt`); `extract_graph.py` rebuilds the graph from the Flask source for anyone who distrusts the shipped `graph.json`; `score.py` grades an LLM's answers by precision/recall/F1 and flags fabrication. This closes the Round-4 limitation that the author hand-built the ToC and held the answer key privately.
- **`benchmark/verification_kit/data/nonlinearity_proof.json`** — machine-generated proof the codebase is non-linear (not a DAG; 4 cycles; 27 fan-out, 20 fan-in points; density 1.78), so the test cannot be dismissed as "still linear."
- **Round-5 results section in `benchmark/RESULTS.md`** — 7 independent AIs (Gemini, Claude Sonnet 4.6, ChatGPT, Grok, Qwen3.6, MathGPT, Claude 3.5 Sonnet).

### Result (recorded against the prior framing)

- **The open question is answered, directionally: on non-linear code, the graph's edges DO pull ahead of a plain ToC in multi-turn.** 6 of 7 AIs put Graph below ToC on total token_in — the reverse of Round 4's linear-codebase finding. ToC still wins the static single lookup (Q1) in 6/7; the graph overtakes once relationship queries accumulate, usually by Turn 2. No accuracy loss: all 7 AIs reported every answer matched across methods.
- **Upgraded by exactly one notch:** the multi-turn edge-advantage claim moves from "hypothesis" to "preliminary evidence." NOT to proof — it is one non-linear codebase, the magnitude spread is large (Graph/ToC totals from ~0.34 to ~0.55 among the favouring AIs), and one AI reversed.

### Honesty notes kept

- **The one reversal (MathGPT) stays in the table with an explanation:** it counted literal edge-list length without modelling the re-citation cost ToC pays to resolve relationships. The majority reading counts that cost (correctly — it is the point of a relationship query); the reversal does not. A benchmark where every AI agreed would be more suspicious, exactly as the reversed DeepSeek run was treated in Round 1.
- **Large per-AI counting noise is stated:** identical ToC text was counted 3.5× differently by different AIs, so several estimated rather than applied the regex convention. Only the 6/7 direction is robust; per-turn magnitudes are not.
- **No fixed savings ratio is claimed.** Behaviour beyond 100 nodes, and the larger O(1)-in-N / semantic-jump claim, remain unproven — as before.
- **Round 5 uses a different codebase than Rounds 1–4 (Flask vs Pipeline V11), by design.** Stated openly so it is not mistaken for a like-for-like continuation or a data swap.

---


## V1.2 — Two stronger baselines added (ToC RAG + GraphRAG)

This version re-runs the three existing problem sets with two additional retrieval methods, to test a fair critique: that graph-walk beat flat RAG only because building a graph pre-organizes knowledge ("compression effect"), not because the *edges* carry value. The two new baselines are stronger than flat RAG and are handed to each AI ready-made (no AI builds its own structure).

### Added

- **Method C — ToC RAG** (a hierarchical table of contents: module → function → one-line summary → file:line; lists *where things live* but not *how modules relate*) and **Method D — GraphRAG** (Microsoft-style pre-built community report) in all three problem files. Each problem set now compares four methods (A flat, B graph, C ToC, D GraphRAG).
- **Round-4 results section in `benchmark/RESULTS.md`** — re-runs across multiple AIs with explicit reliability filtering.

### Honest headline (recorded against the architecture's framing)

- **Structured retrieval (B/C/D) beats flat RAG (A) robustly** — across all three rounds, every reliable AI, no accuracy loss. This is the solid, repeatable result, now *strengthened* (it holds for three different structures, not just the graph).
- **The graph (B) is NOT the absolute token winner.** A plain Table of Contents (C) ties or beats it on absolute token_in: unanimous in Round 1, majority in Round 3, split in Round 2. On this small, largely linear codebase, much of the gain comes from **hierarchy**, not from edges. The "compression effect" critique has real empirical support here, and is recorded as such.
- **Where the graph does win: multi-turn growth rate** (Round 3) — node-id signatures are shorter than ToC entries and compress better as history accumulates. This is the narrower defensible claim, not a blanket token win.
- **GraphRAG (D) sits mid-pack** — beats flat, usually loses to ToC, often loses to the graph.
- **Fabrication unchanged by structure**, again (Round-2 traps): each AI gave the same honest-or-fabricated verdict across all four methods.

### Reliability filtering (stated openly)

- Runs were excluded where an AI loaded the whole structure instead of filtering/drilling (tell: B or C token_in larger than flat A, or a fixed constant across questions): DeepSeek R2, Qwen R1, Gemini R1, and a broken "Claude (simulated)" R1 run. The failure does not track vendor — a Google model and a US-labelled run failed the same way two Chinese models did. The cause is whether the AI actually filters, not who made it.

### Still hypothesis (unchanged)

- Whether the graph's edges pull ahead of a plain hierarchy on a **non-linear codebase** (dense cross-dependencies) is not answered here — it is the obvious next test.
- B3 / semantic jump / O(1)-in-N remains unproven, as before.

---

## V1.1 — Round 3 added (multi-turn token accumulation)

This version adds the third benchmark round, which directly tests the core mechanism claim behind the architecture: that flat history accumulation inflates token_in across a multi-turn conversation, while a compact graph signature keeps growth sublinear.

### Added

- **`benchmark/round3_problem.md`** — self-contained problem statement for a 4-turn conversation chain. Method A resends full accumulated history each turn; Method B carries forward only a compact `TURN_N_SIG` graph signature.
- **Round 3 results in `benchmark/RESULTS.md`** — 5 AIs (GPT5.5, Gemini, Grok, Qwen, DeepSeek). All 5 show the B/A token_in ratio decreasing turn-over-turn, and all report no answer-quality loss from compression. Across the 3 serious measurements (large enough token_in to have loaded the codebase), flat history grows +64–104% while graph signature grows only +27–62%.
- This is the first direct measurement of the multi-turn accumulation claim that motivates the architecture. Still preliminary: 1 codebase, 1 topic domain.

### Honesty notes kept

- Round 3 magnitude is split by measurement depth: the two shallow measurers (DeepSeek, Qwen) show the most dramatic gap but loaded the least context. Magnitude is taken from the serious three (GPT5.5, Gemini, Grok); only the *direction* is unanimous across all five.
- The earlier "graph resists fabrication better" hypothesis remains **not supported** (from Round 2) — unchanged.

---

## V1.0 — First stable release (after a round of work + testing)

This version lifts concept v1.32 (Concept + Partial PoC) to a version with a **broader empirical anchor**: beyond confirming the graph is correctly extracted from code, there is now a multi-AI blind benchmark measuring token cost. The original's honesty spirit is preserved — recording both supporting results and results that went against expectation.

### Data fixes (re-checked against the real V11 code)

- **Removed the incorrect `diarize → audio` edge** in `data/graph_v11_enriched.json` and `data/pipeline_v11_graphs.json`. This edge came from the AST extraction tool misreading `from pyannote.audio import Pipeline` (at `diarize.py:92`) as an import of an internal `audio` module. The `diarize` module does NOT actually import `audio`. Updated the `in_degree` of the `audio` node (3 → 2).
- **Added the `download_models` node** (previously missing entirely from the graph) along with 4 `reads-env` edges: reading `WHISPER_MODEL`, `WHISPER_DEVICE`, `WHISPER_COMPUTE_TYPE`, `HF_TOKEN` (at `download_models.py:46-49`). This is the file that had a cross-drive cache bug in the real project, so the graph being "blind" to this file was a significant gap that has been patched.

### Edge architecture upgrade (data_flow)

- **Separated the edge role from the node.** An edge becomes a *path to an answer*, not *the answer*. Each data_flow edge now carries: `seq` (sequence number), direction (from→to), `route` (a light routing label), `op`, `evidence`. The data's characteristics (`reversible`, `lossy`, `mutable`, `fields_changed`...) are consolidated into `node.props` — because these are characteristics of the *data state*, not of the *transformation step*.
- **Replaced `type: "transforms"` (repeated 9 times)** with a distinct routing vocabulary: `reads / replaces / derives / edits / annotates / emits`. Now one can filter "which step edits data content" without opening a node.
- **Added `edge_index`** — a summary table for queries to read first, each row having `answer_in` pointing to the node holding the answer. This is the concrete realization of the "filter out branches on the edge before entering the node" principle.
- *Principle derived:* if many edges carry near-identical information, that is a sign of poor node decomposition — not a flaw to patch by enriching the edge.

### Added empirical evidence

- **`benchmark/RESULTS.md`** — results of a 2-round multi-AI blind benchmark (see that file).
  - SUPPORTED: graph-walk loads fewer input tokens than flat RAG for structural-lookup questions (repeated across 2 rounds, multiple independent AIs).
  - NOT SUPPORTED: the hypothesis "graph resists fabrication better than RAG" — a model prone to fabrication fabricates under both methods.
- **`benchmark/round1_problem.md`, `round2_problem.md`** — self-contained problem sets so anyone can reproduce with other AIs.

### Viewer

- `poc/pipeline_v11_graph_viewer.html` upgraded to v2: the Data flow tab shows `seq · route` on edges, colors edges by route, the node panel shows `props`, the edge panel notes "the answer is in the target node," and the `edge_index` table appears in the sidebar.

### Honest stance retained

- Still stated clearly: **B3 / semantic jump / O(1)-in-N is NOT proven.** This benchmark measures *token savings* on a small codebase, NOT *teleportation independent of node count*. Behavior at >100 nodes is still hypothesis.
- The magnitude of token savings (26–73%) is *scattered* and should be read only as a direction, not a constant.

---

## v1.32 and earlier (original concept)

See `docs/Knowledge_Graph_Architecture_v1_32.md` for the concept version history (v1.3 → v1.31 → v1.32).
