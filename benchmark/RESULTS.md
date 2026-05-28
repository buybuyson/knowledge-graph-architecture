# Multi-AI Blind Benchmark Results (3 rounds + a 4-method re-run + a non-linear multi-turn round)

> **Status: preliminary evidence.** This is NOT rigorous proof. The measurement method has limitations (see "Limitations"). Every number should be read as a *directional signal*, not a *validated constant*.
>
> **Update (4-method round):** the three problem sets were re-run with two stronger baselines added — ToC RAG (C) and GraphRAG (D) — to test whether the graph's *edges* drive the token savings or whether a plain hierarchy does just as well. Honest headline: structured retrieval beats flat RAG robustly, but the graph does **not** beat a plain Table of Contents on absolute token_in for this codebase. See "Round 4" below.

## Experimental Design

Goal: compare token cost between two ways of answering questions on the Pipeline V11 codebase (36→37 module nodes after the fix).

- **Method A — Flat RAG / flat accumulation (baseline):** chunk the code, load relevant chunks, answer. In the multi-turn round, resend the full prior history each turn.
- **Method B — Graph-walk / graph signature:** load the graph's edge list, filter relevant edges, open only the code lines at `evidence` (file:line) to confirm. In the multi-turn round, carry forward only a compact graph signature instead of full prior answers.

How objectivity was maintained:
- **Blind:** the problem statement does not reveal the answer, nor which method is expected to win. Sent to multiple independent AIs (GPT, Grok, Gemini, DeepSeek, Qwen, MathGPT) to run and measure themselves.
- **Token in/out separated:** because the initial hypothesis held that the advantage was in output.
- **A unified token-counting convention** stated in the problem so the AIs count the same way.
- **The grader (Claude) keeps the answer key private**, not sent to the answering AIs.

## Round 1 — structural-lookup questions (5 questions, 5 AIs)

Ratio of graph (B) token_in to RAG (A), lower = graph more efficient:

| AI | token_in B/A | note |
|---|---|---|
| GPT5.5 | 27% | serious measurement (loaded real context) |
| Grok | 33% | serious measurement |
| MathGPT | 49% | shallow measurement (small token_in, may not have loaded enough code) |
| Gemini | 61% | shallow measurement |
| DeepSeek | 133% | **not really measured** (round numbers, wrong direction) — excluded |

All 5 AIs reported the "match" column = yes (the two methods gave the same answer). DeepSeek gave a reversed result and fabricated numbers — this actually *reinforces* the non-bias of the problem (if every AI dutifully said "graph wins," that would be more suspicious of a primed problem).

## Round 2 — open question + 2 trap questions (6 questions, 6 AIs)

Question 2 (retry/backoff when calling Ollama) and Question 4 (embedding model) ask about something that **does not exist** in the code. The correct answer = "not found." This is a test of honesty.

### token_in results (B/A)

| AI | token_in B/A | token_out B/A |
|---|---|---|
| DeepSeek | 26% | 60% |
| GPT5.5 | 28% | 81% |
| MathGPT | 28% | 96% (shallow) |
| Qwen | 54% | 100% |
| Grok | 57% | 92% |
| Gemini | 73% | 92% |

### Trap-test results (fabricate or be honest)

| AI | Q2 RAG | Q2 graph | Q4 RAG | Q4 graph |
|---|---|---|---|---|
| Grok | honest | honest | honest | honest |
| Gemini | honest | honest | honest | honest |
| MathGPT | honest | honest | honest | honest |
| DeepSeek | **FABRICATED** | honest | honest | honest |
| Qwen | **FABRICATED** | **FABRICATED** | honest | honest |
| GPT5.5 | honest | honest | **FABRICATED** | **FABRICATED** |

## Round 3 — multi-turn token accumulation (4-turn chain, 5 AIs)

This round directly tests the README's core mechanism claim: in a multi-turn conversation, flat history **accumulates** each turn (resend everything, including prior answers), squeezing the shared token budget; graph signature compression should keep growth **sublinear**.

Setup: a 4-question chain where each question builds on the previous answer. Method A resends full accumulated history each turn; Method B carries forward only a compact `TURN_N_SIG` graph signature. The critical measurement is **token_in at each turn**, not just the total.

### token_in B/A ratio per turn (lower = graph compresses better)

