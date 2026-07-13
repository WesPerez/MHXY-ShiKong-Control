<!-- generated-by: scripts/execution_progress.py; do-not-edit-manually -->
<!-- state-digest: sha256:ded9ca07b6c8b2a41532d33ba30358c9512c6ed4337677536fdf6d234bcb4ea1 -->
<!-- checkpoint-id: CP-0022 -->
# 长任务执行状态

> 本页由 `scripts/execution_progress.py` 从 `state.json`、事件账本和证据账本生成。
> 线程聊天不是恢复权威；冲突时以当前源码、Git、测试和实际运行结果为准。

## 恢复首屏

- 恢复结论：**可恢复代码工作；其它副作用仍需各自门禁**
- 更新时间（UTC）：`2026-07-13T08:17:59Z`
- 更新时间（北京时间）：`2026-07-13T16:17:59+08:00`
- 长期任务：`MHXY-AUTOMATION-WORKBENCH`
- 运行：`RUN-20260710-CONTINUITY-BASELINE` / attempt `1`
- 总体状态：`active`
- 当前阶段：`P3`
- 当前切片：`P3-S2` - ROI-required template matching with search budget and fail-closed wait_image
- 阶段状态：`in_progress`；切片状态：`verified`；动作状态：`none`
- 当前切片验收：已满足 `4`，待验证或阻塞 `0`，合计 `4`
- 本轮是否发送真实游戏输入：`false`
- 当前工作：当前没有副作用动作在执行，停在下一动作之前
- 最新当前有效证据：P3-S2 after vision match budget: Vite production build green（EVD-0097，当前工作区绑定有效）
- 唯一下一动作：git commit P3-S2 product + ledger
- 当前切片执行 blocker：none
- 全局恢复/验收风险：P2 UI 切片需要启动本任务构建的本地应用；externalAuthorization=appdata_backup_only 不包含进程启动
- 最新 checkpoint：`CP-0022`；safeToResume=`true`；safeToRunLiveInput=`false`
- 当前允许：只读审计、连续性元数据对账、当前切片内的代码工作。
- 当前禁止：归属不明对象的清理或停止、未登记 intent 的副作用动作、真实游戏输入。
- 运行观察（STATUS 生成时）：**已过期**；observedAt=`2026-07-11T18:46:50Z`；年龄=`135069s`；TTL=`300s`；expiresAt=`2026-07-11T18:51:50Z`。执行窗口/进程动作前以 `execution:resume-check` 的动态结果为准。

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
| `P2` 工作台可达性与单步调试 | `verified` | 重构默认窗口下的操作路径，建立每个功能即时可见、可测的工作台。 |
| `P3` 严格捕获和视觉引擎 | `in_progress` | 修复捕获、ROI、模板、OCR 和预览一致性。 |
| `P4` 第一个真实纵向任务 | `pending` | 以家园活力完成 UI 到游戏后置验证的真实闭环。 |
| `P5` 持久化和素材文件化 | `pending` | 按方案评估 SQLite/结构化 JSON，补版本迁移、原子写入和备份。 |
| `P6` 第二至第五个真实任务 | `pending` | 逐个纵向闭环更多真实任务，不用草稿数量代替可用性。 |
| `P7` 双窗口并行和队列控制 | `pending` | 验证同窗口串行、跨窗口并行、暂停继续和隔离。 |
| `P8` 回归任务与发布门 | `pending` | 扩展到 5-10 个可重复回归任务并完成失败矩阵。 |
| `P9` 源码清理、稳定提交和发布 | `pending` | 在调用链和完整验证后清理、提交、推送和发布稳定版本。 |

## 当前切片

### 范围

- src-tauri/src/main.rs
- src-tauri/src/runtime/vision_match.rs
- src-tauri/src/runtime/mod.rs
- scripts/audit_capture_policy.py

### 非目标

- Do not integrate OpenCV in this slice
- Do not send live game input

### 安全边界

- wait_image/detect_page without template never report matched=true
- Unbudgeted full-frame brute-force search fails closed

### 验收条件

| ID | 条件 | 状态 | 允许证据类别 | 证据 |
|---|---|---|---|---|
| `P3-S2-C1` | wait_image without template returns missing_template and matched=false | `passed` | `test` | `EVD-0094`, `EVD-0095`, `EVD-0096` |
| `P3-S2-C2` | template search enforces ROI/search budget and fails closed when over budget | `passed` | `test` | `EVD-0094`, `EVD-0095`, `EVD-0096` |
| `P3-S2-C3` | match_template still supports cancel/deadline checkpoints and finds exact matches inside ROI | `passed` | `test` | `EVD-0094`, `EVD-0095`, `EVD-0096` |
| `P3-S2-C4` | Rust vision unit tests and Node/Python core regression remain green | `passed` | `build`, `test` | `EVD-0094`, `EVD-0095`, `EVD-0096`, `EVD-0097` |

## 当前动作

- 当前没有未决副作用动作。

## 下一步

- 唯一下一动作：git commit P3-S2 product + ledger
- 命令：`npm run execution:resume-check`

## 阻塞与风险

### 阻塞

- P2 UI 切片需要启动本任务构建的本地应用；externalAuthorization=appdata_backup_only 不包含进程启动

### 禁止盲目执行

- 未扩展授权前不启动/停止应用、不发送游戏输入、不改写 AppData、不 commit/push

