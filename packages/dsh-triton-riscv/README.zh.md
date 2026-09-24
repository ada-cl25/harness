# Triton-RISCV Agent 插件

前端、Python 后端、算子开发与修复、远程执行、RAG、记忆和上下文管理的代码，
现在统一放在这个插件目录。算子仓库仍然是独立工作区，编译器不是插件的一部分。

先看 [迁移后的完整目录说明](DIRECTORY_MAP.zh.md)，再看下方运行步骤。

## 按目标仓库的方式安装

从 Harness 仓库根目录复制 `config.yml.example` 为私人 `config.yml`，按根 README
填好宿主配置，然后配置其中的 `triton-riscv-native-host` 段。设置 `repoRoot` 为
算子仓库的绝对路径，再将 `enabled` 改为 `true`。修改和执行权限先保持 `false`，
需要时分别开启 `permissions.validation`、`development`、`repair`；开启后仍要审批。

```sh
./tools/scripts/install-all.sh
./dsh web
```

模型凭据按宿主要求设置，不由这个插件选择模型。需要 Python >=3.10；可通过
`PYTHON` 指定解释器。安装脚本现在会调用插件的 `setup:backend`，在插件内安装后端，
不需要往每个算子目录复制一套 Agent。没有配置时插件保持未启用，不阻塞其他插件。

配置集中在 `config.yml`：`repoRoot`、`python`、`stateDir`、`permissions`、`remote`、
`memory`。MCP、审批桥和状态存储使用同一份经过校验的配置，避免目录或权限不一致。
`mcp-triton-riscv` 行只是依赖声明，保持 disabled；真正的 MCP 由已启用插件创建和卸载。
下方环境变量命令保留给原来的独立演示入口，不再是原生仓库接入的首选方法。

## 安装与打开原有界面

需要 Node >=22.19、npm、Python >=3.10。Harness 宿主还需遵守根 README 的要求。

```sh
cd packages/dsh-triton-riscv
npm run setup
export TRITON_RISCV_REPO_ROOT=/你的路径/triton-riscv
export TRITON_RISCV_MCP_PYTHON="$PWD/.venv/bin/python"
npm run workbench
```

打开 http://127.0.0.1:8765。端口占用时先设置
`export TRITON_RISCV_WORKBENCH_PORT=8776`。
安装会创建本机的插件虚拟环境，不需要原作者的虚拟环境。
改完 Python 代码后重新安装，或使用英文 README 中的 editable 安装模式。

打开页面不需要 API；真实模型请求仍需要终端环境中的 `ISRC_API_KEY`。
不把密钥提交到 Git。原来的模型代理和 Responses 适配保留。

## 两种运行方式

