# Evidence-Based Failure Diagnosis

## Goal

The validation Agent must not turn a nonzero exit code into an unsupported root
cause claim. Diagnosis therefore runs as a deterministic evidence extraction
step before an LLM is asked to explain or repair a failure.

```text
validation log + exit code + compiler stage events
  -> ordered signature rules
  -> structured diagnosis and cited log lines
  -> lifecycle repair policy
  -> Harness model explanation or repair proposal
```

## Diagnosis Contract

`failure_diagnosis.diagnose_log` returns:

- `rule_id`: stable identity of the matched diagnostic rule
- `failure_stage`: tool-oriented stage used by repair policy
- `pipeline_stage`: TTIR, MLIR, LLVM, RISC-V, runtime, or correctness boundary
- `category`: environment, compiler, hardware, runtime, test, or correctness class
- `summary`: concise interpretation supported by the matched signature
- `confidence`: rule confidence, not a statistical production accuracy estimate
- `repair_scope`: which subsystem may be changed
- `failed_command`: exact failed stage command when stage events provide it
- `evidence`: deduplicated log lines with original line numbers
- `recommended_actions`: bounded next steps that preserve acceptance tests

Specific signatures are evaluated before generic compiler and pytest rules.
Temporary-directory differences are normalized only for evidence deduplication;
the displayed evidence retains the original text and line number.

When no signature matches, a failed compiler stage event may identify the stage
with medium confidence. With neither a signature nor a stage event, the result
is `unknown-nonzero-exit`, confidence is low, and source repair is not allowed.

## Safety Boundary

The diagnosis engine does not edit files and does not ask a model to invent a
failure stage. `operator_lifecycle.diagnose_failure_run` applies a second policy
gate:

- environment, dependency, timeout, link, hardware, and compiler-pipeline
  failures are diagnosis-only
- operator-source repair is possible only for reviewed, test-backed stages
- acceptance tests remain hash-locked by the existing repair lifecycle
- low-confidence unknown failures require more evidence or human triage

## Evaluation

The curated fixture contains representative signatures observed in the project
or expected at documented compiler/runtime boundaries. It is a regression
suite, not an estimate of production accuracy.

```sh
python -m codex_agent.evaluate_diagnosis \
  --json-output agent-results/diagnosis-evaluation.json \
  --markdown-output agent-results/diagnosis-evaluation.md
```

The evaluator reports rule, stage, category, and evidence-substring accuracy.
New confirmed failures should first be retained as raw logs, reviewed, and then
added as fixtures before a new rule is introduced.
