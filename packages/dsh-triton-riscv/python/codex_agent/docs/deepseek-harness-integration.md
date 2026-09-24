# Harness Integration

## Native Plugin

```text
Harness web/CLI and model loop
  -> five domain prompt sections
  -> native tool hooks, approval and task context
  -> official stdio MCP client
  -> codex_agent.harness.mcp_server
  -> operator contracts, discovery, validation, diagnosis and repair
  -> configured checkout or SSH validation workspace
```

The host owns models, chat history and conversation compaction. The plugin
owns domain contracts, evidence-backed memory and execution receipts. Native
configuration uses the repository's config.yml. Python environment variables
are a child-process interface, not the host configuration API.

## Optional Workbench

```text
React workbench -> FastAPI sessions/approvals/SSE
  -> official Harness Python SDK -> same Python MCP/domain tools
```

This is a separate, explicitly started UI with its own sessions and context
summaries. The native sidebar can open it in an overlay; it does not transfer
native sessions or start another model loop in the native conversation. No
LangGraph runtime is shipped.

## Approval and Evidence

Discovery and environment checks do not authorize source writes or tests.
Development produces a contract and proposal; validation produces a plan.
Side effects require enabled capabilities and a trusted host approval tied to
the session and source fingerprint. Approval is not a model-facing tool.
Modified sources invalidate previous success. Failures can lead to bounded
repair proposals and approved revalidation without weakening acceptance tests.

Historical evidence is retrieved through the shared memory implementation.
Native context uses bounded task facts and evidence; the host manages its full
window. The workbench manages recent turns and older summaries separately.
Defaults remain legacy retrieval, classic rendering and no embedding provider.

## Setup and Verification

Use the package [README](../../../README.md) for native registration,
config.yml fields, workbench startup and optional CLI commands. Local smoke
commands after setup, from packages/dsh-triton-riscv:

```sh
npm test
npm run test:frontend
.venv/bin/python -I -m pytest -q python/codex_agent/tests
.venv/bin/python -I -m codex_agent.harness.mcp_demo relu_and_mul --repo-root "$TRITON_RISCV_REPO_ROOT"
```

The MCP demo exercises discovery, not model reasoning or numerical correctness.
See [TESTING.md](../../../TESTING.md) for isolated real-host integration and
[VERIFICATION.md](../../../VERIFICATION.md) for dated acceptance boundaries.
API credentials belong to the host or explicit workbench configuration, never
source control. Actual RISC-V acceptance requires its configured toolchain and
SSH access; local tests do not establish remote success.
