# 4 Fundamental Principles for Drawing Network Diagrams
## Foundation Document — Step B2 in the Knowledge Graph Construction Process

**Version:** 2.0  
**Status:** Foundation document — validated through real-world application  
**Position in system:** B2 — the step that transforms a Tree (B1) into a Graph with genuine relationships  
**Related to:** Hierarchical Knowledge Graph Architecture v1.3

---

## Where This Document Sits in the 3-Step Process

Before reading the 4 principles, understand where they stand in the Knowledge Graph construction process:

```
B1 — TREE          →    B2 — FLAT GRAPH        →    B3 — SPHERE GRAPH
Static hierarchy        (This document)               Even distribution
Define the shape        Draw real relationships        Guarantee O(1)
"What exists?"          "How do things relate?"        "3-step traversal is inevitable"
```

**B2 is the pivotal step:** B1 tells you *which nodes exist*. B2 determines *how nodes relate to one another*. If B2 is wrong — nodes are not truly independent, arrows lack clear causality — then B3 cannot achieve even distribution, and the O(1) property of the graph can no longer be guaranteed.

The 4 principles below are the standards for executing B2 correctly.

---

## Introduction

This document is not about drawing "pretty diagrams" — it is about ensuring **correct thinking**.

A correct diagram must enable:
- problem analysis
- avoiding causal errors
- and not deceiving the person who drew it

> **Additional note:** Many diagrams look "seemingly correct" but are actually concealing errors in reasoning. The author convinces themselves they understand the system, while the diagram is merely an illustration with no analytical capability. This document sets a higher standard: a diagram must be a genuine thinking tool, not a decorative figure.

---

## I. PRINCIPLE 1 — DECOMPOSITION

Each block (node) in the diagram must simultaneously satisfy two conditions:

**1. Rich in internal characteristics**
- the interior may be complex
- may contain many steps, many factors

**2. Independent externally**
- does not need to know the details of other blocks to exist
- does not "absorb" multiple roles of fundamentally different natures

> One block = one unit of responsibility.

If a single block simultaneously:
- generates data
- makes decisions
- and adjusts behavior

→ that block has **incorrect decomposition**.

---

> **Additional note — why both conditions must hold simultaneously:**
>
> Condition 1 alone is insufficient — a block that is "internally complex" but not externally independent will create hidden dependencies with other blocks. Whenever block A changes, block B is also affected even though no one wrote that down explicitly — this is the source of the hardest bugs to debug.
>
> Condition 2 alone is also insufficient — a block that is "independent" but internally combines too many roles cannot be extracted or replaced later.
>
> **Violation example:** A node in the Knowledge Graph that simultaneously stores raw data, computes summaries, and decides when to update edges — this node is absorbing 3 fundamentally different roles. When raw data changes, no one knows which part of the node needs to re-run.
>
> **B2→B3 relationship:** A node correctly decomposed per Principle 1 is a prerequisite for B3 to "distribute evenly" onto the sphere surface. A node absorbing multiple roles creates "gravity" pulling other nodes toward it — breaking even distribution.

---

## II. PRINCIPLE 2 — RELATIONSHIPS / CAUSALITY

Arrows in a diagram are not there to connect things for the sake of appearance.

Each arrow must:
- be readable as a sentence
- clearly express a cause–effect, before–after, or condition–result relationship

Examples:
- A occurs → B is permitted to occur
- Without A → B is invalid

If an arrow cannot be read as a clear proposition → the diagram is wrong.

---

> **Additional note — a practical test:**
>
> The quickest test: cover the node names and look only at the arrows. If you cannot read "what leads to what and why" — that arrow is connecting form, not logic.
>
> There are 3 valid relationship types an arrow can represent:
> - **Temporal (before–after):** A must complete before B can begin
> - **Conditional (condition–result):** Only when A is true does B occur
> - **Trigger:** A occurs → B is permitted/required to occur
>
> If an arrow does not belong to one of these three types, it is expressing "vague association" — not causality.
>
> **Knowledge Graph relationship:** An edge in the graph is not just a connecting line — an edge is metadata carrying a relationship. Principle 2 is the reason an edge can answer a query without entering the node, because the relationship was clarified at the time B2 was drawn correctly.

---

## III. PRINCIPLE 3 — CONSTRAINTS

Constraints are **mandatory**, not optional.

Constraints may be:
- logical
- physical
- legal
- system-architectural
- resource-based

A diagram that does not clearly express constraints  
→ will cause the author to unconsciously "patch" it with overlapping arrows.

---

> **Additional note — how to represent constraints:**
>
> This is the least concretely taught principle, but it has a clear implementation:
>
> Constraints are represented **not by adding more arrows** — but by conditions attached directly to existing nodes or edges. For example:
> - Node A only accepts input when total resources < 80% → this condition is attached to node A, not a new arrow from a "resource monitoring module"
> - Edge from B → C is only active when legal condition X is satisfied → this condition is an attribute of the edge, not a new node
>
> **Why this matters:** When constraints are omitted, the author senses the diagram is "missing something" but cannot identify what. The natural reflex is to add arrows to "explain" it — and this is precisely the origin of overlapping and intersecting arrows.
>
> **Knowledge Graph relationship:** The Δ threshold in the Graph architecture is a constraint expressed explicitly — not a new node, not an added arrow, but a parameter attached to nodes/edges that defines when an update occurs.

