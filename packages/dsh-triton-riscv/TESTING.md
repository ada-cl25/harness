# Plugin Test Contracts

The repository's Vitest configuration discovers this package directly.

- Inputs: `tests/unit/inputs.spec.ts` validates host config, rejects invalid
  permissions/paths, checks disabled activation and explicit legacy translation.
- Outputs: `tests/unit/outputs.spec.ts` checks packaging, five prompt sections,
  safe bundle defaults, retired-framework exclusion and workbench launch parameters.
  `tests/unit/client.spec.ts` checks the sidebar entry, workbench overlay,
  safe URLs and disposal without replacing the native conversation.
- Execution/state: `tests/unit/native-adapter.spec.ts` checks tool hooks, native
  approval, cancellation, ownership, retrieval failure, context bounds and stale
  validation invalidation; `native-state.spec.ts` checks persistence and isolation.
- Integration: `tests/integration/native-host.spec.ts` calls the actual pinned
  host suite in `tests/native-host.spec.ts`. This activates the real parameterized
  entry with real stdio Python MCP, validates development/apply, rejected approval,
  failure receipts, context reaching the next scripted-model request, and tool
  removal after plugin disposal. No live API or SSH is used.

```sh
# Repository root, following install-all.sh:
pnpm test
pnpm test:integration

# Plugin-only unit suite:
cd packages/dsh-triton-riscv
pnpm install --frozen-lockfile
pnpm test
npm run test:frontend
cd python
../.venv/bin/python -I -m pytest -q
```

For a disposable already-built host, set `TRITON_PLUGIN_TEST_HOST` before the
integration command. The native test script refuses to overwrite a pre-existing
temporary test file and removes its own file afterward. Python tests require
the workbench extra installed by setup, not the removed LangGraph extra.

Live-model and RISC-V logs in VERIFICATION.md are separate historical acceptance
records; a passing fixture is not a new live-model or business success result.