| AI | Turn 1 | Turn 2 | Turn 3 | Turn 4 | decreasing? | reliability |
|---|---|---|---|---|---|---|
| GPT5.5 | 0.30 | 0.26 | 0.23 | 0.22 | yes | serious (largest token_in) |
| Gemini | 0.45 | 0.42 | 0.39 | 0.37 | yes | serious |
| Grok | 0.50 | 0.45 | 0.42 | 0.39 | yes | serious |
| Qwen | 0.75 | 0.42 | 0.31 | 0.25 | yes | shallow (small token_in) |
| DeepSeek | 0.77 | 0.39 | 0.26 | 0.20 | yes | shallow |

### token_in growth, Turn 1 → Turn 4

| AI | Flat (A) growth | Graph (B) growth |
|---|---|---|
| Gemini | +64% | +35% |
| Grok | +104% | +62% |
| GPT5.5 | +76% | +27% |
| Qwen | +254% | +16% |
| DeepSeek | +335% | +15% |

All 5 AIs answered "yes" to "does B.token_in grow slower than A.token_in across turns?" and all reported every turn's answer matched between the two methods (no accuracy loss from compression).

**Reading this honestly:** the three serious measurements (GPT5.5, Gemini, Grok — the ones with large enough token_in to have actually loaded the codebase) show graph growing 27–62% while flat grows 64–104%. The two shallow measurements (DeepSeek, Qwen) show the most dramatic gap (graph nearly flat) but loaded too little to fully trust the magnitude. The *direction* is unanimous across all five; the *magnitude* is best taken from the three serious ones.

## Conclusions

### 1. SUPPORTED: graph-walk loads fewer token_in than flat RAG (structural-lookup)

Rounds 1 and 2, every AI pointed the same way: graph token_in is lower than RAG (26–73%). Repeated across two different single-shot question sets. Plausible mechanism: the graph loads a compact edge table + a few precise `evidence` lines, instead of many full code chunks.

### 2. SUPPORTED (new, Round 3): graph signature keeps multi-turn token growth sublinear

Across a 4-turn chain, the B/A ratio decreases consistently turn-over-turn for all 5 AIs. Flat accumulation grows much faster than graph signature. This is the first direct measurement of the multi-turn accumulation claim that motivates the architecture. Still preliminary: 1 codebase, 1 topic domain, 3 fully reliable measurements.

### 3. NOT SUPPORTED: "graph resists fabrication better than RAG"

The initial hypothesis: the graph more readily says "not found" because if there is no corresponding edge, it knows there is nothing there. **The data does not confirm this.** When a model tends to fabricate, it fabricates under *both* methods (Qwen Q2, GPT5.5 Q4). Only 1 single case (DeepSeek Q2) was rescued by the graph. Conclusion: fabricating or being honest depends on the **model's nature**, not the **data structure**. Recorded exactly as such, against expectation.

## Round 4 — adding two stronger baselines (ToC RAG and GraphRAG)

> **Why this round exists.** Rounds 1–3 only compared graph-walk (B) against *flat* RAG (A). A fair critique: flat RAG is a weak baseline, and graph-walk might win simply because building a graph pre-organizes the knowledge ("compression effect"), not because the *edges* (relationships) carry value. To test this, the same three problem sets were re-run with two additional methods, both given **ready-made** structure so no AI has to build its own (mirroring how Method B is handed the graph in Section 5):
> - **Method C — ToC RAG:** a hierarchical table of contents (module → function → one-line summary → file:line). It says *where things live* but NOT *how modules relate* — the deliberate difference from the graph.
> - **Method D — GraphRAG:** Microsoft-style pre-built community report (clusters + summaries + drill-in nodes).
>
> The key question: **if the graph (B) only ties or loses to a plain hierarchy (C), then the gain came from hierarchy, not from edges.**

### Reliability filtering (stated openly, to avoid cherry-picking)

Several runs were excluded because the AI clearly did not filter/drill but loaded the whole structure (the tell: B or C token_in *larger* than flat A, or a fixed constant across all questions). Excluded: **DeepSeek** R2 (B/A = 1.82, graph heavier than flat), **Qwen** R1 (B and C ~3800 fixed, both >3× A), **Gemini** R1 (B = 1150 fixed, >3× A), and a broken **"Claude (simulated)"** R1 run (mismatched answers on 4/5 questions). Note the failure does not track vendor — a Google model and a US-labelled run failed the same way two Chinese models did. The cause is whether the AI actually filters, not who made it.

