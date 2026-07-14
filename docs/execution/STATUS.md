<!-- generated-by: scripts/execution_progress.py; do-not-edit-manually -->
<!-- state-digest: sha256:937dc303d760432fc170ddbd7536003a11b4d27a85910c2e4ec7a3ad03bb69d8 -->
<!-- checkpoint-id: CP-0052 -->
# 长任务执行状态

> 本页由 `scripts/execution_progress.py` 从 `state.json`、事件账本和证据账本生成。
> 线程聊天不是恢复权威；冲突时以当前源码、Git、测试和实际运行结果为准。

## 恢复首屏

- 恢复结论：**STOP：存在未决副作用，只允许只读对账**
- 更新时间（UTC）：`2026-07-14T10:59:28Z`
- 更新时间（北京时间）：`2026-07-14T18:59:28+08:00`
- 长期任务：`MHXY-AUTOMATION-WORKBENCH`
- 运行：`RUN-20260710-CONTINUITY-BASELINE` / attempt `8`
- 总体状态：`active`
- 当前阶段：`P4`
- 当前切片：`P4-S5` - Home-vitality bounded live queue under elevated controller
- 阶段状态：`in_progress`；切片状态：`in_progress`；动作状态：`running`
- 当前切片验收：已满足 `0`，待验证或阻塞 `2`，合计 `2`
- 本轮是否发送真实游戏输入：`false`
- 当前工作：未决动作 `ACT-P4S5-COMMIT-001` 处于 `running`，等待只读对账
- 最新当前有效证据：P4-S5 pre-commit: python audits（EVD-0329，当前工作区绑定有效）
- 唯一下一动作：对账未决副作用动作 ACT-P4S5-COMMIT-001；结果明确前禁止重放
- 当前切片执行 blocker：none
- 全局恢复/验收风险：Game HWND exists (PID 86812 / HWND 26157554) but controller privilege is insufficient for gated input.
- 最新 checkpoint：`CP-0052`；safeToResume=`true`；safeToRunLiveInput=`false`
- 当前允许：只读审计、连续性元数据对账。
- 当前禁止：归属不明对象的清理或停止、未登记 intent 的副作用动作、重放未决动作、真实游戏输入。
- 运行观察（STATUS 生成时）：**已过期**；observedAt=`2026-07-14T10:50:00Z`；年龄=`568s`；TTL=`300s`；expiresAt=`2026-07-14T10:55:00Z`。执行窗口/进程动作前以 `execution:resume-check` 的动态结果为准。

## 验收轴

| 验收轴 | 状态 | 依据/限制 |
|---|---|---|
| 代码表面能力 | `部分` | 源码已有 15 类步骤、任务/目标/队列/readiness/失败报告等表面能力，但大型文件耦合且真实闭环不足。 |
| 自动测试 | `已过期` | P2-S2 verifier 配置、10 个测试发现和静态全回归通过；真实 Playwright UI 未执行；当前没有绑定现有 HEAD/工作树指纹的有效通过证据 |
| 当前提交构建 | `已过期` | 源码已新增 source-aware audit 修复，旧 build evidence 不再代表当前工作树。 |
| 当前提交应用已启动 | `已过期` | 源码已新增 source-aware audit 修复，旧 app-runtime/window evidence 不再代表当前工作树。 |
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
| `P2` 工作台可达性与单步调试 | `verified` | 重构默认窗口下的操作路径，建立每个功能即时可见、可测的工作台。 |
| `P3` 严格捕获和视觉引擎 | `verified` | 修复捕获、ROI、模板、OCR 和预览一致性。 |
| `P4` 第一个真实纵向任务 | `in_progress` | 以家园活力完成 UI 到游戏后置验证的真实闭环。 |
| `P5` 持久化和素材文件化 | `pending` | 按方案评估 SQLite/结构化 JSON，补版本迁移、原子写入和备份。 |
| `P6` 第二至第五个真实任务 | `pending` | 逐个纵向闭环更多真实任务，不用草稿数量代替可用性。 |
| `P7` 双窗口并行和队列控制 | `pending` | 验证同窗口串行、跨窗口并行、暂停继续和隔离。 |
| `P8` 回归任务与发布门 | `pending` | 扩展到 5-10 个可重复回归任务并完成失败矩阵。 |
| `P9` 源码清理、稳定提交和发布 | `pending` | 在调用链和完整验证后清理、提交、推送和发布稳定版本。 |

