# Triton-RISCV Agent Plugin

An installable DeepSeek Harness domain plugin with its own Python backend and
an optional React/FastAPI workbench. The target Triton-RISCV checkout is **data
and the compilation workspace**, not where the backend must be installed.

[中文说明](README.zh.md) | [Migration boundaries](MIGRATION.md)

## Layout

```text
index.js + prompts/ + cordis.patch.yml    Structured policy and bundle registration
lib/config.js                           Validated host configuration -> Python ABI
native.js + lib/native-*.js              Native approval, task state and RAG adapter
lib/client.js                           Native sidebar entry and optional workbench overlay
python/codex_agent/                      Installable Python backend
  harness/                              MCP tools and SDK adapter
  platform/                             FastAPI, sessions, approvals, context
  memory*.py + diagnostic_memory.py      RAG, evidence, chunking and memory
  operator_*.py + remote_executor.py     Development, validation, repair and SSH
frontend/                               React + TypeScript source and tests
scripts/                                Build, setup and launchers
```

## Install Locally

Requires Node >=22.19, npm, Python >=3.10. The host repository also requires its
root README prerequisites (pnpm >=11 and the Harness submodule).

```sh
cd packages/dsh-triton-riscv
npm run setup
export TRITON_RISCV_REPO_ROOT=/absolute/path/to/triton-riscv
export TRITON_RISCV_MCP_PYTHON="$PWD/.venv/bin/python"
```

Setup builds the frontend and policy resources and installs the backend in the
plugin's `.venv`. Re-run setup after source changes, or use
`.venv/bin/python -m pip install -e './python[workbench]'` for editable development.
No API key is needed to install, load the page or run read-only MCP discovery.

## Native Harness Plugin

After building the host per its README, register this package with the host CLI:

```sh
cd /absolute/path/to/harness
DSH_HOME="$PWD/.dsh" pnpm --dir thirdparty/deepseek-harness dsh plugin --profile web add "$PWD/packages/dsh-triton-riscv"
./dsh web
```

Configure the `triton-riscv-native-host` row in the repository's **config.yml**,
using the block in `config.yml.example`. Example:

```yaml
- id: triton-riscv-native-host
  config:
    enabled: true
    repoRoot: /absolute/path/to/triton-riscv
    permissions:
      validation: false
      development: false
      repair: false
    memory:
      retrievalMode: legacy
      contextFormat: classic
      embedding:
        provider: none
```

Installation is **once per Harness profile**, not inside every operator checkout.
The Python environment lives in this plugin's `.venv`; `repoRoot` selects data.
The bundle is inert until enabled with valid paths. The native entry derives MCP,
approval-bridge and state-store settings from the same validated configuration.
The official MCP client is mounted as a child and stops when this plugin unloads.
Its disabled dependency row `mcp-triton-riscv` must remain disabled to avoid a
duplicate namespace. No global environment mutation or second model loop occurs.

Model credentials and provider settings are configured in **the host Harness**.
The plugin does not select the host model or create another model loop. It adds
domain policy, a stdio MCP server and a native approval/context adapter; it does
not replace the host UI by default. Integration is tested against the host
revision recorded in [VERIFICATION.md](VERIFICATION.md).
The root `tools/scripts/install-all.sh` builds/registers packages and invokes this
package's `setup:backend` hook to install Python dependencies. Python >=3.10 is
required for this plugin (set `PYTHON` to an appropriate interpreter).

Alternatively, this package provides a persistent local launcher using an
already-built pinned host. It does not depend on a temporary source directory:

```sh
export DSH_NATIVE_SOURCE=/absolute/path/to/built/deepseek-harness
export TRITON_RISCV_REPO_ROOT=/absolute/path/to/triton-riscv
export DSH_MODEL=your-model-id
# Supply ISRC_API_KEY via the environment or the native Models page.
npm run native:install
npm run native
```

`pnpm` must be executable on PATH for installation. The launcher uses a private
`.state/native-host` profile and prints the authenticated local URL (port 8780;
override with `TRITON_RISCV_NATIVE_PORT`). Its optional `.state/native-local.json`
accepts only configuration keys, never the API key. Do not share the printed
local access token in reports. The ISRC adapter configuration is local to this
launcher, not a model constraint imposed on other Harness installations.