### Result — token_in ranking among B / C / D (reliable runs only)

| Round | C beats B? | Verdict |
|---|---|---|
| R1 (single-shot lookup) | **C < D < B in all 3 reliable AIs** (MathGPT, GPT5.5, Grok) | ToC wins absolute token_in, unanimously |
| R2 (open + traps) | B wins 3/5 (Gemini, GPT5.5, Grok); C wins 2/5 (Qwen, MathGPT) | Split — B and C close |
| R3 (multi-turn) | C wins absolute 3/5; **B wins growth-rate** 3/5 | ToC lowest absolute; graph lowest growth-rate |

All reliable runs, all rounds: **every structured method (B/C/D) still crushed flat RAG (A)** on token_in (A typically 2–6× heavier), with **no accuracy loss** (every "match" column = yes on reliable runs).

### What this means — recorded against expectation

**1. SUPPORTED (and strengthened): structured retrieval beats flat RAG.** This is the robust, repeatable result. It holds for graph, ToC, and GraphRAG alike, across all three rounds and every reliable AI.

**2. NOT SUPPORTED as stated: "the graph is the token winner."** On this codebase, a plain Table of Contents ties or *beats* the graph on absolute token_in (unanimous in R1, majority in R3). The "compression effect" critique has real empirical support here: much of the gain comes from **hierarchy**, not from edges. Recorded honestly, against the architecture's framing.

**3. Where the graph does win: multi-turn growth rate.** In R3, the graph signature's token_in grows the *slowest* turn-over-turn in 3/5 reliable AIs, because node-ids are shorter than ToC entries and compress better as history accumulates. This is a narrower, defensible claim than "graph saves the most tokens" — it is "graph compresses best as a conversation lengthens."

**4. GraphRAG (D) sits mid-pack:** consistently beats flat RAG, usually loses to ToC, and often loses to the graph. A fair statement is "this architecture is lighter than GraphRAG on multi-turn growth," not a blanket win.

**5. Fabrication unchanged by structure (R2 traps), again.** On the trap questions (Q2 retry/backoff, Q4 embedding — both nonexistent), each AI gave the *same* honest-or-fabricated verdict across all four methods. A model that fabricates fabricates regardless of A/B/C/D. This re-confirms the Round-2 finding: honesty is a property of the model, not the retrieval structure.

### Honest reading

The strongest claim this benchmark supports is **"structured retrieval (any of graph / ToC / GraphRAG) is far lighter than flat RAG, with no accuracy loss."** The narrower claim **"graph compresses multi-turn history better than a flat hierarchy"** has directional support from growth-rate data but not from absolute token counts. The claim **"the graph's edges are what drive token savings"** is **not** supported on this small, largely linear codebase — a plain ToC does comparably or better. Whether edges pull ahead on a codebase with dense, non-linear cross-dependencies is the obvious next test, and is not answered here.


## Round 5 — the non-linear codebase test (multi-turn, 7 AIs)

> **Why this round exists.** Every prior round ended on the same open question: Rounds 1–4 ran on the Pipeline V11 codebase, which is *largely linear* (a sequential STT pipeline) — exactly the shape where a plain ToC is expected to do well, and indeed ToC tied or beat the graph on absolute token_in there. The repeated caveat was: *"whether edges pull ahead on a codebase with dense, non-linear cross-dependencies is the obvious next test, and is not answered here."* **Round 5 answers it.**

### What changed from Round 4

