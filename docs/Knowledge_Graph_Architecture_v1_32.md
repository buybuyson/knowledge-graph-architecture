# Hierarchical Knowledge Graph Architecture
## A New Direction for Information Retrieval in LLMs

**Version:** 1.32
**Status:** Concept + Partial PoC (B1→B2) — B3/O(1) not yet benchmarked
**Goal:** Maximize token savings, increase retrieval accuracy, extend context efficiently
**Origin:** An idea from hands-on experience building no-IT apps (3→5→17 nodes) + discussion with AI + multiple rounds of adversarial rebuttal + **a partial PoC extracting a graph from a real STT codebase (Pipeline V11)**
**Scope of application:** Greenfield projects. Legacy/Brownfield left open for a later version.

> **⚠️ Important note:** This is still a **concept** — not a framework, not an implementation guide.
> The goal is to articulate a way of organizing knowledge for LLMs clearly enough that a technical reader can read and evaluate it.
> **v1.32 adds a partial PoC** extracted from a real codebase, confirming the B1→B2 layers (real code can be graphed, edges carry verifiable metadata, multi-family nodes + conditional edges are real phenomena). **This PoC does NOT prove B3 / semantic jump / O(1)-in-N** — those claims remain at the concept stage *(see Section 15)*. A solo individual cannot fully implement it — a multidisciplinary team is needed *(see Section 10)*.

**Main changes from v1.31 (v1.32):**
- Added **Section 15 — Partial PoC Trace** from Pipeline V11: the concept's first empirical anchor, however narrow
- Empirical confirmation for **B1 (hierarchical tree)** and **B2 (edges carrying metadata per Principle 2)** — on 10 module nodes extracted via AST, each edge with `file:line` evidence
- Confirmed **multi-family nodes, Conditional Edges, cross-check across two independent families** are real phenomena, not theoretical assumptions
- Added the **path-independence condition (LCA check)** for cross-domain synthesis (Section 6.5, gap group 4)
- Updated **Sections 14.2 + 14.6** recording the v1.32 milestone and moving several unknowns from "purely theoretical" to "has partial evidence for B1-B2"
- Corrected the boundary: **the PoC confirms B1-B2, does NOT touch B3** — keeping the honest stance of Section 14.3

**Editorial additions in V1.0 (concept status unchanged, no proven-claims added):**
- Sharpened **Section 1.1**: added subsection **1.1.1** explaining the "context explosion" mechanism — 1M is a shared in+out budget; history accumulating turn over turn shrinks the output budget → truncated / inaccurate answers. Distinguishes "token accumulation" (causes truncation) from "compute O(n²)" (causes slowness/cost). Framed as *problem explanation*, not measured numbers.
- Connected **Section 1.4** to the 1.1.1 mechanism, noting that the current benchmark only measures single-shot token_in; the multi-turn accumulation axis remains an unbenchmarked hypothesis.
- Added **Section 8.1**: states clearly that this architecture **differs from GraphRAG at the ideological level** (optimization-first / top-down / verified by NLC, not retrieval-first / bottom-up) — to avoid being miscategorized as a GraphRAG variant. Still notes no direct benchmark against GraphRAG yet.

**Main changes from v1.3 (v1.31):**
- Changed **"3-step traversal" → "4 constant operations"** — clarifying that semantic jump is a distinct operation, not hidden preprocessing
- Clarified **B3 is not pure graph traversal** — but *graph traversal + semantic teleportation*, closer to an address space than a shortest-path graph
- Added the **4-operations table** in Section 2.3 and Section 4 (B3)
- Updated **Section 14** recording the v1.31 milestone: discovery of semantic jump through adversarial dialogue with GPT-4

**Changes from v1.3 retained:**
- Section 2.3 expanding B1→B2→B3 (v1.3)
- Principle 2 as the foundation of the Edge (v1.3)
- Companion document 4 Principles v2.0 (v1.3)
- Δ is not a quantity recomputed when new data arrives (v1.2)
- Update cost vs Query lifetime cost analysis against RAG (v1.2)
- Δ-branch execution latency split into 4 cases (v1.2)
- External review trace (v1.2)

---

## 1. The Problem to Solve

### 1.1 Limitations of Traditional RAG

```
Raw documents → Chunking → Vector embedding → Vector DB → Similarity search → Context → LLM
```

Core limitations:

- **Mechanical chunking:** Documents are cut at fixed sizes, not along meaning boundaries.
- **Flat retrieval:** Every chunk is equal in vector space. There is no hierarchical structure.
- **No relationships:** The vector DB stores content but not the relationships between document segments.
- **Wasted tokens:** Many chunks must be loaded into context for the LLM to infer relationships itself.
- **Context explosion over turns:** Not just "large document → long context → LLM forgets the start of context" (an attention problem). In multi-turn conversations, accumulated history **eats into the shared token budget**, shrinking the room left for the answer — mechanism detailed in 1.1.1.
- **Expensive debugging:** When a bug occurs, the entire context must be reloaded to find the cause.
- **Whole-pipeline coupling:** Changing one part requires re-testing or rewriting the entire pipeline.

#### 1.1.1 Explanation: the "context explosion" mechanism — why answers degrade over long conversations

*(This subsection is a **problem explanation**, not a measured claim. Its purpose: to state clearly what this architecture is solving.)*

A common misunderstanding: thinking "1M tokens" is capacity the model **sets aside to read documents**, so one should just stuff everything in. In reality that number is a **shared budget for both input and output in a single call** — tokens fed in and tokens generated out are drawn from the same pool.

In multi-turn conversations, because the model **does not remember between calls**, each turn must resend the entire prior history — including the answer the model itself just produced. History therefore **accumulates turn over turn**, eating into the shared budget. The consequence does not stop at "forgetting the middle," but is a more concrete operational chain:

```
Turn 1: [small question] + [large empty room to answer]   → full answer
Turn N: [entire accumulated history] + [remaining room, now shrunk]
        → no room left to generate tokens  → answer is TRUNCATED
        → or history must be compressed/cut to fit → answer on a DEGRADED context → INACCURACY
```

This is the real reason quality degrades across long conversations — a **distinct layer of problem** from "lost in the middle." Two things often conflated must be separated, to avoid being caught out when presenting:

- **Token accumulation (causes truncation + inaccuracy):** accumulated history fills the shared in+out budget. This is the direct mechanism squeezing output.
- **Compute cost (causes slowness + expense):** each new token must attend to the *entire* growing context, so compute grows with the square of length (O(n²)). This does not subtract from the token budget; it is the price (latency, VRAM, money) paid for each token sitting inside the budget.

**Why this matters for this architecture:** flat context-stuffing has no escape from the accumulation loop — history can only grow. The graph architecture attacks exactly this: instead of resending raw text each turn, history is **graphed into a compact signature** (see Section 6.3), keeping token cost near-constant rather than linearly accumulating. That is why this architecture's advantage lies in **multi-turn**, not single-shot (see 1.4).

### 1.2 Goal of the New Direction

> With the same amount of tokens (e.g. 1M tokens), the new system must:
> - Retrieve more context
> - Be more accurate
> - Retain longer conversation history
> - **Graph traversal cost = O(1)** — counting only the steps from the Hub entry point down to the Leaf, not the query-graphing step *(see Section 13)*
> - Debug faster by isolating the faulty node
> - **Extend by adding new nodes — without rewriting old nodes**

### 1.3 Why It Saves More Tokens Than Traditional RAG

The savings mechanism is structural — not random compression:

- **Traversal by role:** A query passes through at most 3 steps per the schema — no full scan
- **Edge metadata:** Aggregated information sits ready on the connecting edge — answers many queries without entering nodes
- **Contract-Guarded Node:** Internal node changes do not propagate to the graph — no context reload needed
- **Debug by node:** Load only the node producing the bug, not the whole project
- **Contract-Driven:** Cross-cutting concerns are managed in the Hub's spec — no tangled web of edges
- **Multi-turn advantage:** History is graphed into a signature, not re-fed as raw text every turn (see Section 6.3)

