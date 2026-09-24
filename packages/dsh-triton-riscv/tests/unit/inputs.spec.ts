import { describe, it, expect, vi } from 'vitest'
import { resolveConfig, bridgeEnvironment, mcpConfiguration, configFromEnvironment } from '../../lib/config.js'
import { apply } from '../../native.js'
import { apply as policy } from '../../index.js'

describe('inputs: configuration and activation boundaries', () => {
  it('is inert until explicitly configured, without requiring Python or a checkout', async () => {
    const ctx = { plugin: vi.fn(), on: vi.fn(), effect: vi.fn() }
    await apply(ctx, {})
    expect(ctx.plugin).not.toHaveBeenCalled()
    expect(ctx.on).not.toHaveBeenCalled()
    expect(ctx.effect).not.toHaveBeenCalled()
  })
  it('validates paths, booleans, field names and remote pairs', () => {
    for (const value of [
      { enabled: 'false' },
      { enabled: true },
      { repoRoot: 'relative' },
      { repoRoot: '/tmp/op', permissions: { validation: '1' } },
      { apiKey: 'not-an-allowed-field' },
      { remote: { required: true } },
      { remote: { host: 'h;sh', repository: '/repo' } },
      { remote: { host: 'host', repository: '/repo/../other' } },
      { memory: { embedding: { tokenBudget: -1 } } },
      { memory: { embedding: { apiKeyEnv: 'TRITON_RISCV_ALLOW_VALIDATION' } } },
    ])
      expect(() => resolveConfig(value)).toThrow()
  })
  it('defaults capabilities off and keeps the existing RAG defaults', () => {
    const result = resolveConfig({ enabled: true, repoRoot: '/tmp/operators' })
    expect(result.env.TRITON_RISCV_ALLOW_VALIDATION).toBe('0')
    expect(result.env.TRITON_RISCV_ALLOW_REPAIR_APPLY).toBe('0')
    expect(result.env.TRITON_RISCV_ALLOW_DEVELOPMENT_APPLY).toBe('0')
    expect(result.env.TRITON_RISCV_REQUIRE_APPROVED_VALIDATION).toBe('1')
    expect(result.env.TRITON_RISCV_MEMORY_RETRIEVAL_MODE).toBe('legacy')
    expect(result.env.TRITON_RISCV_MEMORY_CONTEXT_FORMAT).toBe('classic')
    expect(result.env.TRITON_RISCV_EMBEDDING_PROVIDER).toBe('none')
  })
  it('uses the same explicit target and permissions for MCP and approval bridge', () => {
    const config = resolveConfig({
      enabled: true,
      repoRoot: '/tmp/operators with spaces',
      python: '/tmp/python',
      stateDir: '/tmp/state',
      permissions: { validation: true },
    })
    const ambient = {
      PATH: '/bin',
      TRITON_RISCV_REPO_ROOT: '/wrong',
      TRITON_RISCV_ALLOW_REPAIR_APPLY: '1',
      RISCV_HOST: 'wrong',
      AGENT_EMBEDDING_PROVIDER: 'wrong',
    }
    const bridge = bridgeEnvironment(config, ambient)
    const mcp = mcpConfiguration(config, ambient)
    for (const [key, value] of Object.entries(config.env)) {
      expect(bridge[key]).toBe(value)
      expect(mcp.env[key]).toBe(value)
    }
    expect(bridge.TRITON_RISCV_ALLOW_REPAIR_APPLY).toBe('0')
    expect(bridge.AGENT_EMBEDDING_PROVIDER).toBeUndefined()
    expect(bridge.PATH).toBe('/bin')
    expect(mcp.args).toEqual(['-I', '-m', 'codex_agent.harness.mcp_server'])
    expect(mcp.cwd).toBe(config.repoRoot)
    expect(ambient.RISCV_HOST).toBe('wrong')
  })
  it('does not put provider credentials in declarative config', () => {
    const config = resolveConfig({
      repoRoot: '/tmp/op',
      memory: { embedding: { apiKeyEnv: 'EMBEDDING_TEST_KEY' } },
    })
    expect(JSON.stringify(config)).not.toContain('secret-value')
    expect(mcpConfiguration(config, { EMBEDDING_TEST_KEY: 'secret-value' }).env.EMBEDDING_TEST_KEY).toBe('secret-value')
  })
  it('keeps legacy launcher translation explicit instead of reading ambient settings in apply', async () => {
    const input = configFromEnvironment({
      TRITON_RISCV_REPO_ROOT: '/tmp/op',
      TRITON_RISCV_ALLOW_VALIDATION: '1',
    })
    expect(resolveConfig(input).env.TRITON_RISCV_ALLOW_VALIDATION).toBe('1')
    vi.stubEnv('TRITON_RISCV_ALLOW_VALIDATION', '1')
    vi.stubEnv('TRITON_RISCV_WORKBENCH_AUTOSTART', '1')
    try {
      expect(resolveConfig({}).enabled).toBe(false)
      const sections = []
      policy({
        effect: fn => fn(),
        systemPrompt: {
          section: s => {
            sections.push(s)
            return () => {}
          },
        },
      })
      expect(sections).toHaveLength(5)
    } finally {
      vi.unstubAllEnvs()
    }
  })
})