- **Codebase swapped to Flask core** (`src/flask`, BSD-3-Clause), decomposed to **100 function-level nodes with 178 call edges**. This swap is deliberate and stated openly: Pipeline V11 has no dependency cycles, so it cannot test whether edges help on non-linear structure. Flask does. Proof of non-linearity is shipped in `verification_kit/data/nonlinearity_proof.json`: **4 dependency cycles (not a DAG), 27 fan-out branch points, 20 fan-in convergence points, density 1.78 edges/node.** This is a web of relationships, not a straight line.
- **Same 100 nodes presented three ways** (Flat / ToC / Graph). The only difference between ToC and Graph is the presence of the edge list — identical node set, so the comparison isolates the value of edges.
- **Questions are 4-turn cumulative and relationship-bearing:** Q1 direct lookup (static), Q2 conditional filter reusing Q1, Q3 transitive reach into a cycle reusing Q2, Q4 convergence (next-hop set) reusing Q2. These force *following relationships*, not just locating a node — the case where edges should matter and a flat hierarchy should not.
- **Ground truth is machine-generated, not author-asserted.** `verification_kit/scripts/build_answers.py` regenerates the answer key deterministically from the graph and emits a SHA-256 integrity hash (`EXPECTED_HASH.txt`). Anyone re-running gets the same key, or the hash mismatches and the data is known to be tampered. This closes the Round-4 limitation that the author hand-built the ToC.

### Results — total token_in across the 4-turn chain (7 independent AIs)

| AI | Flat | ToC | Graph | Q1 winner (static) | Graph overtakes ToC at |
|---|---|---|---|---|---|
| Gemini | 13419 | 10887 | **3711** | ToC | Turn 2 |
| Claude Sonnet 4.6 | 5631 | 2303 | **1016** | ToC | Turn 2 |
| ChatGPT | 4629 | 4030 | **3188** | ToC | Turn 3 |
| Grok | 2904 | 1456 | **1007** | ToC | Turn 2 |
| Qwen3.6 | 5410 | 5580 | **4675** | Graph | Turn 1 |
| Claude 3.5 Sonnet | 2411 | 2268 | **1250** | ToC | Turn 2 |
| MathGPT | 5728 | **4444** | 6796 | ToC | never |

All 7 AIs reported `answers_agree = yes` on every question — no method produced a wrong or different answer. The structure does not change correctness, only cost.

### What this means — recorded against the prior framing

**1. The open question is now answered, directionally: on a non-linear codebase, the graph's edges DO pull ahead of a plain ToC in multi-turn.** 6 of 7 AIs put Graph below ToC on total token_in — the opposite of the linear-codebase result in Round 4, where ToC won. The mechanism is visible in the per-turn data: ToC still wins the *static* Q1 in 6/7 (it carries no edges, so it is lighter to send once), but from Turn 2–3 onward, every relationship question forces ToC/Flat to re-cite node context so the LLM can reason out connections the hierarchy doesn't encode, while the graph reads them straight off the edges. Graph starts behind and overtakes — usually by Turn 2.

**2. This upgrades a claim from "hypothesis" to "preliminary evidence," and ONLY by one notch.** The prior repo said the graph's edge advantage on non-linear code was untested. It is now tested, 6/7 in favour, on one non-linear codebase, by independent measurers. That is real support for the *direction*. It is NOT proof of a magnitude — see below.

**3. The magnitude is not pin-down-able, and the spread is large.** Graph/ToC total ratios range from ~0.34 (Gemini) to ~0.55 (Claude 3.5) among the AIs that favour graph — and one AI reverses entirely. No single "graph is X× cheaper" number is defensible. Report the direction (6/7), never a constant.

**4. The MathGPT anomaly — kept in, not hidden.** MathGPT is the one reversal: it has Graph *heavier* than ToC at every turn and never lets Graph overtake. This is not a measurement failure to discard — it is informative. MathGPT appears to have measured a consistent literal cost (the edge list is genuinely longer than the bare ToC list at every single turn) **without modelling the re-citation cost that ToC incurs to resolve relationship queries.** In other words, the 6 AIs that favour graph are crediting the graph for *saving the work of reasoning out relationships*; MathGPT only counted bytes on the page. Both readings are internally consistent; they disagree about whether "the tokens you must add back to reason without edges" should be counted. They should — that is the entire point of a relationship query — which is why the majority reading is the more faithful one. But MathGPT staying in the table is the honest move: a benchmark where every AI dutifully agrees would be more suspicious of a primed problem, exactly as the reversed DeepSeek run was treated in Round 1.

**5. Caution on token-counting discipline (a real weakness this round exposed).** The per-turn numbers vary wildly between AIs that nonetheless agree on direction — e.g. ToC's Q1 was counted as 467 by one AI and 1635 by another (3.5× apart) on identical text. This means several AIs estimated rather than applied the stated regex convention. The 6/7 directional result is robust to this noise (the structural effect is large enough to survive sloppy counting); the absolute numbers are not. A cleaner follow-up should force each AI to report token_in broken into parts (view / history / re-citation) so estimation can be told apart from measurement.

