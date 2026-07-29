# Synaptic pathways & novel thought (bio-comparable)

## What you asked for

Trace **synaptic pathways**, compare to the human body, allow **disconnect/reconnect**, form **long-term bonds**, and when a query co-activates knowledge, **walk those bonds** and **create new pathways** (new thought) — especially **cross-domain**.

That maps to real neurobiology more as **plasticity + association** than as “the brain invents facts from nowhere.”

## Human body ↔ FSOT Fixed map

| Human process | FSOT Zig analogue | Honesty |
|---------------|-------------------|---------|
| **LTP / Hebb** (“fire together, wire together”) | `HEBB_LR` increases `W[post,pre]` when pre & post co-fire | Same idea; not full STDP timing curve |
| **LTD / pruning** | Weight decay + `pruneWeakBonds` on weak unused edges | Simplified |
| **Synaptogenesis** | Zero weight → small contact on co-fire | Structural plasticity stand-in |
| **Adult neurogenesis** | **Limited** — we **rewire**, we do **not** mass-birth new units each thought | Matches adult human reality better than infinite new neurons |
| **Long-range association** | Concept graph bonds (taught + novel) across math/science/literacy | Memory association layer |
| **Anatomical routes** | `pathways_fixed`: thal / sens / assoc / hipp | Coarse 4-region map |
| **New idea** | Compose statement only from **grounded** bonds + co-activation; edge origin=`novel` | Not LLM free invention |

## Run

```powershell
cd embodiment\zig
zig build -Doptimize=ReleaseFast
.\zig-out\bin\fsot_mind.exe pathways
# aliases: synapse | synaptic | trace | think-path
```

## What a successful run shows

1. **BIO MAP** — explicit human ↔ machine correspondence  
2. **SYNAPTIC EDGE TRACE** — which unit→unit synapses carried spikes this query (`region[id] → region[id]`, weight, events)  
3. **CONCEPT PATHWAY** — walk from query seeds along taught bonds (e.g. plant→sun→water, two→three)  
4. **Novel bonds** — co-activated concepts from **different domains** get new edges (`origin=novel`)  
5. **NOVEL PATHWAY THOUGHT** — a sentence that was **not taught as a whole**, but every piece is grounded  

Example gate line:

```text
PATH edges=… hebb=… bonds 12→68 novel=56 cross=44 …
FSOT_SYNAPSE_PATH PASS
FSOT_NOVEL_PATHWAY_OK
```

## How this deepens “understanding”

Previous depth: **paraphrase → answer** on curriculum.  

This layer: **query → neural traffic + associative walk → new cross-links → new composite idea**.

That is the biological story of thinking with what you know:

- Pathways that fire get stronger  
- Pathways that sit idle can weaken  
- Co-activating “plant” (science) with “two/five” (math) or “read/book” (literacy) builds **cross-connective** structure — your “cross domain analysis”  
- A **new thought** is a **new path**, not a random token string  

## What is still not full human brain

- 32-unit lattice (not 86 billion neurons)  
- No molecular cascades, glia, full STDP windows  
- Concept graph is explicit (inspectable) on top of genetic `W`  
- Novel sentences are **composed from bonds**, not free generative language models  

That is intentional: **claimable process** on a genetic Fixed mind, not opaque SOTA chat.

## Expansion order (unchanged)

1. Keep STEM/literacy truth curriculum  
2. Deepen pathway tracing + multi-hop composition  
3. Only later: more units, richer STDP, broader knowledge  
