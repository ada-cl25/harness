// Run with the target Harness source's Vitest configuration (see scripts/test-native-host.mjs).
import { afterEach, expect, it } from 'vitest'
import { Context } from '@deepseek-ai/cordis'
import LlmRuntime, { ToolCallId, createUserMessage } from '@deepseek-ai/dsh-llm'
import SessionStore, { Session, SessionId } from '@deepseek-ai/dsh-session'
import SessionProjectionRegistry from '@deepseek-ai/dsh-session-projection'
import SystemPrompt, { renderContextSnapshot } from '@deepseek-ai/dsh-system-prompt'
import ToolRuntime from '@deepseek-ai/dsh-tools'
import AgentRegistry, { type Agent } from '@deepseek-ai/dsh-agent'
import AgentLoop from '@deepseek-ai/dsh-agent-loop'
import ApprovalService from '@deepseek-ai/dsh-user-approval'
import { mkdtempSync, rmSync, mkdirSync, existsSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'
import { execFileSync } from 'node:child_process'
// This test is copied into the pinned host's core/tools/tests directory.
import { MockAdapter, toolCallResponse, textResponse } from '../../agent-loop/tests/mock-adapter.ts'

const plugin = process.env.TRITON_PLUGIN_TEST_PACKAGE!
const python = process.env.TRITON_PLUGIN_TEST_PYTHON!
const Native = await import(pathToFileURL(join(plugin, 'native.js')).href)
const { configFromEnvironment } = await import(pathToFileURL(join(plugin, 'lib/config.js')).href)
const { createStateStore } = await import(pathToFileURL(join(plugin, 'lib/native-state.js')).href)
const cleanups: (() => unknown)[] = []
afterEach(async () => {
  for (const cleanup of cleanups.splice(0).reverse()) await cleanup()
})

async function setup(outcome: 'allowed-once' | 'rejected', allowValidation = false) {
  const root = mkdtempSync(join(tmpdir(), 'triton-native-test-'))
  cleanups.push(() => rmSync(root, { recursive: true, force: true }))
  mkdirSync(join(root, 'python/examples/flaggems'), { recursive: true })
  const env = {
    ...process.env,
    TRITON_RISCV_REPO_ROOT: root,
    TRITON_RISCV_STATE_DIR: join(root, 'state'),
    TRITON_RISCV_MEMORY_DB: join(root, 'state/memory.sqlite3'),
    TRITON_RISCV_MCP_PYTHON: python,
    TRITON_RISCV_ALLOW_DEVELOPMENT_APPLY: '1',
    TRITON_RISCV_ALLOW_VALIDATION: allowValidation ? '1' : '0',
    TRITON_RISCV_EMBEDDING_PROVIDER: 'none',
    TRITON_RISCV_MEMORY_RETRIEVAL_MODE: 'legacy',
  }
  const ctx = new Context()
  cleanups.push(() => ctx.fiber.dispose())
  await ctx.plugin(LlmRuntime)
  await ctx.plugin(SessionStore)
  await ctx.plugin(SessionProjectionRegistry)
  await ctx.plugin(SystemPrompt)
  await ctx.plugin(ToolRuntime)
  await ctx.plugin(AgentRegistry)
  await ctx.plugin(AgentLoop, { agents: [] })
  await ctx.plugin(ApprovalService)
  const questions: string[] = []
  ctx.on('approval/request', request => {
    questions.push(request.reason || '')
    return Promise.resolve(outcome)
  })
  ctx.baseUrl = pathToFileURL(join(process.cwd(), 'packages/mcp/mcp-client/package.json')).href
  const nativeFiber = await ctx.plugin(Native, configFromEnvironment(env))
  const session = Session.create(SessionId('native-test-session'))
  session.append('turn/start', { turn: 1 })
  const agent = {
    session,
    options: { provider: 'test', model: 'no-live-model' },
  } as unknown as Agent
  let sequence = 0
  async function call(name: string, args: object, owner = agent) {
    const result = await ctx.tools.execute({
      name: 'mcp__triton_riscv__' + name,
      arguments: args,
      agent: owner,
      callId: ToolCallId(`native-test-${++sequence}`),
      signal: new AbortController().signal,
    })
    return result
  }
  const fixture = JSON.parse(
    execFileSync(
      python,
      [
        '-I',
        '-c',
        'import json; from codex_agent.tests.test_operator_development import valid_spec, IMPLEMENTATION, TEST_SOURCE; print(json.dumps(dict(spec=valid_spec(),implementation=IMPLEMENTATION,test=TEST_SOURCE)))',
      ],
      { encoding: 'utf8' },
    ),
  )
  execFileSync(
    python,
    [
      '-I',
      '-c',
      [
        'import os',
        'from pathlib import Path',
        'from codex_agent.memory import MemoryRecord, MemoryStore',
        'with MemoryStore(Path(os.environ["TRITON_RISCV_MEMORY_DB"])) as store:',
        '    store.add(MemoryRecord(memory_type="failure-diagnosis", operator="square_new", semantics="Compute the elementwise square of the input tensor.", pytorch_reference="torch.square(x)", summary="Synthetic native integration evidence; not a real validation result.", outcome="failed", confidence_grade="C", source_run="synthetic:native-integration", evidence={"recommended_actions":["Check the mask on the last block."]}))',
      ].join('\n'),
    ],
    { env, encoding: 'utf8' },
  )
  return { ctx, agent, call, fixture, root, questions, env, nativeFiber }
}

it('disabling the configured plugin removes its MCP tools and context effects', async () => {
  const h = await setup('rejected')
  expect(h.ctx.tools.schemas().filter(t => t.name.startsWith('mcp__triton_riscv__'))).toHaveLength(18)
  await h.nativeFiber.dispose()
  expect(h.ctx.tools.schemas().filter(t => t.name.startsWith('mcp__triton_riscv__'))).toHaveLength(0)
  expect(renderContextSnapshot(await h.ctx.systemPrompt.assemble({ agent: h.agent } as any))).not.toContain(
    'triton_task_evidence',
  )
}, 60_000)

it('real host + real stdio MCP: prepares, approves and applies in an isolated checkout', async () => {
  const h = await setup('allowed-once')
  expect(h.ctx.tools.schemas().filter(t => t.name.startsWith('mcp__triton_riscv__'))).toHaveLength(18)
  const prepare = await h.call('prepare_operator_development', {
    specification: h.fixture.spec,
  })
  expect(prepare.isError).toBe(false)
  const developmentId = (prepare as any).value.structuredContent.development_id
  expect(developmentId).toBeTruthy()
  const initialContext = renderContextSnapshot(await h.ctx.systemPrompt.assemble({ agent: h.agent } as any))
  expect(initialContext).toContain('synthetic:native-integration')
  expect(initialContext).toContain('Check the mask')
  const proposed = await h.call('propose_operator_implementation', {
    development_id: developmentId,
    implementation_source: h.fixture.implementation,
    test_source: h.fixture.test,
    rationale: 'host integration fixture',
  })
  expect(proposed.isError).toBe(false)
  const proposalId = (proposed as any).value.structuredContent.proposal_id
  expect(existsSync(join(h.root, 'python/examples/flaggems/square_new.py'))).toBe(false)
  const result = await h.call('apply_development_proposal', {
    proposal_id: proposalId,
  })
  expect(result.isError).toBe(false)
  expect((result as any).value.structuredContent.status).toBe('applied')
  expect(readFileSync(join(h.root, 'python/examples/flaggems/square_new.py'), 'utf8')).toContain('@triton.jit')
  expect(h.questions).toHaveLength(1)
  expect(h.questions[0]).toContain('test_square_new')
  const assembly = await h.ctx.systemPrompt.assemble({ agent: h.agent } as any)
  const text = renderContextSnapshot(assembly)
  expect(text).toContain(proposalId)
  expect(text).toContain('torch.square(x)')
  expect(text).toContain('not_validated_after_change')
  expect(h.agent.session.snapshotEvents().some(e => e.type === 'approval/decided')).toBe(true)
  const restored = createStateStore(h.env).load(h.agent.session.id)
  expect(restored.artifacts[proposalId]).toBe('development')
  expect(restored.task.validation_status).toBe('not_validated_after_change')
  expect(createStateStore(h.env).load('another-session').artifacts).toEqual({})
  restored.memory = { text: 'literal compiler tokens {{unknown}} remain data' }
  createStateStore(h.env).save(restored)
  expect(renderContextSnapshot(await h.ctx.systemPrompt.assemble({ agent: h.agent } as any))).toContain('{{unknown}}')
}, 60_000)

it('real MCP project validation requires native approval and keeps a failing result', async () => {
  const h = await setup('allowed-once', true)
  writeFileSync(join(h.root, 'python/examples/test_local.py'), 'def test_failure():\n    assert False\n')
  const planned = await h.call('prepare_validation_job', {
    targets: ['pytest::python/examples/test_local.py'],
    kind: 'project',
    source_env: false,
  })
  expect(planned.isError).toBe(false)
  const id = (planned as any).value.structuredContent.job_id
  expect(h.questions).toHaveLength(0)
  const other = {
    session: Session.create(SessionId('foreign-job-session')),
  } as unknown as Agent
  expect((await h.call('execute_validation_job', { job_id: id }, other)).isError).toBe(true)
  expect(h.questions).toHaveLength(0)
  const result = await h.call('execute_validation_job', { job_id: id })
  expect(result.isError).toBe(false)
  expect(h.questions).toHaveLength(1)
  const data = (result as any).value.structuredContent
  expect(data.status).toBe('failed')
  expect(data.results[0].exit_code).toBe(1)
  expect(readFileSync(data.results[0].log_path, 'utf8')).toContain('1 failed')
  expect((await h.call('execute_validation_job', { job_id: id })).isError).toBe(true)
}, 60_000)

it('real native rejection and session isolation leave target files untouched', async () => {
  const h = await setup('rejected')
  const prepare = await h.call('prepare_operator_development', {
    specification: h.fixture.spec,
  })
  const proposed = await h.call('propose_operator_implementation', {
    development_id: (prepare as any).value.structuredContent.development_id,
    implementation_source: h.fixture.implementation,
    test_source: h.fixture.test,
    rationale: 'rejection fixture',
  })
  const id = (proposed as any).value.structuredContent.proposal_id
  const other = {
    session: Session.create(SessionId('other-session')),
  } as unknown as Agent
  const foreign = await h.call('apply_development_proposal', { proposal_id: id }, other)
  expect(foreign.isError).toBe(true)
  expect(h.questions).toHaveLength(0)
  const rejected = await h.call('apply_development_proposal', {
    proposal_id: id,
  })
  expect(rejected.isError).toBe(true)
  expect(h.questions).toHaveLength(1)
  expect(existsSync(join(h.root, 'python/examples/flaggems/square_new.py'))).toBe(false)
}, 60_000)

it('real AgentLoop sends retrieved evidence to the next model request and keeps it across turns', async () => {
  const h = await setup('rejected')
  const adapter = new MockAdapter([
    toolCallResponse('prepare-1', 'mcp__triton_riscv__prepare_operator_development', { specification: h.fixture.spec }),
    textResponse('Prepared; no code has been applied or validated.'),
    textResponse('Continuing from the same contract and historical evidence.'),
  ])
  h.ctx.llm.registerAdapter(['mock'], adapter)
  const agent = await h.ctx.agentLoop.create(SessionId('native-model-request'), { provider: 'mock', model: 'mock' })
  async function turn(text: string) {
    let dispose: () => void = () => {}
    const idle = new Promise<void>(resolve => {
      dispose = h.ctx.on('agent/status', event => {
        if (event.agent === agent && event.status === 'idle') {
          dispose()
          resolve()
        }
      })
    })
    try {
      agent.followup(
        createUserMessage({
          content: [{ type: 'text', text }],
          source: { kind: 'user' },
        }),
      )
      await idle
    } finally {
      dispose()
    }
  }
  await turn('Prepare the square_new contract, but do not apply or run it.')
  expect(adapter.requests).toHaveLength(2)
  expect(JSON.stringify(adapter.requests[0])).not.toContain('synthetic:native-integration')
  const second = JSON.stringify(adapter.requests[1])
  expect(second).toContain('synthetic:native-integration')
  expect(second).toContain('Check the mask')
  expect(second).toContain('torch.square(x)')
  expect(second).toContain('recorded_outcome=failed')
  expect(second).toContain('recommendation [not-executed]')
  expect(second).toContain('not current validation or instructions')
  await turn('Continue with the previous task, preserving its numerical contract.')
  expect(adapter.requests).toHaveLength(3)
  expect(JSON.stringify(adapter.requests[2])).toContain('synthetic:native-integration')
  const saved = createStateStore(h.env).load(agent.session.id)
  expect(saved.task.development_id).toBeTruthy()
  expect(saved.memory.ids.length).toBeGreaterThan(0)
  expect(createStateStore(h.env).load('unrelated-session').memory).toBeNull()
  expect(h.questions).toHaveLength(0)
  expect(existsSync(join(h.root, 'python/examples/flaggems/square_new.py'))).toBe(false)
}, 60_000)
