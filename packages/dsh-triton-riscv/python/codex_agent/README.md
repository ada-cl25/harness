# Triton-RISCV Plugin Backend

This is the installable `codex_agent` Python namespace inside the
`dsh-triton-riscv` plugin, not a separate application checkout. The target
Triton-RISCV repository contains operators and compilation inputs; it does not
need another copy of this backend.

Use the package [README](../../README.md) for installation, configuration,
native Harness registration and optional React/FastAPI workbench startup.
Harness owns native model orchestration. The former LangGraph experiment is
removed. Native and workbench sessions remain separate.

## Module Responsibilities

- `harness/`: typed stdio MCP tools, trusted native approval bridge and optional
  SDK adapter. See [integration architecture](docs/deepseek-harness-integration.md).
- `platform/`: the optional workbench's HTTP API, sessions, approval cards,
  streaming and managed conversation context. The UI sources live in the
  plugin's `frontend/`; Python serves generated assets, not a second frontend.
- `operator_development.py`, `operator_lifecycle.py`: contracts, implementation
  proposals, source-locked validation, evidence receipts and bounded repair.
- `discover_operators.py`, `operator_tools.py`: operator implementations, tests,
  references and static risks. Discovery is not a correctness result.
- `discover.py`, `project_tools.py`, `run_validation.py`: broader project target
  discovery and execution reused by project MCP tools.
- `remote_executor.py`, `pipeline_observer.py`, `validation_evidence.py`: SSH
  workspaces, compilation-stage observations and independent result evidence.
- `failure_diagnosis.py`, `project_diagnosis.py`, `project_repair.py`: diagnostic
  rules and repair scope. See [diagnosis contract](docs/failure-diagnosis.md).
- `memory*.py`, `diagnostic_memory.py`, `embeddings.py`, `reference_library.py`:
  evidence memory, chunking, retrieval, context rendering and optional embeddings.
  See [memory architecture](MEMORY.md) and [reference library](docs/reference-library.md).
- `develop_operator.py`, `operator_agent.py`, `core/`, `adapters/`: retained
  standalone development/batch workflows. These are not another native Harness
  loop; the development CLI uses its separately configured Codex CLI adapter.
- `evaluate_*.py`, `migrate_memory.py`, `demo.py`: offline evaluation, opt-in
  history-copy utilities and evidence demonstrations. Fixture results must not
  be presented as new hardware or business-success measurements.
- `tests/`, `specs/`, `operator-spec.schema.json`: regression tests, example
  semantic contracts and schema. They remain available for development/review.

## Operator Lifecycle

```text
Request and semantic contract
  -> discover implementation/tests and relevant historical evidence
  -> propose implementation or repair
  -> trusted approval and fingerprint check
  -> apply allowed source changes
  -> prepare source-locked validation plan
  -> trusted execution approval
  -> local/SSH test, raw log and structured receipt
  -> pass, or diagnose and propose a bounded repair
```

The model cannot approve its own patch. Tests are not weakened to turn failures
into passes. Environment/compiler limitations remain explicit. Results apply
only to the tested contract, sources and environment, not arbitrary inputs.
See the package README for the current tool list and capability settings.

## CLI Access

After plugin setup, use its installed interpreter with isolation so a target
checkout's old `codex_agent` cannot shadow this package. From the plugin root:

```sh
.venv/bin/python -I -m codex_agent.harness.mcp_demo --help
.venv/bin/python -I -m codex_agent.operator_agent --help
.venv/bin/python -I -m codex_agent.develop_operator --help
.venv/bin/python -I -m codex_agent.migrate_memory --help
.venv/bin/python -I -m pytest -q python/codex_agent/tests
```

Native host configuration uses `config.yml`; compatibility environment variables
are for standalone launchers/CLIs. Credentials, state databases and historical
logs are not source files and are never included in the distribution.
Generated operators and receipts belong to the configured target checkout.

See [TESTING.md](../../TESTING.md) for test boundaries and
[VERIFICATION.md](../../VERIFICATION.md) for dated evidence. A green offline
test suite is not a new live-model or RISC-V acceptance run.
