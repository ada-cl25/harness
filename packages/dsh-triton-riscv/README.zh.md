# dsh-triton-riscv

这是一个面向 DeepSeek Harness 的 Triton-RISCV 算子开发插件。插件不替换
Harness 的模型和 Agent Loop，而是向 Harness 注册领域规则、MCP 工具以及现有
React/FastAPI 工作台入口。

## 代码边界

```text
Harness Web
  -> dsh-triton-riscv 插件
     -> 注入 Triton-RISCV 生命周期规则
     -> 启动官方 dsh-mcp-client
        -> 启动 Triton-RISCV checkout 中的 Python MCP 服务
           -> 算子发现、开发、验证、诊断、记忆检索和远程执行
     -> 在 Harness Web 根视图中加载 Triton-RISCV 工作台
```

Harness 负责对话、模型推理和工具调度；Triton-RISCV Python 引擎负责确定性的
算子操作。模型不能自行选择 SSH 主机、仓库路径或任意命令，也不能批准自己的
源码提案和验证计划。

## 安装

先准备一份包含 `codex_agent` 的 Triton-RISCV checkout：

```sh
export TRITON_RISCV_CHECKOUT=/absolute/path/to/triton-riscv
export TRITON_RISCV_MCP_PYTHON="$TRITON_RISCV_CHECKOUT/.harness-venv/bin/python"
export TRITON_RISCV_WORKBENCH_PORT=8765
```

在 Harness 仓库根目录执行：

```sh
cp config.yml.example config.yml
./tools/scripts/install-all.sh
DEEPSEEK_API_KEY=sk-... ./dsh web
```

`install-all.sh` 会自动构建并安装 `packages/` 下的插件。启动后，Harness 会拉起
Python MCP 服务和工作台，Web 页面显示 Triton-RISCV Agent 界面。

## 远程验证

只有显式设置下列环境变量时才允许远程验证：

```sh
export RISCV_HOST=sg2044
export RISCV_REPO=/home/lichunbo/work/triton-riscv
export TRITON_RISCV_REQUIRE_REMOTE=1
export TRITON_RISCV_ALLOW_VALIDATION=1
export TRITON_RISCV_REQUIRE_APPROVED_VALIDATION=1
```

源码应用和修复应用默认关闭。只应在受信任的开发 checkout 中启用：

```sh
export TRITON_RISCV_ALLOW_DEVELOPMENT_APPLY=1
export TRITON_RISCV_ALLOW_REPAIR_APPLY=1
```

## 测试

```sh
cd packages/dsh-triton-riscv
pnpm install --frozen-lockfile
pnpm build
pnpm test
```

当前插件仍依赖单独的 Triton-RISCV checkout。后续可以将 Python 领域引擎制作成
独立安装包，以减少源码 checkout 依赖。
