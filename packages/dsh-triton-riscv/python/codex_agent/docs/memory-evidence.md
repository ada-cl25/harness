# Source-bound memory evidence

The default retrieval algorithm remains `legacy`. This change enriches ingestion
and bounded evidence delivery; it does not add embedding, reranking, automatic
repair, or proof that a historical fix is valid on the current machine.

## Entry Points

`diagnostic_memory.remember_validation` collects local artifacts through
`memory_evidence.collect_lifecycle_sources`, then passes them to
`record_from_validation_receipt(..., sources=...)`. Offline callers can pass an
explicit list of `EvidenceSource` objects instead. This is also how a historical
export or a restricted as-of corpus can be ingested without reading live files.

`memory.records_from_run` keeps the existing development parser, including its
repair-history support, and attaches the new evidence envelope. It does not infer
that a saved patch was applied when no application history exists.

`retrieve_memories` returns bounded `evidence_chain` fields and a
`context_excerpt`. `operator_lifecycle.MemoryRetrievalToolResult` and
`RetrievedMemoryCase` retain these extensions through the actual
`retrieve_operator_memory` MCP tool. The plugin still starts the Python backend
from `TRITON_RISCV_CHECKOUT`; it does not contain a second copy of the memory code.
The development prompts also use `memory.render_memory_context`.

## Evidence Schema

Evidence is stored under `MemoryRecord.evidence.chain`, schema
`evidence-chain-v1`. The envelope contains a stable source-scoped identity,
items, gaps, conflicts, `remote_version_binding`, and `repair_causality`.

Each item records its stable ID, kind, state, source path, JSON pointer or line
range, run ID, proposal ID, attempt when known, relation, content/value/source
hashes, available time and time basis, bounded text, and truncation flag.
Hashes describe source/pre-normalization content. Storage still applies the
existing secret redaction and temporary-path normalization, so a hash is not a
claim that the normalized display is byte-identical to the source file.

Supported kinds include contract, environment, error, diagnosis, recommendation,
action, patch, validation, log, test summary, conflict, and gap. An empty value
does not manufacture a fact. Derived conflict/gap locators use `#` markers, not
JSON pointers into an original source document.

## Association Rules

- A receipt is bound by its run ID and source content. Planned/dry-run receipts
  remain outside the default execution-memory pool.
- Logs must match the receipt's explicit `log_path`; long logs retain selected
  error/result events with line ranges. Current filesystem proximity is not a
  relationship. Live reads are limited to checkout-contained files up to 4 MiB.
- Proposals attach through `run_id` or `validation_run_id`, with operator
  consistency checked. Patch paths use the lifecycle writer's proposal-ID
  naming convention; proposal JSON can also carry its own diff/rationale.
- `status=applied` plus `applied_at` is a host-recorded application, not proof of
  remote source binding or repair causality. Missing follow-up validation IDs
  remain explicit gaps. An unrelated later passed receipt is never joined by
  operator name or temporal adjacency.
- Development patch attempts and candidate validation iterations remain
  separate. Missing repair history yields a saved-patch/application-unknown
  artifact, not a verified repair. Separate accepted attempts cannot share an
  upsert identity.
- Nested `remote_preflight` environment fields are read explicitly. Conflicting
  top-level/nested values are preserved as conflicts and the common environment
  field becomes unknown rather than choosing one version.

The assembler's optional `as_of` rejects unknown/future availability for every
source, including patches and logs. This does not make the live retrieval API a
complete historical-query service: callers still must supply an allowed corpus
and exclude the current repair family. Timestamps are recorded host times, not
signed remote clocks.

## Budgets and Compatibility

Existing flat tool fields remain for older callers. The additive evidence view
has an 8,000-character budget within the 12,000-character per-item envelope,
with fallback budgets for oversized metadata. Context rendering defaults to
6,000 Unicode characters across the returned cases. These are not measured token
budgets. Text and metadata clipping, omitted counts, and second-stage rendering
truncation are surfaced; source pointers do not count as delivered evidence.

The existing SQLite schema and chunk splitter are reused. Evidence-ID source
fields bind chunks to the parent evidence item. New source-scoped fingerprints
keep different runs/attempts apart; reimporting the same source replaces its
evidence and rebuilds affected chunks, removing stale blocks.

No original database is migrated or backfilled by the stage3A experiment. For a
deployment, build a separate database from approved historical sources and
inspect counts/associations before changing `TRITON_RISCV_MEMORY_DB`. Mixing
new source-scoped records with old fingerprint rows in place may duplicate
episodes; use a clean rebuild instead. Rollback selects the retained old database
and matching code snapshot. Full index/model migration remains a later stage.

## Verification Boundary

Tests cover typed tool delivery, real offline rendering, wrong-run/attempt links,
as-of filtering, unknown versions, planned/proposed states, idempotent updates,
stale chunks, malformed/missing local inputs, and repeated truncation. The
stage3A pilot compares fixed records and independent old/new import databases.
No generation request or remote repair is part of that verification.