### 1.4 On Cost Comparison with RAG

A previous version tried to compare numbers (500 nodes + 2000 edges vs 500 chunks). That comparison was withdrawn because:
- A real vector DB cannot have only 500 vectors for 500 chunks — the context that creates vectors is much larger
- Comparing a single-shot query is unfair — RAG accumulates history cost per turn, this architecture does not

**The correct comparison:** In a multi-turn setting (long conversations, iterative debugging, multi-question document analysis):
- RAG / flat context-stuffing: token cost grows linearly with the number of turns — because history accumulates verbatim (mechanism in 1.1.1). By turn N, the budget for output is squeezed → the answer is truncated or inaccurate.
- This architecture: the initial query-graphing cost is amortized across the whole session, and graphed history holds token cost near-constant → the output budget is not devoured by history.

→ **This architecture's real advantage lies in multi-turn, not single-shot.** A single-shot benchmark may not reveal the advantage — as the current blind benchmark (which only measures single-shot token_in) gives a signal about token_in but does *not* yet reach this per-turn accumulation axis. The multi-turn axis remains an **unbenchmarked hypothesis** (see Section 14).

---

## 2. Theoretical Foundation

### 2.1 Design Philosophy — Modular with Additive Extension

**This is the most fundamental difference from modern systems.**

Most current AI systems (RAG, GraphRAG, fine-tuned pipelines) follow an **end-to-end** ideology: the whole pipeline is optimized together, and changing one part affects everything.

This architecture follows a **modular with additive extension** philosophy — close to the design of information hiding (Parnas 1972) and microservices with clear API contracts:

```
End-to-end (modern):
[Input] → [Large pipeline tuned together] → [Output]
 Change one place → affects everything → rewrite a lot

Modular with additive extension (this architecture):
[Input] → [Node A] → [Node B] → [Node C] → [Output]
          independent independent independent
 Add new node → write that node + update orchestration
 → Old nodes are untouched
```

**Terminology note:** A previous version used "Composable" — this misuses the standard CS sense. "Composable" usually implies free combination at runtime (Unix pipes, FP). This architecture locks the structure at B0, so the correct word is **modular**. The "add without breaking the old" property is called **additive extension** — adding to, not replacing.

**Everyday example:**
Project folders on a computer. Adding a new file to the "Contracts" folder does not affect the "Drawings" or "Estimates" folders at all. Each folder operates independently — that is modular.

**Direct consequences:**

- O(1) graph traversal is not a natural property — it is a **design constraint enforced from B0**
- Maintenance cost is far lower than estimates made from an end-to-end view
- Extending the system = adding new nodes + updating the relevant Hub/orchestration
- **Why 3 steps is feasible:** With independent nodes correctly decomposed at B0, "3 steps" is a schema designed from the start → naturally correct, with nothing extra to impose. Correct decomposition is verified by the author's NLC-EVO skill.

**Hands-on experience:** Building no-IT apps from 3 → 5 → 17 nodes under this philosophy showed that when the schema is locked correctly from the start, routing does not explode with volume. Each extension only adds new nodes and updates orchestration — old nodes stay intact. **Not yet tested at >100 nodes — this is an important unknown (see Section 14).**

### 2.2 Deliberate Inheritance from Database Design

This architecture deliberately inherits principles proven over decades of database design:

- **Edge metadata** → equivalent to a materialized view: summary information precomputed for fast querying without reading the whole node
- **Trigger to update edges when a node exceeds Δ** → equivalent to a database trigger + cache invalidation
- **Hierarchical Hub/Node** → equivalent to a relational schema with foreign keys
- **Schema Versioning** → equivalent to database migration

**Everyday example for edge metadata:**
A filename describing its content fully — "Contract_ContractorA_2024_Signed.pdf" — lets you know which file to grab the moment you open the folder, without opening each file to read it.

### 2.3 Three Maturity Stages of the Graph — B1, B2, B3

B1, B2, B3 are **3 maturity stages of the same graph** — not 3 different kinds of graph.

| Stage | Name | Characteristics | Everyday image |
|-------|------|----------------|---------------|
| B1 | Tree | Branching out, no lateral links | Company org chart — who reports to whom |
| B2 | Web (flat graph) | Lateral links between branches, clear cause–effect relationships | Road map — many connecting roads, each with signs |
| B3 | Spherical graph (Spatial graph) | B2 distributed evenly onto a sphere — no edges, no blind corners | GPS — enter a destination, the system computes the route immediately, no alley-by-alley search |

---

#### B1 — Tree: The Hierarchical Backbone

B1 defines **who is who in the graph** — Hub Root, Intermediate Hub, Leaf Node. This is a static structure, branching top-down, with no lateral links yet.

B1 answers the question: *"What components does this domain have, and who do they belong to?"*

If B1 is wrong — nodes wrongly merged, hierarchy unclear — then B2 and B3 cannot be correct, because the decomposition foundation is already skewed.

---

#### B2 — Flat Graph: Where Relationships Are Drawn

B2 is the pivotal step: from B1's hierarchical tree, draw the **lateral relationships between nodes** — forming a true network.

**B2's foundational document: *4 Basic Principles for Drawing Network Diagrams v2.0***

Those four principles — correct decomposition, clear cause–effect, explicit constraints, specific purpose — are the standard for B2 to reach the quality required for B3. A B2 that violates any principle cannot transition to B3 correctly.

**Principle 2 (Cause–Effect) is the foundation of the Edge:**

This is the most direct link between the B2 document and the Graph architecture. In the 4-principles document, Principle 2 requires: every arrow must be readable as a sentence, clearly expressing a cause–effect, before–after, or condition–result relationship.

When B2 is drawn correctly — i.e. every arrow has clear cause–effect — those arrows are not just formal connectors. They carry relationship information. And that relationship information becomes the **edge metadata** in the Knowledge Graph.

In other words: **edge metadata is not "designed in" to the graph after B2 — it already exists in B2's arrows if B2 is drawn correctly per Principle 2**.

This is why edges in this architecture can answer many queries without entering nodes — because the relationship was made clear at the B2 step, not the B3 step.

```
B2 — arrow with clear cause–effect:
  [Node A] ──"A completes → B is then allowed to start"──→ [Node B]

↓ Becomes an edge in the Graph:

  [Node A] ──[edge metadata: activation condition, relationship direction, summary info]──→ [Node B]
```

**Conditions for B2 to reach the quality needed to transition to B3:**
- No crossing arrows (a symptom of bad decomposition)
- Every node independent (not holding multiple roles)
- Every relationship has a readable cause–effect
- Constraints represented explicitly on nodes/edges, not via extra arrows

---

#### B3 — Spherical Graph (Semantic Manifold): Why 4 Operations Are Constant

**Core image:** B2 is a flat diagram. B3 is that diagram pasted onto a transparent sphere and spread out evenly.

"Transparent" is the key word — from any point on the surface, you can *see through* to the destination point without going around the topology. This is not literal geometry — it is a **semantic manifold**: topological distance no longer matters as much as *semantic addressability* — the ability to locate directly into the right semantic region.

**B3 is not pure graph traversal — it is graph traversal + semantic teleportation.**

In classical graph traversal:
```
A → B → C → D → ...   (distance = real topology distance)
```

In B3:
```
query understanding → semantic coordinate → jump into the right local region → local traversal
```

Traversal "bends space" — closer to a routing table, DNS lookup, or memory addressing than a shortest-path graph.

**4 constant operations — do not scale with N:**

| Operation | Content | Property |
|-----------|---------|----------|
| **Op 1** | Query → semantic edge (graphing the query into a signature) | Reasoning happens here — only once |
| **Op 2** | Semantic region resolve — determine the correct Hub entry point for the region | Deterministic lookup |
| **Op 3** | Semantic jump → to the Intermediate Hub of the target region | Teleportation — no sequential traversal |
| **Op 4** | Intermediate Hub → target Leaf Node → LLM synthesis | Local traversal |

