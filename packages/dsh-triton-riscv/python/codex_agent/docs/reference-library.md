# Evidence-gated repository references

This is an **offline intake pilot**, not a replacement for production RAG.
`reference_library.py` collects implementation/test pairs without importing or
executing them, and writes a new, separate SQLite catalog. It never opens the
production memory database through `MemoryStore`, changes retrieval defaults,
calls an LLM, runs pytest on collected operators, or connects to SSH.

## Scope and authority

The first source type is `repository-reference`, not `successful-repair`.
The reference says only that recorded tests passed for specific source hashes
and an environment. It does not prove the general algorithm correct, establish
repair causality, or make source comments into instructions. Arbitrary web
pages, unreviewed PR claims and automatically generalized coding rules are not
ingested by this pilot. Mandatory permissions and acceptance rules remain in
trusted host/tool code, not retrieved text.

## Admission

1. Read only bounded files beneath the explicit operator checkout. Reject path
   escapes, invalid Python and missing implementation/test pairs.
2. Extract AST facts: Triton kernels, functions, explicit implementation imports,
   calls and recognized numerical assertions. Missing evidence fails closed;
   this heuristic can reject legitimate wrappers and unusual test styles.
3. Quarantine recognizable reference-library mutation, dynamic patching,
   instruction-like text and potential credentials. Pattern checks are not a
   complete prompt-injection detector or security sandbox.
4. Reuse `audit_validation_receipt` to bind a live passing receipt to current
   implementation/test hashes, source-stability evidence, a hashed log and, for
   remote runs, its approved plan. Do not add today's hashes to an old receipt
   and pretend that they were measured during the old execution.
5. Require a pytest command selecting the recorded test file, a positive test
   count, no conflicting failure output, and a recorded riscv64/Triton binding.
   Conflicting passing/failing receipts for the same current source are withheld.
6. Quarantine unknown, controlled-demo and synthetic provenance. `--provenance
real` is a caller declaration, not independent certification or human review;
   it never bypasses the evidence checks. Explicit evaluation targets are also
   excluded. Alias/family-level exclusions must be supplied by the experiment.
7. Store one reference per exact source pair. On read, require matching known
   environment fields and recheck all retained source/evidence hashes. A changed
   source or receipt requires a new catalog version; no stale automatic fallback.

## Usage

Use the migrated backend, not the old checkout's same-named Python package:

```sh
cd packages/dsh-triton-riscv/python
../.venv/bin/python -B -m codex_agent.reference_library build \
  --repo-root /absolute/path/to/triton-riscv \
  --output /absolute/path/to/new-reference-catalog \
  --provenance unknown

../.venv/bin/python -B -m codex_agent.reference_library search \
  --library /absolute/path/to/new-reference-catalog \
  --query 'relu mask load' --triton 3.4.0 --execution-mode native-riscv
```

The output directory must not already exist. `references.sqlite3` holds separate
admission flags; `admitted.jsonl` and `quarantine.jsonl` are readable exports.
`manifest.json` records source checkout, actual HEAD, provenance declaration,
counts, exclusions and limitations. Per-file hashes identify working-tree
content even when it differs from HEAD. Raw secrets and full raw logs are not
exported. Existing sources stay in their original checkout and are referenced,
not silently copied to a supposedly validated historical version.

Search is read-only and intentionally limited: it uses the existing token-set
Jaccard helper on operator/function/operation facts after strict eligibility
filtering. This is **not** the production legacy/fusion pipeline, a new retrieval
benchmark, or automatically exposed MCP functionality. Do not point
`TRITON_RISCV_MEMORY_DB` at this catalog: its schema is deliberately separate.

## What is not guaranteed

Hash agreement detects changes, not forged receipts or a compromised runner.
Recognizing an assertion does not prove comprehensive or independent numerical
coverage. Provenance is not inferred reliably from `passed`, a filename or a
caller declaration. A failure log is evidence of failure under those conditions,
not proof of an unsupported compiler feature. Quarantine means insufficient
admission evidence, not that an implementation is wrong.

The present catalog is a source registry plus admission gate. To grow useful
active data, first produce fresh source-bound validation receipts for a small
set of relevant references, then rebuild a new catalog version. Connect accepted
reference contexts to the online generator only in a separately reviewed change
with clear contract/version labels, budgets and evaluation leakage controls.
Do not weaken the gate merely to obtain a larger record count.

## Tests

`tests/test_reference_library.py` uses synthetic fixtures to test admission and
read-time rejection. Passing these unit tests demonstrates guard behavior, not
real operator correctness, RAG usefulness or production security certification.