## 当前切片

### 范围

- src/main.js
- src/home-vitality-core.js
- docs/execution

### 非目标

- Do not stop user game process
- Do not expand beyond home-vitality first vertical task

### 安全边界

- Live input only via controller PostMessage path after manual confirmation
- Game process is user_preexisting; cleanupAllowed=false

### 验收条件

| ID | 条件 | 状态 | 允许证据类别 | 证据 |
|---|---|---|---|---|
| `P4-S5-C1` | bounded home-vitality input path executes with inputSent evidence only after manual confirmation and elevated window gates | `pending` | `live_input` | none |
| `P4-S5-C2` | game postcondition observed for vitality change without claiming broader multi-task completion | `pending` | `live_outcome` | none |

## 当前动作

- actionId：`ACT-P4S5-COMMIT-001`
- 类型：`git_commit`
- 目标：`HEAD`
- 副作用级别：`git_commit`
- 状态：`running`

## 下一步

- 唯一下一动作：对账未决副作用动作 ACT-P4S5-COMMIT-001；结果明确前禁止重放
- 命令：`npm run execution:resume-check`

## 阻塞与风险

### 阻塞

- Game HWND exists (PID 86812 / HWND 26157554) but controller privilege is insufficient for gated input.

### 禁止盲目执行

- Do not stop MyGame_x64r without user request.

## Git 现场

- 分支：`main`
- observed HEAD：`3e6066660d7774f94b5cf4f1ed21631bb7d38701`
- verified HEAD：`162a96a9b9e65cf55a131a22b6c7870de70cec5d`
- origin/main：`3eef34f8c4b115c94e2c3cd6adb93cf329a60ef9`
- working tree fingerprint：`sha256:a4428ef5b84fc88f023baa90caf0ea78d6c7f0fa013c6fdb3695ff348a4f3493`
- 最新 checkpoint：`CP-0052` (state_snapshot)
- checkpoint safeToResume：`true`
- checkpoint safeToRunLiveInput：`false`

### 当前非 ignored 改动

- `docs/execution/STATUS.md`
- `docs/execution/checkpoints/CP-0038-p4-s2-runtime-rebind.json`
- `docs/execution/checkpoints/CP-0039-p4-s2-game-identity-rebind.json`
- `docs/execution/checkpoints/CP-0040-p4-s2-game-no-window.json`
- `docs/execution/checkpoints/CP-0041-p4-resume-before-s3.json`
- `docs/execution/checkpoints/CP-0042-p4-strict-preflight-offline.json`
- `docs/execution/checkpoints/CP-0043-p4-strict-preflight-hardened.json`
- `docs/execution/checkpoints/CP-0044-p4-final-readonly-runtime.json`
- `docs/execution/checkpoints/CP-0045-p4-s2-strict-preflight-identity-hardening.json`
- `docs/execution/checkpoints/CP-0046-p4-home-vitality-offline-contract.json`
- `docs/execution/checkpoints/CP-0047-p4-offline-manual-confirm-snapshot.json`
- `docs/execution/checkpoints/CP-0048-p4-offline-contracts-final-bind.json`
- `docs/execution/checkpoints/CP-0049-p4-controller-elevated.json`
- `docs/execution/checkpoints/CP-0050-p4-s3-live-preflight-passed.json`
- `docs/execution/checkpoints/CP-0051-p4-s4-offline-ready.json`
- `docs/execution/checkpoints/CP-0052-p4-s5-pre-commit-offline-rebind.json`
- `docs/execution/events.jsonl`
- `docs/execution/evidence.jsonl`
- `docs/execution/state.json`
- `docs/next-agent-goal-prompt.md`
- `index.html`
- `package.json`
- `scripts/audit_execution_state.py`
- `scripts/audit_runtime_lane.py`
- `scripts/audit_strict_capture_preflight.py`
- `scripts/audit_workflow_readiness.py`
- `scripts/execution_progress.py`
- `scripts/test_execution_progress.py`
- `scripts/test_home_vitality_core.mjs`
- `scripts/test_manual_confirmation_core.mjs`
- `scripts/test_runtime_lane_audit.py`
- `scripts/test_strict_capture_preflight_audit.py`
- `scripts/test_strict_capture_probe_binary.py`
- `scripts/test_verify_strict_capture_preflight.py`
- `scripts/test_workflow_readiness_audit.py`
- `scripts/verify_app_runtime_launch.py`
- `scripts/verify_strict_capture_preflight.py`
- `scripts/verify_window_identity.py`
- `src-tauri/src/bin/strict_capture_probe.rs`
- `src-tauri/src/main.rs`
- `src-tauri/src/runtime/vision_match.rs`
- `src/home-vitality-core.js`
- `src/main.js`
- `src/manual-confirmation-core.js`
- `src/target-library-core.js`
- `src/workspace-normalization-core.js`

