# Optional record selection

The default remains `record-top5` after the existing `legacy` scoring, with
`classic` context rendering and no embedding provider unless separately configured.
No service or plugin configuration is changed by this feature.

## Explicit use

For the existing MCP `retrieve_operator_memory` tool, supply:

```json
{
  "operator_name": "example_operator",
  "failure_stage": "mlir-translate",
  "error_text": "the observed error",
  "limit": 5,
  "candidate_strategy": "evidence-diverse-v1"
}
```

Omit `candidate_strategy` to retain the original record-level selection. The
typed option passes through `harness/mcp_server.py` to
`operator_lifecycle.retrieve_operator_memory`, `diagnostic_memory.retrieve_memories`,
then `MemoryStore.retrieve`. Direct Python callers accept the same keyword.
Invalid MCP values are rejected by schema validation. The diagnostic interface
reports errors as `unavailable`, not an empty successful search.

`MemoryStore.rank_candidates` exposes the unchanged filtered scoring order without
updating usage timestamps. `retrieve` selects from that order and records usage
only for selected records, as before. A Python caller may supply an empty
`selection_trace` dict to obtain the per-record selection reasons; this does not
change the returned records or the MCP payload schema.

## Policy and limits

`evidence-diverse-v1` uses exact operator, record type, outcome, stage, error
signature and environment as a _heuristic bucket_, not a repair-chain identity.
Missing operator/type/outcome/environment, or missing stage/signature for a
non-passed record, disables grouping for that record. Two failures with different
signatures, stages or environments remain separate. Even equal signatures do not
prove equal root causes.

In original score order, keep the first record in a bucket and any later record
that adds a `(kind, state)` evidence role: error, diagnosis, recommendation,
action, patch, validation, test_summary, rationale, conflict or gap. Other
same-bucket records are deferred. If the limit is not filled, backfill in original
order. Return the selected raw records in their original relative order. An
applied action and a recommended action are distinct states, not equivalent
evidence. No preference is added for successful outcomes.

This conservative role heuristic cannot judge whether two validation commands
or test summaries with the same role contain different essential facts. It can
lose valuable repeated-run evidence or substitute a less relevant record. It
must not be described as causal grouping, complete deduplication, or a generally
superior ranking algorithm. Source, run and attempt bindings are never merged.

Active and source-run filters and the existing score threshold precede selection.
Environment compatibility remains the existing soft scoring signal, not a new
hard filter. The store still reads all active records; there is no new candidate
cap. It uses full-scan scoring and sorting, with O(N log N) sorting and memory
proportional to the loaded records/evidence. Large-library performance is untested.

Public projection and rendering are unchanged. The 6000-character budget covers
only `context_excerpt`; the tool still returns `items` as well. Five raw records
are not necessarily equal serialized size. There is no extra lookup or expanding
one slot into multiple runs. The default development/repair callers do not pass
the new option, so they remain on the old policy. Plugin sources need no change
to expose an updated backend MCP schema, but actual deployed schema refresh and
host model consumption have not been tested or restarted here.

For the Stage4A comparison, historical availability/current-chain exclusion comes
from the previously frozen per-query experiment databases. That adapter is not a
production `as_of` service. Functional synthetic fixtures, local MCP checks,
offline field retention and actual model/repair success are separate evidence
levels; none should be substituted for the others.
