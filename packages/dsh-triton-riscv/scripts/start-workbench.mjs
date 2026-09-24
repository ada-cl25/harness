import { spawn } from 'node:child_process'
import { resolveWorkbenchLaunch } from '../index.js'

const launch = resolveWorkbenchLaunch({
  enabled: true,
  repoRoot: process.env.TRITON_RISCV_REPO_ROOT || process.env.TRITON_RISCV_CHECKOUT,
  python: process.env.TRITON_RISCV_MCP_PYTHON,
  port: Number(process.env.TRITON_RISCV_WORKBENCH_PORT || 8765),
})
const child = spawn(launch.command, launch.args, {
  cwd: launch.cwd,
  env: process.env,
  stdio: 'inherit',
})
child.on('error', error => {
  console.error(error.message)
  process.exitCode = 1
})
child.on('exit', code => {
  process.exitCode = code ?? 1
})
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal))
