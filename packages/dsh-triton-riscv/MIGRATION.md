# Migration Boundaries

## Scope and Sources

The Harness fork is the new home for plugin development. Neither original checkout
is deleted. No commits, pushes, target compiler changes or credential transfers
are part of this migration. Historical memory may be copied explicitly by the
opt-in migration command; installation itself never opens an original database.

- `ruyi_AI/codex_agent`: latest memory/chunking/retrieval/evidence, context summaries,
  CLI development/repair, diagnostics and pipeline observation.
- `triton-riscv-tool-pr/codex_agent`: remote executor, audited receipts, current
  typed lifecycle, approval-aware FastAPI/frontend, ISRC Responses and streaming.
- Existing Harness package: manifest, policy, Cordis bundle and optional web client.

Adapters reconcile shared spec validation, typed retrieval through MCP,
evidence-gated memory writes, stable source-locked validation plan IDs and managed
context checkpoints. `migration-provenance.json` records source paths and hashes.
Earlier raw experiments remain in their archives, not as runtime dependencies.

The standalone LangGraph experiment was removed on 2026-09-24 together with
its dedicated tests, documentation and optional dependencies. The provenance
manifest is an immutable record of the original migration, not a current file
list; its removed-file entries are retained for traceability. Shared core,
discovery and validation modules still serve the CLI and MCP paths.

The Python namespace remains `codex_agent`, distribution `dsh-triton-riscv-agent`.
Launchers use `python -I` so an old backend in the target checkout cannot shadow
the installed plugin. Generated operator files still go to the configured checkout.

## Ownership

The native host owns its loop, credentials, sessions and compaction. The Python
plugin owns contracts, guards, plans, patches, diagnosis, memory and receipts.
The optional workbench owns a separate UI, approvals, chat SQLite and context
summaries, using the SDK and the same MCP tools. SSH owns hardware execution.

Installing this plugin does not make native host sessions and workbench sessions
interchangeable. Host approvals must reach trusted lifecycle APIs before protected
tools execute. No tool allows the model to approve its own changes.

## Data Compatibility

Setup does not open production SQLite. To reuse history, point
`TRITON_RISCV_MEMORY_DB` to an explicitly prepared backup. Existing schema migration
logic is retained. Preserve the associated evidence paths; missing files cannot
be treated as verified. `TRITON_RISCV_STATE_DIR` relocates session data, not target
receipts, proposals or generated source. Original experiment baselines stay intact.

## Verification Boundaries

Migration tests cover installed-package resolution outside the source tree,
served assets, HTTP session controls, context persistence, actual MCP serialization
and memory evidence. Inherited tests cover discovery, contracts, approval,
rollback, diagnosis, RAG and SSH command construction. Synthetic results are not
real operator success rates.

SDK initialization requires no model turn. Paid model execution, real remote
compilation and installation into the target fork's full web profile are separate
acceptance checks; passing local tests does not prove them.

The native adapter now uses the host approval service and dynamic context API.
Domain state is stored separately by repository/session; it does not add unknown
events to the host's versioned session log. Native conversation compression stays
with the host. The workbench retains its independent approvals and managed context.
Production authentication, live-model/SSH acceptance and chat-history migration
are follow-up work, not implicitly complete. This is a trusted local plugin, not
an authorization boundary against an unrestricted host shell.

## Opt-in Memory Copy

`python -I -m codex_agent.migrate_memory --source DATABASE --source-root ROOT
--destination NEW_DIRECTORY` uses a read-only SQLite connection and the backup
API, including committed WAL state. Schema changes, chunk rebuilding and stale
vector removal apply only to the copy. Referenced evidence is archived within
size/type limits and a manifest retains original paths, hashes and gaps. Missing
evidence stays unknown; stored outcomes are not promoted to newly verified facts.

The local 2026-09-21 acceptance copy contains five legacy memory rows and fifty
evidence files. It is private runtime data, not part of the package. The original
database checksum remained unchanged. Raw evidence files remain unmodified; an
absolute path embedded inside a copied raw log may still refer to the original
machine. Consult the relocation manifest in that case.