Tools: `discover_operator`, `check_validation_environment`,
`prepare_operator_development`, `propose_operator_implementation`,
`get_operator_implementation_proposal`, `apply_operator_implementation` (alias `apply_development_proposal`),
`validate_operator`, `execute_approved_validation`, `diagnose_failure`,
`propose_repair`, `apply_repair`, `retrieve_operator_memory`, `inspect_project`,
`prepare_validation_job`, `execute_validation_job`, `get_validation_job`, and
`evaluate_plugin_fixtures`. Validation jobs accept discovered target IDs only,
require native approval and cannot be replayed. Project checks run on the local
host and are rejected when remote execution is mandatory; operator batches can
use SSH. Fixture evaluations are explicitly not production-quality metrics.

## Existing Demonstration UI

```sh
# From packages/dsh-triton-riscv, with the exports above:
npm run workbench
```

Open **http://127.0.0.1:8765**. Set `TRITON_RISCV_WORKBENCH_PORT` for another port.
The backend serves the built React assets, API and SSE stream. No Vite server is
needed. Session pin/delete, approval cards, streamed responses and receipts remain.

For live workbench turns, supply `ISRC_API_KEY` through your terminal's secret
input mechanism; do not commit it. Defaults remain `isrc-proxy`, `gpt-5.6-sol`
and the ISRC Responses endpoint, defined in `harness/cordis.yml`. This optional
workbench uses the official SDK; its sessions are **not** the native host sessions.

To embed the UI inside Harness, start it explicitly, then click **Operator
workbench** above Settings in the native sidebar (a code icon when collapsed).
The close button returns to the still-mounted native conversation. The button
does not start the workbench service or share sessions between the two UIs.
The legacy `?tritonWorkbench=1` link opens the same overlay, not a root replacement.
For a custom port add `&tritonWorkbenchUrl=http%3A%2F%2F127.0.0.1%3A8776`.
`?nativeHarness=1` prevents automatic opening but leaves the sidebar entry available.
This is a local workbench, not an authenticated multi-user service. Do not expose
it to the public Internet without authentication and deployment hardening.

## Target and State

For native repository integration configure these fields in `config.yml`:
`repoRoot`, optional `python` and `stateDir`, `permissions.validation/development/repair`,
`remote.host/repository/required`, and `memory.database/retrievalMode/contextFormat/embedding`.
Unknown fields, invalid booleans and unsafe/relative paths are rejected.
Permissions default off and approval is always required. Embedding accepts
provider/model/baseUrl/tokenizerJson/tokenBudget/apiKeyEnv; put only the secret's
environment variable **name**, never its value, in configuration.

The following environment variables remain a compatibility interface for the
standalone launcher and Python CLIs, not the native plugin's primary configuration:

- `TRITON_RISCV_REPO_ROOT`: target checkout; `TRITON_RISCV_CHECKOUT` is a legacy alias.
- `TRITON_RISCV_STATE_DIR`: session DB, inventory, default memory DB and SDK sessions; defaults to target `agent-results/`.
- `TRITON_RISCV_MEMORY_DB`: explicit memory database, overriding the state default.
- `RISCV_HOST`, `RISCV_REPO`: SSH alias and absolute remote checkout path.
- `TRITON_RISCV_REQUIRE_REMOTE=1`: reject local live validation.
- `TRITON_RISCV_ALLOW_VALIDATION=1`, `TRITON_RISCV_ALLOW_DEVELOPMENT_APPLY=1`,
  `TRITON_RISCV_ALLOW_REPAIR_APPLY=1`: explicit side-effect permissions, default off.
- `TRITON_RISCV_REQUIRE_APPROVED_VALIDATION=1`: require a host-approved, source-locked plan.

Proposals, patches, receipts and their evidence paths remain under the **target
checkout's** `agent-results/`. Generated implementations/tests/tasks also go there,
not to the plugin. Remote compilation still needs SSH and the configured
Triton/Buddy/LLVM environment with `scripts/triton-riscv-env.sh` on the server.

Approval decisions are not model-facing tools. In native Harness, calling a
typed apply/execute tool opens the host's approval UI before dispatch. The adapter
reads the exact proposal/command, verifies it belongs to this session, requests
one-shot authorization, rechecks its fingerprint, and records the trusted
decision in Python. A missing answerer, rejection, cancellation or disabled
capability never runs the action. The standalone workbench keeps its own cards.
Artifacts created in another session (including old workbench sessions) are not
implicitly authorized. Prepare a fresh proposal/plan in the active session.

## Memory and Context

