import assert from 'node:assert/strict'
import { test } from 'vitest'
import { installNativeAdapter, contextText } from '../../lib/native-adapter.js'

const prefix = 'mcp__triton_riscv__'
function session(id, events = []) {
  return {
    id,
    snapshotEvents: () => events,
    append(type, data) {
      events.push({ type, data: structuredClone(data) })
    },
  }
}
function harness(outcome = 'allowed-once', bridgeOverride) {
  const seen = [],
    questions = [],
    hooks = {}
  const states = new Map()
  const store = {
    load(id) {
      return (
        states.get(id) || {
          session_id: id,
          artifacts: {},
          task: {},
          contract: null,
          memory: null,
        }
      )
    },
    save(state) {
      states.set(state.session_id, structuredClone(state))
    },
  }
  let context
  let variable
  const ctx = {
    effect(fn) {
      return fn()
    },
    systemPrompt: {
      context(value) {
        context = value
        return () => {}
      },
      variable(_name, value) {
        variable = value
        return () => {}
      },
    },
    on(name, fn) {
      hooks[name] = fn
    },
    get() {
      return outcome === 'missing'
        ? undefined
        : {
            async request(req) {
              questions.push(req)
              return outcome
            },
          }
    },
  }
  installNativeAdapter(ctx, {
    store,
    bridge: async (req, options) => {
      seen.push(req)
      if (bridgeOverride) return bridgeOverride(req, options)
      return req.action === 'review'
        ? { reason: 'exact command and diff', fingerprint: 'abc' }
        : req.action === 'memory'
          ? {
              status: 'found',
              items: [{ memory_id: 7 }],
              context_excerpt: 'historical evidence #7',
            }
          : { status: 'approved' }
    },
  })
  let calls = 0
  async function call(s, name, args, data, signal = new AbortController().signal) {
    return hooks['tools/execute'](
      {
        name: prefix + name,
        arguments: args,
        agent: { session: s },
        callId: 'c',
        signal,
      },
      async () => {
        calls++
        return {
          isError: false,
          value: { structuredContent: data },
          content: [],
        }
      },
    )
  }
  return {
    call,
    seen,
    questions,
    context: s => context.text.replace('{{triton_task_evidence}}', variable({ agent: { session: s } })),
    calls: () => calls,
  }
}
async function plan(h, s, id = 'run-1') {
  await h.call(
    s,
    'validate_operator',
    { execute: false },
    {
      run_id: id,
      operator: 'add',
      status: 'planned',
      command: 'pytest test_add.py',
    },
  )
}

test('native approval binds exact session and artifact; rejection has no execution', async () => {
  for (const outcome of ['rejected', 'cancelled', 'unavailable', 'missing']) {
    const h = harness(outcome),
      s = session('s1')
    await plan(h, s)
    await assert.rejects(h.call(s, 'execute_approved_validation', { run_id: 'run-1' }, {}))
    assert.equal(h.calls(), 1)
    assert.equal(h.seen.filter(x => x.action === 'decide').length, outcome === 'rejected' ? 1 : 0)
  }
})

test('native grant commits trusted decision before calling the domain tool', async () => {
  const h = harness(),
    s = session('s1')
  await plan(h, s)
  await h.call(
    s,
    'execute_approved_validation',
    { run_id: 'run-1' },
    { run_id: 'run-result', operator: 'add', status: 'passed' },
  )
  assert.equal(h.calls(), 2)
  assert.deepEqual(
    h.seen.map(x => x.action),
    ['review', 'decide'],
  )
  assert.equal(h.seen[1].session_id, 's1')
  assert.equal(h.seen[1].fingerprint, 'abc')
  assert.equal(h.questions[0].reason, 'exact command and diff')
  assert.match(h.context(s), /run-result/)
})

test('conversation text and another session cannot authorize an artifact', async () => {
  const h = harness(),
    a = session('a'),
    b = session('b')
  await plan(h, a)
  await assert.rejects(h.call(b, 'execute_approved_validation', { run_id: 'run-1' }, {}), /not created/)
  assert.equal(h.questions.length, 0)
  const fork = session('fork', a.snapshotEvents())
  await assert.rejects(h.call(fork, 'execute_approved_validation', { run_id: 'run-1' }, {}), /not created/)
})