Whether the graph has 100 or 1 million nodes, it is still **4 constant operations** — because Op 3 (semantic jump) jumps straight into the right region, not traversing the intervening nodes.

**Why the initial intuition was "3 steps":**

The human brain naturally does not count the semantic jump (Op 3) as a step — it treats it as "spatial localization," similar to looking at a map and instantly knowing which district to head to before starting to move. The localization step does not *feel* like traversal. So intuition says "3 steps" — but more formally it is 4 operations.

**Important: 3 or 4 is not the crux.** The crux is **O(1) — does not scale with N**. That is the result of value.

**Conditions for B3 to work correctly:**

B3 can only distribute evenly (a clean semantic manifold) if B2 has no crossings. If B2 still has crossings — nodes holding multiple roles, relationships without clear cause–effect — then when "pasted onto the sphere," those crossing points create "bumps" that break uniform addressability. Result: the semantic jump is no longer accurate — it no longer jumps to the right region.

**The full cause–effect chain:**

```
B0: Nodes correctly decomposed (verified via NLC-EVO)
      ↓
B1: Clean hierarchical tree — no node holding multiple roles
      ↓
B2: Flat graph with no crossings — every relationship has clear cause–effect (4 Principles)
      ↓
B3: Semantic manifold (evenly distributed spherical graph)
    — accurate semantic jump → 4 constant operations (inevitable)
      ↓
O(1) traversal — not a claim, a consequence
```

**Operating-system analogy:**

| Graph Architecture | Equivalent in OS |
|-------------------|------------------|
| Hub | Namespace |
| Query signature | Address translation |
| Semantic jump | Page table lookup |
| Leaf Node | Memory page |
| Edge metadata | Routing metadata |

This is why this concept is closer to a **semantic operating system** than an ordinary graph retrieval system.

### 2.4 The Delta (Δ) Principle — Node Stability Threshold + Schema Versioning

Each node has a stability threshold Δ. When content changes:

```
Change < Δ1        →  Update node content
                       Schema: unchanged

Δ1 ≤ change < Δ2   →  Update node content + trigger update of related edge metadata
                       Schema: unchanged

Δ2 ≤ change < Δ3   →  Restructure node + related edges
                       Schema: local version bump for that node

Change ≥ Δ3        →  Break the node, restructure the whole graph region
                       Schema: version bump for the whole region
```

**Everyday example:**
Node "Steel unit price":
- Price changes 5% (below Δ1) → just update the number in the node, no outside effect
- Price changes 30% (exceeds Δ1) → update node + trigger update of the total estimate on edge metadata
- The entire material catalog changes structure (exceeds Δ3) → restructure the whole "Materials" region

**"Lock" in B0 is the baseline version 1.0 — not immutable forever.**

**Δ is an operational parameter with a feedback loop — not a made-up number:**

Δ1, Δ2, Δ3 are derived from domain mechanics, not chosen arbitrarily:
- Δ1 tied to **propagation cost** — if propagating too frequently → Δ1 too sensitive → raise the threshold
- Δ2 tied to the **document review cycle** in the domain — e.g. the review cycle for estimate changes
- Δ3 tied to **signs of stale answers** — if user feedback "the answer is no longer correct" rises → Δ3 too sluggish → lower the threshold

This is an industry-proven pattern: autoscaling thresholds, cache TTL, circuit breakers — all start with **heuristic + feedback tuning**, not closed-form proof.

**Δ is not a quantity recomputed when new data arrives:**

Δ1, Δ2, Δ3 are derived **offline** from domain mechanics and tuned via the feedback loop above. When new data enters the system, the system **does not "wait for Δ to be computed"** — Δ is already there. The system only does 2 things:
1. Measure the magnitude of the new data's change relative to the current node
2. Compare against the existing Δ thresholds → choose the handling branch

This is a **comparison**, not a **Δ computation**. So the latency when new data enters is the **latency of executing the corresponding branch**, not a "latency of waiting for a Δ check."

However, there is an important distinction that most "threshold-based" frameworks in industry overlook: **Δ in this architecture is not the difference of two quantities**. It is the **quantity accumulated up to the point of breaking a structural constraint**. Δ1 and Δ2 are tunable parameters. Δ3 is not — it is the point after which the region's logic system no longer exists. "Fixing Δ3" is meaningless; there is only "building a new region." The formal foundation for Δ and binary constraints: the **Threshold–Quantity–Quality** framework (Zenodo DOI: 10.5281/zenodo.18449570).

**Contract-Guarded Node lifecycle:**
```
B0: Open     → node is analyzed to determine its Hub/Leaf role,
               hierarchical relationships, contract interface
B1: Locked   → contract is locked, node built independently
Runtime:     → Contract-Guarded — internal changes do not spread beyond the contract
               Delta trigger only updates edge metadata (controlled coupling),
               does not break the contract
```

**Why not called "Encapsulated Node":** Encapsulation in classical CS means no side-effects outward when internals change. This node has an edge-metadata trigger when exceeding Δ1 — that is a controlled side-effect (controlled coupling), not pure encapsulation. The name "Contract-Guarded" is more accurate.

### 2.5 On Edge Metadata — Current Scope

Edge metadata is designed to be enough to:
- Direct traversal without entering nodes
- Store aggregated information for common queries
- Trigger updates when a node exceeds the Δ threshold

The optimal structure of the metadata is an open question — not a blocker for the PoC.

### 2.6 Hard Principle — The Edge Is an Architectural Relationship

**The Edge in this model is an architectural / knowledge-hierarchy relationship Edge** — absolutely not an Edge describing function-call flow.

Cross-cutting components (Logger, Auth, Config) are managed by a **Contract-Driven** mechanism — specified within the parent Hub's spec, not represented with Edges.

---
## 3. Detailed Architecture

### 3.1 Component Definitions

**Everyday example before reading the definitions:**

```
Project folders on a computer:
/Project-A                          ← Hub Root
  /Contracts                        ← Intermediate Hub
    Contract_ContractorA.pdf         ← Leaf Node
    Contract_ContractorB.pdf         ← Leaf Node
  /Estimates                        ← Intermediate Hub
    Estimate_Construction.xlsx       ← Leaf Node
    Estimate_Equipment.xlsx          ← Leaf Node

Subfolder name = edge metadata (read the name and you know what's inside)
Open the right folder → grab the right file = 3-step traversal
```

**Role definitions:**

```
Hub Root           — The root Hub of the whole graph. Represents the largest Domain.
Intermediate Hub   — Both a child Node of the Hub above and a parent Hub of the Nodes below.
Leaf Node          — The final node in a branch. No child nodes below.
                     The smallest information unit: a specific document, code module,
                     or specific unit of information.
```

**Hub (any level):**
- Contains: contract, glossary, test spec, pipeline of the entire sub-graph below
- **Cross-cutting concerns (Logger, Auth, Config) are defined in the Hub's contract — no separate edge created**

**Leaf Node:**
- Each node = a single task, describable in one sentence
- **Contract-Guarded:** Internal changes do not propagate outward if the contract is unchanged
- **Modular & Additive:** New nodes can be added without affecting existing nodes

**Edge:**
- Directed
- Carries metadata on the edge itself — not just connecting two points
- **Represents an architectural / knowledge-hierarchy relationship — not function-call flow**
- **Metadata content is formed from the cause–effect relationship clarified at B2** (see Section 2.3)
- When a node exceeds Δ1: triggers an update of the corresponding edge metadata

**Shadow Edge (temporary edge):**
- Created automatically when traversal detects a real relationship between 2 nodes that have no edge
- Labeled `unverified` — does not participate in official routing
- Logged into the Schema Review Queue for a B0 minor review
- Lifecycle: create → verify → promote to permanent or discard

**Conditional Edge:**
- Exists in the schema from B0 but disconnected by default
- Activates only when a query satisfies a condition predefined in the schema
- **[Confirmed by PoC V11]** On a real codebase graph, the on–match–off mechanism works correctly: query touches a region → same-family hubs raise an alarm → only edges carrying matching information turn on, non-matching edges stay off. This is a *binary constraint* (match or off, no intermediate state) — see Section 15.3.