## Git 现场

- 分支：`main`
- observed HEAD：`8747ff9a708217ae5784b354140b07fdcc1a869b`
- verified HEAD：`3eef34f8c4b115c94e2c3cd6adb93cf329a60ef9`
- origin/main：`3eef34f8c4b115c94e2c3cd6adb93cf329a60ef9`
- working tree fingerprint：`sha256:32780dae7809287ec3756cf5605a9a7d7b7e00785accff314b5fc21f7b97667f`
- 最新 checkpoint：`CP-0022` (state_snapshot)
- checkpoint safeToResume：`true`
- checkpoint safeToRunLiveInput：`false`

### 当前非 ignored 改动

- `docs/execution/STATUS.md`
- `docs/execution/checkpoints/CP-0022-p3-s2-verified.json`
- `docs/execution/events.jsonl`
- `docs/execution/evidence.jsonl`
- `docs/execution/state.json`
- `src-tauri/src/main.rs`
- `src-tauri/src/platform.rs`
- `src-tauri/src/runtime/capture_health.rs`
- `src-tauri/src/runtime/mod.rs`
- `src-tauri/src/runtime/vision_match.rs`

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
| `EVD-0090` | `test` | `passed` | `stale` | P3-S1 health-verified capture providers and black/stale frame gates: full core regression green<br>证据 HEAD 与当前 observed HEAD 不同 |
| `EVD-0091` | `build` | `passed` | `stale` | P3-S1 after capture health changes: Vite production build green<br>证据 HEAD 与当前 observed HEAD 不同 |
| `EVD-0092` | `test` | `passed` | `stale` | P3-S1 rebind on HEAD: capture health core regression<br>证据 HEAD 与当前 observed HEAD 不同 |
| `EVD-0093` | `build` | `passed` | `stale` | P3-S1 rebind on HEAD: Vite build<br>证据 HEAD 与当前 observed HEAD 不同 |
| `EVD-0094` | `test` | `failed` | `not_passed` | P3-S2 ROI-budgeted template matching: cargo fmt/check/test/clippy green with fail-closed wait_image<br>命令/观察结果不是 passed |
| `EVD-0095` | `test` | `passed` | `valid` | P3-S2 ROI-budgeted template matching: cargo fmt/check/test/clippy green with fail-closed wait_image<br>绑定当前 HEAD、工作树指纹和受信来源 |
| `EVD-0096` | `test` | `passed` | `valid` | P3-S2 after vision match budget: full core regression green<br>绑定当前 HEAD、工作树指纹和受信来源 |
| `EVD-0097` | `build` | `passed` | `valid` | P3-S2 after vision match budget: Vite production build green<br>绑定当前 HEAD、工作树指纹和受信来源 |

## 最近事件

| seq | 时间 | 类型 | 摘要 |
|---:|---|---|---|
| 261 | `2026-07-13T08:07:16Z` | `decision` | P3-S1 product commit 683cbac is landed; evidence rebound on HEAD 00f4f28 |
| 262 | `2026-07-13T08:08:12Z` | `slice_started` | 开始切片 P3-S2：ROI-required template matching with search budget and fail-closed wait_image |
| 263 | `2026-07-13T08:11:25Z` | `reconciliation` | Align ledger after P3-S2 product commit 8747ff9 (vision_match + fail-closed wait_image); no pending side-effect actions |
| 264 | `2026-07-13T08:15:11Z` | `test_run` | P3-S2 ROI-budgeted template matching: cargo fmt/check/test/clippy green with fail-closed wait_image |
| 265 | `2026-07-13T08:16:26Z` | `test_run` | P3-S2 ROI-budgeted template matching: cargo fmt/check/test/clippy green with fail-closed wait_image |
| 266 | `2026-07-13T08:17:22Z` | `test_run` | P3-S2 after vision match budget: full core regression green |
| 267 | `2026-07-13T08:17:24Z` | `test_run` | P3-S2 after vision match budget: Vite production build green |
| 268 | `2026-07-13T08:17:56Z` | `slice_state_changed` | P3-S2 verified: budgeted template match, ROI enforcement, fail-closed wait_image without template; EVD-0095/0096/0097 green |
| 269 | `2026-07-13T08:17:59Z` | `checkpoint` | 创建 CP-0022：P3-S2 acceptance criteria passed with trusted profile evidence before product commit |
| 270 | `2026-07-13T08:17:59Z` | `decision` | P3-S2 closed on worktree evidence; product commit next so verifiedHead can advance after rebind if needed |

## 异常恢复

1. 阅读 `AGENTS.md`、本页和 `docs/execution/PROTOCOL.md`。
2. 运行 `npm run execution:resume-check`；退出码非 0 时不要执行任何副作用动作。
3. 再运行 `npm run audit:execution-state` 和 `git status --short --ignored`，比较 observed/verified/upstream HEAD 和 dirty 文件。
4. 重新核验 AppData、应用版本、进程、窗口身份和证据文件；过期 PID 只能作为线索。
5. 若存在 `running` 或 `unknown_after_interruption` 动作，先 reconciliation，禁止直接重试。
6. 追加 `reconciliation` 事件后，从“唯一下一动作”继续。

详细规则见 [PROTOCOL.md](PROTOCOL.md)，长期产品方案见 [project-audit-and-master-plan.md](../project-audit-and-master-plan.md)。
