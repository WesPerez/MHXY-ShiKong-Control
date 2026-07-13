<!-- generated-by: scripts/execution_progress.py; do-not-edit-manually -->
<!-- state-digest: sha256:fe9e75f4948efa375edc0e028aabbf8255c604a48f97fdf351289f5de385a9ca -->
<!-- checkpoint-id: CP-0016 -->
# 长任务执行状态

> 本页由 `scripts/execution_progress.py` 从 `state.json`、事件账本和证据账本生成。
> 线程聊天不是恢复权威；冲突时以当前源码、Git、测试和实际运行结果为准。

## 恢复首屏

- 恢复结论：**STOP：存在未决副作用，只允许只读对账**
- 更新时间（UTC）：`2026-07-13T06:57:23Z`
- 更新时间（北京时间）：`2026-07-13T14:57:23+08:00`
- 长期任务：`MHXY-AUTOMATION-WORKBENCH`
- 运行：`RUN-20260710-CONTINUITY-BASELINE` / attempt `1`
- 总体状态：`active`
- 当前阶段：`P2`
- 当前切片：`P2-S2` - 五视口真实渲染与检查器交互验收
- 阶段状态：`blocked`；切片状态：`blocked`；动作状态：`running`
- 当前切片验收：已满足 `0`，待验证或阻塞 `4`，合计 `4`
- 本轮是否发送真实游戏输入：`false`
- 当前工作：未决动作 `ACT-COMMIT-P0-P2-SNAPSHOT-001` 处于 `running`，等待只读对账
- 最新当前有效证据：P0 workspace backup verified without overwriting the source or an existing destination（EVD-0030，当前工作区绑定有效）
- 唯一下一动作：对账未决副作用动作 ACT-COMMIT-P0-P2-SNAPSHOT-001；结果明确前禁止重放
- 当前切片执行 blocker：缺少本地预览进程启动与只读 UI 测试授权
- 全局恢复/验收风险：P2 UI 切片需要启动本任务构建的本地应用；externalAuthorization=appdata_backup_only 不包含进程启动
- 最新 checkpoint：`CP-0016`；safeToResume=`true`；safeToRunLiveInput=`false`
- 当前允许：只读审计、连续性元数据对账。
- 当前禁止：归属不明对象的清理或停止、未登记 intent 的副作用动作、重放未决动作、真实游戏输入。
- 运行观察（STATUS 生成时）：**已过期**；observedAt=`2026-07-11T18:46:50Z`；年龄=`130233s`；TTL=`300s`；expiresAt=`2026-07-11T18:51:50Z`。执行窗口/进程动作前以 `execution:resume-check` 的动态结果为准。

## 验收轴

| 验收轴 | 状态 | 依据/限制 |
|---|---|---|
| 代码表面能力 | `部分` | 源码已有 15 类步骤、任务/目标/队列/readiness/失败报告等表面能力，但大型文件耦合且真实闭环不足。 |
| 自动测试 | `已过期` | P2-S2 verifier 配置、10 个测试发现和静态全回归通过；真实 Playwright UI 未执行；当前没有绑定现有 HEAD/工作树指纹的有效通过证据 |
| 当前提交构建 | `已过期` | P2-S2 当前工作树 Vite 生产构建通过；本地预览尚未启动；当前没有绑定现有 HEAD/工作树指纹的有效通过证据 |
| 当前提交应用已启动 | `未验证` | 当前没有 mhxy-shikong-control.exe 控制器进程；本轮未启动当前 HEAD 应用 |
| 后台 HWND 输入已实际发送 | `未验证` | 当前 HEAD 没有应用 UI 到指定 hwnd 的真实输入通过证据。 |
| 游戏后置状态已观察 | `未验证` | 没有绑定当前 HEAD、exe、workspace 和窗口身份的游戏后置状态证据。 |
| 前台鼠标键盘未受影响 | `部分` | 静态安全审计只允许 PostMessageW 路径，但尚缺当前版本实测前后台 HWND、鼠标位置和用户并行操作证据。 |
| 双窗口隔离 | `未验证` | 两个游戏进程存在，但当前 HEAD 尚未完成双窗口不同队列并行隔离验收。 |
| 重启持久化 | `未验证` | EVD-0029 和 EVD-0030 已证明 workspace.json 与旧 workspace.json.bak 分别完成不可覆盖备份且源/目标 SHA-256 一致；真实 AppData 迁移、应用重启回读和第二次重启幂等仍未验证。 |