## 运行进程与产物

### 本轮管理的进程

- PID `61780`：controller-app；cleanupAllowed=`true`

### 只观察到的外部进程

- PID `42432`：`mhxy-shikong-control.exe`，旧控制器历史线索；present=`false`，归属=`preexisting`，cleanupAllowed=`false`
- PID `26056`：`MyGame_x64r.exe`，历史游戏窗口线索 A；present=`false`，归属=`user_preexisting`，cleanupAllowed=`false`
- PID `52448`：`MyGame_x64r.exe`，历史游戏窗口线索 B；present=`false`，归属=`user_preexisting`，cleanupAllowed=`false`
- PID `12744`：`mhxy-shikong-control.exe`，controller-app；present=`false`，归属=`task-owned`，cleanupAllowed=`false`
- PID `16244`：`mhxy-shikong-control.exe`，controller-app；present=`false`，归属=`created_by_current_run`，cleanupAllowed=`false`
- PID `18332`：`mhxy-shikong-control.exe`，controller-app；present=`false`，归属=`created_by_current_run`，cleanupAllowed=`false`
- PID `50936`：`mhxy-shikong-control.exe`，controller-app；present=`false`，归属=`created_by_current_run`，cleanupAllowed=`false`
- PID `80388`：`mhxy-shikong-control.exe`，controller-app；present=`false`，归属=`created_by_current_run`，cleanupAllowed=`false`
- PID `2960`：`mhxy-shikong-control.exe`，controller-app；present=`false`，归属=`created_by_current_run`，cleanupAllowed=`false`
- PID `73840`：`mhxy-shikong-control.exe`，controller-app；present=`false`，归属=`created_by_current_run`，cleanupAllowed=`false`
- PID `1832`：`MyGame_x64r.exe`，game-client；present=`false`，归属=`user_preexisting`，cleanupAllowed=`false`
- PID `61780`：`mhxy-shikong-control.exe`，controller-app；present=`false`，归属=`created_by_current_run`，cleanupAllowed=`false`
- PID `68420`：`MyGame_x64r.exe`，game-client；present=`false`，归属=`created_by_current_run`，cleanupAllowed=`false`
- PID `86812`：`MyGame_x64r.exe`，game-client；present=`true`，归属=`user_preexisting`，cleanupAllowed=`false`
- PID `71740`：`mhxy-shikong-control.exe`，controller-app；present=`true`，归属=`task_owned`，cleanupAllowed=`false`

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
| `EVD-0322` | `test` | `passed` | `stale` | P4-S5 rebind: Rust static profile retry after flaky ocr_pool queue_full test<br>证据工作树指纹与当前现场不同 |
| `EVD-0323` | `window_identity` | `passed` | `stale` | Verified live window identity for game-client (read-only, no input)<br>证据工作树指纹与当前现场不同 |
| `EVD-0324` | `window_identity` | `passed` | `stale` | Verified live window identity for game-client (read-only, no input)<br>证据工作树指纹与当前现场不同 |
| `EVD-0325` | `live_preflight` | `passed` | `stale` | Strict target capture completed bounded zero-input wait_image preflight<br>证据工作树指纹与当前现场不同 |
| `EVD-0326` | `test` | `passed` | `valid` | P4-S5 pre-commit: core tests after supporting live evidence verifier patch<br>绑定当前 HEAD、工作树指纹和受信来源 |
| `EVD-0327` | `build` | `passed` | `valid` | P4-S5 pre-commit: Vite build after supporting live evidence verifier patch<br>绑定当前 HEAD、工作树指纹和受信来源 |
| `EVD-0328` | `source_audit` | `passed` | `valid` | P4-S5 pre-commit: home-vitality offline audit<br>绑定当前 HEAD、工作树指纹和受信来源 |
| `EVD-0329` | `test` | `passed` | `valid` | P4-S5 pre-commit: python audits<br>绑定当前 HEAD、工作树指纹和受信来源 |

