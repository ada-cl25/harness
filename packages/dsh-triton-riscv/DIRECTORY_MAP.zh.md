# 迁移后代码在哪里

主仓库工作目录是 `/Users/cl25/harness-plugin-pr`，Agent 插件集中在
`packages/dsh-triton-riscv/`。这是后续开发主入口；不再需要从
`/Users/cl25/ruyi_AI/codex_agent` 导入运行时代码。

## 插件与原生 Harness

- `package.json`：插件包、入口和安装/构建/测试命令。
- `lib/config.js`：把仓库 `config.yml` 中的明确参数校验后统一传给 MCP、审批桥与状态存储。
- `prompts/`、`lib/prompts.js`：提示、技能步骤、失败经验、成功经验、验收规则五类提示词。
- `cordis.patch.yml`：把领域策略、原生适配器和 Python MCP 接入宿主。
- `index.js`：分段注册提示词；`policy.md` 是构建生成的兼容资源，不是另一份手改源文件。
- `native.js`、`lib/native-adapter.js`：原生工具拦截、审批、任务状态和 RAG 注入。
- `lib/native-state.js`：按仓库/会话保存任务快照，避免不同任务串用状态。
- `lib/native-bridge.js`、`python/codex_agent/harness/native_bridge.py`：可信宿主审批桥。模型不能调用它给自己批准。
- `scripts/native-host.mjs`：原生 Harness 安装和网页启动入口。原生 agent loop 由宿主提供，不复制到插件里。

## Python 后端和算子工具

- `python/pyproject.toml`：独立后端包 `dsh-triton-riscv-agent` 的依赖和安装入口。
- `python/codex_agent/harness/mcp_server.py`：18 个领域 MCP 工具的参数和接口。
- `discover_operators.py`、`operator_tools.py`：发现实现、测试、语义和静态风险。
- `operator_development.py`：合同、开发提案、审批应用。
- `operator_lifecycle.py`：测试计划、回执、失败诊断、修复提案和复测。
- `remote_executor.py`：SSH 预检，临时快照，传文件，真实 pytest，日志与清理。不会把测试文件覆盖到服务器主工作树。
- `failure_diagnosis.py`、`validation_evidence.py`：报错分类和独立核对回执，不把模型说“成功”当证据。
- `project_tools.py`：项目盘点、批量验证计划、任务结果、离线夹具评测。

本节省略目录前缀的文件都在 `python/codex_agent/`。

## RAG、上下文和记忆

- `memory.py`：SQLite 父案例、块、检索及模式。
- `memory_chunking.py`：结构切分、预算和来源。
- `memory_evidence.py`：区分建议、执行动作、修复与验证证据。
- `memory_selection.py`、`memory_view.py`、`memory_context.py`：候选选择、父案例聚合和上下文组织。
- `memory_api.py`、`diagnostic_memory.py`：查询构造及工具返回。
- `embeddings.py`：可选 Embedding 适配，不代表默认启用。
- `migrate_memory.py`：只读备份旧库，在副本上处理结构和证据引用。
- `platform/conversation_context.py`：原工作台的近期对话、摘要和预算管理。
- 原生 Harness 的完整对话与压缩归宿主管理；插件通过 `lib/native-adapter.js` 保留当前任务合同、执行状态及历史证据。两条路径不会叠加两个 agent loop。

当前保守默认为 `legacy / provider=none / classic`；长期记忆数据库不打入源码发行包。

## 两个界面都保留

1. 原生 Harness 聊天界面：由 Harness 提供，直接调用上述插件工具和原生审批。
2. 原来的 React 工作台：源代码在 `frontend/src/`，`App.tsx` 是页面入口；FastAPI 在 `python/codex_agent/platform/`。构建产物进入 `python/codex_agent/frontend/dist/`，通过 `npm run workbench` 启动。

`lib/client.js` 在原生侧栏提供“算子工作台”按钮，点击后用弹层打开已启动的工作台；
兼容 `?tritonWorkbench=1`。关闭弹层返回原生对话。
插件安装不会把原生聊天界面强制替换成旧工作台，也不会默认同时启动两个后台。

## 状态、代码产物与实验记录

- `.state/native-local.json`：本机非密钥配置，不提交。密钥通过环境变量或系统钥匙串读取。
- `.state/native-host/`：默认原生 Harness profile；`DSH_HOME` 可指定独立 profile。
- `.state/agent/`：默认插件运行状态；`TRITON_RISCV_STATE_DIR` 可调整。
- `.state/history-20260921/`：迁移的私人历史库副本与证据清单，不提交。
- `.runtime/native-host/`：当前本机固定版本的宿主运行副本，不是插件交付源码，不打包。
- `TRITON_RISCV_REPO_ROOT`：要操作的算子仓库。生成实现写入其 `python/examples/flaggems/`，合同写入 `tasks/operators/`，提案、日志和回执写入其 `agent-results/`。
- 本次真实验收独立目录：`/Users/cl25/ruyi_AI/agent-results/migration/20260921-live-acceptance/`。里面的 `operator-workspace/` 不是用户正式算子仓库；生成和修复实验只改这里。
- 历史评测、月报和汇报文件继续保留在 `/Users/cl25/ruyi_AI/agent-results/`、`united-interns/`。它们不被作为插件运行依赖，也没有全部塞入新仓库。

## 测试与交付

后端测试在 `python/codex_agent/tests/`，插件 Vitest 单测在 `tests/unit/`，仓库集成入口在 `tests/integration/`，实际原生宿主测试在 `tests/native-host.spec.ts`，前端测试在 `frontend/src/`。
运行步骤见 `README.zh.md`，迁移边界见 `MIGRATION.md`，验证证据见 `VERIFICATION.md`。
旧 LangGraph 学习实现、专属测试、说明和依赖已删除。`core/` 和 `adapters/`
不是 LangGraph：它们仍支撑开发 CLI 的状态与模型接口；`discover.py` 和
`run_validation.py` 仍被项目级 MCP 工具复用，不能仅因文件名相近就删除。
