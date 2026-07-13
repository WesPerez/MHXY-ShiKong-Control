# 长任务连续执行、进度可见与异常恢复协议

> 适用项目：`MHXY-ShiKong-Control`  
> 协议版本：1  
> 初始日期：2026-07-10  
> 目标：让 10-30 小时、可能经历上下文压缩、Codex 中断、应用重启、子代理结束和人员交接的开发任务，始终能回答“做到哪里、依据是什么、下一步是什么、中断后怎样安全继续”。

## 1. 为什么不能只写一份 PROGRESS.md

单一人工 Markdown 可以给人看，但无法可靠解决以下问题：

1. agent 忘记更新，页面与源码漂移。
2. 会话在一个副作用执行后、结果写入前中断，文档不知道动作是否已经发生。
3. 后续 agent 只看到“已完成”，但不知道对应哪个 commit、哪个 exe、哪个 workspace、哪个 hwnd 和哪份证据。
4. 线程恢复、fork、handoff 或上下文压缩保留了叙述，却没有保留运行进程、ignored 报告、AppData 和未提交文件。
5. 静态测试、应用启动、真实输入和游戏结果被混成一个“完成”状态。
6. 多个子代理同时写状态，导致 JSONL 顺序、Markdown 和机器状态互相覆盖。

本项目采用“稳定计划 + 机器状态 + 追加账本 + 人类投影 + Git/证据”的组合。它不是完整工作流引擎，但覆盖本项目真正遇到的中断、误报、实机验证和清理风险。

## 2. 多源依据与取舍

### 2.1 OpenAI Codex 官方资料

- Codex 官方建议把仓库约束、验证命令和完成定义放进 `AGENTS.md`，并明确指出文件过大时应引用任务专用文档，而不是把所有内容塞进一处。
- 官方手册建议长、多步骤工作使用执行计划模板；Goal 能附着持续目标，但目标不是代码、证据或副作用现场的替代品。
- Subagents 适合探索、测试和日志分析，主线程负责需求、判断和最终输出；这与本项目“子代理只读审计、主代理单写状态”一致。
- Fork 用于保留原 transcript 后探索另一条路线；Handoff 通过 Git 在 Local/Worktree 间移动任务和代码，但 ignored 文件默认不会移动。
- Worktree 隔离并行修改，但 AppData、运行进程、截图、报告和本地 ignored 资源仍需单独核对。
- Hooks 支持 `SessionStart`、`PreCompact`、`PostCompact`、`Stop` 等生命周期事件，但多个匹配 hook 可能并发，且项目 hook 依赖信任。第一版只建议用 hook 做提醒/只读校验，不自动 commit、清理、杀进程或发游戏输入。

官方入口：

