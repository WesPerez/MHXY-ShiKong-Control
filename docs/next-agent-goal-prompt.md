# 下一 Agent 长期 Goal 提示词

以下正文可直接放入 Codex Goal：

```text
使用 $orchestrate-long-projects 恢复并持续完成这个长期项目，直到达到主方案 P0-P9 的最终交付门槛，或只剩无法由 Agent 自主解决的安全阻塞。

repo=E:\Project\Common\mhxy-shikong-control
workflow=resume
userAuthorization=repo_write
externalAuthorization=appdata_backup_and_migrate_verified,local_preview_server_owned_process_only,local_app_run_owned_process_only,ui_read_only_test,game_client_launch_owned_process_only,game_window_read_only,background_hwnd_input_verified_targets_only,local_config_write_project_scope_only,dependency_downloads,git_commit,git_push_current_tracked_branch_no_force

长期目标：交付一个真正可用、可安装、用户操作量低、功能一目了然的 Windows 多窗口后台任务编排器。用户可以低成本创建和组合键盘、鼠标、OCR、识图、条件、循环、恢复和任务跳转步骤；共享目标素材；为每个游戏窗口配置独立队列；同一 HWND 严格串行，不同 HWND 并行；所有真实输入只定向到经过身份验证的目标 HWND，不抢焦点、不移动真实鼠标、不污染用户前台键盘。最终必须通过真实工作区迁移与重启、当前应用、至少两个真实游戏窗口、5-10 个真实任务、失败矩阵、打包、commit 和 push 验收。

上述授权在本 Goal 整个 P0-P9 周期持续有效，不需要每个切片重复询问用户。普通实现选择、代码组织、测试补充、依赖于现有惯例的 UI 决策、本任务拥有的本地进程管理、应用启动和低风险调试，由你自主判断并继续。不要因为工作量大、测试慢、需要多轮修复、已有 dirty worktree 或需要启动应用而停下询问。

授权的准确含义：

- repo_write：允许修改当前仓库代码、测试、文档和执行台账。
- appdata_backup_and_migrate_verified：只允许在项目专用 verifier、action intent、机器级 lease、源/目标身份、不可覆盖备份、hash 和后置验证全部通过时，备份和迁移该应用自己的 AppData workspace。
- local_preview_server_owned_process_only：允许启动和停止由本任务明确启动、PID/命令/cwd 可证明归属的 localhost 预览服务。
- local_app_run_owned_process_only：允许构建、启动、重启和停止由本任务明确启动的当前项目应用；不得停止用户已有或归属不明实例。
- ui_read_only_test：允许 Playwright、应用窗口截图、可访问性树和普通只读 UI 操作。
- game_client_launch_owned_process_only：允许在合法客户端已安装且无需输入账号、密码或验证码时启动游戏客户端；只停止本任务明确启动且不再需要的实例。
- game_window_read_only：允许枚举和只读观察游戏 PID、HWND、标题、尺寸、权限、截图和后置状态。
- background_hwnd_input_verified_targets_only：允许对通过当前身份门禁的明确 HWND 执行项目范围内、最小、可恢复的后台定向输入。
- local_config_write_project_scope_only：允许写入项目自己的本地配置和测试数据，不包含其它应用或系统全局配置。
- dependency_downloads：允许按现有 package/Cargo/toolchain 方式获取项目依赖，不安装无关软件。
- git_commit：允许按纵向切片创建本地 commit。
- git_push_current_tracked_branch_no_force：最终门禁通过后允许 push 当前跟踪分支，禁止 force push。

一、权威顺序和开工读取

当前源码、Git、测试、构建、实际运行和外部现场 > 绑定当前源码指纹的证据 > state/events/evidence/checkpoint > STATUS > 主方案 > 历史线程和模型记忆。

先完整读取：

1. $orchestrate-long-projects 的 SKILL.md。
2. E:\Project\Common\mhxy-shikong-control\AGENTS.md。
3. docs/execution/STATUS.md。
4. docs/current-progress-and-handoff.md。
5. docs/execution/PROTOCOL.md 中与恢复、安全、AppData、真实输入和 P0 有关的规则。

在同一个 PowerShell 进程设置：

$env:PYTHONDONTWRITEBYTECODE='1'
$env:GIT_OPTIONAL_LOCKS='0'

依次执行：

npm run execution:resume-check
npm run audit:execution-state
git --no-optional-locks status --short --ignored
git rev-parse HEAD
git rev-parse origin/main
npm run execution:preflight-p0

审计允许继续后，只读主方案当前 phase/slice 章节。异常、未决动作或账本冲突时才深入读取 state、events、evidence 和 checkpoint。历史任务 019f4aba-edef-76e2-9b65-0dac9a270872 只用于理解动机和旧审计，不能覆盖当前证据。

当前预期停点是 P2/P2-S2。先实际执行五视口 Playwright，不要从头重复 P0/P1，也不要因 preflight 的通用 nextAction 重复创建 P0 备份。先验证 EVD-0029、EVD-0030 和 CP-0005；源 hash 未变化且两个可信备份仍在时，直接承认备份门已完成。迁移和重启持久化仍需后续独立验证。

二、固定执行循环

一次只推进一个用户可观察的纵向切片，固定循环为：

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

每完成一个主要视图或一个执行能力就立即启动并实际验证，不允许连续数小时只写代码。每 30-60 秒给简短进度，每 10-20 分钟或每个闭环说明：完成、当前、下一步、风险、是否启动当前版本、是否执行真实输入、证据位置。

可以主动使用子代理并行做源码搜索、日志、测试矩阵、截图分析和方案审查，但边界必须窄且默认只读。共享执行台账只由主代理写；主代理必须复核子代理结论。最终前等待或中断所有子代理。

三、当前第一动作：P2-S2

1. 核对 Playwright 配置、10 个测试和五个视口仍与当前工作树一致。
2. 登记本任务 localhost preview 的 action intent/进程归属，启动预览。
3. 运行 npm run test:ui-viewports。
4. 检查截图和 viewport metrics：页面级横向滚动、任务/步骤列表可达、检查器 tabs 鼠标/键盘、补全定位、失败步骤定位、文本溢出、遮挡、焦点顺序和动态布局跳动。
5. 发现问题就做最小修复，重跑 Playwright、Node、Python 和 Vite build。
6. 用当前证据完成 P2-S2-C1 至 C4，更新 STATUS/checkpoint，创建独立 commit。
7. 仅停止本任务启动的 preview PID。

随后严格按主方案推进 P3-P9，不跳过真实纵向闭环，不用“代码存在”代替“用户可用”。

四、UI 和产品质量

- 这是高频 Windows 操作工作台，界面应安静、紧凑、可扫描、低误触，不做营销页或装饰性卡片堆叠。
- 默认窗口和最小窗口下，窗口列表、队列、任务、步骤、属性、目标、运行状态和失败报告都必须可达。
- 用户高频流程应短：粘贴图片、ROI、采点、绑定目标、添加步骤、分配窗口、运行、定位失败。
- readiness 必须来自 runner 的真实门禁，不能只按文案或前端推断。
- 空、加载、失败、权限不足、目标消失、部分就绪、运行、暂停、取消和完成状态都要完整。
- 每次视觉修改都在 1460x880、1280x720、1120x720、920x680、820x720 实测；桌面 Tauri 用不抢前台的只读窗口捕获复核。
- 不为美观重写已验证的业务逻辑；先保持行为，再改善信息架构和交互效率。

五、AppData 和持久化

P0 的两个真实 v6 备份已经形成可信证据，禁止重复覆盖。开始真实迁移前必须：

1. 建立 pre-live checkpoint。
2. 登记 action intent 和机器级 lease。
3. 重新确认应用 AppData 目录、workspace.json、workspace.json.bak、schema、size、mtime 和 SHA-256。
4. 核验 EVD-0029/EVD-0030 的两个备份存在、hash 匹配且未被覆盖。
5. 若阶段需要额外备份，只能创建新的不可覆盖目标；目标存在就停止该动作。
6. 使用项目迁移器和原子临时文件/replace，不手工拼 JSON，不提交真实 workspace。
7. 验证迁移幂等、future schema 保护、失败恢复、应用关闭重开和第二次重开。
8. 动作结果未知时先对账，禁止重放。

六、应用和游戏实例

开始真实运行前先枚举当前控制器和游戏的 PID、启动时间、命令行、exe 路径、父进程、HWND、标题、client size 和权限。

- 已存在且身份验证通过的应用或游戏实例必须复用，不重复启动。
- 当前验证通过的游戏窗口少于两个时，才补启动到恰好两个；零个就启动两个，一个就再启动一个，两个或更多不再为数量重复启动。
- 如果游戏启动后需要用户账号、密码、验证码、人工登录或选择不可逆业务动作，不代填、不绕过；保留进程并继续所有离线代码、UI、mock、测试和构建工作，最后一次性报告这一真实阻塞。
- 本任务启动的每个进程登记 PID、完整命令、cwd、启动时间、父进程和所有权证据。
- 只停止本任务明确启动且确认不再需要的进程。不得停止用户已有游戏、Codex、IDE、浏览器、共享 Node/Cargo 服务或归属不明进程。
- 启动失败先查现有实例、端口、日志、依赖和配置，不通过反复启动制造重复实例。

七、真实后台 HWND 输入门禁

每次真实输入前必须重新通过：

1. 当前用户授权仍覆盖该动作。
2. pre-live checkpoint。
3. action intent 和未冲突的机器级 lease。
4. PID + HWND + title + process path + client size + privilege + 启动实例联合身份。
5. HWND 仍属于同一 PID，防止句柄复用。
6. 严格目标窗口捕获 health verified；黑帧、旧帧、桌面 fallback 或 capture_unreliable 时零输入。
7. 任务和步骤 readiness 全部通过。
8. 动作是最小、可观察、可恢复、非交易、非付款、非不可逆游戏动作。

只能使用明确 HWND 的后台定向路径。禁止 SendInput、SetCursorPos、抢焦点、激活窗口、广播输入、依赖当前前台窗口或移动真实鼠标作为兼容回退。权限不足、身份漂移、目标消失、捕获不可靠、OCR/模板不确定时 fail closed 且零输入。

八、至少两个游戏窗口的实测

最终必须实际证明：

- A/B 两个窗口身份均经过上述门禁。
- A/B 绑定不同任务和不同队列。
- 同一 HWND 的步骤严格串行，不同 HWND 可并行。
- 暂停、继续、取消只影响指定窗口。
- A 超时、关闭、OCR 失败或图像不匹配时，不向 B 误输入，反之亦然。
- 真实前台 HWND 在测试前后不变，鼠标坐标不变，用户前台键盘没有串入游戏。
- 每次输入前后保留当前应用、窗口身份、截图/OCR/模板结果、时间戳、步骤轨迹和游戏后置状态证据。
- 先用无破坏、可重复、可观察的最小动作，再进入完整任务。

技术成功不等于平台许可。最终报告披露游戏条款和反作弊风险，不承诺账号绝对安全。

九、P3-P9 的完成要求

- P3：完成 health-verified 捕获 provider、黑帧/旧帧检测、ROI/模板/OCR 一致性、取消/超时和预览/执行同源。
- P4：把“家园活力”做成第一个真实端到端任务，配置、执行、失败恢复和游戏后置状态全部有证据。
- P5：完成真实持久化设计、素材文件化、迁移、原子保存、备份、future schema 和重启验证。是否使用 SQLite 必须由当前数据规模和调用链决定，不为使用技术而使用。
- P6：再完成至少四个真实任务，每个至少 10 步，覆盖 hotkey、文本、左键、右键、双击、image_click、OCR、条件、循环、恢复和任务跳转。
- P7：完成双窗口并行、同 HWND 串行、暂停/继续/取消、窗口丢失和隔离验收。
- P8：扩展到 5-10 个可重复真实任务，完成缺素材、缺坐标、OCR 不匹配、图片找不到、权限不足、窗口消失、捕获不可靠、任务中断和重启恢复矩阵。
- P9：只在调用链和验证证明后清理无用代码；完成 Node、Python、Rust、Playwright、Tauri release、安装包 smoke、tracked clean、文档和最终交付报告。

十、测试、证据和提交

- 使用 docs/execution/profiles.json 中的固定 profile 生成可信 passed evidence；不要用自由文本伪造通过。
- 分开报告：源码表面能力、自动测试、当前构建、当前应用启动、真实输入、游戏后置状态、前台不受影响、双窗口隔离、重启持久化和失败恢复。
- 每个完成且验证通过的纵向切片独立 commit。提交前核对 diff、测试、STATUS、evidence 和 checkpoint。
- 不提交真实 AppData、凭据、未脱敏截图、大型 target/dist、临时报告或归属不明产物。
- 最终 release gate 全部通过后才 push。push 前 fetch 并核对远端 ref，禁止 force push。
- 优先 push 当前已跟踪分支。远端非快进或冲突时不覆盖他人提交；保留本地 commit，继续完成不受影响工作，最后准确报告 blocker。
- 除非主方案明确要求，不自动创建 PR、tag 或 release。

十一、无需询问和 fail-closed

不要为低风险实现选择反复询问用户。只有以下情况禁止冒进：无法确认 AppData 源/目标/备份身份；无法确认游戏 PID/HWND 身份；需要账号密码、验证码、人工登录或付款；动作不可逆或超出项目目标；需要停止、删除或覆盖归属不明资源；需要 force push 或覆盖远端他人提交；台账损坏、连续性审计失败或存在 unknown_after_interruption 动作；当前证据证明主方案与用户核心目标实质冲突。

遇到这些情况时不要执行风险动作，也不要反复追问。继续完成所有不受影响的代码、测试、文档、mock、构建和离线验证；在最终报告中一次性列出准确阻塞、已完成部分和用户需要做的最小动作。

十二、收尾

最终前：等待或中断所有子代理；运行完整授权范围内验证；核对 git --no-optional-locks status --short --ignored；核对文件、下载、配置、环境变量、凭据、进程、服务、页签、AppData、游戏状态和清理归属；只清理由本任务直接创建且已证明不再需要的目标。

只有同时满足主方案第 21 节全部最终交付门槛，才把项目标为 completed。最终报告必须给出：实现内容、用户操作流程、文件改动、全部测试、当前应用和两个游戏窗口的真实运行证据、失败矩阵、迁移和重启、前台不受影响、生成产物、保留/清理、commit hash、远端分支和 push 结果、已知限制与合规风险。
```
