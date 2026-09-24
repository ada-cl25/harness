# Migration Verification

Verified locally on 2026-09-21, macOS / Python 3.13 / Node 22.19.

## Repository Review Conformance (2026-09-21)

Fetched upstream main `87b01ba`; the working branch already contains it. No
reset, stash, commit or push was performed. See REVIEW_FOLLOWUP.md for the
mapping to PR #1's review comments.

- Official CLI installed the package into a new isolated web profile. With
  explicit config, the real pinned host served its authenticated HTML page
  (HTTP 200) without startup errors. The test process was shut down afterward.
- Plugin unit tests: **22 passed** under the repository's Vitest entry.
- Actual pinned host/Python MCP: **5 integration scenarios passed**, also
  invoked successfully by the root integration suite's single wrapper test.
- Python: **239 passed and 3 subtests passed**, one dependency deprecation warning.
- Retained React UI: **8 passed**; TypeScript/Vite production build passed.
- Frozen plugin dependency install, package audit, Git whitespace check, and
  the repository's formatting/JSON/YAML/conflict/file-size hook implementations
  passed. Custom-tag YAML checking is scoped to the retained SDK configuration.
- The complete root unit command reported **48 passed tests and one failed
  suite import** in the unrelated agent-observer plugin: missing
  `@deepseek-ai/dsh-tools`, linked to the unavailable host submodule. Fetching
  that submodule failed twice (HTTP2/SSL timeout). Whole-repository install-all
  and full CI are therefore **not established** by this increment. Integration
  used the already-built archive of the exact pinned host revision, not a new
  or substituted version of the submodule.

No model requests or remote execution occurred in this review increment. No
RAG algorithm/default or historical database was changed. Local detailed logs
are retained in `agent-results/plugin-review/20260921/` of the original workspace,
not bundled into the plugin.

## Live Native Acceptance (Earlier on 2026-09-21)

On 2026-09-21 the installed plugin completed a real native web session using
ISRC Responses model `AZ-GPT-5.6-Sol`, official Harness approvals and SSH to
`sg2044` (riscv64, Triton 3.4.0), on the pinned host revision below.

- New `acceptance_scaled_square_20260921`: **4 passed**.
- Controlled implementation-only constant mutation: **4 failed**. The model
  diagnosed the actual failed run, proposed a one-line repair and reran the same
  unchanged acceptance tests: **4 passed after one repair**.
- Existing `relu_and_mul` regression: **9 passed** with a fresh per-run cache.
- Actual 30-second timeout fixture: exit **124**, classified timeout, remote
  staging directory removed. This fixture is not an operator correctness case.
- Browser automation exercised the real native approval buttons (2 development
  and 3 repair decisions). These were authorized test-harness decisions, not
  model self-approval or manually recorded user clicks. Desktop results rendered;
  mobile with the host sidebar open squeezes the transcript and needs the
  sidebar collapsed. After waiting for responsive layout and verifying the
  sidebar was collapsed, the 390px transcript was readable with no page-level
  horizontal overflow. No claim of comprehensive responsive UI acceptance.
- Offline evidence audit: **17/17 checks passed**, including log/source hashes,
  immutable tests, native execution, approvals and final verified receipt.
- Final local regression: **239 Python tests and 3 subtests, 16 Node tests,
  8 frontend tests, 4 native integration tests passed**. TypeScript/Vite build
  and the package audit (**184 files**) passed. One dependency deprecation warning.

Remote validation now copies a bounded FlagGems source/config snapshot to a
unique temporary workspace with its own compiler cache. It does not replace
files in the shared remote checkout. SSH quoting, strict preflight, timeout,
cleanup and result metadata have regression tests. This is not an OS sandbox;
hard crashes and multi-tenant stress still require deployment testing.

The two native main loops recorded 520378 / 514493 total tokens respectively.
Those totals include separately reported cached input, not just uncached input.
Each session has one title request without usage, so complete billing totals
are unknown. No new RAG effectiveness or cost-reduction claim is made: the
repair was a controlled fault and could access its earlier successful history.

Evidence is under the original workspace's
`agent-results/migration/20260921-live-acceptance/` directory. The Chinese report,
raw receipts/logs, source snapshots, UI screenshots and usage export are retained;
none of those private artifacts are included in the package. The final
`fresh_compile` metadata fix was followed by a new existing-operator regression;
older native receipts were not retroactively rewritten.

## Earlier Incremental Verification

The earlier migration snapshot below is retained as historical evidence, not a
claim that its older wheel was rebuilt with today's additions.

- Installed editable backend: **226 tests passed**.
- Native plugin/state tests: **16 passed**; retained frontend: **8 passed**;
  TypeScript and production UI build passed.
- Actual pinned Harness and actual stdio MCP: **4 integration tests passed**.
  Added an actual AgentLoop test with a scripted model adapter: retrieval after
  task preparation appears in the next model request, persists across turns,
  and labels a recommendation as not executed. Also tested approved project
  execution, a real failing local pytest, single-use execution and session isolation.
  Switching from an operator to a validation job clears unrelated task context.
