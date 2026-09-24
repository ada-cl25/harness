# Conversation context management

The platform now treats the SQLite message log as the source of truth and the
model prompt as a bounded projection. A new Harness session is created for each
user turn, so opaque SDK history cannot silently exceed the application budget.

The projection contains, in order:

1. the current user request;
2. immutable task and run identifiers;
3. source anchors such as proposal IDs, run IDs, paths, commands and statuses;
4. a rolling summary of older complete turns;
5. recent turns in their original text;
6. bounded prior tool and execution results;
7. bounded RAG evidence, when preloaded.

Compaction is triggered only when projected input exceeds the configured safety
budget. The default budget is `80% * 16384 - 2048`, or 11059 estimated tokens.
This deliberately stays conservative under the current 64 KiB Harness workspace
context limit. Four recent turns remain raw. Older turns are summarized incrementally and recorded in the
`context_checkpoints` table; original messages are never deleted.

The default summary mode uses the configured OpenAI-compatible model. If that
call fails, the platform falls back to an extractive summary. In both cases the
application independently appends missing source anchors, because a model summary
must not be trusted to preserve approval IDs or execution evidence.

Configuration:

- `TRITON_RISCV_MANAGED_CONTEXT=1`
- `TRITON_RISCV_CONTEXT_WINDOW_TOKENS=16384`
- `TRITON_RISCV_CONTEXT_SAFETY_RATIO=0.80`
- `TRITON_RISCV_CONTEXT_OUTPUT_RESERVE=2048`
- `TRITON_RISCV_CONTEXT_RECENT_TURNS=4`
- `TRITON_RISCV_CONTEXT_SUMMARY_MODE=model` (`model` or `extractive`)

Every run emits a `context-prepared` event containing the estimated prompt size,
whether compaction occurred, how many messages were summarized, and summary-call
usage when available. This lets evaluations count summary cost rather than hide it.