**Actor (Agent / User):**
- Not a Hub, not a Node
- An entity that **travels on the graph** per the schema
- Capability map: stores each LLM/API's capability per benchmark
- **Escalation logic:** When the target node exceeds current capability → automatically escalate to a stronger LLM

### 3.2 Connection Rules — By Role

| Connection | Allowed | Edge type |
|-----------|---------|-----------|
| Hub → direct child Node | ✅ | Permanent edge, with metadata |
| Hub ↔ Hub same level | ✅ | Permanent edge if a real relationship exists |
| Hub ↔ Hub different level | ✅ | Permanent edge, carrying relationship info |
| Leaf Node ↔ peer Leaf Node | ❌ by default | Conditional edge — opens only when activated |
| Leaf Node → direct parent Hub | ✅ | One step up |
| Leaf Node → skip Hub straight to root | ❌ | Never — if it does, it is a Hub |
| Any → Any (temporary) | ⚠️ Shadow Edge | unverified — does not participate in main routing |

**Principle:**
> If a node needs to connect directly up to the root Hub, skipping the intermediate layer — that is a signal the node is playing the role of an Intermediate Hub. It needs reclassifying at B0.

**Signal that B0 is not yet achieved — When a need for a 4th layer or below appears:**

If analysis leads to a need for a child layer below the current Leaf Node, this indicates the schema is not decomposed cleanly enough. Correct actions:

- **Option 1:** Return to B0, split an Intermediate Hub or re-decompose the Leaf Node
- **Option 2:** If the domain is genuinely complex — split into an independent sub-graph with its own Hub Root

### 3.3 Three Types of Node Change

| Type | Description | Schema impact |
|------|-------------|---------------|
| **Type A** — Intra-zone | Add a Leaf Node under an existing Intermediate Hub | No need to re-verify the graph. Only verify the new node + edge with the parent Hub |
| **Type B** — Inter-zone | Add a new Intermediate Hub under the Hub Root | Verify the new edge + ensure no path >3 steps is created |
| **Type C** — Topology change | Add a new Hub Root or change the hierarchy | Schema migration — triggers Schema Versioning, re-verify the affected region |

---

## 4. Graph Lifecycle — B0 to B3

### B0 — Feasibility & Schema (Mandatory before everything)

The entire graph is defined here. **Applies to Greenfield Projects.**

**Why B0 is the key to O(1) and modular extension:**

O(1) graph traversal is not a natural property — it is a design constraint enforced at B0. When the schema is designed correctly from the start with a clear Hub/Node hierarchy (verified via NLC-EVO), traversal in at most 3 steps is an inevitable result of the architecture — not because it is forced, but because the B0→B1→B2→B3 chain has guaranteed it (see Section 2.3).

```
User request
        │
   [Request analysis — parse entities, scope, constraints]
        │
   [Feasibility check]
   - Call multiple LLMs/APIs to analyze
   - At most 5 debate rounds (hard limit)
   - The strongest LLM (by convention) plays the critic
   - If disagreement → NLC-EVO recombination → a new debate round
   - At most 3 NLC-EVO iterations
        │
   Feasible? ──── NO ──→ Answer the cause + stop
        │
       YES
        │
   [Quality Validation chooses architecture]
   - ≥ 3 different hierarchical options
   - Scored by: node independence, debuggability, extensibility
   - The winning option exceeds a user-defined threshold
        │
   [Lock the overall schema]
   - All Hubs/Nodes, edges, conditional edges
   - Cross-cutting contracts in the Hub spec
   - Capability map: which LLM/API does which node
   - Extension zone: define the region permitting Type A extension
```

B0 does not answer the question "who has the right to call the debate result optimal?" by AI consensus. It uses a formal 6-question test — a test that any decomposition option must pass, regardless of how many AIs agree. The foundation of the 6-question test: P. N. Son, *Am I Really Optimizing — Or Am I Hurting The System?* (Gumroad).

---

### B1 — Single Tree (Decompose & Build Independently)

```
              [Hub Root: Project A]
             /        |          \
   [Int.Hub]      [Int.Hub]    [Int.Hub]
   Estimates      Contracts    Drawings
   /      \           |             |
[Leaf:   [Leaf:   [Leaf:        [Leaf:
 Const]   Equip]   Terms]        Arch dwg]
```

**Contract-Guarded Node principle (mandatory at B1):**
- Each node is built fully independently
- Each node has its own contract + test + definition of done
- A node is considered stable only when it **passes the interface test suite**
- Fail > 2 times → switch LLM, do not get stuck

---

### B2 — Multiple Linked Trees (Integrate & Debug cross-module)

```
[Hub Root: Project A] ──────────────────── [Hub Root: Project B]
        │                                         │
[Int.Hub: Est-A]──[edge: "same contractor"]──[Int.Hub: Est-B]
    /      \                                   /      \
[Leaf:Const-A][Leaf:Equip-A]       [Leaf:Const-B][Leaf:Equip-B]
              ╌╌╌╌╌(conditional cross-domain)╌╌╌╌╌
```

- Intermediate Hubs of different domains connect if a real relationship exists
- Lateral relationships are drawn per the 4 Principles — each edge carries clear cause–effect, explicit constraints
- A cross-module bug = an overall-schema bug → isolate immediately
- Integrate in a chain: A+B → test → A+B+C → test (not all at once)

**B2 quality check before going to B3:**
- No more crossing arrows
- Every edge readable as a cause–effect proposition
- Constraints sit on nodes/edges, not extra arrows
- The purpose of each graph region is clearly defined

---

### B3 — Semantic Manifold (Production-ready)

**Core principle:**
> B3 is not pure graph traversal — it is **graph traversal + semantic teleportation**. From the Hub entry point (determined by the semantic jump), at most 4 constant operations reach the answer — not scaling with N.

**4 operations — how they are measured:**

```
CORRECT:
  Query
    ↓
  Op 1: Graph the query → Query Signature
        (AI reasoning happens here — only once)
    ↓
  Op 2: Semantic region resolve → determine the Hub entry point
        (deterministic lookup by signature)
    ↓
  Op 3: Semantic jump → Intermediate Hub of the target region
        (teleportation — no sequential traversal through intervening nodes)
    ↓
  Op 4: Intermediate Hub → target Leaf Node → LLM synthesis
        (local traversal)

  = always 4 operations, whether the graph has 100 or 1 million nodes
    (assuming the graph is correctly decomposed via NLC-EVO and B2 has no crossings)

NOT:
  The topology distance between any two Leaf Nodes

Cross-domain query:
  Op 1: Graph the query
  Op 2: Resolve Hub-A and Hub-B simultaneously
  Op 3: 2 semantic jumps in parallel
  Op 4: 2 local traversals in parallel → synthesis merging the results
  = still 4 operations, run in parallel
```

**The O(1) property is a property of the whole query path — not the graph diameter.**

```
User query
      │
   [Op 1 — Graph the query → Query Signature]
   (AI reasoning happens here — only once)
      │
   [Op 2 — Pre-Routing Classifier]
      │ does the query signature fit the schema?
      ├── YES → [Op 3] Semantic jump → Intermediate Hub of the right region
      │              │   (deterministic, no topology traversal)
      │         [Op 4] Target Leaf Node → LLM synthesis
      │              │
      │         Traversal cost = O(1)
      │
      └── NO → Gap Classification → Exception Path
```

**Conditions for the graph to reach B3:**
- B2 has passed the 4 Principles — no crossings, every relationship has clear cause–effect
- Clean semantic manifold — no "bumps" breaking addressability
- Every Hub entry point can reach the target Leaf via semantic jump + local traversal
- No isolated nodes
- Every Hub has enough edge metadata to navigate after the semantic jump
- The Pre-Routing Classifier works stably
- The packaged schema = the living document of the system

---