test('same session restored with domain state retains ownership', async () => {
  const h = harness(),
    s = session('s1')
  await plan(h, s)
  const restored = session('s1', JSON.parse(JSON.stringify(s.snapshotEvents())))
  await h.call(restored, 'execute_approved_validation', { run_id: 'run-1' }, { status: 'passed' })
  assert.equal(h.questions.length, 1)
})

test('generation and failure retrieve evidence automatically, with current run excluded by bridge query', async () => {
  const h = harness(),
    s = session('s1')
  await h.call(
    s,
    'prepare_operator_development',
    {
      specification: { semantics: 'x*x', pytorch_reference: 'torch.square(x)' },
    },
    { operator: 'square', status: 'planned', development_id: 'dev-1' },
  )
  assert.equal(h.seen[0].query.semantics, 'x*x')
  assert.match(h.context(s), /historical evidence #7/)
  await plan(h, s)
  await h.call(
    s,
    'execute_approved_validation',
    { run_id: 'run-1' },
    { operator: 'add', status: 'failed', run_id: 'run-2' },
  )
  assert.equal(h.seen.at(-1).query.run_id, 'run-2')
  assert.doesNotMatch(h.context(s), /torch.square/)
})

test('missing historical DB does not discard a successful preparation', async () => {
  const h = harness('allowed-once', async () => {
      throw new Error('unavailable')
    }),
    s = session('s1')
  await h.call(
    s,
    'prepare_operator_development',
    { specification: { semantics: 'x*x' } },
    { operator: 'square', development_id: 'dev-1' },
  )
  await h.call(
    s,
    'propose_operator_implementation',
    { development_id: 'dev-1' },
    { proposal_id: 'proposal-1', operator: 'square' },
  )
  assert.match(h.context(s), /retrieval unavailable/)
  assert.equal(h.calls(), 2)
})

test('switching to a validation job clears unrelated operator contract and evidence', async () => {
  const h = harness(),
    s = session('s1')
  await h.call(
    s,
    'prepare_operator_development',
    {
      specification: { semantics: 'x*x', pytorch_reference: 'torch.square(x)' },
    },
    { operator: 'square', status: 'planned', development_id: 'dev-1' },
  )
  assert.match(h.context(s), /historical evidence #7/)
  await h.call(s, 'prepare_validation_job', {}, { job_id: 'job-1', status: 'planned' })
  assert.match(h.context(s), /job-1/)
  assert.doesNotMatch(h.context(s), /torch.square|historical evidence #7|dev-1/)
  await h.call(
    s,
    'propose_operator_implementation',
    { development_id: 'dev-1' },
    { operator: 'square', proposal_id: 'p-1' },
  )
  assert.equal(h.calls(), 3)
})

test('changed review and cancellation cannot run the underlying operation', async () => {
  const h = harness('allowed-once', async req => {
      if (req.action === 'decide') throw new Error('Artifact changed during review')
      return { reason: 'cmd', fingerprint: 'old' }
    }),
    s = session('s1')
  await plan(h, s)
  await assert.rejects(h.call(s, 'execute_approved_validation', { run_id: 'run-1' }, {}), /changed/)
  assert.equal(h.calls(), 1)
  const abort = new AbortController()
  abort.abort()
  await assert.rejects(h.call(s, 'discover_operator', {}, {}, abort.signal))
  assert.equal(h.calls(), 1)
})

test('bounded context retains IDs; no partial semantic contract presented as complete', () => {
  const text = contextText({
    task: { operator: 'new', proposal_id: 'p-1', task_file: 'task.md' },
    contract: { semantics: 'x'.repeat(20000) },
    memory: { text: 'm'.repeat(7000) },
  })
  assert.match(text, /p-1/)
  assert.match(text, /read the immutable contract/)
  assert.match(text, /exceeds 6000/)
  assert.ok(text.length < 19000)
})

test('applied source invalidates a stale passing receipt in task context', async () => {
  const h = harness(),
    s = session('s1')
  await plan(h, s)
  await h.call(
    s,
    'execute_approved_validation',
    { run_id: 'run-1' },
    { status: 'passed', operator: 'add', run_id: 'result-1', exit_code: 0 },
  )
  await h.call(s, 'propose_repair', { run_id: 'result-1' }, { operator: 'add', proposal_id: 'fix-1' })
  await h.call(s, 'apply_repair', { proposal_id: 'fix-1' }, { status: 'applied', operator: 'add' })
  assert.match(h.context(s), /not_validated_after_change/)
  assert.doesNotMatch(h.context(s), /result-1/)
})
