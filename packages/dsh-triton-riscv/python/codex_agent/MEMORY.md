# Agent Memory and Hybrid Retrieval

The operator agent uses a two-level memory design. Memory provides historical
evidence to the model, while the workflow, compiler, and locked tests remain
the source of control and correctness.

## Short-Term Working Memory

Short-term memory exists for one development run. Before every repair the
agent writes `working-memory-repair-<n>.json` with:

- immutable operator reference and allowed implementation file
- locked acceptance-test path and SHA-256
- current first failure stage, likely reason, and concise error excerpt
- previous repair outcomes and remaining repair budget

Only the latest five repair outcomes are expanded in the prompt. Full logs and
patches remain in the run directory for audit, but do not consume model
context. Short-term state is not directly reused by future tasks.

## Long-Term Evidence Memory

Long-term memory is stored in `agent-results/memory.sqlite3`. The database
contains compact records rather than raw logs:

- `successful-run`: a locked acceptance test passed
- `failure-diagnosis`: a validation produced a classified failure and evidence
- `successful-repair`: an accepted repair with a recorded passing validation
- `failed-repair`: an attempt without a recorded passing validation, including
  partial improvements that did not finish the repair
- `safety-event`: a locked test or file allowlist was violated

Every record includes provenance, environment metadata, confidence grade,
test hash, error signature, evidence paths, and a stable fingerprint. Duplicate
records update their timestamp rather than creating another memory.

Confidence grades are evidence based:

- `A`: locked tests passed in established native RISC-V execution
- `B`: tests passed without established native RISC-V evidence
- `C`: classified diagnostic or rejected repair evidence
- `D`: incomplete evidence; retained for audit but weakly weighted

Secrets are redacted before insertion. Obsolete or superseded memories are
soft-archived, so they remain auditable but are excluded from retrieval.

## Version 1: Structured and Lexical Retrieval

The first version uses SQLite plus explainable scoring. A query contains the
operator semantics, PyTorch reference, Triton operations, failure stage, error
signature, and available toolchain metadata. Retrieval combines:

- lexical overlap: 35%
- failure stage or exact error signature: 25%
- Triton operation overlap: 15%
- environment compatibility: 10%
- evidence confidence: 10%
- successful-outcome preference: 5%

Low-score memories are omitted. The prompt receives at most the configured
top-k records and a strict character budget.

## Version 2: Embedding-Assisted Hybrid Retrieval

The second version keeps structured filtering and adds semantic similarity:

```text
task or failure
    -> structured query
    -> lexical/stage/environment scoring
    -> query embedding
    -> cosine similarity against stored embeddings
    -> 55% structured + 45% semantic score
    -> bounded context builder
```

Embeddings are optional. Existing lexical-only memories can be embedded later,
and retrieval automatically falls back to version 1 when a provider is absent.
Provider code is isolated in `embeddings.py`.

## Chunked Retrieval Experiment

The three-way ablation is implemented separately from the current production
ranking. `MemoryStore.retrieve(..., score_mode=...)` accepts `jaccard`,
`embedding`, and `fusion`; the default remains `legacy` until the experiment is
reviewed. All active memories are eligible, including cases older than the
former newest-1000 cutoff.

Each source-backed case has one parent record and `memory_id`-linked children
in `memory_chunks`. The parent schema is uniform; `evidence` is intentionally
sparse and varies by source, so absent actions or validation are not inferred.
Each child stores its section, original field, and order:

- `contract`: operator semantics, PyTorch reference, and Triton operations
- `diagnosis`: failure stage, short error evidence, and diagnostic summary
- `outcome`: separately labeled recommendations, attempted/applied actions,
  recorded patch excerpts, and observed validation results

Short complete fields stay whole, including line breaks. Long fields split
recursively by paragraph, line/log event, sentence, whitespace, then Unicode
code point. A token-aware policy checks the entire embedding input, including
its source title, against the configured model tokenizer (default target: at
most 180 tokens and 600 characters; up to 24 tokens of overlap only within one
source field). Contract and diagnostic queries use the same token policy.
Without a model tokenizer, lexical storage and search still work, but vector
indexing fails closed instead of silently truncating Chinese or long logs.
Contract queries compare with contract chunks; diagnostic queries compare with
diagnosis and outcome chunks. The best compatible chunk similarity is the
case-level semantic score, so multiple child hits consume one result slot.
The returned case also carries bounded matched-chunk provenance and parent
evidence. Environment versions are stored as metadata rather
than embedded text: semantic similarity does not prove version compatibility.
Chunk embeddings are batched and tagged with provider/model identity. Run
`embed-missing` after changing models; experimental embedding and fusion modes
fail rather than silently mixing missing or stale vectors.

The fusion mode uses weighted reciprocal rank fusion with `k=60` and an initial
keyword weight of 0.60. Exact compiler terms motivated that starting weight;
it is a hypothesis, not an optimized or validated production setting. Ranks
are fused instead of raw Jaccard/cosine values because their numerical scales
are not calibrated to each other.

Run the experiment with an actual embedding provider and its matching tokenizer:

```sh
python -m codex_agent.evaluate_memory_modes \
  --fixture codex_agent/tests/fixtures/memory_retrieval_challenge.json \
  --embedding-provider openai-compatible \
  --embedding-model your-embedding-model \
  --embedding-base-url http://localhost:11434/v1 \
  --embedding-tokenizer-json /path/to/this-model/tokenizer.json \
  --embedding-token-budget 256 \
  --json-output agent-results/memory-ablation.json \
  --markdown-output agent-results/memory-ablation.md
```