## 5. Application in a Dev / Coding Agent Environment

### 5.1 Mapping the architecture onto a codebase

| Graph layer | Entity in dev |
|------------|---------------|
| Hub Root | Repository / Project |
| Intermediate Hub | Module / Feature / Service |
| Leaf Node | Function / File / specific Task |
| Edge metadata | API contract, test coverage, architectural dependency |
| Conditional edge | Cross-module dependency, activated when debugging |
| Shadow Edge | Relationship discovered at runtime, awaiting promotion |
| Actor (Agent) | Coding agent — travels on the graph per the schema |
| Log Node | A dedicated node in the corresponding Hub — debug by traversal |

### 5.2 Extending the pipeline — The modular additive advantage

```
Add a new feature (end-to-end approach):
→ Edit pipeline → test everything → may break many places → rewrite a lot

Add a new feature (this architecture):
→ Identify the change type: Type A, B, or C
→ Type A: Write a new Leaf Node (independent, with its own contract)
          Update the related Intermediate Hub
          Test the new node + integration test with the Hub
          → Old nodes are untouched
→ Type B: Write a new Intermediate Hub + its child Leaf Nodes
          Verify no path >3 steps is created
→ Type C: Schema migration — re-verify the affected region
```

---

## 6. User Questions — Parallel Graphing

### 6.1 The Core Idea

A user's question is graphed into a **query signature** and then matched against the document graph — not fed into context as raw text.

**Example query signature:**
> Query: *"steel unit price, Hanoi project, 2024"*
> → entity: "steel", "Hanoi project"
> → intent: unit-price lookup
> → scope: 2024
> → Pre-routing determines the Hub entry point: "Hanoi Project"

**Routing is deterministic once the query has been graphed.** LLM reasoning happens only once, at the query-graphing step. After that, traversal is a schema lookup — not reasoning at each step.

### 6.2 Three Kinds of Schema-Fit Query

**Query B1 — Simple question:**
```
"Total construction estimate of Project A?"
→ Graphed: {entity: "Project A", intent: "total estimate", scope: "construction"}
→ Step 1: Hub Root: Project A
→ Step 2: Edge metadata → Intermediate Hub: Estimates
→ Step 3: Leaf: Construction Estimate → LLM synthesis
```

**Query B2 — Cross-domain comparison:**
```
"Compare the labor unit price of Project A and Project B?"
→ Path 1: PA → Est-A → Labor A  (3 steps)
→ Path 2: PB → Est-B → Labor B  (3 steps)
→ 2 parallel traversals → LLM synthesis merging results
```

**Query B3 — Complex multi-hop:**
```
"If steel rises 10%, how do the total contracts of projects under construction change?"
→ Filter Hub Roots by "under construction"
→ For each Hub Root: Intermediate Hub Estimates → Leaf Materials → Steel
→ Activate conditional edges → Aggregate → LLM synthesis
```

### 6.3 Graphing Conversation History

```
Traditional: N raw messages = N × tokens (grows linearly)

New direction:
[Hub: Conversation topic]
├── [Node: Main intent]
├── [Node: Entities mentioned]
├── [Node: Conclusions reached]
└── [Node: Open questions]
= K × tokens (K << N, grows constantly)
```

This is **the architecture's main advantage in a multi-turn setting**. A single-shot benchmark may not reflect this value correctly.

### 6.4 Query-Schema Gap Classification & Exception Paths

| # | Gap group | Cause | Handling |
|---|-----------|-------|----------|
| **1** | Ambiguous query / wrong terminology | Intent cannot map to the Hub glossary | Clarification Loop |
| **2** | Data does not exist | Source document missing | Scoped Negative Answer |
| **3** | Edge not yet mapped | Relationship exists but B0 missed it | Temporary Shadow Edge + log Schema Review Queue |
| **4** | Need cross-source synthesis | Query joins data from multiple Hubs | Parallel Multi-Path Traversal → **LCA check (path independence)** → Aggregate |
| **5** | World Knowledge / External Context | Information lies outside the graph | External Tool Routing |
| **6** | Requires computation / simulation | The graph stores facts, not an execution engine | Code Interpreter Handoff |
| **7** | Stale schema (Data Drift) | Node updated but graph not synced | Delta-Bypass Refresh + warning |
| **8** | Node in transition state | Node rebuilding due to exceeding Δ | Read-Through Cache + queue retry |
| **9** | Actor lacks synthesis capability | Target node exceeds current LLM capability | Escalate to a stronger LLM |

### 6.5 Path-Independence Condition — Valid Cross-Check

For gap group 4 (cross-synthesis), when two hubs H and K each hold a fragment of the result, the two fragments arrive at the merge point as two distinct objects → this is a **cross-check**, a strength compared to an LLM retrieving on its own (which blends the two fragments in a single generation and so cannot see contradictions).

**But a cross-check is only valuable when the two fragments are genuinely independent.** If the fragment in H and the fragment in K both originate from one root (two edges leading back to the same Leaf), we get a **cross-check illusion**: two sources look independent but share a root, so they always "match" — and that match proves nothing.

→ Before Aggregating, the system **must check whether the two paths share an ancestor** — a lowest-common-ancestor (LCA) query on the graph. Shared root (beyond the base Hub Root) → weak cross-check, attach a warning. Independent → valid cross-check. This is where the graph can *prove* independence rather than taking it on faith. **[PoC V11 simulated the LCA check — see Section 15.4.]**

---

## 7. Problem 2 — Normalizing Raw Documents

### 7.1 Normalization pipeline

```
Step 1 — Classify: the LLM determines the document type, domain, and which Hub it belongs to
Step 2 — Decompose structure: hierarchical headings, tables, key figures, relationships
Step 3 — Map into the schema (locked from B0)
Step 4 — Extract information for edge metadata
Step 5 — Normalize node content (semantic chunking along meaning boundaries)
Step 6 — Verify conditional edges
```

### 7.2 Incremental Update

After the graph is built the first time, there is no need to re-read everything. Update only when a node exceeds the delta threshold — similar to database indexing not rebuilding the entire index every time a new record arrives.

---

## 8. Comparison with Current Approaches

| Criterion | Traditional RAG | GraphRAG (Microsoft) | This architecture |
|-----------|----------------|---------------------|-------------------|
| Document structure | Flat chunks | Automatic graph (bottom-up) | Hierarchical graph, top-down schema (B0) |
| System extension | Re-embed + re-index | Re-build graph | Add node (Type A/B/C) |
| Information on edges | No | Yes (limited) | Yes + direction + metadata |
| Edge type | Not applicable | Execution-style | Architectural relationship (foundation from B2) |
| Contract-Guarded Node | No | No | Yes |
| Schema Versioning | No | No | Yes — Δ1/Δ2/Δ3 |
| Shadow Edge | No | No | Yes |
| Query graphing | No | No | Yes |
| Query-Schema Gap handling | Fallback vector | Fallback vector | 9 gap groups, handled separately |
| Traversal cost / query (schema-fit) | Grows with volume | Medium | O(1) — a consequence of B3 |
| Multi-turn advantage | None | Limited | High — graphed history |

### 8.1 The Fundamental Difference — This Is NOT a GraphRAG Variant

The table above can give the misleading impression that this architecture is just "GraphRAG with a few extra features." **It is not.** The difference lies in *ideology*, not in a feature list. A reader who reads only the table and skips this subsection will miscategorize it into the GraphRAG family.

**GraphRAG (and most modern systems) is *retrieval-first* thinking:** it starts from a pile of existing documents and builds a graph **bottom-up** to *find* information better. The goal is to improve recall over existing data. The graph here is an *index tool* serving the search.

**This architecture is *optimization-first* thinking:** it starts from the question "given a hard resource limit (the token budget), how do we organize knowledge to achieve the most?" The schema is **locked top-down at B0** *before* there is data, verified by the THRESHOLD–QUANTITY–QUALITY (NLC) framework and EVO — that is, the correctness of the decomposition is checked by a standard of optimization, not by vector similarity. The graph here is not an index tool; it is **the consequence of an already-optimized decomposition**.

