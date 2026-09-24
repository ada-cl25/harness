import { installNativeAdapter } from './lib/native-adapter.js'
import { callBridge } from './lib/native-bridge.js'
import { createStateStore } from './lib/native-state.js'
import { resolveConfig, bridgeEnvironment, mcpConfiguration } from './lib/config.js'
import { createRequire } from 'node:module'
import { pathToFileURL } from 'node:url'

export const name = 'triton-riscv-native-host'
export const inject = ['tools', 'systemPrompt']

export async function apply(ctx, input = {}) {
  const config = resolveConfig(input)
  if (!config.enabled) return
  if (!ctx.baseUrl) throw new Error('Harness config-tree baseUrl is required to resolve the official MCP client')
  const require = createRequire(ctx.baseUrl)
  const mcp = await import(pathToFileURL(require.resolve('@deepseek-ai/dsh-mcp-client')).href)
  const env = bridgeEnvironment(config)
  installNativeAdapter(ctx, {
    store: createStateStore(config.env),
    bridge: (request, options) => callBridge(request, { ...options, env }),
  })
  // Child disposal disconnects MCP and unregisters its tools with this plugin.
  await ctx.plugin(mcp, mcpConfiguration(config))
}