See `docs/rag-ablation.md` for the **pre-rechunking** pilot results and their
limitations; those scores are not evidence that the new chunker improves
retrieval. A new labeled-query comparison is still required.
The CLI accepts `memory search --score-mode jaccard|embedding|fusion`; the MCP
bridge accepts `TRITON_RISCV_MEMORY_RETRIEVAL_MODE` with the same values. Both
default to `legacy`. Embedding and fusion modes require a configured embedding
provider and a completed `embed-missing` backfill for that exact model.

Supported adapters:

- local `sentence-transformers`
- company or hosted OpenAI-compatible `/embeddings` endpoint

API keys are read only from a named environment variable and are never written
to the database, prompts, logs, or command line.

## Commands

Import existing development runs:

```sh
python -m codex_agent.memory ingest \
  --results-dir agent-results/development
```

Inspect statistics or search lexical memory:

```sh
python -m codex_agent.memory stats
python -m codex_agent.memory search \
  --operator tanh_and_mul \
  --semantics "compute tanh(x) multiplied by y" \
  --failure-stage llvm-ir
```

Add local embeddings to memories that do not have vectors:

```sh
python -m codex_agent.memory embed-missing \
  --embedding-provider sentence-transformers \
  --embedding-model sentence-transformers/all-MiniLM-L6-v2
```

Use a company OpenAI-compatible endpoint:

```sh
export AGENT_EMBEDDING_BASE_URL=https://company.example/v1
export AGENT_EMBEDDING_MODEL=company-embedding-model
export AGENT_EMBEDDING_API_KEY=...
export AGENT_EMBEDDING_TOKENIZER_JSON=/path/to/company-model/tokenizer.json
export AGENT_EMBEDDING_TOKEN_BUDGET=256

python -m codex_agent.memory embed-missing \
  --embedding-provider openai-compatible
```

The tokenizer JSON must be from the _same_ embedding model, with its special
token post-processing intact. `tokenizers` is an optional dependency for this
adapter. If the model's tokenizer or supported input limit is unavailable,
leave vector retrieval disabled and use `legacy`/`jaccard` until they are
known. A tokenizer from a different chat model is not a valid substitute.

Opening a version-3 database migrates its child chunks while retaining parent
IDs and source references; old chunk vectors are invalidated. Previously
flattened parent text cannot regain lost line breaks by migration alone.
Re-ingest available original run directories (same fingerprint refreshes the
parent in place), then rebuild and re-embed:

```sh
python -m codex_agent.memory ingest --results-dir agent-results/development
python -m codex_agent.memory rebuild-chunks
python -m codex_agent.memory embed-missing --embedding-provider openai-compatible
```

The last command needs the endpoint, key, tokenizer JSON, and token budget
settings above. Keep a backup before migrating a production SQLite file.

Soft-archive invalidated evidence:

```sh
python -m codex_agent.memory archive 42 \
  --reason "invalidated by a newer Triton toolchain"
```

Apply retention rules for stale low-confidence and duplicate diagnostic
evidence:

```sh
python -m codex_agent.memory maintain --low-confidence-days 90
```

## Development-Agent Integration

Memory is enabled by default in `develop_operator.py`. Useful controls are:

```sh
--no-memory
--memory-limit 5
--no-memory-auto-ingest
--embedding-provider none
```

Every run records `memory-status.json`, generation and repair retrieval JSON,
working-memory snapshots, and final memory statistics. Retrieved text is
explicitly labeled as historical evidence rather than trusted instructions.

## Harness and MCP Integration

Executed lifecycle validations are now written to the same SQLite store
automatically. A planned command is not evidence and is never stored. Successful
runs become `successful-run` memories; failed runs become
`failure-diagnosis` memories containing the structured rule, stage, confidence,
failed command, evidence excerpts, and provenance.

DeepSeek Harness can retrieve memory through the typed
`mcp__triton_riscv__retrieve_operator_memory` tool. It accepts either:

- an operator name, semantics, and PyTorch reference before implementation; or
- a validation `run_id` after failure.

`diagnose_failure` also retrieves related cases automatically. The current
receipt is excluded so that the result contains prior experience rather than a
copy of the failure being diagnosed. Tool output is bounded and omits raw
embeddings and full logs.

Lexical and structured retrieval works without an external API. Optional
embeddings can be enabled for the Harness MCP subprocess with:

```sh
export TRITON_RISCV_EMBEDDING_PROVIDER=openai-compatible
export TRITON_RISCV_EMBEDDING_MODEL=your-embedding-model
export TRITON_RISCV_EMBEDDING_BASE_URL=https://example.test/v1
export TRITON_RISCV_EMBEDDING_TOKENIZER_JSON=/path/to/embedding/tokenizer.json
export TRITON_RISCV_EMBEDDING_TOKEN_BUDGET=256
export AGENT_EMBEDDING_API_KEY=...
```

The chat-model endpoint is not assumed to support embeddings. Leave the
provider as `none` when no dedicated embedding model is available.

Run the deterministic retrieval benchmark with:

```sh
python -m codex_agent.evaluate_memory_retrieval \
  --json-output agent-results/memory-retrieval-evaluation.json \
  --markdown-output agent-results/memory-retrieval-evaluation.md
```

The fixture is a regression benchmark, not a measurement of production
retrieval quality.