Three core points of distinction:

1. **Direction of graph construction.** GraphRAG: bottom-up from data (the graph is derived *after*). This architecture: top-down from a schema locked at B0 (the graph exists *first*, data is filled in after). This is a difference in causal order, not in construction technique.

2. **The measure of "correct."** GraphRAG measures by retrieval quality (did it find the right thing). This architecture measures by the NLC optimization standard — does the decomposition meet threshold, quantity, quality; is each node genuinely independent. "Correct" here means *optimized*, not *found*.

3. **The problem being solved.** GraphRAG solves "do retrieval better." This architecture solves "within the same token budget, maximize accessible knowledge and keep cost near-constant across multi-turn" (see 1.1.1 and 1.4). Token savings are not a side-effect of a good index — they are a *design goal* set from the start.

> In short: GraphRAG uses a graph to **find knowledge better**. This architecture uses a graph as **the representation of an already-optimized decomposition** — sitting within a consistent system of optimization (NLC–EVO), where saving tokens and staying accurate across long conversations are inevitable consequences of correct decomposition, not something patched on.

*(Discipline note: this subsection describes a difference in **design orientation**, not a claim that this architecture has beaten GraphRAG on benchmarks. A direct empirical comparison with GraphRAG is still on the to-do list — see Sections 12/14.)*

---

## 9. Scope of Application & Limitations

### Best application (Greenfield Project):
- Newly built projects — the schema can be locked top-down before building
- Domains with hard structure: construction estimates, new codebases, technical dossiers
- Systems stable enough for B0 to be amortized over years

### Scale already field-tested:
- No-IT apps from 3 → 5 → 17 nodes — the modular additive pattern confirmed correct at this scale
- **Not yet tried at >100 nodes — this is an important unknown**

### Not yet defined (left open):
- Legacy/Brownfield Projects
- Fully unstructured domains
- Real-world compression ratio
- Optimal edge metadata structure
- Detailed Shadow Edge lifecycle
- Propagation cost of edge metadata
- Pre-Routing Classifier formal spec

### Update cost vs Query lifetime cost — Comparison with RAG

| Case | Classical RAG | This architecture |
|---|---|---|
| Every update | Uniform: embed every chunk + insert into vector index | Tiered by Δ |
| Case <Δ1 (majority) | Embed + insert | Only classify route + update a field in the node |
| Case Δ1–Δ2 | Embed + insert | Update node + propagate edge metadata |
| Case Δ2–Δ3 | Embed + insert | Rebuild node structure |
| Case ≥Δ3 (rare by design) | Embed + insert | Restructure the graph region |

**Opposite-signed trade-off:** RAG is cheap on update, increasingly expensive over query lifetime. This architecture tiers updates by Δ, keeping token efficiency stable over query lifetime.

---

## 10. Development Roadmap

> A solo individual cannot implement this architecture. A multidisciplinary team is needed.

**Phase 1 — Proof of Concept (1 narrow domain)**
- Proposed domain: construction estimate dossiers or a small Greenfield codebase
- Measure: traversal cost vs RAG, accuracy, debug speed
- Measure: P_fit_volume, P_fit_value
- Measure: Δ-branch execution latency (4 cases: L_classify, L_<Δ1, L_Δ1→Δ2, L_Δ2→Δ3, L_≥Δ3)
- Measure: the real distribution among the 4 Δ cases
- Measure: cumulative token cost vs RAG on a multi-turn workload

**Phase 2 — Generalization**
- Meta-schema for new domains
- Test B2: cross-domain linking
- Test scaling to >100 nodes, >500 nodes

**Phase 3 — Spatial graph + Query graph**
- Implement B3 fully
- Graph the query and the history
- Comprehensive benchmark vs RAG and GraphRAG

**Team needed:**

| Role | Task |
|------|------|
| Graph theorist / Mathematician | Delta formalization, topology, conditional edges, Shadow Edge lifecycle |
| NLP/ML Engineer | Normalization pipeline, Pre-Routing Classifier, query graphing |
| Domain Expert | Hub/Node schema, delta rules, contract spec |
| Systems Engineer | End-to-end pipeline, LLM API integration, node state management |
| LLM Researcher | Query mapping, context compression, benchmark, capability map |

---

## 11. Open Questions

1. **Delta formalization:** How to formally define and measure Δ1, Δ2, Δ3 for each document type?
2. **Small-world with a large graph:** Guarantee ≤3 steps from the Hub entry point on a >1000-node graph? *(cf. Watts-Strogatz)*
3. **Multi-turn compression ratio:** How many tokens does graphing history save?
4. **Brownfield B0:** The process and cost of bottom-up scanning?
5. **Real P_fit_volume:** The proportion of schema-fit queries in a real domain?
6. **P_fit_value:** How to define and measure it?
7. **Edge metadata structure:** The optimal structure?
8. **Shadow Edge lifecycle:** The detailed process?
9. **Schema migration cost:** The cost and process?
10. **Propagation cost:** When a node has many edges exceeding Δ1?
11. **Verifying node independence at large scale:** Is NLC-EVO at B0 enough, or is a runtime check needed?
12. **Real distribution among the 4 Δ cases:** What % does the <Δ1 case occupy in a real workload?
13. **Token cost lifetime:** Total cumulative tokens of this architecture vs RAG on the same multi-turn workload?
14. **B2 → B3 transition formalization:** What condition is sufficient to prove that a non-crossing B2 guarantees an evenly-distributed B3? Needs a formal proof from a graph theorist.

---

## 12. Explicit Assumptions

### A. Query Cost — Clear Separation

| Cost layer | Symbol | Definition | Complexity |
|-----------|--------|-----------|-----------|
| Query Understanding | C_qu | Op 1: Graph the query + Op 2: Semantic region resolve | Depends on query complexity, amortizable in multi-turn |
| Traversal | C_tr | Op 3: Semantic jump + Op 4: Local traversal to Leaf | **O(1) — 4 constant operations, a consequence of B3** |
| Synthesis | C_syn | LLM processing at the target node (within Op 4) | Depends on node size |
| **Total** | **C_total** | **C_qu + C_tr + C_syn** | |

> **O(1) is the SLA of the C_tr component (Op 3 + Op 4)** — not an end-to-end latency commitment. The semantic jump (Op 3) is a constant-cost operation because it is an address lookup, not topology traversal.

### B. Modular Additive — Why Maintenance Is Lower

Maintenance cost = the cost of the changed node + the cost of updating the related Hub. Other nodes are untouched — **assuming nodes are genuinely independent, verified via NLC-EVO at B0**.

### C. What the LLM Does in This Architecture

The graph does routing (deterministic once the query is graphed). The LLM does synthesis from clean nodes. LLM reasoning happens only once, at the query-graphing step (C_qu).

### D. Vector Retrieval Is a Cooperating Component

Vector retrieval can do the initial Hub-finding step. Graph traversal takes over from there.

### E. The B0 Schema Has a Lifecycle Tied to the Project

The B0 schema is the baseline version 1.0 — not immutable forever. Schema Versioning (Δ1/Δ2/Δ3) allows scoped, region-bounded migration.

### F. The 9 Gap Groups — Not a Closed List

The current 9 groups are based on theoretical analysis. A PoC may discover new groups.

---

## 13. Summary

> Instead of storing raw documents and searching by vector similarity in an end-to-end pipeline mindset, this concept organizes knowledge into a hierarchical, modular graph with additive extension — where the schema is locked top-down by B0 (verified via NLC-EVO), the graph matures through 3 stages B1→B2→B3 (hierarchical tree → flat graph with clear cause–effect per the 4 Principles → semantic manifold), B3 is not pure graph traversal but *graph traversal + semantic teleportation* — closer to a semantic operating system than a graph retrieval system, the 4-constant-operations property is a consequence of the semantic manifold rather than an imposed constraint, edges represent architectural relationships with metadata inherited directly from B2's cause–effect relationships, each node is a Contract-Guarded Node with controlled coupling and local Schema Versioning when Δ occurs, Δ is an operational parameter with a feedback loop (not a made-up number), queries are graphed into signatures for deterministic traversal with C_tr = O(1), queries that do not fit the schema are classified into 9 gap groups with dedicated exception paths, the LLM does synthesis on clean nodes after reasoning only once at the graphing step, and conversation history is graphed for the multi-turn advantage — thereby maximizing the amount of accessible knowledge within the same token limit.