- MCP now exposes **18 tools**, including project inventory, bounded validation
  jobs and fixture evaluation. Project jobs are local-only; operator batches may
  use the configured remote executor. Fixture results are not business metrics.
- Read-only migration copied **5 memory rows and 50 evidence files** into a new
  private directory. No referenced-file gaps were found by the migration tool;
  original database hash unchanged. Historical labels were not re-audited.
  Retrieval through the installed plugin returned evidence from the copy.
- Package audit passed (**183 files**), excluding `.runtime`, `.state`, databases,
  keys and logs. The exact host is now in a persistent ignored runtime directory.
- No new paid model or RISC-V numerical repair experiment was performed in this
  increment. Historical effect measurements remain separate from integration tests.

Current logs are in the local `agent-results/migration/20260921-full-plugin/`
artifact directory of the original development workspace.

## Earlier Migration Snapshot

- Backend: **220 passed** from the final Harness plugin directory, including
  migration and native approval/bridge tests.
- Independent wheel installation: **220 passed** from outside both source repos,
  loading `codex_agent` from site-packages with Python isolated mode.
- Frontend: **8 passed**; TypeScript check and Vite production build passed.
- Plugin/adapter/state: **15 passed**, including policy injection, native approval,
  cancellation, session isolation, state restore and bounded context.
- Real native host integration: **2 passed**, both with the editable backend and
  with the independent wheel. Real host tool/approval services call the real
  stdio MCP server and Python bridge. Tests prepare, propose, approve/reject and
  apply temporary implementations; they check automatic memory evidence and
  current task state in native context. Approval answers and memory fixtures
  are deterministic, not live model decisions or production history.
- Official Harness SDK: real initialization passed from the installed backend.
  No model turn was submitted.
- Real local checkout: stdio MCP listed **13 tools** and discovered `relu_and_mul`
  implementation and test paths. Discovery is read-only, not a numerical test.
- Local workbench: `/`, `/api/health`, `/api/bootstrap` served successfully.
  Fresh inventory contains 266 operator records and 691 project validation
  targets; these are static discovery counts, not passed-test counts.
- Distribution audit: backend, built UI and policy are present; private/runtime
  artifacts (venv, node_modules, databases, logs, keys) are excluded (178 files).
- Native host: built and launched from the exact fork gitlink revision
  `c389f96bf3a9b6807cb71ed6bdad5849be0df6d8` (0.1.3-alpha.2). The official CLI
  installed this plugin into an isolated web profile; MCP startup succeeded.
  Desktop 1440x960 and mobile 390x844 browser smoke checks rendered the native
  page with no page errors. The smoke check is not a live chat acceptance test.
- `git diff --check` passed. Changes remain within this package; no commit/push.

## Reproduce

From the package directory, after setup:

```sh
npm test
npm run test:frontend
npm run build
npm run check:package
.venv/bin/python -I -m pytest -q python/codex_agent/tests
.venv/bin/python -I -m codex_agent.harness.mcp_demo relu_and_mul --repo-root "$TRITON_RISCV_REPO_ROOT"
```

The obsolete LangGraph experiment was removed on 2026-09-24. Earlier results
above describe their original revisions; current commands use only the retained
backend. API/SSH credentials are not part of setup. Side-effect permissions
still default off.

Native integration requires a disposable copy of the pinned host, dependencies
installed according to that host's README, and the plugin Python environment:

```sh
TRITON_PLUGIN_TEST_HOST=/path/to/disposable/deepseek-harness npm run test:native-host
```

The test adds a temporary spec to the host's test suite and removes it afterwards.
It does not change the host core. The target fork's submodule could not be cloned
over Git during verification; a source archive of its exact pinned revision was
built in a temporary directory instead. The fork's submodule was not modified.

## Native Integration Scope

- Official Harness owns the agent loop, model provider, chat history and
  conversation compaction; the plugin does not start a second loop.
- The plugin adds typed tool dispatch, trusted native approval, per-session
  lifecycle ownership, atomic domain state, proactive retrieval and bounded
  evidence/current-task context.
- Domain state uses separate files, not custom core session events. State is
  reloaded after restart; a source modification invalidates earlier success.
- The original React/FastAPI workbench, batch/project CLIs
  and retrieval/context experiments remain available in the packaged backend.
  Not every CLI has been exposed as a separate native MCP tool.

## Not Established By These Checks

- The latest acceptance verifies one controlled development/repair chain, not
  arbitrary operator repair, independent RAG improvement or multi-tenant reliability.
- The copied history preserves source labels; migration does not certify those
  labels or migrate the original chat sessions. Source databases remain untouched.
- Integration tests use scripted model responses; they are separate from the
  latest real-model browser acceptance. Neither is a production load test.
- No new RAG quality/cost or task-success claim is made.
- Native guards are not an OS sandbox. Unrestricted host Bash/filesystem tools
  require separate host-side permissions and deployment hardening.

The retained React/FastAPI workbench is independently runnable. Its managed
context and approvals remain separate from the native Harness UI/session policy.
See MIGRATION.md before moving historical databases or exposing the service.
