import { readFile } from 'node:fs/promises'

import { describe, expect, it } from 'vitest'

import {
  TRITON_RISCV_SYSTEM_PROMPT,
  apply,
  resolveWorkbenchLaunch,
} from '../../index.js'

const packageRoot = new URL('../../', import.meta.url)

describe('dsh-triton-riscv package', () => {
  it('declares a Harness bundle and web client', async () => {
    const manifest = JSON.parse(
      await readFile(new URL('package.json', packageRoot), 'utf8'),
    )

    expect(manifest.dsh.bundle.patch).toBe('./cordis.patch.yml')
    expect(manifest.dsh.client.platform).toBe('web')
    expect(manifest.exports['./client']).toBe('./lib/client.js')
  })

  it('registers the guarded lifecycle policy', () => {
    let section: { name: string; order: number; text: string } | undefined
    const ctx = {
      effect(setup: () => (() => void) | undefined) {
        const dispose = setup()
        dispose?.()
      },
      systemPrompt: {
        section(value: { name: string; order: number; text: string }) {
          section = value
          return () => undefined
        },
      },
    }

    const previous = process.env.TRITON_RISCV_WORKBENCH_AUTOSTART
    process.env.TRITON_RISCV_WORKBENCH_AUTOSTART = '0'
    try {
      apply(ctx)
    } finally {
      if (previous === undefined) {
        delete process.env.TRITON_RISCV_WORKBENCH_AUTOSTART
      } else {
        process.env.TRITON_RISCV_WORKBENCH_AUTOSTART = previous
      }
    }

    expect(section?.name).toBe('tool:triton-riscv')
    expect(section?.text).toBe(TRITON_RISCV_SYSTEM_PROMPT)
    expect(section?.text).toContain('retrieve_operator_memory')
    expect(section?.text).toContain('verified-passed')
  })

  it('constructs a bounded workbench launch command', () => {
    expect(
      resolveWorkbenchLaunch({
        TRITON_RISCV_CHECKOUT: '/tmp/triton-riscv',
        TRITON_RISCV_MCP_PYTHON: '/tmp/venv/bin/python',
        TRITON_RISCV_WORKBENCH_PORT: '9000',
      }),
    ).toEqual({
      command: '/tmp/venv/bin/python',
      args: [
        '-m',
        'codex_agent.platform',
        '--host',
        '127.0.0.1',
        '--port',
        '9000',
      ],
      cwd: '/tmp/triton-riscv',
      url: 'http://127.0.0.1:9000',
    })
  })
})