## 阶段表

| 阶段 | 状态 | 验收摘要 |
|---|---|---|
| `P0` 数据保护与可重复基线 | `verified` | 保护真实 v6 工作区、建立匿名迁移 fixture 和可重复验证基线。 |
| `P1` 运行安全硬化 | `verified` | 消除窗口身份、权限、误跑和输入安全 P0/P1 风险。 |
| `P2` 工作台可达性与单步调试 | `blocked` | 重构默认窗口下的操作路径，建立每个功能即时可见、可测的工作台。 |
| `P3` 严格捕获和视觉引擎 | `pending` | 修复捕获、ROI、模板、OCR 和预览一致性。 |
| `P4` 第一个真实纵向任务 | `pending` | 以家园活力完成 UI 到游戏后置验证的真实闭环。 |
| `P5` 持久化和素材文件化 | `pending` | 按方案评估 SQLite/结构化 JSON，补版本迁移、原子写入和备份。 |
| `P6` 第二至第五个真实任务 | `pending` | 逐个纵向闭环更多真实任务，不用草稿数量代替可用性。 |
| `P7` 双窗口并行和队列控制 | `pending` | 验证同窗口串行、跨窗口并行、暂停继续和隔离。 |
| `P8` 回归任务与发布门 | `pending` | 扩展到 5-10 个可重复回归任务并完成失败矩阵。 |
| `P9` 源码清理、稳定提交和发布 | `pending` | 在调用链和完整验证后清理、提交、推送和发布稳定版本。 |

## 当前切片

### 范围

- index.html,src/styles.css,src/main.js,Playwright screenshots and viewport metrics

### 非目标

- 本切片不启动 Tauri 应用、不读取或迁移真实 AppData、不枚举游戏窗口、不发送输入

### 安全边界

- 只启动本任务拥有的 localhost 预览进程；完成后仅停止该 PID；浏览器只做只读 UI 交互

### 验收条件

| ID | 条件 | 状态 | 允许证据类别 | 证据 |
|---|---|---|---|---|
| `P2-S2-C1` | 当前工作树 Vite 预览以可核验 PID/命令启动并可访问 | `pending` | `app_runtime` | none |
| `P2-S2-C2` | 1460x880、1280x720、1120x720、920x680、820x720 均无页面级横向滚动且任务/步骤列表可达 | `pending` | `test` | none |
| `P2-S2-C3` | 检查器 tab 鼠标和键盘切换、补全定位与失败步骤定位能揭示正确面板 | `pending` | `test` | none |
| `P2-S2-C4` | 视觉发现的布局问题修复后 Node/Python/Vite 回归继续通过 | `pending` | `test` | none |

## 当前动作

- actionId：`ACT-COMMIT-P0-P2-SNAPSHOT-001`
- 类型：`git_commit`
- 目标：`HEAD:main working tree P0-P2 snapshot`
- 副作用级别：`git_commit`
- 状态：`running`

## 下一步

- 唯一下一动作：对账未决副作用动作 ACT-COMMIT-P0-P2-SNAPSHOT-001；结果明确前禁止重放
- 命令：`npm run audit:execution-state`
- 命令：`git status --short --ignored`
- 命令：`npm run execution:preflight-p0`

## 阻塞与风险

### 阻塞

- P2 UI 切片需要启动本任务构建的本地应用；externalAuthorization=appdata_backup_only 不包含进程启动

### 禁止盲目执行

- 未扩展授权前不启动/停止应用、不发送游戏输入、不改写 AppData、不 commit/push

## Git 现场

- 分支：`main`
- observed HEAD：`3eef34f8c4b115c94e2c3cd6adb93cf329a60ef9`
- verified HEAD：`3eef34f8c4b115c94e2c3cd6adb93cf329a60ef9`
- origin/main：`3eef34f8c4b115c94e2c3cd6adb93cf329a60ef9`
- working tree fingerprint：`sha256:06b677eac89f7f4c9ad6913d4fb67120d3e5b29a2d1c4dda0d3854ae3d010435`
- 最新 checkpoint：`CP-0016` (state_snapshot)
- checkpoint safeToResume：`true`
- checkpoint safeToRunLiveInput：`false`

### 当前非 ignored 改动