**Status:** Concept v1.32 + Partial PoC (B1→B2). The PoC confirms graphing a real codebase for B1-B2; B3/O(1)/semantic-jump remain concept. A multidisciplinary team is needed for full implementation.

---

## 14. Notes After Adversarial Rebuttal

### 14.1 Points Successfully Defended

**On "3-step traversal from the Hub entry point" — reinforced in v1.3:**
- Not an arbitrary constraint — a geometric consequence of B3
- Full cause–effect chain: B0 correct decomposition → B1 clean tree → B2 no crossings (4 Principles) → B3 even distribution → 3 steps inevitable
- Falsifiable: find a domain where NLC-EVO does not pass under any decomposition → the architecture does not apply to that domain

**On safety when Δ3 is misjudged:**
- Thanks to the node-independence principle from B0, a wrong schema migration only re-groups nodes, it does not destroy content
- The error is conspicuous → users notice immediately, unlike the hallucination of traditional RAG

**On cost comparison with RAG:**
- Single-shot comparison is unfair — must compare in a multi-turn setting
- Opposite-signed trade-off between two axes: update cost vs query lifetime cost

**On Δ thresholds:**
- Δ1 and Δ2 are operational parameters with a feedback loop — an industry-proven pattern
- Δ3 is the structural-constraint-breaking point — not a tunable parameter

**On "Knowledge Freezing Latency":**
- Δ is not recomputed when data arrives — Δ is a parameter derived offline
- Real latency is tiered across the 4 Δ cases, not a single uniform metric

### 14.2 Points at 50/50 Status

**Scale >100 nodes:** No real evidence yet — the biggest unknown. *(PoC V11 is only at 10 module nodes — does not touch this unknown.)*

**P_fit_volume ≥ 80%:** An operational target hypothesis — needs a real benchmark.

**Hidden coupling between nodes:** At large scale, coupling not revealed in B0 analysis may exist. *(PoC V11 shows coupling CAN be revealed via in-degree: `utils` in-degree 21 is high hub coupling, measured automatically from AST — but this is static coupling at small scale, not hidden runtime coupling at large scale.)*

**Real distribution among the 4 Δ cases:** The assumption that the <Δ1 case is the majority has no real data yet.

**B2 → B3 transition formalization (new in v1.3):** The geometric argument about "pasting onto a sphere" currently stops at intuition — a graph theorist is needed to formally prove that a non-crossing B2 is a sufficient condition for B3 to guarantee even distribution and the 3-step property. *(PoC V11 does NOT touch this transition — it stops at B2.)*

**B1→B2 graphing from real code (new in v1.32 — now has partial evidence):** Before v1.32 this was purely theoretical. Now PoC V11 confirms: a real codebase was extracted into a Hub/Leaf tree (B1) and a graph with edges carrying metadata per Principle 2 (B2), each edge verifiable by `file:line`. *This is evidence for B1-B2, not B3.*

### 14.3 The Honest Stance

After all the rebuttal:

- The concept has **no proven fatal flaw**
- The concept **has many unknowns** solvable only by a PoC
- The concept **is worth a PoC** based on sound reasoning and hands-on experience at small scale
- The concept **is not enough to claim a "new paradigm"** — only enough to call a "serious architectural hypothesis"

### 14.4 Milestone v1.3 — Completing the B1→B2→B3 Chain

Version 1.3 marks the first time the concept has a **full cause–effect chain from B0 to O(1)**:
- v1.2 knew 3 steps was correct but could not explain why from a structural angle
- v1.3 established: the bounded-step property is a geometric consequence of B3, and B3 is only achieved when B2 is correct per the 4 Principles
- Linked with the companion document *4 Basic Principles v2.0*

### 14.5 Milestone v1.31 — Discovering the Semantic Jump

Version 1.31 marks an important clarification through adversarial dialogue with GPT-4:

**Discovery:** "3 steps" in v1.3 was a correct intuition about O(1), but missing one operation — the semantic jump. GPT-4, in formal analysis, made the same mistake in the same place: both failed to count the semantic jump as a separate operation because it does not *feel* like traversal.

**Important clarification:**
- B3 is not pure graph traversal — it is *graph traversal + semantic teleportation*
- The "transparent sphere" is not literal geometry — it is a semantic manifold: topology distance matters less than semantic addressability
- The formal count is 4 constant operations, not 3 steps

**Why the concept is stronger after this clarification:**
- The O(1) property does not rely only on the geometry of even distribution — it relies on a semantic addressing mechanism, closer to DNS/routing table/page table lookup than shortest-path
- This explains why the concept can scale to a very large graph: the semantic jump is no more expensive as N grows, because it is an address lookup, not topology traversal

**Open point after v1.31:** The formal proof of the B2→B3 transition still needs a graph theorist — it currently stops at an intuitive argument that is persuasive but not yet a mathematical proof. The specific question: what condition on B2 (no crossings + clear cause–effect relationships) is sufficient to guarantee that B3's semantic manifold has the constant-addressability property?

### 14.6 Milestone v1.32 — Partial PoC on a Real Codebase

Version 1.32 marks the first time the concept has an **empirical anchor**, however narrow — ending the "pure concept, no PoC" status for the B1→B2 layer specifically.

**Context:** The PoC extracts a graph from Pipeline V11 — a real Vietnamese STT codebase (faster-whisper + Ollama + pyannote), 10 main module nodes, via static AST analysis. Each edge carries `evidence` pointing to `file:line`, so no relationship is inferred.

**Confirmed (within the B1-B2 scope):**
- A real codebase was extracted into a **Hub/Leaf hierarchical tree** (B1) — `utils`, `transcribe`, `export`, `hardware_detect`, `model_locator` emerged as Hubs by measured in-degree, not hand-assigned.
- **Edges carry metadata** in the spirit of Principle 2 (B2) — each edge has a relationship type (`imports`/`calls`/`reads-env`/`resolves`) + information + evidence, not just a connecting arrow.
- **Multi-family nodes are a real phenomenon** — `transcribe` belongs to both the `model_locator` and `utils` families; `main` belongs to all 5 families. This is a case v1.31 did not anticipate: a node belonging to multiple Hubs.
- **Conditional Edge on–match–off** runs correctly on the real graph (Section 15.3).
- **Cross-check across two independent families + LCA check** was simulated (Section 15.4).
- **Preliminary (−) classification:** 2 direct `resolve` edges were labeled `legitimacy?` — exactly the points that should go through a centralized registry rather than calling directly.

**Not confirmed (still concept):**
- **B3 / semantic manifold / semantic jump:** the PoC is still topology traversal with family coloring — NO real teleportation.
- **O(1) not scaling with N:** only one N=10. Constancy as N grows cannot be measured.
- **Query graphed into a signature:** queries in the PoC are pre-written scenarios, not signatures generated from reasoning.
- **Δ, Schema Versioning, multi-turn history:** not touched.

**The honest stance is unchanged (Section 14.3):** This PoC lifts the concept from "no anchor at all" to "an anchor for B1-B2." It does NOT lift the concept to "B3 proven" or "enough to claim a paradigm." A single PASS at small scale proves *existence* (it can be done within one scope), not *always-correct* — in keeping with the discipline of the Threshold–Quantity–Quality framework that grounds it.

---

## 15. Partial PoC Trace — Pipeline V11 (new in v1.32)

> **PoC scope:** Confirms the **B1→B2** layer on a real codebase. Does **not** touch B3, O(1)-in-N, semantic jump, Δ, or multi-turn. Read Section 14.6 for the full boundary before interpreting the results below.

