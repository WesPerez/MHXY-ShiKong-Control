# 下一 Agent 长期 Goal 提示词

> 生成时间：2026-07-14
> 基于会话 019f5a42-5766-7be3-9861-f979ab529d26 之后的真实现场重写
> 权威现场以开工时 docs/execution/STATUS.md、源码、Git、测试和实际运行结果为准；本文件是交接提示，不是更高权威

以下正文可直接放入 Codex Goal：

```text
使用 $orchestrate-long-projects 恢复并持续完成这个长期项目，直到达到主方案 P0-P9 的最终交付门槛，或只剩无法由 Agent 自主解决的安全阻塞。

repo=E:\Project\Common\mhxy-shikong-control
workflow=resume
userAuthorization=repo_write
externalAuthorization=appdata_backup_and_migrate_verified,local_preview_server_owned_process_only,local_app_run_owned_process_only,ui_read_only_test,game_client_launch_owned_process_only,game_window_read_only,background_hwnd_input_verified_targets_only,local_config_write_project_scope_only,dependency_downloads,git_commit,git_push_current_tracked_branch_no_force

长期目标：交付一个真正可用、可安装、用户操作量低、功能一目了然的 Windows 多窗口后台任务编排器，用于对多个“梦幻西游：时空”窗口执行互不干扰的后台自动化。用户可以低成本创建和组合键盘、鼠标、OCR、识图、条件、循环、恢复和任务跳转步骤；共享目标素材；为每个游戏窗口配置独立队列；同一 HWND 严格串行，不同 HWND 并行；所有真实输入只定向到经过身份验证的目标 HWND，不抢焦点、不移动真实鼠标、不污染用户前台键盘。最终必须通过真实工作区迁移与重启、当前应用、至少两个真实游戏窗口、5-10 个真实任务、失败矩阵、打包、commit 和 push 验收。

上述授权在本 Goal 整个 P0-P9 周期持续有效，不需要每个切片重复询问用户。普通实现选择、代码组织、测试补充、依赖现有惯例的 UI 决策、本任务拥有的本地进程管理、应用启动、低风险调试、纵向切片 commit，由你自主判断并继续。不要因为工作量大、测试慢、需要多轮修复、已有 dirty worktree、需要启动应用、需要 elevated 控制器、或需要绑定模板而停下询问。

================================================================
0. 当前真实现场快照（开工必须重新核验，不得当永久真理）
================================================================

生成此 Goal 时的现场快照（2026-07-14）：

- 分支：main
- observed HEAD：3e6066660d7774f94b5cf4f1ed21631bb7d38701
  提交说明：Record P4-S2 game window identity with privilege blocker
- verified HEAD：162a96a9b9e65cf55a131a22b6c7870de70cec5d
- origin/main：3eef34f8c4b115c94e2c3cd6adb93cf329a60ef9
- 本地 main 相对 origin/main：ahead 约 33，且有大量未提交改动；最终 release 前才能 push
- 当前阶段：P4 in_progress
- 当前切片：P4-S5 - Home-vitality bounded live queue under elevated controller
- 切片状态：in_progress；动作状态：none
- safeToResume=true；safeToRunLiveInput=false
- 本轮是否发送真实游戏输入：false
- 最新 checkpoint：CP-0051
- 最近有效进度线索（可能因 dirty 指纹而 stale，必须重验）：
  - P0、P1、P2、P3 阶段状态为 verified
  - P4-S1 离线家园活力接线已提交（162a96a）
  - P4-S2 记录过游戏窗口身份与 privilege blocker（3e60666）
  - 事件账本显示 P4-S3 零输入 live_preflight 与 P4-S4 离线人工确认/就绪合同已做过，但相关 evidence 相对当前 dirty 指纹可能 stale
  - P4-S5 已 begin，验收条件仍 pending：
    - P4-S5-C1：bounded home-vitality input path executes with inputSent evidence only after manual confirmation and elevated window gates
    - P4-S5-C2：game postcondition observed for vitality change without claiming broader multi-task completion
- 已知阻塞线索：Game HWND 可能存在，但控制器 privilege 可能不足以做 gated input
- 大量 dirty / untracked 文件已存在（产品代码、strict capture、manual confirmation、execution 台账、CP-0038 至 CP-0051 等），必须先对账再推进，禁止当作“干净基线”或“可丢弃临时文件”

历史任务：
- 019f4aba-edef-76e2-9b65-0dac9a270872：审计与主方案，不是当前实现权威
- 019f5a42-5766-7be3-9861-f979ab529d26：推进到 P3 verified 与 P4 前期；其聊天摘要不得覆盖当前 STATUS/源码/Git

docs/current-progress-and-handoff.md 在生成时仍停在旧的 P2-S2 叙述，已过时。冲突时以 STATUS、state、源码、Git、测试、实际运行为准。

================================================================
1. 授权的准确含义
================================================================

- repo_write：允许修改当前仓库代码、测试、文档和执行台账。
- appdata_backup_and_migrate_verified：只允许在项目专用 verifier、action intent、机器级 lease、源/目标身份、不可覆盖备份、hash 和后置验证全部通过时，备份和迁移该应用自己的 AppData workspace。
- local_preview_server_owned_process_only：允许启动和停止由本任务明确启动、PID/命令/cwd 可证明归属的 localhost 预览服务。
- local_app_run_owned_process_only：允许构建、启动、重启和停止由本任务明确启动的当前项目应用；不得停止用户已有或归属不明实例。需要 elevated 控制器时，只提升/重启本任务拥有的控制器实例。
- ui_read_only_test：允许 Playwright、应用窗口截图、可访问性树和普通只读 UI 操作；优先不抢前台。
- game_client_launch_owned_process_only：允许在合法客户端已安装且无需输入账号、密码或验证码时启动游戏客户端；只停止本任务明确启动且不再需要的实例。
- game_window_read_only：允许枚举和只读观察游戏 PID、HWND、标题、尺寸、权限、截图和后置状态。
- background_hwnd_input_verified_targets_only：允许对通过当前身份门禁的明确 HWND 执行项目范围内、最小、可恢复的后台定向输入。
- local_config_write_project_scope_only：允许写入项目自己的本地配置和测试数据，不包含其它应用或系统全局配置。
- dependency_downloads：允许按现有 package/Cargo/toolchain 方式获取项目依赖，不安装无关软件。
- git_commit：允许按纵向切片创建本地 commit。
- git_push_current_tracked_branch_no_force：最终门禁通过后允许 push 当前跟踪分支，禁止 force push。

================================================================
2. 权威顺序
================================================================

当前源码、Git、测试、构建、实际运行和外部现场
> 绑定当前源码/工作树指纹的证据
> state/events/evidence/checkpoint
> STATUS.md
> 主方案 docs/project-audit-and-master-plan.md
> docs/current-progress-and-handoff.md 与历史线程/模型记忆

STATUS.md 是 scripts/execution_progress.py 生成文件，禁止手工编辑。
docs/execution/ 实时台账只允许主代理通过 execution_progress.py 写入。
events.jsonl 与 evidence.jsonl 只追加，不改旧行。

================================================================
3. 开工读取与恢复命令（强制）
================================================================

先完整读取：

1. $orchestrate-long-projects 的 SKILL.md 及它指向的恢复/安全/台账规则。
2. E:\Project\Common\mhxy-shikong-control\AGENTS.md。
3. docs/execution/STATUS.md。
4. docs/execution/PROTOCOL.md 中与恢复、安全、AppData、真实输入、lease、action-start/finish、checkpoint 有关的规则。
5. docs/project-audit-and-master-plan.md 的当前阶段章节：至少 14.5-14.10、15.1-15.5、16、17、21；需要全局方案时再读全文。
6. 仅在需要理解动机时参考 docs/current-progress-and-handoff.md 和历史任务；不得用其覆盖当前证据。

在同一个 PowerShell 进程设置：

$env:PYTHONDONTWRITEBYTECODE='1'
$env:GIT_OPTIONAL_LOCKS='0'

依次执行并保留输出：

npm run execution:resume-check
npm run audit:execution-state
git --no-optional-locks status --short --ignored
git --no-optional-locks rev-parse HEAD
git --no-optional-locks rev-parse origin/main
git --no-optional-locks log -15 --oneline
npm run execution:preflight-p0

然后只读枚举当前控制器与游戏现场（不输入）：

- 所有 mhxy-shikong-control.exe / MyGame_x64r.exe 的 PID、启动时间、命令行、exe 路径、父进程、是否 elevated
- 每个相关 HWND 的 title、client size、owner PID
- 当前前台 HWND 与鼠标坐标基线

审计允许继续后，只读主方案当前 phase/slice 章节。异常、未决动作、unknown_after_interruption 或账本冲突时，先 reconciliation，再深入 state/events/evidence/checkpoint。resume-check 非 0 时禁止副作用动作。

P0 备份门：先验证 EVD-0029、EVD-0030 和相关 checkpoint；源 hash 未变化且两个可信备份仍在时，直接承认备份门已完成。禁止因 preflight 通用 nextAction 重复覆盖备份。真实迁移和重启持久化仍属后续独立验收。

================================================================
4. 当前第一优先级：先收口 dirty 现场，再做 P4-S5 有界 live
================================================================

不要从 P0/P1/P2-S2 重新开始。
不要把“代码里有家园活力”写成“真实任务完成”。
不要在未 elevated、未 manual-confirm、未 match-only precheck 时发送游戏输入。

### 4.1 现场对账与证据 rebind

1. 对照 STATUS/state/events/evidence 与 git status，列出：
   - 已 verified 的 phase/slice
   - 已 begin 但未完成的 slice
   - dirty 改动分别属于哪些 slice/能力
   - 哪些 evidence 因 HEAD/工作树指纹漂移而 stale
2. 对已实现且可验证的离线能力，按纵向切片最小单位 rebind：
   - 相关 core/unit/audit 测试
   - production build（至少 Vite；涉及 Rust/Tauri 时包含对应门）
   - 若切片要求 app_runtime/window_identity，则启动本任务拥有的当前构建并做只读窗口身份
3. 用 docs/execution/profiles.json 的固定 profile 生成证据，禁止自由文本伪造 passed。
4. 每完成一个已验证闭环：更新 STATUS/checkpoint，再独立 commit。
5. 对无法证明完成的事项保持 pending，不得“顺手标 verified”。

### 4.2 进程与权限现实

- 用户已有游戏进程必须复用；cleanupAllowed=false 的游戏绝不能 stop/kill。
- 当前验证通过的游戏窗口少于两个时，才补启动到恰好两个；已有两个或更多就不再为数量重复启动。
- 若游戏需要账号、密码、验证码、人工登录或不可逆业务选择：不代填、不绕过；保留现场，继续所有离线工作，最后一次性报告阻塞。
- 真实输入前控制器与目标游戏窗口 privilege 必须兼容。若游戏 elevated 而控制器非 elevated，只能：
  1) 以本任务拥有方式重启/启动 elevated 控制器；
  2) 重新做 window_identity 与 live_preflight；
  3) 仍 fail closed 时继续离线工作并报告阻塞。
- 禁止停止用户游戏、Codex、IDE、浏览器、共享 Node/Cargo 服务或归属不明进程。
- 只停止本任务明确启动且确认不再需要的 preview/app/probe 进程。

### 4.3 当前唯一切片目标：P4-S5

在 elevated 控制器中完成“家园活力”有界真实队列，而不是一次做完 P4 全部愿景。

强制顺序：

1. rebind 当前 dirty 中与 P4 离线/strict capture/manual confirmation 相关的测试、审计、构建。
2. 启动/确认当前工作树对应的控制器实例，记录 exe 路径、PID、elevated、窗口身份。
3. 只读验证至少一个真实游戏 HWND 身份：
   PID + HWND + title + process path + client size + privilege + 启动实例联合身份。
4. 做零输入 strict capture live_preflight；黑帧/旧帧/桌面 fallback/capture_unreliable 时零输入。
5. 绑定 jiayuan/家园相关模板与 ROI（项目现有素材与蓝图源优先，统一 home-vitality-core 真源）。
6. 对 entry.home 与 button.home_clean（或当前蓝图等价目标）做 manual confirmation 记录；未经人工确认不得 live click。
7. 先 match-only / wait_image / ocr_assert 预检，确认页面与按钮可见。
8. 仅在全部门禁通过后，发送最小、可观察、可恢复的后台点击/热键。
9. 观察并记录游戏后置状态：活力文本变化或等价安全结果；保存前后截图、OCR/模板、步骤轨迹、时间戳、窗口身份。
10. 同步记录前台 HWND 与鼠标坐标前后对比；证明未抢焦点、未移动真实鼠标。
11. 对照窗口若存在：证明其未收到误输入。
12. 用 live_input / live_outcome 类证据关闭 P4-S5-C1/C2；更新 checkpoint；独立 commit。

家园活力完整任务语义以主方案 15.1 为准，目标形态包括但不限于：

detect_page 主界面
-> snapshot
-> hotkey ALT+N（或当前版本已验证入口）
-> wait_image 家园入口
-> ocr_assert “家园”
-> image_click 家园入口
-> detect_page 家园页
-> ocr_assert 活力文本
-> wait_image 打理按钮
-> image_click 打理按钮（人工确认目标）
-> delay
-> ocr_assert 预期变化
-> snapshot
-> ESC 返回
-> detect_page 主界面

失败恢复块：ESC -> wait -> 检测主界面 -> 保存失败现场 -> stop。
禁止购买、交易、付款、删号、送物、不可逆操作。

P4 完整阶段完成前，还需要补齐主方案 14.5 要求中尚未证明的部分：
- 任务从 UI 创建或从蓝图实例化
- 素材通过 Ctrl+V/ROI 绑定
- 每步前后证据
- 完整任务成功
- 失败场景可恢复
- 应用重启后任务和素材保留（若仍缺，可在 P4 收口或与 P5 边界清晰衔接，但不得谎称已完成）

================================================================
5. 固定执行循环
================================================================

一次只推进一个用户可观察的纵向切片：

确认当前验收条件
-> 读取真实调用链和已有模式
-> 实现最小但完整的代码
-> 局部测试
-> 全量相关测试
-> production build
-> 启动当前构建
-> 实际 UI/API 操作
-> 必要的最小真实游戏动作
-> 后置状态和前台不受影响验证
-> evidence
-> STATUS/checkpoint
-> slice commit

规则：

- 同一时间只允许一个产品纵向切片 in_progress。
- 每完成一个主要视图或执行能力就立即启动并实际验证，不允许连续数小时只写代码。
- 每 30-60 秒给简短进度；每 10-20 分钟或每个闭环说明：完成、当前、下一步、风险、是否启动当前版本、是否执行真实输入、证据位置。
- 禁止用单一百分比表示完成。必须分开报告：
  代码表面能力 / 自动测试 / 当前提交构建 / 当前提交应用启动 / 真实 HWND 输入 / 游戏后置状态 / 前台无干扰 / 双窗口隔离 / 重启持久化 / 失败恢复
- preflight_only、input_not_allowed、静态测试通过、PostMessageW 返回成功，都不能单独证明游戏功能完成。

可主动使用子代理并行做源码搜索、日志、测试矩阵、截图分析、方案审查；边界必须窄且默认只读。共享执行台账只由主代理写；主代理必须复核子代理结论。最终前等待或中断所有子代理。

================================================================
6. 真实后台 HWND 输入门禁（每次输入前重新检查）
================================================================

每次真实输入前必须重新通过：

1. 当前用户授权仍覆盖该动作。
2. pre-live checkpoint（state_snapshot）。
3. action intent 与未冲突的机器级 lease。
4. PID + HWND + title + process path + client size + privilege + 启动实例联合身份。
5. HWND 仍属于同一 PID，防止句柄复用。
6. 严格目标窗口捕获 health verified；黑帧、旧帧、桌面 fallback 或 capture_unreliable 时零输入。
7. 任务和步骤 readiness 全部通过；readiness 必须来自 runner 真源，不能只靠前端文案。
8. 目标已经 manual confirmation（至少首次 live 点击目标）。
9. 动作最小、可观察、可恢复；非交易、非付款、非不可逆。
10. 输入路径只能是明确 HWND 的后台定向路径（项目允许的 PostMessage 等），禁止任何兼容回退。

明确禁止：

- SendInput
- SetCursorPos
- mouse_event / keybd_event
- SetForegroundWindow / 抢焦点 / 激活窗口作为输入手段
- 广播输入
- 依赖当前前台窗口
- 移动真实鼠标作为定位/点击手段
- 在权限不足、身份漂移、目标消失、捕获不可靠、OCR/模板不确定时强行输入

输入前后必须保留：

- 当前应用 commit/fingerprint/exe
- 目标窗口身份
- 前台 HWND
- 鼠标坐标
- 截图 / OCR / 模板匹配
- 步骤轨迹与时间戳
- 游戏后置状态
- 对照窗口未受影响证据（若存在对照窗口）

================================================================
7. 应用、预览、游戏实例规则
================================================================

开始真实运行前先枚举当前控制器和游戏的 PID、启动时间、命令行、exe 路径、父进程、HWND、标题、client size、权限。

- 已存在且身份验证通过的应用或游戏实例必须复用，不重复启动。
- 当前验证通过的游戏窗口 < 2 时，才补启动到恰好 2 个。
- 本任务启动的每个进程登记：PID、完整命令、cwd、启动时间、父进程、所有权证据、cleanupAllowed。
- 启动失败先查现有实例、端口、日志、依赖和配置，不通过反复启动制造重复实例。
- localhost preview 与 Tauri/app 进程都只管理本任务拥有者。
- ignored 产物（reports/、captures/、target*/、dist/、node_modules/、.codex-window-*.png 等）默认保留；不能证明归属就不得清理。

================================================================
8. AppData 与持久化
================================================================

P0 两个真实 v6 备份已形成可信证据，禁止重复覆盖。

开始真实迁移前必须：

1. 建立 pre-live checkpoint。
2. 登记 action intent 和机器级 lease。
3. 重新确认应用 AppData 目录、workspace.json、workspace.json.bak、schema、size、mtime、SHA-256。
4. 核验 EVD-0029/EVD-0030 两个备份存在、hash 匹配且未被覆盖。
5. 若需要额外备份，只能创建新的不可覆盖目标；目标已存在就停止该动作。
6. 使用项目迁移器和原子临时文件/replace；不手工拼 JSON；不提交真实 workspace。
7. 验证迁移幂等、future schema 保护、失败恢复、应用关闭重开和第二次重开。
8. 动作结果未知时先 reconciliation，禁止重放。

P5 是否上 SQLite，必须由当前数据规模和调用链证明，不为使用技术而使用。至少完成：

- 原子保存 / SaveCoordinator 或等价物
- 素材文件化与 hash 去重
- 备份与恢复
- future schema 只读保护
- 导入导出一致性
- 100 次快速编辑不丢最后 revision（或等价压测）
- 保存中关闭可 flush
- 磁盘满/权限拒绝明确失败
- 游戏重启后 profile 可重新绑定，但必须重新确认身份

================================================================
9. UI 与产品质量
================================================================

- 这是高频 Windows 操作工作台，界面应安静、紧凑、可扫描、低误触；不做营销页或装饰性卡片堆叠。
- 默认窗口和最小窗口下，窗口列表、队列、任务、步骤、属性、目标、运行状态和失败报告都必须可达。
- 用户高频流程应短：粘贴图片、ROI、采点、绑定目标、添加步骤、分配窗口、运行、定位失败。
- 空、加载、失败、权限不足、目标消失、部分就绪、运行、暂停、取消、完成状态都要完整。
- 每次视觉修改都在 1460x880、1280x720、1120x720、920x680、820x720 实测。
- 桌面 Tauri 优先用不抢前台的只读窗口捕获复核。
- 不为美观重写已验证业务逻辑；先保持行为，再改善信息架构和交互效率。
- readiness、失败原因、阻塞原因必须可定位到具体窗口/步骤/门禁。

================================================================
10. P4 之后严格顺序与完成要求
================================================================

完成 P4 后，严格按主方案推进，不跳过真实纵向闭环，不用“代码存在”代替“用户可用”。

### P5 持久化和素材文件化
- 真实持久化设计落地
- 素材文件化
- 迁移、原子保存、备份、future schema
- 应用重启与第二次重启验证
- 不提交真实 AppData/凭据/未脱敏截图

### P6 第二至第五个真实任务
按顺序逐个完整纵向验收，不得批量编码后统一测试：
1. 福利签到
2. 背包整理
3. 组队准备（只安全观察，不自动申请/创建未知队伍）
4. 摊位搜索（只搜索不购买）

每个任务至少 10 步，覆盖并累计证明：
hotkey、文本、左键、右键、双击、image_click、OCR、条件、循环、恢复、任务跳转。
每个任务独立 commit。

### P7 双窗口并行和队列控制
必须实际证明：
- A/B 两个窗口身份均通过门禁
- A/B 绑定不同任务和不同队列
- 同一 HWND 步骤严格串行，不同 HWND 可并行
- 暂停/继续/取消只影响指定窗口
- A 超时、关闭、OCR 失败或图像不匹配时，不向 B 误输入，反之亦然
- 真实前台 HWND 测试前后不变，鼠标坐标不变，用户前台键盘不串入游戏
- 事件时间轴：跨窗口可重叠，同窗口不重叠
- 重启后只恢复队列配置，不自动恢复未完成输入会话

### P8 回归任务与发布门
- 扩展到 5-10 个可重复真实任务
- 未真实完成的任务必须明确标注 blueprint / needs_capture / unsupported
- 完成失败矩阵：缺素材、缺坐标、OCR 不匹配、图片找不到、权限不足、窗口消失、捕获不可靠、任务中断、重启恢复
- 每个任务有成功/失败 fixture、当前游戏版本素材 profile、证据包索引

### P9 清理、打包、提交、推送
只在前述行为有测试保护后清理：
- 删除确认无引用包装/断链 UI/legacy 分支
- 合并重复 readiness 文案和映射
- 合理拆分单体文件
- 补 LICENSE、第三方 NOTICE、素材来源策略
- 统一 validate
- Node、Python、Rust、Playwright、Tauri release、安装包 smoke
- tracked clean
- 最终交付报告
- release gate 全过后才 push；push 前 fetch 并核对远端 ref；禁止 force push
- 除非主方案明确要求，不自动创建 PR、tag 或 release

================================================================
11. 最终交付门槛（主方案第 21 节，缺一不可）
================================================================

只有同时满足以下条件，才能把项目标为 completed：

1. 当前运行应用能证明来自最终 commit。
2. 真实工作区迁移和重启保留通过。
3. 默认和最小窗口尺寸下核心功能全部可达。
4. 至少 5 个真实任务完整通过，每个至少 10 步。
5. hotkey、文本、左键、右键、双击、image_click、OCR、条件、循环、恢复和任务跳转均有真实证据。
6. 两个窗口不同队列并行通过。
7. 同一 HWND 无并发交错。
8. 用户前台 HWND 不被切换。
9. 真实鼠标不被移动。
10. 用户前台键盘输入不丢失、不串入游戏。
11. 捕获不可靠时任务阻塞且零输入。
12. 缺素材、缺坐标、缺 OCR、窗口丢失、权限不足均在运行前阻断。
13. 暂停、继续、停止按窗口生效。
14. 失败报告包含窗口身份、步骤轨迹、前后截图、OCR/识图和失败包。
15. Node、Python、Rust、UI E2E、打包 smoke 全部通过。
16. tracked 工作树干净。
17. 稳定改动已提交并推送。
18. 最终报告列出文件、测试、进程、产物、清理和 commit hash。

技术成功不等于平台许可。最终报告必须披露游戏条款和反作弊风险，不承诺账号绝对安全。

================================================================
12. 测试、证据、Git
================================================================

- 使用 docs/execution/profiles.json 固定 profile 生成可信 passed evidence。
- 常用入口包括但不限于：
  npm run execution:resume-check
  npm run audit:execution-state
  npm run audit:all
  npm run test:all-core
  npm run test:home-vitality
  npm run test:manual-confirmation
  npm run audit:home-vitality-offline
  npm run audit:strict-capture-preflight
  npm run test:ui-viewports
  npm run build
  npm run verify:window-identity
  npm run tauri:build
- 每个完成且验证通过的纵向切片独立 commit。
- 提交前核对 diff、测试、STATUS、evidence、checkpoint。
- 不提交真实 AppData、凭据、未脱敏截图、大型 target/dist、临时报告或归属不明产物。
- 未提交状态只能建 state_snapshot，不能冒充 git_checkpoint。
- commit、push、handoff、长时间暂停和真实输入前必须创建 checkpoint。
- 远端非快进或冲突时不覆盖他人提交；保留本地 commit，继续不受影响工作，最后准确报告 blocker。

================================================================
13. 无需询问与 fail-closed
================================================================

不要为低风险实现选择反复询问用户。

只有以下情况禁止冒进：
- 无法确认 AppData 源/目标/备份身份
- 无法确认游戏 PID/HWND 身份
- 需要账号密码、验证码、人工登录或付款
- 动作不可逆或超出项目目标
- 需要停止、删除或覆盖归属不明资源
- 需要 force push 或覆盖远端他人提交
- 台账损坏、连续性审计失败或存在 unknown_after_interruption 动作
- 当前证据证明主方案与用户核心目标实质冲突

遇到这些情况时：
- 不执行风险动作
- 不反复追问
- 继续完成所有不受影响的代码、测试、文档、mock、构建和离线验证
- 在阶段报告/最终报告中一次性列出准确阻塞、已完成部分和用户需要做的最小动作

================================================================
14. 副作用动作与清理
================================================================

以下动作执行前必须 action-start 写 intent，执行后 action-finish：
- 向游戏窗口发送后台输入
- 启动或停止长期进程
- 写入、迁移、覆盖 AppData
- commit、push、发布或修改外部状态
- 删除、移动、覆盖文件或清理产物
- 修改配置、环境变量或凭据

异常中断后，未完成动作必须视为 unknown_after_interruption，先 reconciliation，禁止盲目重试。

清理规则：
- 只能清理有直接归属证据且确认不再需要的本任务产物/进程
- 名称相似、时间接近、扩展名匹配都不是充分证据
- 不能证明属于本任务的，一律保留

================================================================
15. 每轮 live 证据包最低字段
================================================================

每次真实输入或完整任务至少包含：
- run/slice/criterion id
- git HEAD 与 working tree fingerprint
- app exe 路径、PID、是否 elevated、窗口身份
- game PID/HWND/title/path/client size/privilege
- capture health 结果
- readiness 结果
- manual confirmation 记录
- 输入前/后截图
- OCR/模板匹配结果
- 步骤轨迹
- inputSent 真值
- 游戏后置状态
- 前台 HWND 前后对比
- 鼠标坐标前后对比
- 对照窗口状态（如有）
- 失败时 failure bundle 路径

================================================================
16. 收尾与最终报告
================================================================

最终前：
- 等待或中断所有子代理
- 运行完整授权范围内验证
- 核对 git --no-optional-locks status --short --ignored
- 核对文件、下载、配置、环境变量、凭据、进程、服务、页签、AppData、游戏状态和清理归属
- 只清理由本任务直接创建且已证明不再需要的目标

只有同时满足主方案第 21 节全部最终交付门槛，才把项目标为 completed。

最终报告必须给出：
- 实现内容
- 用户操作流程
- 文件改动
- 全部测试
- 当前应用和两个游戏窗口的真实运行证据
- 失败矩阵
- 迁移和重启
- 前台不受影响
- 生成产物
- 保留/清理
- commit hash
- 远端分支和 push 结果
- 已知限制与合规风险
- 若未完成：准确阻塞、已完成部分、用户最小动作

现在立刻开始：先做恢复读取与 resume-check，再按第 4 节收口 dirty 现场并推进 P4-S5；不要等待额外确认。
```