- `AGENTS.md`
- `README.md`
- `docs/current-progress-and-handoff.md`
- `docs/execution/PROTOCOL.md`
- `docs/execution/STATUS.md`
- `docs/execution/checkpoints/CP-0001-continuity-baseline.json`
- `docs/execution/checkpoints/CP-0002-continuity-parser-fix.json`
- `docs/execution/checkpoints/CP-0003-hardened-continuity-baseline.json`
- `docs/execution/checkpoints/CP-0004-hardened-long-task-resume.json`
- `docs/execution/checkpoints/CP-0005-p0-s1-verified.json`
- `docs/execution/checkpoints/CP-0006-p1-s1-verified.json`
- `docs/execution/checkpoints/CP-0007-p1-s1-final.json`
- `docs/execution/checkpoints/CP-0008-p1-s2-verified.json`
- `docs/execution/checkpoints/CP-0009-p1-s2-final.json`
- `docs/execution/checkpoints/CP-0010-p1-s3-final.json`
- `docs/execution/checkpoints/CP-0011-p1-s4-final.json`
- `docs/execution/checkpoints/CP-0012-p1-s5-final.json`
- `docs/execution/checkpoints/CP-0013-p2-s1-static-layout.json`
- `docs/execution/checkpoints/CP-0014-p2-s2-verifier-ready.json`
- `docs/execution/checkpoints/CP-0015-p2-s2-goal-handoff.json`
- `docs/execution/checkpoints/CP-0016-repository-directory-rename.json`
- `docs/execution/events.jsonl`
- `docs/execution/evidence.jsonl`
- `docs/execution/state.json`
- `docs/next-agent-goal-prompt.md`
- `docs/project-audit-and-master-plan.md`
- `docs/workflow-model.md`
- `index.html`
- `package-lock.json`
- `package.json`
- `playwright.workbench.config.mjs`
- `scripts/anonymize_workspace_fixture.py`
- `scripts/audit_capture_policy.py`
- `scripts/audit_execution_state.py`
- `scripts/audit_input_safety.py`
- `scripts/audit_ocr_worker.py`
- `scripts/audit_p0_safety_boundary.py`
- `scripts/audit_queue_readiness.py`
- `scripts/audit_runtime_lane.py`
- `scripts/audit_workbench_layout.py`
- `scripts/audit_workbench_viewport_test.py`
- `scripts/audit_workspace_migration.py`
- `scripts/execution_progress.py`
- `scripts/fixtures/workspace-v6-anonymized.json`
- `scripts/playwright/workbench-viewports.spec.mjs`
- `scripts/preflight_p0_workspace.py`
- `scripts/test_capture_policy_core.mjs`
- `scripts/test_control_flow_core.mjs`
- `scripts/test_execution_progress.py`
- `scripts/test_failure_evidence_core.mjs`
- `scripts/test_live_validation_core.mjs`
- `scripts/test_run_dispatch_core.mjs`
- `scripts/test_workbench_layout_core.mjs`
- `scripts/test_workspace_migration_core.mjs`
- `scripts/verify_p0_workspace_backup.py`
- `src-tauri/Cargo.toml`
- `src-tauri/src/main.rs`
- `src-tauri/src/platform.rs`
- `src-tauri/src/runtime/mod.rs`
- `src-tauri/src/runtime/ocr_pool.rs`
- `src-tauri/src/runtime/window_lane.rs`
- `src/capture-policy-core.js`
- `src/control-flow-core.js`
- `src/failure-evidence-core.js`
- `src/main.js`
- `src/run-dispatch-core.js`
- `src/styles.css`
- `src/workbench-layout-core.js`
- `src/workspace-normalization-core.js`

## 运行进程与产物

### 本轮管理的进程

- none

### 只观察到的外部进程

- PID `42432`：`mhxy-shikong-control.exe`，旧控制器历史线索；present=`false`，归属=`preexisting`，cleanupAllowed=`false`
- PID `26056`：`MyGame_x64r.exe`，历史游戏窗口线索 A；present=`false`，归属=`user_preexisting`，cleanupAllowed=`false`
- PID `52448`：`MyGame_x64r.exe`，历史游戏窗口线索 B；present=`false`，归属=`user_preexisting`，cleanupAllowed=`false`

### 本轮管理的产物

- `AGENTS.md`
- `docs/execution/`
- `scripts/execution_progress.py`
- `scripts/audit_execution_state.py`

### 观察到但未接管的产物

- `assets/resource/ShiKong/reports/`
- `src-tauri/target*/`
- `.codex-window-*.png`

## 最近证据