## 最近事件

| seq | 时间 | 类型 | 摘要 |
|---:|---|---|---|
| 668 | `2026-07-14T10:48:05Z` | `runtime_observation` | Verified live window identity for game-client (read-only, no input) |
| 669 | `2026-07-14T10:49:34Z` | `runtime_observation` | Verified live window identity for game-client (read-only, no input) |
| 670 | `2026-07-14T10:50:00Z` | `runtime_observation` | Strict target capture completed bounded zero-input wait_image preflight |
| 671 | `2026-07-14T10:56:32Z` | `decision` | P4-S5 progress: privilege elevated confirmed (game 86812 + controller 71740); supporting window_identity EVD-0324 and zero-input live_preflight EVD-0325 rebound. Live game_input still blocked until non-metadata dirty is committed, verifiedHead advanced, currentCommitBuilt/AppLaunched pass, and pre-live checkpoint sets safeToRunLiveInput. |
| 672 | `2026-07-14T10:57:54Z` | `test_run` | P4-S5 pre-commit: core tests after supporting live evidence verifier patch |
| 673 | `2026-07-14T10:58:01Z` | `test_run` | P4-S5 pre-commit: Vite build after supporting live evidence verifier patch |
| 674 | `2026-07-14T10:58:05Z` | `evidence_recorded` | P4-S5 pre-commit: home-vitality offline audit |
| 675 | `2026-07-14T10:58:19Z` | `test_run` | P4-S5 pre-commit: python audits |
| 676 | `2026-07-14T10:58:33Z` | `checkpoint` | 创建 CP-0052：Before committing P4 offline rebind and supporting live-evidence verifier paths; tests EVD-0326 build EVD-0327 home EVD-0328 audits EVD-0329; elevated identity EVD-0324 preflight EVD-0325; no live input yet. |
| 677 | `2026-07-14T10:59:28Z` | `action_intent` | 登记副作用动作 ACT-P4S5-COMMIT-001 |

## 异常恢复

1. 阅读 `AGENTS.md`、本页和 `docs/execution/PROTOCOL.md`。
2. 运行 `npm run execution:resume-check`；退出码非 0 时不要执行任何副作用动作。
3. 再运行 `npm run audit:execution-state` 和 `git status --short --ignored`，比较 observed/verified/upstream HEAD 和 dirty 文件。
4. 重新核验 AppData、应用版本、进程、窗口身份和证据文件；过期 PID 只能作为线索。
5. 若存在 `running` 或 `unknown_after_interruption` 动作，先 reconciliation，禁止直接重试。
6. 追加 `reconciliation` 事件后，从“唯一下一动作”继续。

详细规则见 [PROTOCOL.md](PROTOCOL.md)，长期产品方案见 [project-audit-and-master-plan.md](../project-audit-and-master-plan.md)。
