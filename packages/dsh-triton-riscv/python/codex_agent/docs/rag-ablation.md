# Chunked Memory Retrieval Ablation

## Question and scope

Compare three ways to retrieve historical operator cases from the same corpus:

1. Jaccard overlap on the case's searchable text.
2. Best matching semantic chunk embedding.
3. Weighted reciprocal rank fusion of those two rankings.

All three score every active case; there is no newest-1000 candidate cutoff.
The old structured/semantic production ranking is retained as `legacy` while
the experiment is reviewed. The ablation deliberately isolates text retrieval;
it does **not** yet enforce environment compatibility as a hard filter.

## Chunk design in this pilot

One validation or repair case is not one embedding. This pilot split cases into
`contract`, `diagnosis`, and `outcome` sections, then into at most 600-character
word-boundary chunks with up to 80 characters of overlap. Each chunk kept the
source case ID, section kind, position, provider, and model. Query contracts
only compare with contract chunks; query diagnostics compare with diagnosis or
outcome chunks. The maximum compatible cosine score is aggregated back to the
case. Architecture and toolchain versions remained structured metadata outside
the embedding text.

The current implementation now preserves source-field and paragraph/log/patch
boundaries and enforces a model-tokenizer budget. The results below have not
been rerun under that newer layout.

The pilot uses the local `all-minilm:v2` model (Ollama ID `1b226e2802db`)
through Ollama's OpenAI-compatible embedding endpoint. The model and corpus
are fixed across the three modes.
This is an English-language pilot model, not a recommendation for a bilingual
production deployment.

## Fusion weight

The preselected fusion is `0.60 * keyword_rank_signal + 0.40 * vector_rank_signal`
using reciprocal-rank fusion with `k=60`. Exact compiler names and error tokens
motivated the slight keyword preference. Raw Jaccard and cosine magnitudes are
not directly comparable, hence rank fusion. We tested 0.30 and 0.80 keyword
weights as sensitivity checks; choosing the best weight on this same small
fixture would overfit it.

## Pilot results

These results were recorded **before** the source-preserving/token-aware
chunker replaced the earlier character/word chunker. They are a historical
baseline, not a measured result for the new chunk layout. Re-run on real
labeled cases before comparing the new layout or enabling it in a main path.

The original easy regression fixture contains 8 cases and 8 queries. All modes
achieved 8/8 Hit@1, so it cannot distinguish them. The separate _synthetic_
challenge fixture contains 12 cases and 10 labeled queries, including paraphrase
and known cross-version/architecture traps:

| Mode                 | Hit@1 | Recall@5 |   MRR | nDCG@5 | Known incompatible in Top 5 |
| -------------------- | ----: | -------: | ----: | -----: | --------------------------: |
| Jaccard              |   70% |     100% | 0.850 |  0.898 |                         30% |
| Chunk embedding      |   80% |     100% | 0.900 |  0.929 |                         20% |
| Fusion, keyword 0.60 |   80% |     100% | 0.900 |  0.934 |                         30% |

On the same local warm-model run, median retrieval latency was 0.7 ms for
Jaccard, 19.2 ms for chunk embedding, and 19.5 ms for fusion. P95 was 1.3,
21.9, and 25.5 ms respectively. These are descriptive timings for 12 cases,
not a large-corpus latency guarantee. Indexing/backfill cost is separate.

Fusion keyword-weight sensitivity on the same challenge fixture:

| Keyword weight | Hit@1 | nDCG@5 | Known incompatible in Top 5 |
| -------------: | ----: | -----: | --------------------------: |
|           0.30 |   80% |  0.929 |                         20% |
|           0.60 |   80% |  0.934 |                         30% |
|           0.80 |   70% |  0.897 |                         30% |

Embedding brought the relevant broadcasting-index case to rank 1 when Jaccard
put an unrelated reduction case first. However, all methods ranked a newer
x86/LLVM case ahead of the compatible RISC-V/LLVM case for a literal linalg
error. Similarity alone cannot decide whether a repair can be applied to the
current toolchain. The high Recall@5 is unsurprising with only 12 candidates.

The full per-query ranks and score breakdown are saved in
`agent-results/memory-challenge-all-minilm.json` and its Markdown companion.
Those generated artifacts are local and are not required to run the tests.
`test_old_relevant_case_is_retrieved_after_1000_newer_records` separately proves
that an older exact case remains eligible in all three modes after 1001 newer
distractors. That stress test uses a deterministic fake embedding provider to
test candidate reachability, not semantic quality.

## Interpretation and next gate

These numbers are exploratory, not a production success-rate estimate. Cases
and query labels are hand-written, the sample is small, and no downstream model
repair was evaluated. The observed 10-point Hit@1 difference is one query.
Before promoting a mode, collect a larger time-separated set of real validation
receipts, label version compatibility independently of rankings, and rerun the
same ablation. Then compare the selected mode on fixed operator development and
repair tasks with locked acceptance tests. Add an explicit environment
compatibility check before any historical repair is presented as directly
applicable.

## Reproduce

Configure any supported real embedding provider and run:

```sh
python -m codex_agent.evaluate_memory_modes \
  --fixture codex_agent/tests/fixtures/memory_retrieval_challenge.json \
  --embedding-provider openai-compatible \
  --embedding-model all-minilm:v2 \
  --embedding-base-url http://127.0.0.1:11434/v1 \
  --embedding-tokenizer-json /path/to/matching/tokenizer.json \
  --embedding-token-budget 256 \
  --lexical-weight 0.6 \
  --json-output agent-results/memory-challenge-all-minilm.json \
  --markdown-output agent-results/memory-challenge-all-minilm.md
```

This command now reruns the _new_ chunker; it will not reproduce the historical
numbers above exactly. The OpenAI-compatible adapter reads the key from `AGENT_EMBEDDING_API_KEY` by
default. A local Ollama endpoint accepts a non-secret placeholder value; a
remote endpoint needs its own real credential. Never store keys in fixtures or
results.
