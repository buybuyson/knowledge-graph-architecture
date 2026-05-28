# Multi-AI Blind Benchmark Results (3 rounds + a 4-method re-run)

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

## Reproduction

The full problem statements (self-contained, paste into any LLM) are in `benchmark/round1_problem.md`, `benchmark/round2_problem.md`, and `benchmark/round3_problem.md`. Each now includes all four methods (A flat RAG, B graph-walk, C ToC RAG, D GraphRAG) with ready-made structures so any AI can measure them directly. Anyone can re-run with other AIs and compare — and is encouraged to try a non-linear codebase to test whether the graph's edges pull ahead of a plain hierarchy.