### Honest bottom line for Round 5

The strongest claim Round 5 supports: **on a codebase with real dependency cycles and branching, a graph (nodes + edges) compresses a multi-turn, relationship-following conversation more cheaply than a plain hierarchy (nodes only) — confirmed in direction by 6 of 7 independent AIs, with no accuracy loss.** This is the specific gap the prior versions left open. What it does NOT establish: a fixed savings ratio, behaviour beyond 100 nodes, or that edges help on *linear* code (Round 4 showed they do not). The concept's larger O(1)-in-N / semantic-jump claim remains unproven, as before.

## Limitations (read before citing)

- **Tokens counted by an approximate convention**, not each model's real tokenizer. Trust only the *ratios*, not absolute numbers.
- **Savings magnitude scattered** (Round 1–2: 26%–73%; Round 3 growth varies widely between serious and shallow measurements) — no single number can be pinned down. Depends on how each AI chunks and defines "load."
- **token_out inconclusive:** middling across all rounds. The claim "graph is lighter on output" is not proven.
- **Round 3 magnitude is split by measurement depth:** shallow measurers (DeepSeek, Qwen) show the biggest gap but loaded the least context. Take magnitude from the serious three (GPT5.5, Gemini, Grok).
- **Tested on only 1 small codebase** (37 nodes) and a single topic domain. Behavior at large scale (>100 nodes) is still hypothesis — exactly as `docs/` Section 14 states.
- **The "do not speculate" warning in the round-2 problem made the AIs more cautious**, possibly inflating the "honesty" rate slightly. A later round should drop this warning for a cleaner test.
- **Each AI measured its own tokens** — more objective than the author measuring, but still has measurement error.
- **Round 4 ToC/GraphRAG structures were hand-built by the author**, then handed to the AIs ready-made. This keeps the test fair on the *retrieval* step (no AI builds its own structure), but the *quality* of the ToC and community summaries is the author's — a different author might build them better or worse. The comparison is "this graph vs this ToC vs this GraphRAG," not a universal claim about the methods.
- **The codebase is largely linear (a sequential STT pipeline).** This is exactly the structure where a plain hierarchy/ToC is expected to do well, which may be why ToC ties or beats the graph. A codebase with dense non-linear cross-dependencies has not been tested and could change the C-vs-B result.

- **Round 5 ran on a different codebase (Flask, 100 nodes) than Rounds 1–4 (Pipeline V11, 37 nodes).** This is intentional — V11 has no cycles and cannot test non-linearity — but it means Round 5 is not a like-for-like continuation; it is a separate experiment answering the open question. Do not compare Round 5 absolute numbers against earlier rounds.
- **Round 5 per-turn token counts are noisy across AIs** (same text counted 3.5× differently by different AIs), indicating several estimated rather than applied the regex convention. Only the 6/7 *direction* is robust; per-turn magnitudes are not.
- **Round 5 has one reversal (MathGPT).** Kept in the table deliberately. The majority reading credits the graph for saving relationship-reasoning work; the reversal counts only literal list length. The disagreement is about whether re-citation cost counts — it does — but the reversal is reported, not discarded.
- **Round 5 graph signature / delta model in the kit's `simulate_tokens.py` uses an author-set parameter** (`PER_NODE_CTX`) for the re-citation cost. The 7-AI run does not depend on it, but the kit's reference table does. Treat the kit's simulated table as illustration; trust the 7-AI measured table.

## Reproduction

The full problem statements (self-contained, paste into any LLM) are in `benchmark/round1_problem.md`, `benchmark/round2_problem.md`, and `benchmark/round3_problem.md`. Each now includes all four methods (A flat RAG, B graph-walk, C ToC RAG, D GraphRAG) with ready-made structures so any AI can measure them directly. Anyone can re-run with other AIs and compare. **The non-linear test that earlier rounds called for is now `benchmark/round5_problem.md`** (self-contained, paste into any LLM), with an independent verification kit in `benchmark/verification_kit/` that regenerates the ground-truth answers from the graph and checks them against a SHA-256 hash — so no one has to trust the author's answer key.