RAG keeps the current `legacy` retrieval, `classic` rendering and
`TRITON_RISCV_EMBEDDING_PROVIDER=none` defaults. Optional providers, chunking,
candidate selection, evidence linking and evaluation entrypoints are retained.
This migration does not tune retrieval or claim higher task success rates.

The workbench retains recent dialogue, bounded older summaries, current state
and tool evidence. Settings: `TRITON_RISCV_MANAGED_CONTEXT`,
`TRITON_RISCV_CONTEXT_WINDOW_TOKENS`, `TRITON_RISCV_CONTEXT_SAFETY_RATIO`,
`TRITON_RISCV_CONTEXT_OUTPUT_RESERVE`, `TRITON_RISCV_CONTEXT_RECENT_TURNS`,
`TRITON_RISCV_CONTEXT_SUMMARY_MODE` (`model` or offline `extractive`).
Native Harness owns its history/compaction; this plugin does not override it.

The native adapter proactively retrieves history after discovery, new-operator
preparation and failed validation/diagnosis, using the existing retrieval and
rendering implementation. It injects current task facts, the immutable contract
and up to 6000 characters of evidence into `systemPrompt.context`. Task facts use
a separate 12000-character budget, not an advertised token count. Oversized
contracts are replaced by an explicit reference, never silently cut mid-contract.
The host's token meter and compaction manage the entire conversation window.

Domain state is persisted atomically under `TRITON_RISCV_STATE_DIR/native-harness/`,
keyed by canonical repository and native session ID, separately from the host's
versioned session log. Source changes invalidate the previous passing status.
The host retains full chat, tool calls, native approval events and context snapshots.
The standard host profile supplies conversation compaction; a custom minimal
profile must configure it separately. The plugin does not start a second model
loop or silently reuse the workbench's model/summarizer configuration.

History DBs, keys, `.env`, SSH credentials and raw experiments are not distributed.
To reuse history, back up a database and point to the copy. MemoryStore can
upgrade schema on open: do not use an immutable experiment baseline. Preserve
the associated receipt/log paths as well; a database path alone is not migration.

## Verification

```sh
pnpm install --frozen-lockfile
npm test # Vitest unit tests, no model or SSH
npm run test:frontend
npm run build
npm run check:package
.venv/bin/python -I -m pytest -q python/codex_agent/tests
.venv/bin/python -I -m codex_agent.harness.mcp_demo relu_and_mul --repo-root "$TRITON_RISCV_REPO_ROOT"
```

The repository's `pnpm test` discovers `tests/unit/*.spec.ts` directly.
`pnpm test:integration` / `pnpm test:all` also run the native host wrapper after
`install-all.sh`; set `TRITON_PLUGIN_TEST_HOST` only when using a disposable copy.
Unit contracts cover inputs (configuration/hooks), outputs (tools/prompts/UI),
and state (ownership, persistence, context and invalidation). See [TESTING.md](TESTING.md).

Prompt sources are split under `prompts/` into hints, operator skills, failure
experience, success experience and verification. `lib/prompts.js` registers five
ordered sections. `policy.md` is a generated compatibility resource; change the
source sections and rebuild, not a second hand-maintained policy. Historical
cases still come from RAG; the instruction files do not fabricate experience.

Optional real-host integration, in a **disposable** checkout of the pinned
Harness revision after installing its dependencies:

```sh
TRITON_PLUGIN_TEST_HOST=/absolute/path/to/disposable/deepseek-harness npm run test:native-host
```

This starts the real stdio MCP server and real host tool/approval services,
temporarily places one test in that checkout and removes it afterwards. All
operator writes and memory records are temporary fixtures; the approval answerer
is deterministic and no model or SSH is called.

## Security and Completion Limits

These guards protect the typed domain workflow in a trusted local installation.
They are not an OS sandbox: a host that gives the model unrestricted Bash/write
access must configure its own sandbox, permissions and credential isolation.
Do not expose the trusted bridge as an MCP tool or public HTTP endpoint.
Batch/project CLIs, evaluation scripts and the prior workbench
remain packaged; they are not additional autonomous loops in the native session.
A native live-model -> approved SSH -> numerical test -> repair run still needs
the host's actual model configuration, explicit capabilities and remote environment.

Tests use temporary fixtures, mocks and local MCP, not models or SSH. They do not
establish RISC-V numerical correctness. The obsolete LangGraph experiment and
its dependency extra have been removed; Harness remains the native orchestrator.
Optional embedding dependencies:
`.venv/bin/python -m pip install './python[embedding]'`.