- [Codex Manual](https://developers.openai.com/codex/codex-manual.md)
- [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees)
- [Hooks](https://learn.chatgpt.com/docs/hooks)
- [Scheduled tasks](https://learn.chatgpt.com/docs/automations)
- [Execution plans guide](https://developers.openai.com/cookbook/articles/codex_exec_plans)

### 2.2 成熟 agent 工具

- OpenHands 使用“基础状态 + 追加事件”恢复 conversation，说明当前快照和不可变历史应分开。
- SWE-agent 保存 trajectory、配置快照、日志和最终 patch，并把执行与评估分开；本项目同样不把“执行完”当“验收通过”。
- Aider 用 Git diff/commit/undo 建立可回滚点，但其高频自动提交不适合本项目的共享 dirty 工作树；本项目按验收切片提交。
- Claude Code 官方说明会话 checkpoint 不是 Git 的替代品，Bash、用户手动修改和并行会话变化可能不被完整追踪；因此本项目不依赖任一产品的私有 transcript 格式。

参考：

- [OpenHands conversation persistence](https://docs.openhands.dev/sdk/guides/convo-persistence)
- [SWE-agent trajectories](https://swe-agent.com/latest/usage/trajectories/)
- [Aider Git integration](https://aider.chat/docs/git.html)
- [Claude Code checkpointing](https://code.claude.com/docs/en/checkpointing)

### 2.3 工作流编排器

- Temporal 的 durable history、activity heartbeat 和幂等原则说明：恢复不是复活原调用栈，而是从持久事件判断哪些活动可信、哪些需要重试或对账。
- Airflow 区分任务定义和 task instance/attempt，保留重试历史，并强调任务应像数据库事务一样幂等。
- Prefect 区分 paused、failed、crashed、retrying 等状态，并使用持久结果、事务和 retry condition。
- Dagster 区分 materialization 与 observation：写出产物和只读观察不是一回事；这正好防止“代码存在”冒充“游戏已生效”。

参考：

- [Temporal workflow execution](https://docs.temporal.io/workflow-execution)
- [Temporal activities](https://docs.temporal.io/activities)
- [Airflow tasks](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/tasks.html)
- [Airflow best practices](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html)
- [Prefect states](https://docs.prefect.io/v3/concepts/states)
- [Prefect events](https://docs.prefect.io/v3/concepts/events)
- [Dagster run retries](https://docs.dagster.io/deployment/execution/run-retries)
- [Dagster asset observations](https://docs.dagster.io/guides/build/assets/metadata-and-tags/asset-observations)

### 2.4 GitHub Actions

- Artifact 适合保存证据并提供 digest，但有保留期，不能作为唯一状态源。
- Cache 可能按 key 回退、过期和淘汰，只能加速依赖，不能表示“做到哪里”。
- Job summary 是人类看板，不是永久恢复状态。
- rerun 使用原始 workflow/source 语义，不能假设它自动包含最新本地代码。

参考：

- [Store and share data with workflow artifacts](https://docs.github.com/en/actions/tutorials/store-and-share-data)
- [GitHub Actions limits](https://docs.github.com/en/actions/reference/limits)

### 2.5 社区和公开 issue

公开 issue 不是厂商正式承诺。多个公开问题报告提示：上下文压缩后可能回退、重做旧动作、丢失子代理关联或把未完成计划当成完成；这些问题是否普遍发生尚未由官方确认。因此线程历史只能辅助恢复，不能成为唯一事实源。

高相关例子：

- [openai/codex#31099](https://github.com/openai/codex/issues/31099)：压缩后丢失真实当前步骤，提出结构化 resume state。
- [openai/codex#30945](https://github.com/openai/codex/issues/30945)：出现未完成计划却结束 task 的报告。
- [openai/codex#24281](https://github.com/openai/codex/issues/24281)：多代理关系在压缩/恢复后不可发现。
- [anthropics/claude-code#70555](https://github.com/anthropics/claude-code/issues/70555)：建议把 RIGHT NOW 状态和 narrative summary 分离并落盘。

采用原则：官方文档决定产品能力边界；成熟项目提供机制；编排器提供状态/重试模型；社区 issue 用来识别实际故障模式。任何单一信源都不能独立决定本项目方案。

## 3. 五层连续性体系

```text
长期目标与阶段计划
  docs/project-audit-and-master-plan.md

稳定执行协议
  AGENTS.md
  docs/execution/PROTOCOL.md

机器权威现场
  docs/execution/state.json

追加历史与证据
  docs/execution/events.jsonl
  docs/execution/evidence.jsonl
  docs/execution/checkpoints/*.json

人类可读投影
  docs/execution/STATUS.md
```

### 3.1 主方案

主方案定义长期目标、架构、风险、P0-P9 阶段、验收矩阵和代码落点。它低频更新，不承担“当前正在跑哪条命令”的职责。

### 3.2 协议

`AGENTS.md` 是所有 agent 自动读取的短规则；本文件解释原因、状态模型、命令和恢复算法。协议变化必须经过审查，不能每个切片临时发明新语义。

### 3.3 state.json

它是恢复入口，记录当前 run、attempt、阶段、唯一切片、验收条件、四类状态轴、Git、未决动作、进程/产物归属、阻塞和下一动作。

### 3.4 事件与证据

- `events.jsonl`：只追加重要状态转换和决策。
- `evidence.jsonl`：只追加测试、构建、运行观察和实机证据索引。
- 每条记录有稳定 ID、递增 seq、前一条 hash 和当前 hash。
- JSONL 中间行损坏必须使审计失败；不能静默跳过。
- 命令大输出、截图和完整报告不内联进 JSONL，只存路径、大小和 SHA-256。

### 3.5 STATUS.md

它由 `scripts/execution_progress.py` 生成，包含用户最关心的一页信息：当前阶段、验收门、下一步、阻塞、Git、进程、产物和最近证据。禁止手工编辑。

## 4. 固定权威顺序

发生冲突时固定采用：

```text
当前源码、当前 Git、当前实际运行结果
> 与 commit/workspace/exe/hwnd 绑定的落盘证据
> state.json 与 hash 链账本
> STATUS.md 生成投影
> 线程历史、摘要、早期文档描述
```

例子：

- 线程说“最新版已启动”，但 PID 的文件时间或 exe hash 对不上当前 commit：结论是“当前版本未证实启动”。
- STATUS 说测试通过，但 evidence 绑定旧 commit：当前 commit 的验证状态是 stale/not_verified。
- preflight 报告状态为 done，但实际 `runs=0`：只能算 preflight，不能算 live outcome。
- 旧 checkpoint 记录 PID 存在，但运行观察已过 TTL：PID 只能作为线索，不能用于停止或输入。

## 5. 状态模型：禁止把所有维度塞进一条线

本项目分开保存四类状态。

### 5.1 overallStatus

```text
active | blocked | completed | cancelled
```

它只描述整个长期目标，不表达某条命令是否运行。

### 5.2 phaseStatus

```text
pending | in_progress | verifying | verified | blocked
```

`checkpointed` 不是阶段状态。Checkpoint 是状态快照属性。

### 5.3 actionStatus

```text
none | planned | running | succeeded | failed | unknown_after_interruption
```

它描述一次可能带副作用的动作。异常中断后，不能把 `running` 猜成 succeeded 或 failed，必须先标记/视为 `unknown_after_interruption` 并对账。

### 5.4 acceptanceLevel 与项目验收轴

成熟度从设计到实机逐层提升，但不能只存一个最大值；`projectVerification` 必须分别记录：

```text
codeSurface
automated
currentCommitBuilt
currentCommitAppLaunched
hwndInputActuallySent
gamePostconditionObserved
foregroundUnaffected
secondWindowIsolationVerified
restartPersistenceVerified
```

每轴状态：

```text
pending | partial | passed | failed | blocked | not_required
| stale | outdated | not_verified
```

### 5.5 acceptance criterion

每个切片必须有稳定 criterion ID：

```text
pending | passed | failed | blocked | not_required
```

只有 criterion 绑定的证据存在、commit/运行身份相符时才能 passed。

## 6. Run、attempt、slice、action

### 6.1 Run

一个长期执行周期有稳定 `runId`。新 Codex task 接续同一目标时可以保留 taskId，但应创建新的 runId 或 attempt，并记录 parent/previous thread。

### 6.2 Attempt

失败、异常恢复或人工重做不能覆盖旧结果。attempt 增加，旧事件和证据保留。

### 6.3 Slice

Slice 是可独立验收的纵向工作单元。它必须包含：

- 稳定 ID，例如 `P2-S3`。
- 标题和业务结果。
- scope files/areas。
- non-goals。
- safety boundaries。
- acceptance criteria。
- 唯一 nextAction。

### 6.4 Action

Action 是带副作用、可能在中断后结果未知的具体动作。必须先持久化 intent：

```json
{
  "actionId": "ACT-P0-BACKUP-001",
  "kind": "appdata_backup",
  "targetIdentity": "workspace.json -> timestamped backup",
  "sideEffectClass": "local_file_create",
  "expectedPrecondition": "source exists; destination absent",
  "expectedPostcondition": "destination hash equals source hash",
  "idempotencyKey": "source-hash+destination-path",
  "ownerRunId": "...",
  "ownershipEvidence": ["exact destination path chosen by this run"],
  "status": "running"
}
```

## 7. 单写入器和原子性

`scripts/execution_progress.py` 是连续性元数据的唯一写入器：

1. 使用 `.git/codex-execution.lock` 的 OS 文件锁。锁文件可以存在，但进程退出会释放锁；不能按“有锁文件”判断仍被占用。
2. JSON 写到同目录临时文件，flush/fsync 后 `os.replace`。
3. 证据先 append+fsync，事件再 append+fsync，state 原子替换，STATUS 最后生成。
4. checkpoint 使用独占创建；文件存在则失败，不覆盖旧 checkpoint。
5. 子代理不得调用写入器。
6. AppData 写入、进程停止和游戏输入还会创建 `%LOCALAPPDATA%\MHXY-ShiKong-Control\codex-external-action-lease.json`。该机器级 lease 在 action 完成前保留，用于阻止同机其它 worktree/clone 通过本工具并发执行外部副作用；它不能替代应用 runner 自身的 per-HWND 互斥。

仍然存在的极小崩溃窗口：JSONL 已追加但 state 尚未替换。审计会报告 tail 不一致；恢复时以追加账本为准，执行 reconciliation 后修复 state，禁止删除账本行。

## 8. 什么时候更新进度

必须更新：

1. 开始一个新 slice。
2. scope、非目标、安全边界或验收门变化。
3. 发现重大新风险或子代理结论改变方案。
4. 局部实现完成并通过对应验证。
5. 构建、启动当前版本、真实应用操作或游戏操作前后。
6. 发现 blocker、失败、权限不足或窗口丢失。
7. commit、push 前后。
8. pause、compact、fork、handoff、预计离开超过 15 分钟或结束 turn 前。
9. 每 20-30 分钟持续工作窗口若没有上述事件，也应写一条有信息量的 heartbeat/note，说明当前动作、最近成功点和下一动作。

不需要记录：

- 每次 `rg`、`Get-Content`、`git diff`。
- 无状态变化的重复轮询。
- 子代理原始长输出；只记录主代理复核后的结论和摘要路径。

## 9. 用户进度汇报

长任务不能十几个小时只显示“正在做”。主代理应：

- 每 10-20 分钟或每个可见小闭环给一次简短 commentary。
- 每 30-60 分钟给一次阶段汇报，包含完成、当前、下一步、风险、是否真实启动/输入。
- UI 改动完成一个主要视图就启动当前版本并截图/观察，不积累数天后才第一次看。
- 功能改动按“代码 -> 局部测试 -> 构建 -> 启动当前版本 -> UI 操作 -> 必要时真实 hwnd -> 后置验证 -> 证据”闭环。

ETA 不承诺精确小时。使用范围、置信度和依据：

```text
预计 30-60 分钟，高置信度：只涉及纯函数和 Node 测试。
预计 2-4 小时，中置信度：涉及 Tauri 构建和 UI 实测。
预计 0.5-1 天，低至中置信度：需要真实游戏状态、素材采样和失败调试。
```

AI 写代码很快，但真实产品验收受 Rust/Tauri 编译、游戏状态、管理员权限、图像素材、窗口身份、失败复现和用户前台不受影响等因素约束。时间应按“通过验收门”估算，不按“生成代码行数”估算。

## 10. Checkpoint 类型

### 10.1 state_snapshot

适用于 dirty 工作树、handoff、pre_live、阻塞和异常中断前。它保存现场，但不保证可回滚。

必须记录：

- 当前 run/attempt/phase/slice。
- observed/verified/upstream HEAD。
- dirty status。
- event/evidence tail。
- in-flight action。
- 进程/产物归属。
- blocker、nextAction、doNotDo。
- safeToResume、safeToRunLiveInput。

### 10.2 git_checkpoint

只有满足以下条件才能使用：

- checkpoint 指向可解析 commit。
- 当前 slice 所需静态门禁通过。
- 无 running/unknown action。
- 对应证据绑定该 commit。
- commit 内容范围清晰，不混入归属不明文件。

### 10.3 触发点

- 一个 slice 验收完成。
- 真实输入前 `pre_live`。
- commit 前和 push 后。
- handoff/fork/compact/pause。
- blocker 或工具异常可能中断工作。
- 预计长构建或外部动作开始前。

## 11. 证据模型

每条 evidence 至少包含：

- ID、时间、run、attempt、phase、slice、criterion。
- category、claim、status。
- command、exitCode。
- observed/verified HEAD 和 dirtyPaths。
- artifact 路径、存在性、SHA-256、大小。
- safety：inputSent、foregroundUnchanged、cursorUnchanged。

证据分类：

```text
source_audit
test
build
app_runtime
window_identity
live_preflight
live_input
live_outcome
persistence
failure_reproduction
cleanup_audit
```

证据状态：

```text
observed | passed | failed | blocked | preflight
```

### 11.1 Live 证据最低要求

真实功能通过不能只看输入 API 返回值。至少绑定：

- 完整 commit。
- exe SHA-256 和构建时间。
- workspace schema/hash 或匿名标识。
- 目标 HWND、PID、process、title、client size、权限。
- 操作命令和实际输入类型。
- 输入前状态。
- 输入后游戏后置状态截图/OCR/人工确认。
- 输入前后 foreground HWND 和鼠标坐标。
- 是否存在用户并行前台操作。
- 报告和截图路径。

### 11.2 禁止升级语义

- `preflight_only` 不是 passed。
- `input_not_allowed` 不是 passed。
- `runs=0` 不是 live execution。
- `PostMessageW != 0` 最多证明消息已排队，不证明游戏接受或业务成功。
- `inputSent=true` 不等于 `gamePostconditionObserved=passed`。
- 一个窗口成功不等于双窗口隔离通过。

## 12. 实机开发节奏

用户明确要求开发过程中就看到应用和游戏效果，同时不能影响前台鼠标键盘。因此每个功能应采用小闭环：

1. 纯模型/纯函数先写单元测试。
2. 前端视图改完立即 build，并启动绑定当前 commit 的应用。
3. 先做只读 UI、截图、窗口枚举和预览验证。
4. 需要输入时创建 pre_live checkpoint。
5. 只选择一个明确 hwnd，复核管理员权限和身份。
6. 记录前台 HWND 和鼠标坐标。
7. 通过定向 HWND 路径发送最小动作。
8. 观察游戏后置状态。
9. 再核对前台 HWND、鼠标坐标和用户操作是否受干扰。
10. 失败时保留报告，停止扩大动作；修复后新 attempt。
11. 单窗口稳定后才进入第二窗口并行。

UI 不允许“默默写几天再看”。每个主要视图至少验证：

- 默认窗口尺寸和最小窗口尺寸。
- 关键控件可见、可达、文案不截断。
- 粘贴图片、采点、绑定目标、添加步骤、分配窗口、演练入口操作数。
- readiness 与真实执行门一致。
- 失败报告能定位到步骤和证据。

## 13. 副作用重试分类

| 动作 | 中断后策略 |
|---|---|
| `rg`、只读文件、Git 查询 | 可重新执行 |
| Node/Python/Rust 静态测试 | 可重新执行；新 attempt 记录结果 |
| build | 可重新执行，但旧产物不能自动清理 |
| 原子生成仓库文件 | 比较内容/hash 后决定是否补做 |
| AppData 备份 | 检查目标是否存在、hash 是否匹配，禁止覆盖重做 |
| AppData 迁移 | 核对主文件、备份、schema、mtime、hash 和应用日志；未知则阻塞 |
| commit | 检查 HEAD、reflog、diff 和 commit 内容 |
| push | 检查远端 ref，禁止盲目重复制造提交 |
| 启动应用 | 核对 PID、父 PID、命令行、工作目录、exe hash 和启动时间 |
| 停止进程 | 重新证明进程属于本轮；仅 PID/名称不够 |
| 游戏输入 | 核对报告和后置状态；未知结果禁止重发 |
| 删除/清理 | 重新证明目标由本轮创建且清理安全；不明则保留 |

## 14. 异常恢复算法

恢复分三层，不把完整 live 恢复承诺成五分钟：

1. **5 分钟定向恢复**：读 STATUS、运行状态审计和 Git 状态，确认当前切片、未决副作用、唯一下一动作与禁止动作。完成后只允许继续只读核验。
2. **代码工作恢复**：再核对 checkpoint、dirty diff、测试证据和当前 HEAD，追加 reconciliation/attempt 后才允许编辑和运行静态测试。
3. **AppData/live 恢复**：重新核对数据 hash、应用/exe、PID/HWND/权限、机器级 lease、前台见证和 pre-live checkpoint 后，才允许 AppData 写入或游戏输入。

快速入口：

```powershell
npm run execution:resume-check
npm run audit:execution-state
git status --short --ignored
npm run execution:preflight-p0
```

`execution:resume-check` 严格只读，不刷新 state/STATUS，不创建 checkpoint，也不执行产品命令。通过 `npm run` 使用时只依赖 `0/非 0`：任何非 `0` 都停止副作用并阅读输出。需要机器区分时直接运行 `python -B scripts/execution_progress.py resume-check --json`：`0` 可恢复；`2` 存在工作树漂移或未决动作，必须先对账；`3` 账本、checkpoint、lease、状态投影或 passed gate 语义完整性阻塞。第四条仅适用于当前 P0-S1，是只读 AppData 身份核对，不创建备份、不启动应用、不发送输入。

新 agent 或中断恢复时固定执行：

1. 阅读 `AGENTS.md`。
2. 阅读 `STATUS.md`，只获取当前切片、阻塞和下一动作。
3. 阅读本协议的恢复、安全和当前阶段规则。
4. 运行 `npm run execution:resume-check`；非 `0` 时只允许继续只读对账。
5. 运行 `npm run audit:execution-state`。
6. 运行 `git status --short --ignored`、`git rev-parse HEAD`、`git rev-parse origin/main`。
7. 读取最后 10 条 event 和 evidence；不重写历史。
8. 比较 observed/verified/upstream HEAD 和 dirtyPaths。
9. 核对 checkpoint 文件和 artifact hash。
10. 重新观察进程：PID、创建时间、可执行文件、父 PID、命令行、工作目录；无法读取的字段明确记为限制。
11. 重新枚举游戏 HWND，不从旧 PID 快照直接发送输入。
12. 核对 AppData 主文件、备份、schema、大小、mtime 和 hash。
13. 若发现旧 `running` action，先将其视为 `unknown_after_interruption`。
14. 按第 13 节的分类做 reconciliation。
15. 追加 `reconciliation` 事件，记录采用哪些当前事实、发现哪些冲突、哪些动作禁止重做。
16. 增加 attempt 或开始新 run。
17. 从 `activeSlice.nextAction` 继续。

恢复时禁止：

- 直接相信上一条 commentary 或 final。
- 因为文件名像临时文件就删除。
- 因为 PID 名称相同就杀进程。
- 因为 preflight 通过就发送输入。
- 因为 `state.json` 说 passed 就跳过 Git/证据核验。
- 修复账本漂移时删除事件；只能追加 reconciliation 并重建投影。

## 15. 子代理协议

### 15.1 适合并行

- 大范围源码搜索。
- 调用链审计。
- 测试矩阵设计。
- 构建/日志分析。
- 官方文档、成熟项目和论坛研究。
- UI、Rust 输入、持久化、runner 等独立只读审查。

### 15.2 不适合并行写

- `state.json`、STATUS、events、evidence、checkpoint。
- 同一大型 `src/main.js` 区域。
- AppData、真实窗口和 live 输入。
- commit/push 和清理。

### 15.3 子代理返回格式

必须包含：

```text
结论和证据
不确定点
是否只读
修改文件
创建/删除
缓存/日志/构建产物
下载/网络
配置/环境变量/凭据
进程/服务
测试
commit hash
需主代理清理
```

主代理需要从 Git、文件系统、进程表和测试结果复核。

## 16. Git、Worktree、Fork、Handoff、Automation、Hook 边界

### Git

Git 是代码回滚权威，但不保存运行进程、用户 AppData、ignored 报告和窗口状态。

### Worktree

适合两个独立写任务并行；不适合共享真实 AppData/live 游戏输入。Ignored 文件除非 `.worktreeinclude` 配置，否则不会自动移动。

### Fork

适合替代方案和独立审查。Fork 前必须 checkpoint；运行中的未完成 turn 不保证复制。

### Handoff

适合 Local/Worktree 移动 Git 状态。Handoff 前后都必须核对 ignored 文件、依赖、AppData、进程和证据。

### Scheduled task / heartbeat

适合等待构建、轮询状态和短时续跑，不替代 checkpoint。长任务 prompt 必须包含停止条件、报告条件和需要用户输入的条件。

### Hook

第一版只建议：

- SessionStart/恢复时提醒读取 STATUS 和运行审计。
- PreCompact/Stop 时提醒创建 checkpoint。
- 不自动 commit、push、清理、停止进程、迁移 AppData 或发送游戏输入。

## 17. 工具命令

### 17.1 生成状态页

```powershell
npm run execution:render
```

这会刷新 Git observed 状态并原子生成 `STATUS.md`。

### 17.2 记录重要事件

```powershell
python scripts/execution_progress.py note `
  --type decision `
  --summary "P0 先保护 v6 数据，再启动当前版本" `
  --next-action "只读计算 workspace 和旧 bak 的 hash"
```

### 17.3 开始 slice

```powershell
python scripts/execution_progress.py begin-slice `
  --phase P0 `
  --slice P0-S1 `
  --title "保护真实 v6 工作区并建立迁移基线" `
  --next-action "只读核对 AppData 文件身份" `
  --criterion "P0-S1-C1|appdata_backup=主文件独立备份 hash 一致" `
  --criterion "P0-S1-C2|appdata_backup=旧 bak 独立备份 hash 一致" `
  --safety-boundary "备份前不启动新版本"
```

### 17.4 登记副作用 intent

```powershell
python scripts/execution_progress.py action-start `
  --action-id ACT-P0-BACKUP-001 `
  --kind appdata_backup `
  --target "workspace.json -> workspace.pre-migration-<timestamp>.json" `
  --side-effect-class local_file_create `
  --precondition "source exists; destination absent" `
  --postcondition "destination hash equals source hash" `
  --idempotency-key "<source-sha256>:<destination>" `
  --ownership-evidence "destination path selected by current run"
```

### 17.5 结束副作用

```powershell
python scripts/execution_progress.py action-finish `
  --action-id ACT-P0-BACKUP-001 `
  --status succeeded `
  --result "source and destination SHA-256 match"
```

异常时使用 `unknown_after_interruption`，不要猜成功或失败。进入该状态后，通用 `action-finish` 不能再用自由文本改成 succeeded/failed；在动作专用 reconciliation verifier 实现并提供绑定 actionId、target、idempotencyKey 的证据前，动作保持未决并禁止重放。

### 17.6 记录证据

`status=passed` 禁止由通用 `evidence` 命令或调用者自报。静态审计、测试和构建必须由固定 profile 真实执行命令并自动记录退出码和日志：

```powershell
python scripts/execution_progress.py run-evidence `
  --profile node-all `
  --claim "全部 core 测试通过" `
  --criterion P0-S1-C4
```

可用 profile 只有 `node-all`、`python-audits`、`frontend-build`、`rust-static`、`p0-preflight`，且 profile 与证据类别固定映射。工具使用参数数组、`shell=False` 和超时，不接受任意 shell 字符串；`frontend-build` 自动绑定 `dist/index.html`。应用启动、窗口身份、真实输入、游戏后置状态、双窗口、持久化和 AppData 备份必须由 allowlist 中的专用 verifier 生成结构化证据；专用 verifier 尚未实现的类别保持 fail-closed，不能手工伪造 passed。

通用 `evidence` 入口只用于记录 `observed`、`failed`、`blocked` 或 `preflight` 等不宣称验收通过的事实。真实输入观察即使显式传 `--input-sent`，也仍不自动让 live outcome 通过。

### 17.7 更新验收轴

```powershell
python scripts/execution_progress.py gate `
  --name currentCommitAppLaunched `
  --status passed `
  --note "当前 commit 对应 exe 已启动并完成 UI smoke" `
  --evidence EVD-0012
```

### 17.8 创建 checkpoint

```powershell
python scripts/execution_progress.py checkpoint `
  --label pre-live `
  --type state_snapshot `
  --reason "发送首个真实 hwnd 输入前" `
  --safe-to-resume
```

只有真实可回滚 commit 才用 `git_checkpoint`。

### 17.9 审计

```powershell
npm run audit:execution-state
```

### 17.10 中断 reconciliation / attempt

```powershell
python scripts/execution_progress.py reconcile `
  --summary "重新核对 Git、账本、进程和 AppData 后恢复" `
  --increment-attempt `
  --thread-id "<current-thread-id>" `
  --next-action "<one exact action>"
```

如果 action 在中断前仍为 running，命令会保留它并标记 `unknown_after_interruption`；后续必须先用同一 actionId 对账完成，不能开始新副作用动作。

### 17.11 截断 JSONL 尾记录

只有审计证明“最后一行是没有换行结尾、无法解析的 torn JSON fragment”时，才能显式执行：

```powershell
python scripts/execution_progress.py repair-tail `
  --ledger events `
  --summary "隔离异常中断留下的截断尾片段" `
  --confirm-quarantine-truncated-tail
```

工具先把原始碎片以独占文件保存到 `docs/execution/recovery-fragments/`，再原子恢复有效前缀并追加 reconciliation。完整 JSON、hash 不匹配或中间损坏一律拒绝自动修复。

审计失败的典型原因：

- JSON/JSONL/hash/seq 损坏。
- state tail 与账本不一致。
- STATUS 不是精确生成投影。
- 当前 Git 与 state dirtyPaths/HEAD 不一致。
- checkpoint 不存在或格式错误。
- verifiedHead 不是可解析 commit。
- 验收轴引用不存在证据。
- live passed 只有 preflight、未发送输入或无证据。
- 外部进程被错误标 cleanupAllowed。

## 18. 当前项目的首个恢复入口

当前权威起点：

```text
phase: P0
slice: P0-S1
title: 保护真实 v6 工作区并建立迁移基线
verifiedHead: 3eef34f8c4b115c94e2c3cd6adb93cf329a60ef9
realInputSent: false
```

当前唯一下一动作：

1. 只读核对：
   - `workspace.json`
   - `workspace.json.bak`
   - 路径、大小、mtime、schema、任务/步骤/目标数量、SHA-256。
   - 统一命令：`npm run execution:preflight-p0`。
2. 选择两个新且不存在的备份目标名。
3. 使用 `action-start` 登记备份 intent。
4. 复制后核对 hash，不覆盖源文件或旧 bak。
5. 记录 evidence 和 checkpoint。
6. 建匿名 fixture，跑 migration 测试。

在上述步骤完成前：

- 不启动当前 HEAD 的应用。
- 不停止旧控制器。
- 不发送游戏输入。
- 不清理 ignored 产物。

## 19. Definition of Done

长期目标最终完成必须同时满足：

```text
所有 mandatory slice 的 acceptance criteria passed
AND 所有 required automated gates passed at final commit
AND final commit 对应 release 已构建并启动
AND 真实任务有游戏后置结果证据
AND 前台无干扰有证据
AND 双窗口并行隔离通过
AND 重启持久化通过
AND 无 running/unknown_after_interruption action
AND 文件、进程、产物和 ignored 内容完成归属审计
AND 稳定改动已 commit 并 push
```

聊天中的“完成了”、代码行数、审计脚本数量、蓝图数量和 preflight 数量都不能替代上述门禁。