| ID | 类型 | 原始结果 | 当前适用性 | 结论/原因 |
|---|---|---|---|---|
| `EVD-0069` | `build` | `passed` | `stale` | P1-S5 当前工作树 Vite 生产构建通过<br>证据工作树指纹与当前现场不同 |
| `EVD-0070` | `test` | `passed` | `stale` | P1-S5 固定 OCR workers、有限队列、取消超时和跨 worker 并行 Rust 门禁通过<br>证据工作树指纹与当前现场不同 |
| `EVD-0071` | `test` | `passed` | `stale` | P2-S1 检查器 tab、目标视口布局契约与全部 core 回归通过<br>证据工作树指纹与当前现场不同 |
| `EVD-0072` | `test` | `passed` | `stale` | P2-S1 工作台语义结构、非零列表轨道、响应式滚动和 DOM id 静态审计通过<br>证据工作树指纹与当前现场不同 |
| `EVD-0073` | `build` | `passed` | `stale` | P2-S1 当前工作树 Vite 生产构建通过<br>证据工作树指纹与当前现场不同 |
| `EVD-0074` | `test` | `passed` | `stale` | P2-S2 Playwright verifier 加入后全部 core 与连续性回归通过；真实 UI 尚未执行<br>证据工作树指纹与当前现场不同 |
| `EVD-0075` | `test` | `passed` | `stale` | P2-S2 五视口 verifier 静态覆盖、布局审计和安全审计通过；真实 UI 尚未执行<br>证据工作树指纹与当前现场不同 |
| `EVD-0076` | `build` | `passed` | `stale` | P2-S2 Playwright verifier 加入后 Vite 生产构建通过<br>证据工作树指纹与当前现场不同 |

## 最近事件

| seq | 时间 | 类型 | 摘要 |
|---:|---|---|---|
| 207 | `2026-07-11T18:46:49Z` | `runtime_observation` | 2026-07-12 恢复复核未发现该 PID 或任何 MyGame_x64r.exe 进程 |
| 208 | `2026-07-11T18:46:50Z` | `runtime_observation` | 2026-07-12 恢复复核未发现该 PID 或任何 MyGame_x64r.exe 进程 |
| 209 | `2026-07-11T18:46:51Z` | `slice_state_changed` | 更新验收轴 restartPersistenceVerified -> not_verified |
| 210 | `2026-07-11T18:46:52Z` | `decision` | 完成历史任务与当前累计进度交接文档，并生成可直接放入 Codex Goal 的 P0-P9 自主执行提示词 |
| 211 | `2026-07-11T18:46:54Z` | `checkpoint` | 创建 CP-0015：历史任务归因、P0-P2 当前事实、P3-P9 待办、授权边界和下一 Agent 长期 Goal 提示词已落盘 |
| 212 | `2026-07-11T23:22:53Z` | `action_intent` | 登记副作用动作 ACT-REPO-RENAME-20260712 |
| 213 | `2026-07-11T23:25:24Z` | `action_result` | 副作用动作 ACT-REPO-RENAME-20260712 -> succeeded |
| 214 | `2026-07-11T23:26:47Z` | `decision` | 仓库与本地目录已统一为 mhxy-shikong-control；origin、活动绝对路径和测试 fixture 已迁移，哈希链历史路径按协议保留 |
| 215 | `2026-07-11T23:26:49Z` | `checkpoint` | 创建 CP-0016：完成 GitHub 仓库名、本地目录和活动路径引用迁移 |
| 216 | `2026-07-13T06:57:23Z` | `action_intent` | 登记副作用动作 ACT-COMMIT-P0-P2-SNAPSHOT-001 |

## 异常恢复

1. 阅读 `AGENTS.md`、本页和 `docs/execution/PROTOCOL.md`。
2. 运行 `npm run execution:resume-check`；退出码非 0 时不要执行任何副作用动作。
3. 再运行 `npm run audit:execution-state` 和 `git status --short --ignored`，比较 observed/verified/upstream HEAD 和 dirty 文件。
4. 重新核验 AppData、应用版本、进程、窗口身份和证据文件；过期 PID 只能作为线索。
5. 若存在 `running` 或 `unknown_after_interruption` 动作，先 reconciliation，禁止直接重试。
6. 追加 `reconciliation` 事件后，从“唯一下一动作”继续。

详细规则见 [PROTOCOL.md](PROTOCOL.md)，长期产品方案见 [project-audit-and-master-plan.md](../project-audit-and-master-plan.md)。