### 15.1 Subject and Method

- **Subject:** Pipeline V11 — a Vietnamese STT codebase (faster-whisper for recognition, Ollama for error-correction post-processing, pyannote for speaker diarization).
- **Method:** Static AST analysis of each `.py` file. Each `import` → an `imports` edge; each cross-module function call → a `calls` edge; each `os.getenv(...)` → a `reads-env` edge; each `resolve()` call → a `resolves` edge. Everything is *observed from source*, not inferred — each edge holds `evidence = file:line`.
- **Scale:** 10 main module nodes, 48 inter-module edges (full graph 36 nodes / 78 edges if config variables and models are counted as nodes).

### 15.2 B1 — The Hierarchical Tree Extracted Automatically

Hubs emerge by measured in-degree (not hand-assigned):

| Hub | In-degree | Role |
|-----|-----------|------|
| `utils` | 21 | Heaviest Hub — high coupling, touching it risks wide propagation |
| `transcribe` | 6 | Recognition-processing Hub |
| `export` | 4 | Result-export Hub |
| `hardware_detect` | 4 | Hub selecting the engine by hardware |
| `model_locator` | 4 | Hub resolving model paths |

→ Confirms: **a real codebase can be tiered into Hub/Leaf with correct B1 structure**, and in-degree reveals which Hub is a high-coupling point — measured, not judged.

### 15.3 B2 — Edges Carrying Metadata + Conditional Edge

Each edge is not just an arrow but carries: relationship type, information (`carries`), evidence. In the spirit of Principle 2 — the cause–effect relationship already exists in the edge, not designed in afterward.

The Conditional Edge on–match–off mechanism runs correctly on the real graph:
```
Query graphed → touches a Hub family
  → Same-family Hub raises an alarm (other Hubs stay quiet)
  → Activate the condition edge carrying information matching the query
  → Non-matching edge → off
```
This is a **binary constraint**: an edge matches (exists in this query) or is off — there is no "partial match."

### 15.4 Multi-Family Nodes and Cross-Check Across Two Independent Families

The PoC discovered **multi-family nodes** — a case v1.31 did not anticipate:

| Node | Belongs to families |
|------|---------------------|
| `transcribe` | `model_locator` + `utils` |
| `diarize` | `transcribe` + `utils` |
| `export` | `transcribe` + `utils` |
| `postprocess` | `transcribe` + `utils` |
| `main` | all 5 families |

**Handling multi-family (confirms the Section 3.1 hypothesis):** No "winning family" selection rule is needed. Both Hubs raising an alarm is fine — because after the alarm, the system reads the **information on the edge** to decide where to go. The family narrows the region; the information-on-the-edge is the real filter. The resolution burden sits on the edge (declarable), not on family selection (hidden).

**Cross-check + LCA check:** When a query needs to merge fragments from two families (e.g. "where is the whisper model loaded, does it go through a registry?" — a fragment in `model_locator` where `resolve` is defined, a fragment in `transcribe` where it is called directly), the PoC simulates a lowest-common-ancestor check: if the two paths share only `utils` (the base Hub) they are treated as independent → valid cross-check; if they share another ancestor → a weak-cross-check warning.

### 15.5 Preliminary (−) Classification on the NLC Foundation

Each edge is labeled with `minus_class`:
- `operational` (76 edges): fixable coupling, creates quantity, does not break a constraint.
- `legitimacy?` (2 edges): two direct `resolve` edges — suspicious points that should go through a centralized registry. These are exactly the points a V11 refactor should target.

> **Maturity note:** This classification is at the level of labeling by *edge type*, not yet classification by *runtime behavior*. A rigorous distinction between Operational(−) and Legitimacy(−) across many cases remains open (Section 11).

### 15.6 The Accompanying PoC Document Set

The PoC consists of three pieces, separated by the single-source-of-truth principle:
- **Source graph** (JSON): nodes/edges with `families`, `carries`, `minus_class`, `evidence` labels — for reuse and for the PoC to read.
- **Interactive PoC** (HTML): draws the graph as a radial sphere, lets you fire queries and visually watch the family-alarm chain → activate condition edges → cross-check jump → LCA check on real V11 data.
- **Framework document** (this concept): the theory, pointing to the NLC + EVO foundation, without reprinting the locked content of NLC.

### 15.7 What This PoC Must NOT Be Read As Having Proven

Repeated to avoid misreading (in sync with Section 14.6):
- Does not prove B3 / semantic manifold / semantic teleportation.
- Does not prove O(1) not scaling with N (only one N=10).
- No real query graphing (pre-written scenarios).
- Does not touch Δ, Schema Versioning, multi-turn history, or brownfield.

This PoC is **the narrow step 1** of Phase 1 in the Roadmap (Section 10) — confirming that graphing a codebase is feasible for B1-B2. The steps measuring O(1), P_fit, Δ-distribution, and token-lifetime still need a team and a full benchmark.

---

## Appendix: The NLC (Threshold–Quantity–Quality) Framework — How B0 Decomposition Is Verified

*This architecture verifies whether a B0 decomposition is "correct" using the Threshold–Quantity–Quality (NLC) framework. The summary below is self-contained enough to evaluate the architecture; the full foundation is in the book (linked at the end).*

- **THRESHOLD (Ngưỡng):** A boundary where, once crossed, structural constraints lose effect and the system shifts to different logic. Critically, a threshold is *not* a tunable variable — you cannot "raise it" by adding protective layers. In this architecture, the Δ3 schema-breaking point is a threshold in exactly this sense, not a parameter.
- **QUANTITY (Lượng):** Accumulated factors the system has not yet resolved. Quantity does not break constraints by itself, but each unit raises the probability of hitting one. This is why the architecture treats unresolved coupling as measurable load (e.g. in-degree), not as harmless detail.
- **QUALITY (Chất):** The operational role a node actually holds — not a moral attribute, and not freely chosen. A decomposition has correct *quality* when each node genuinely holds its declared role rather than having silently drifted into another.

A key consequence the architecture inherits directly (NLC, Chapter 11, *"Just Add Constraints"*): **constraints are not accessories.** You cannot fix a bad decomposition by piling metadata onto edges. As the book states verbatim: *"Each added constraint creates new threshold."* This is precisely why edges here carry only routing information, and why redundant edge metadata signals a decomposition fault rather than something to patch.

> From the NLC book's Final Declaration: *"No return to repair → not optimization... Optimization is not belief. Optimization is logical discipline."*

The companion framework, *Am I Really Optimizing — Or Am I Hurting the System?*, contributes the **6-question validation set** that B0 uses to test a decomposition (rather than relying on AI consensus): (1) Who / which perspective sees a need to optimize? (2) Why optimize? (3) What is the purpose? (4) What factors affect the optimization? (5) Does the result yield "+" or "−"? (6) If "−", is there a return loop? On the distinction between authority and capability — central to why pseudo-optimization arises — the book states: *"Having the right to intervene does not mean understanding the consequences... The gap between authority and capability is where pseudo-optimization is born."*

### Books (theoretical foundation, not included in this repo)

- **THRESHOLD–QUANTITY–QUALITY** (the NLC framework): https://nguyenson57.gumroad.com/l/qxbgia
- **Am I Really Optimizing — Or Am I Hurting the System?** (optimization vs. pseudo-optimization, the 6-question set, authority vs. responsibility): https://nguyenson57.gumroad.com/l/oczdmd

The companion book *EVO* is referenced in this concept but is not yet published. The repo is self-contained enough to evaluate without buying anything; the books are for going deeper, not for unlocking the argument.

---

*Version 1.32 — Concept + Partial PoC (B1→B2). Scope: Greenfield Project.*
*Companion document: 4 Basic Principles for Drawing Network Diagrams v2.0*
*Theoretical foundation: Threshold–Quantity–Quality (NLC) + NLC-EVO — pointed to, locked content not reprinted.*
*Author: Pham Nguyen Son.*