---

## IV. PRINCIPLE 4 — INTENT & CONSEQUENCE

Every diagram must be able to answer:
- what is this diagram for?
- if done incorrectly, what are the consequences?

A diagram not oriented toward real consequences  
→ is only an illustration, not a thinking tool.

---

> **Additional note — how these two questions function:**
>
> The question "what is it for?" is not about writing a generic objective in the header. It is a filter to decide what must be in the diagram and what should be left out. A diagram without a clear answer to this question will have everything stuffed into it — because the author has no criterion for elimination.
>
> The question "if done incorrectly, what are the consequences?" forces the author to identify **the single most critical point** in the diagram. The most critical point = the point where, if wrong, the entire system is affected. Those points must be represented most clearly, not buried in a tangle of arrows.
>
> **Practical example:** A contract approval workflow diagram — if the purpose is "explaining the process to new employees" then it should emphasize sequence and conditions. If the purpose is "finding processing speed bottlenecks" then it should emphasize wait times and which conditions can be parallelized. Same system, two completely different diagrams — and both are correct for their respective purposes.
>
> **Knowledge Graph relationship:** The purpose of the entire architecture is "maximizing accessible knowledge within the same token budget." The consequence of error = wasted tokens, query misses, context explosion. Understanding this helps identify which nodes/edges are most critical and deserve the most careful design.

---

## V. THE MOST IMPORTANT CHECK: INTERSECTIONS

### Validation principle:

> **In systems thinking diagrams, if crossing arrows appear, the author has almost certainly decomposed incorrectly or merged concepts incorrectly.**

### What intersections mean:
- a block is carrying too many responsibilities
- causality is mixed across layers
- data is being confused with decisions
- iteration is being confused with recursion

Intersections are **not** the inherent nature of systems thinking,  
they are a **symptom of design errors**.

### How to handle them:
- do not "draw it more neatly"
- do not "accept the complexity"
- instead **re-split the blocks or re-split the layers**

---

> **Additional note — why intersections are a symptom, not an inherent property:**
>
> The most common argument for defending intersections is: "real systems are inherently complex; intersections are inevitable." This argument fails at a critical point: **the complexity of the system does not determine the shape of the diagram — the way it is decomposed does**.
>
> Given the same complex system, if it is decomposed correctly per Principle 1 and relationships are represented correctly per Principle 2, the diagram will naturally have no intersections — not because the system is simple, but because each relationship has been assigned to the correct layer and direction.
>
> **4 error types that lead to intersections:**
>
> 1. **A block absorbs too many responsibilities** → arrows from multiple sources must enter the same block → intersections are unavoidable
> 2. **Causality is mixed across layers** → an arrow from a high layer goes directly to a low layer bypassing the middle layer, while arrows from the middle layer still follow the normal direction → intersection
> 3. **Data is confused with decisions** → a data-storage node suddenly has a control arrow going to another node → intersection with the data flow
> 4. **Iteration is confused with recursion** → a normal processing loop is drawn as an arrow going back to a previous node → creates an intersection with the forward flow
>
> **B2→B3 relationship:** A B2 diagram with no intersections is a necessary condition for B3 to "map onto the sphere surface" evenly. If B2 still has intersections — meaning there are still decomposition errors — then when B3 performs even distribution, those intersection points will create "lumps" on the sphere surface, breaking the evenness property and causing the O(1) property to no longer hold.

---

## VI. CONCLUSION

Drawing network diagrams does not require many methods.

Only four things are needed:
1. correct decomposition
2. clear causality
3. explicit constraints
4. specific purpose

→ the diagram will naturally **have no intersections**.

If intersections remain:  
→ the diagram **has not been optimized or a concept is wrong**.

---

> **Additional note — why these 4 are sufficient:**
>
> No additional methods are needed because the 4 above form a closed system:
> - Principle 1 (decomposition) defines the *units* of the diagram
> - Principle 2 (causality) defines the *relationships* between units
> - Principle 3 (constraints) defines the *operating conditions*
> - Principle 4 (intent) defines the *criteria* for evaluating whether the diagram is correct
>
> A diagram that satisfies all 4 cannot have intersections — because intersections only appear when at least one of the 4 is violated. This is not an empirical observation — it is a logical consequence of each principle's definition.
>
> **Position in the process:** When B2 is completed correctly according to these 4 principles — no intersections, independent nodes, causally clear relationships, explicit constraints — the graph is ready for step B3: even distribution onto the sphere surface, guaranteeing the 3-step traversal property from any entry point.

---

*Version 2.0 — Foundation document B2. Original content preserved; supplementary explanations clearly marked.*  
*Linked to: Hierarchical Knowledge Graph Architecture v1.3 — Section B1/B2/B3.*