1. 原生 Harness：插件注册 MCP 工具和领域规则，模型循环、原生聊天和原生
   对话压缩由宿主负责。现在已接入原生审批，以及按会话隔离的算子状态和 RAG 上下文。
   注册指令见 [README](README.md#native-harness-plugin)。
2. 原有演示平台：React + FastAPI + 官方 Harness SDK，仍能创建/置顶/删除会话、
   展示流式回答、审批开发和验证计划、查看任务结果。这是独立会话系统。

两种方式使用同一套迁移后的 Python 工具。在原生界面左侧底部点击「算子工作台」，
即可在当前页面打开原来的 React 界面，右上角关闭按钮返回原生聊天。侧栏收起时
入口显示为代码图标。原生聊天保持挂载，不会因打开工作台而重新加载。
工作台服务仍需显式启动（`npm run workbench`，默认 8765），不会因点击入口自动启动。
`?tritonWorkbench=1` 兼容入口现在打开同一个浮层，不再替换宿主根界面。
自定义地址使用 `tritonWorkbenchUrl` 查询参数；iframe 不代表会话自动共享。

## 文件的位置

- 插件源码：`python/codex_agent/` 和 `frontend/`。
- 生成的算子、测试和任务：`TRITON_RISCV_REPO_ROOT` 指定的算子仓库。
- 提案、补丁、日志和回执：算子仓库的 `agent-results/`。
- 会话、索引、默认记忆库：按 `TRITON_RISCV_STATE_DIR` 和运行入口配置。原生启动器默认插件内 `.state/agent/`，直接运行后端工具默认算子仓库的 `agent-results/`；原生完整对话在独立 `DSH_HOME` 下。
- 远程执行：由 `RISCV_HOST`、`RISCV_REPO` 指定，仍需 SSH 和 Triton/Buddy/LLVM。

原数据库、历史日志、报告和密钥没有塞进插件代码，旧目录保留。
延续历史时使用数据库备份并保留关联证据路径，不直接升级原始实验库。

可以用附带工具复制记忆及关联证据，目标目录必须尚不存在：

```sh
.venv/bin/python -I -m codex_agent.migrate_memory \
  --source /旧目录/agent-results/memory.sqlite3 \
  --source-root /旧目录 \
  --destination "$PWD/.state/history-copy"
export TRITON_RISCV_MEMORY_DB="$PWD/.state/history-copy/memory.sqlite3"
```

迁移清单记录来源、哈希和缺失证据；迁移不会重新认证历史标签，也不迁移旧聊天会话。

## 持久的原生宿主入口

先按宿主 README 安装并构建固定版本的 Harness；需要可执行的 `pnpm`。
宿主源码可放在自己的持久目录，不依赖临时目录；插件不会改宿主核心代码。

```sh
export DSH_NATIVE_SOURCE=/你的路径/deepseek-harness
export TRITON_RISCV_REPO_ROOT=/你的路径/triton-riscv
export DSH_MODEL=你的模型ID
export ISRC_BASE_URL=https://llmapi.isrc.ac.cn/v1
# ISRC_API_KEY 从环境或原生 Models 页面提供，不要写入代码。
npm run native:install
npm run native
```

默认打开 http://127.0.0.1:8780；占用时设置 `TRITON_RISCV_NATIVE_PORT`。
此入口默认使用插件自己的 `.state/native-host` profile，不会改系统默认 profile。
支持 `.state/native-local.json` 中的白名单配置，但不接受密钥字段。
本地私有配置和数据库不会进入安装包；其他使用者必须配置自己的路径与凭据。

页面需要使用启动日志中带临时 token 的本机链接，直接访问裸地址可能返回 401。
在无桌面环境或自动化验收中，可设置 `TRITON_RISCV_BROWSER_DIRECTORY_PICKER=1`，
使用宿主官方的网页目录选择器，避免弹出操作系统文件夹对话框。

远端测试只复制 FlagGems 源文件和公共 pytest 配置到临时工作区，使用独立编译缓存。
服务器原 checkout 不被替换。正常完成或测试超时后清理工作区；若 SSH 异常中断，
不能确定远端是否仍在运行时，不从客户端强删正在使用的目录。机器崩溃、强制杀进程
留下的临时目录仍需检查后清理，这不是多租户安全沙箱。

## 保留能力与边界

提示词源码拆在 `prompts/` 五类文件：操作提示、开发步骤、失败经验、成功经验、
验收规则；由 `lib/prompts.js` 注册为五个部分。历史经验仍须从 RAG 取得可追溯证据，
不会因为拆了一个“成功经验”文件就凭空写入成功案例。`policy.md` 是构建生成的兼容文件。

插件单测统一使用 Vitest，按输入、输出、状态组织，进入根仓库的测试入口。
Python 工具继续用 pytest，React 继续用前端 Vitest。详见 [测试说明](TESTING.md)。

发现、语义合同、实现提案、审批、文件写入、编译测试、诊断、修复、证据核对、
远程同步、检索和记忆入库均保留。RAG 默认仍是 legacy/classic、Embedding 关闭。
平台的对话摘要保留，但不覆盖原生 Harness 的上下文机制。
已移除旧 LangGraph 实验及专属依赖，原生 Agent 编排统一交给 Harness。

原生流程：用户提出需求，Harness 模型调用 MCP 准备合同/查找算子，插件自动
检索历史证据；模型提出实现或修复，调用应用工具时出现 Harness 原生确认；
批准后 Python 再核对提案指纹并落盘；创建验证计划，再经批准运行本地或远端
测试，生成回执；失败后诊断、检索、提出修复，按现有次数上限继续。
用户拒绝、审批不可用、跨会话提案、提案在审批期间变化都会阻止执行。

原生任务状态单独保存在 `TRITON_RISCV_STATE_DIR/native-harness/`，不改宿主
核心日志格式。聊天和压缩由宿主保存，插件保留合同、提案 ID、回执路径和
历史证据快照。不同会话不共享审批；修改代码后必须重新验证。
RAG 没改排序，仍默认 legacy/classic/无 Embedding。任务上下文与证据分别限制
为 12000、6000 字符，这不是精确 token 数；总窗口由宿主的 token meter 管理。

注意：原有批量回归、项目检查和评测脚本仍在 Python 包中，不代表
每个脚本都新增了独立 MCP 工具。新增的 `inspect_project`、`prepare_validation_job`、
`execute_validation_job`、`get_validation_job` 支持发现、计划、审批执行和读取结果；
`evaluate_plugin_fixtures` 仅运行本地夹具评测，不能作为真实业务效果数据。
项目级任务在宿主本地执行；配置强制远程时会拒绝该模式，算子批量验证可走 SSH。
本机已完成原生模型、审批、SSH 数值验收及一次受控修复，详见
[验证记录](VERIFICATION.md)；其他机器仍需配置并验收自己的 API 和工具链。
宿主的 Bash/文件权限也需独立限制，插件审批不是操作系统沙箱。

执行和写文件开关默认关闭，审批不会因插件化而跳过。
目前是本地开发工具，不能直接作为已具备鉴权的公网服务。
测试命令及配置见 [README](README.md)，迁移边界见 [MIGRATION](MIGRATION.md)。
