# Bounded Context Organization

The deployed default remains `classic`, preserving stage3A rendering. The
stage3B `compact` candidate is implemented and tested but is opt-in: its local
pilot did not improve the frozen field-retention checks. No service was restarted
and no database was migrated for this experiment.

## Selection and Callers

`memory.render_memory_context` accepts `context_format="classic" | "compact"`.
Without an explicit argument it reads `TRITON_RISCV_MEMORY_CONTEXT_FORMAT`,
defaulting to `classic`. Unknown values are rejected. Compact supports
`allocation="equal" | "demand"`; demand is the default **within compact**, not
the default production format. All budgets count Unicode characters, not tokens.

`diagnostic_memory.retrieve_memories` uses this entry point to construct
`context_excerpt`; the lifecycle Pydantic result and MCP tool retain it. Direct
development generation/repair prompts also use the same entry point. Existing
raw records without an evidence chain keep their legacy rendering path. The
plugin and Harness runtime were not modified: a host wishing to opt in must pass
the variable to its Python MCP process. Only local MCP delivery was verified,
not propagation through a running third-party Harness host.

```python
from codex_agent.memory import render_memory_context

text = render_memory_context(items, max_chars=6000, query_text=question,
                             context_format="compact", allocation="demand")
```

## Compact Format

`evidence-context-v2` is a serialized JSON context, not a new database schema.
Cases retain input order and outcome, failure stage, known conflicts/gaps, and
unknown remote binding/causality. Evidence keeps IDs, state, case references,
source, run, proposal, attempt and location. Sources/runs/proposals use local
sequence aliases allocated from their complete values, so shared prefixes cannot
collide. All reference tables count towards the same 6000-character default.
Unrepresentably long metadata is explicitly shortened with a hash; it is not an
exact source locator and must not be treated as a delivered source document.

Only evidence with matching content **and** provenance, state, time and attempt
can be shared. Shared evidence retains all parent-case references and IDs.
Different runs or attempts are never merged merely because their messages match.

Short text stays complete. Longer JSON selects existing complete fields; text
uses paragraph/line boundaries; logs prioritize error/result/negative lines;
patches select whole hunks with adjacent removal/addition lines. Oversized atomic
units can be omitted rather than misleadingly split. Omitted fields/units and
upstream truncation remain visible. This is deterministic excerpt selection,
not LLM summarization or a claim that every important fact survives.

After minimal case information, equal divides incremental character capacity
between cases; demand prioritizes evidence types indicated by the public query.
Both first attempt minimal evidence for each selected case. Neither fetches more
records or uses evaluation labels. Packing recomputes serialized size including
references and markers; extremely small budgets return an explicit omission
notice instead of partial references.

## Whole-Message Boundary

The 6000-character limit applies to `context_excerpt`, **not** the entire MCP
message. Existing `items` are still returned for compatibility, each with its
existing limit, alongside the excerpt. The local SDK exposes both text content
and structured content containing those fields. A consumer may select one
representation; no actual model request was captured here. Do not claim the
model receives only 6000 characters, or that it necessarily receives both
representations twice.

Roll back by keeping/selecting `classic`; no reindexing is needed. Stage3B
artifacts include all candidate results, including regressions, at
`agent-results/rag-study/20260918-stage3b/`.
