# PR #1 Review Follow-up

Review target: [RuyiAI-Stack/harness#1](https://github.com/RuyiAI-Stack/harness/pull/1).
Upstream rechecked on 2026-09-24: `main` at `87b01ba`. The current development
branch already includes that revision. This document records local changes,
not reviewer approval or a claim that the earlier PR has been updated.

## 1. Separate Prompt Responsibilities

[Review comment](https://github.com/RuyiAI-Stack/harness/pull/1#discussion_r3965142177).

`prompts/0-hints.md` through `4-verification.md` separate host constraints,
operator skills, failure experience, success experience and verification.
`lib/prompts.js` registers five ordered sections via the host system-prompt
service; `index.js` owns their disposal. `policy.md` and the SDK resources are
generated during build, not independently maintained prompt copies.
Experience sections explain how to use sourced historical evidence; they do
not invent failures, successful fixes or verification results.

## 2. Define Where MCP Is Installed

[Review comment](https://github.com/RuyiAI-Stack/harness/pull/1#discussion_r3965144315).

The bundle is installed once per Harness profile. Python is installed in this
package's `.venv` by `setup:backend`, now invoked by the repository installer.
`repoRoot` points to the separate operator checkout; no Agent source or virtual
environment is installed into each operator workspace. Execution logs and memory
remain private runtime data, not package contents. One configured checkout is
bound per plugin instance; dynamic multi-tenant routing is not implemented.

## 3. Use the Repository Configuration Entry

[Review comment](https://github.com/RuyiAI-Stack/harness/pull/1#discussion_r3965168197).

The repository's actual filename is `config.yml` (rather than `config.yaml`).
`config.yml.example` documents the optional native-host row. Installation and
`./dsh` already copy this to the web profile; their existing mechanism is reused.
The plugin is disabled until explicitly configured. No API key is stored here.

## 4. Pass Explicit Parameters

[Review comment](https://github.com/RuyiAI-Stack/harness/pull/1#discussion_r3965181854).

`native.js` takes `apply(ctx, config)`. `lib/config.js` checks the configured
checkout, Python executable, state paths, permissions, remote target and memory
options. MCP and the trusted approval bridge receive the same normalized values.
Capability switches from the parent shell do not override explicit configuration.
The existing Python process interface still uses an explicit environment map;
this does not mutate the Harness process environment. Model secrets remain a
host responsibility. Embedding credentials are referenced by environment-key
name and only resolved for process execution, not written into configuration.

The native entry mounts the official MCP client as a scoped child. The disabled
MCP row in the bundle is only a dependency anchor, not a second active client.
Disposing the parent removes its tools and context effects.
Legacy environment translation is confined to optional standalone launchers.

## 5. Use Vitest and Observable Contracts

[Review comment](https://github.com/RuyiAI-Stack/harness/pull/1#discussion_r3965214704).

The duplicate Node runner and placeholder Vitest test are replaced by real
Vitest cases under `tests/unit/`, organized by inputs, outputs and execution/state.
`tests/integration/` is discoverable by the root configuration and exercises the
real pinned host plus Python MCP. See TESTING.md and VERIFICATION.md for commands
and outcomes. Scripted model fixtures are not live model effectiveness tests.

## Packaging and Compatibility

The native chat, model loop and approval UI belong to Harness. The plugin adds
domain tools, guards, evidence memory and bounded task context. It does not
replace the host loop or edit core Harness code.

The original React/FastAPI demo remains an optional independent entry, not an
automatically launched second server. Python resources, UI assets and all five
prompt files are included in the distribution audit. Databases, keys, private
profiles, host copies and logs are excluded. Prompt formatting tests now tolerate
line wrapping without relaxing the acceptance-test protection rule.

Outside this package, only four installation-related files changed: the root
README's Python requirement, config example, optional backend setup hook, and
a scoped YAML parser rule. The
retained SDK config requires Harness's custom `!!js` tags; `check-yaml --unsafe`
parses their syntax without running them. The native bundle itself uses ordinary
YAML and no executable environment expressions.

## Remaining Verification Boundary

### 2026-09-24 Cleanup

Removed the standalone LangGraph runtime (nine files), its dedicated test module,
architecture document and optional dependency extra. No retained runtime imports
that framework. The packaging audit and Vitest output contract now reject its
reintroduction. The original migration provenance remains an historical manifest.

Shared CLI/core adapters, project discovery/execution, remote validation, memory,
context and the optional workbench are retained because they serve existing
entrypoints. Outdated backend installation/pilot instructions now point to the
package README rather than maintaining conflicting setup recipes.

Local checks after cleanup: 269 Python tests plus five subtests, 33 plugin tests,
eight frontend tests and five real-host/MCP integration tests passed. The seven
removed Python tests belonged exclusively to the retired framework (276 before).
Frontend production build passed. The npm distribution audit contains 197 files
(208 before) and excludes private/runtime data and the retired framework.

The root unit command was also executed: 59 tests passed, but the agent-observer
suite could not import `@deepseek-ai/dsh-tools` from the unpopulated host
submodule. That unrelated suite was not deleted, skipped or patched to pass.
These local results are not a claim of passing all upstream CI or a fresh live
model/SSH operator run. No commit or push was made as part of this cleanup.

Plugin unit, backend, UI, real-host integration and isolated-profile boot checks
passed locally. The full repository build/CI is not yet certified: fetching the
pinned upstream host submodule failed twice, leaving another plugin's linked
dependency unavailable. Repeat install-all and root `pnpm test:all` once the
submodules can be fetched; do not bypass unrelated failing suites.

Host generic shell/file tools still require host-side permission and sandbox
policy. Plugin approval is not a multi-tenant security boundary. RAG remains
legacy/classic with embedding off. These changes do not establish new RAG
quality gains or arbitrary-operator repair guarantees.
