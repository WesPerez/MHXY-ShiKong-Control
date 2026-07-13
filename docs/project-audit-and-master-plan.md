# mhxy-shikong-control 项目现状审计与实施总方案

> 文档状态：当前权威实施基线  
> 审计日期：2026-07-10  
> 仓库：`E:\Project\Common\mhxy-shikong-control`  
> 审计基线：`main` / `origin/main` / `HEAD` 均为 `3eef34f8c4b115c94e2c3cd6adb93cf329a60ef9`  
> 长期目标：用户可自定义、可编排、可组合、可持久化、可多窗口并行、且不影响用户前台鼠标键盘的 Windows 后台自动化工作台  

## 1. 文档用途

这份文档不是概念性路线图，而是后续 agent 的施工合同。后续实现必须同时满足以下要求：

1. 以当前源码、真实 AppData 工作区、运行进程、测试结果和实机证据为准，不沿用历史会话中的乐观估计。
2. 每个功能按纵向切片完成，从数据模型、UI、Tauri IPC、Rust 后端、真实窗口验证到证据包一次闭环。
3. 不允许继续以“大量静态代码和审计脚本通过”替代应用真实启动和游戏真实接管。
4. 不允许使用会移动真实鼠标、抢焦点、阻塞用户输入或向系统全局输入流注入事件的兼容方案。
5. 不允许在没有独立备份当前 schema v6 工作区前启动最新构建并触发自动迁移。
6. 不允许为了清理磁盘而删除归属不明的历史构建、截图、日志、报告或采样素材。
7. 每个阶段只能提交已完成、已验证、可回滚的稳定切片。

## 2. 执行结论

### 2.1 总体判断

项目方向没有根本性错误。以下选择应保留：

- Tauri + Rust 作为 Windows 本地能力边界。
- 只向指定 HWND 投递 `PostMessageW`，不使用 `SendInput`、`SetCursorPos` 或 `SetForegroundWindow`。
- 每步执行前复核窗口身份和权限。
- 每个窗口拥有独立任务队列，同窗口串行、不同窗口并行。
- 任务、步骤、目标素材、readiness、运行事件、失败证据等领域模型已经形成。
- 工作区采用原子替换并保留上一版本备份。
- 10 个蓝图和 10 个样例任务已覆盖大多数计划中的步骤类型。

但当前开发顺序明显失衡：项目先横向铺开了大量功能面，再补真实验收。结果是“代码表面能力很多，用户实际可用能力很少”。

### 2.2 三种完成度必须分开报告

| 维度 | 当前估计 | 依据 |
|---|---:|---|
| 代码表面功能覆盖 | 60% 至 70% | 15 类步骤、10 个蓝图、多窗口队列、readiness、失败报告、导入导出均已有代码 |
| 可交付产品完成度 | 30% 至 40% | UI 在默认窗口尺寸下存在功能不可达，持久化和 runner 有高风险缺口，多个字段仍是计划态 |
| 当前 HEAD 的真实端到端验收完成度 | 5% 至 10% | 当前运行应用是旧二进制；当前 HEAD 没有“应用 UI -> 队列 -> 游戏 -> 后置验证 -> 报告”的完整通过证据 |

不得再用单一“项目完成 70%”描述现状。后续报告必须同时给出这三个数值。

### 2.3 当前最重要的纠偏

后续开发顺序必须改成：

1. 保护现有真实数据。
2. 修复运行安全和 UI 可达性。
3. 建立一个真正可用的单任务纵向切片。
4. 用最新版应用接管一个游戏窗口完成该任务。
5. 用第二个游戏窗口做并行和隔离验收。
6. 再扩展第二、第三个任务。
7. 最后扩展到 5 至 10 个样例任务和高级编排能力。

## 3. 当前权威基线

### 3.1 Git 与源码

- 分支：`main`
- HEAD：`3eef34f8c4b115c94e2c3cd6adb93cf329a60ef9`
- `origin/main`：同一提交
- ahead/behind：`0/0`
- tracked 文件：审计开始时干净
- 无 staged、无 untracked 源码、无 stash
- 最近提交集中在 2026-07-10，说明短时间内功能面快速增长

关键文件规模：

| 文件 | 当前行数 | 风险 |
|---|---:|---|
| `src/main.js` | 8220 | 状态、DOM、runner、readiness、持久化、报告和 IPC 全部耦合 |
| `src/styles.css` | 2439 | 单屏固定布局和大量局部覆盖难以维护 |
| `src-tauri/src/main.rs` | 2837 | Tauri 命令、存储、识图、OCR、执行和测试混在同一文件 |
| `index.html` | 627 | 所有一级、二级、调试和高级控件同时展开 |

### 3.2 当前运行进程

| 进程 | PID | 启动时间 | 结论 |
|---|---:|---|---|
| `mhxy-shikong-control.exe` | 42432 | 2026-07-09 15:20:29 | 与旧 `target/release` 构建时间吻合，比当前 HEAD 早 23 个提交，不能代表当前源码 |
| `MyGame_x64r.exe` | 26056 | 2026-07-10 00:55:37 | 当前游戏窗口之一，标题为“梦幻西游：时空” |
| `MyGame_x64r.exe` | 52448 | 2026-07-10 00:55:23 | 当前游戏窗口之一，标题为“梦幻西游：时空” |

当前旧控制器监听 `127.0.0.1:47638`。该端口是应用内部单实例/唤醒监听，不是浏览器页面入口。

### 3.3 当前真实工作区

路径：

- `C:\Users\Wes\AppData\Roaming\local.mhxy.shikong.control\workspace.json`
- `C:\Users\Wes\AppData\Roaming\local.mhxy.shikong.control\workspace.json.bak`

当前主文件：

- 大小：181,948 bytes
- 最后写入：2026-07-09 14:38:19
- schema：v6
- 任务：5
- 步骤：63
- 目标：27
- 内联图片目标：15
- 窗口队列：0 个实际 assignment key
- 运行历史：0

当前备份：

- 大小：178,321 bytes
- 最后写入：2026-07-09 11:33:58
- schema：v6
- 任务：5
- 步骤：63
- 目标：27
- 内联图片目标：14

当前工作区图片 Data URL 约占文件体积 72%。这证明单 JSON 方案在任务数量增加前就已经由图片主导。

### 3.4 当前测试事实

本轮实际运行并通过：

- `test:control-flow`：19 个测试
- `test:failure-evidence`：7 个测试
- `test:step-params`：15 个测试
- `test:workspace-migration`：6 个测试
- `test:target-library`：7 个测试
- `test:live-validation`：9 个测试
- Node 测试合计：63 个
- 12 个 Python 静态审计脚本全部通过
- Rust：55 passed，2 ignored live tests
- Rust Clippy：通过，`-D warnings`

必须明确：这些结果证明核心纯函数和源码契约没有立即失败，不证明当前产品已经完成真实接管。

### 3.5 当前 live 证据

2026-07-10 的结构化 live 报告共 8 份：

- `preflight_only`：5
- `input_not_allowed`：3
- `runs`：全部为 0

2026-07-09 的旧 Rust ignored test 日志曾报告两个窗口串行和并行 `ALT+N` 测试通过，但该测试直接调用后端步骤函数，绕过了：

- 当前应用 UI
- readiness
- 窗口队列
- 前端 runner
- 暂停、继续、停止
- runHistory
- 失败报告
- 当前 schema v9
- 当前 HEAD 的二进制身份

因此旧日志只能证明“旧版本后端曾向两个窗口发送过 `ALT+N` 并观察到画面变化”，不能证明当前产品端到端可用。

## 4. 已实现且应保留的能力

### 4.1 Windows 和输入安全基础

- 窗口枚举和标题过滤。
- HWND、PID、进程名、窗口标题、客户区尺寸、权限状态的身份检查。
- 图片识别后、实际点击前再次复核身份。
- `WM_MOUSE*` 客户区坐标点击。
- `WM_KEY*` 快捷键投递。
- `WM_CHAR` 文本输入。
- release manifest 要求管理员权限。
- 静态扫描未发现 `SendInput`、`SetCursorPos`、`mouse_event`、`keybd_event`、`SetForegroundWindow`、`BringWindowToTop`。

### 4.2 任务模型基础

- 任务新增、复制、删除、排序和持久化。
- 步骤新增、复制、删除、排序、启用/禁用。
- 延迟、超时、重试、失败策略字段。
- 条件、有限循环、任务跳转和恢复入口的部分 runner 语义。
- `Step.params` 与 legacy `target/command/expect` 的兼容层。
- 目标素材共享、目标库导入导出和保守合并。
- 10 个蓝图和 10 个样例任务。
- 每个样例任务 16 至 17 步，蓝图 12 至 13 步。

### 4.3 多窗口基础

- 每个 HWND 拥有独立队列数据。
- 同一任务队列内部串行执行。
- 不同窗口可以异步执行。
- 窗口错峰和任务间隔字段。
- 队列 readiness 合并窗口缺失、身份漂移和权限问题。

### 4.4 用户操作基础

- Ctrl+V 图片绑定。
- ROI 裁剪保存为共享目标。
- 预览采点生成坐标点击步骤。
- 快捷步骤和步骤片段。
- readiness 动作坞。
- 目标验证入口。
- 失败报告、证据包和 live 报告导入。

这些能力不是无用代码。问题在于它们缺少可靠边界、合理信息架构和真实验收。

## 5. 最高优先级问题

### 5.1 P0：当前运行的应用不是当前源码

现状：

- PID 42432 是 2026-07-09 的旧构建。
- 当前 HEAD 是 2026-07-10 的 `3eef34f`。
- 旧应用启动后又产生 23 个提交。
- 最新 release 构建位于历史隔离 target 目录，未作为当前进程启动。

影响：

- 用户当前看到的界面和行为不能代表最新源码。
- 最新任务模型、readiness、失败报告、live 导入功能没有在真实 Tauri 应用中验证。
- 任何“应用已经完成某功能”的结论都必须重新验证。

处理原则：

- 不能直接启动最新构建，因为真实工作区仍为 v6，新版加载后会迁移并保存。
- 必须先执行第 15.1 节的数据保护门。

### 5.2 P0：后台执行对象存在误解和误跑风险

当前“后台执行窗口队列”实际行为：

1. 对所有已选窗口执行。
2. 如果某个窗口没有队列，会回退执行当前激活任务。
3. “准备演练”会自动选择所有窗口。
4. “选择全部”没有对应的取消全选行为。
5. 运行前没有清晰列出每个 HWND、任务清单和首个输入动作。

这可能导致用户以为只运行已配置队列，实际对多个窗口执行当前样例任务。

必须修改：

- 删除无队列时隐式回退当前任务。
- 把“当前预览窗口”和“运行批次窗口”拆成两个状态。
- 后台输入前显示执行计划确认页。
- 计划必须列出窗口身份、任务、步骤数、首个输入动作、权限和 readiness。
- 只有计划中所有阻塞项为 0 时才允许武装运行。

### 5.3 P0：UI 在默认窗口尺寸下存在功能不可达

Tauri 默认窗口：1460×880。实测结果：

- 页面整体 `height: 100dvh` 且 `overflow: hidden`。
- 顶部区域高约 357px。
- 工作区仅剩约 522px。
- 工作台定义的行高总计约 740px，外层隐藏溢出。
- 任务列表 `.workflow-list` 可用高度为 0。
- 步骤列表 `.step-list` 可用高度为 0。
- inspector 内部内容高约 5888px、宽约 542px，容器仅约 321px 宽。
- 右侧 inspector 需要横向和纵向滚动才能看到大量字段。
- 顶部工具栏在默认尺寸下仍有按钮被截断。

Tauri 最小窗口：920×680。实测结果：

- 顶部区域高约 403px。
- 工作区只剩约 276px。
- 工作台实际内容高约 1310px，外层禁止滚动。
- 任务列表和步骤列表仍为 0 高度。
- 只有宽度小于 820px 时 CSS 才恢复页面滚动，821 至 1120px 是明显断层。

这不是视觉品味问题，而是核心功能不可达问题。必须在任何真实任务开发前修复。

### 5.4 P0：预览异步竞态会错绑窗口素材

当前流程：

1. 用户切换窗口。
2. 异步截图使用旧 target 发起。
3. 用户快速切换到另一个窗口。
4. 旧请求较晚返回，覆盖全局预览。
5. `state.preview` 没有保存来源 HWND 和完整身份。
6. 用户保存 ROI 时使用当前 active window 作为来源。

结果：旧窗口截图可能被标为新窗口素材，ROI 和坐标与窗口身份错配。

必须实现：

- 每次预览请求增加单调递增 request id。
- 返回时校验 request id、HWND 和 expected identity。
- `PreviewState` 必须保存 `hwnd/windowIdentity/captureProvider/capturedAt/frameHash`。
- ROI、采点、目标验证前再次核对 PreviewState 与当前窗口一致。

### 5.5 P0：最新工作区迁移可能覆盖唯一旧备份

当前真实工作区和 `.bak` 都是 v6。最新应用加载时会 normalize 到 v9 并保存。Rust 保存会把当前主文件复制到固定 `.bak`，覆盖旧 `.bak`。

首次启动最新构建前必须：

1. 复制 `workspace.json` 到带时间戳和 SHA-256 的只读验收备份目录。
2. 复制 `workspace.json.bak` 到同一目录。
3. 记录文件长度、SHA-256、schema、任务数、步骤数、目标数、图片数和队列数。
4. 用复制文件作为 v6 迁移 fixture，不直接拿唯一真实文件试错。
5. 只有 fixture 迁移和回读通过后，才允许启动最新应用。

## 6. 运行时和后端高风险问题

### 6.1 P1：同一 HWND 的互斥不是原子的

`src/main.js` 先检查 `state.sessions[key]`，随后执行异步窗口身份读取，最后才登记 session。快速双击运行按钮时，两个调用可能同时通过检查。

Rust 端也没有 per-HWND 互斥锁。结果可能是：

- 两个 runner 同时向同一窗口发送消息。
- 后一个 session 覆盖前一个状态。
- 停止、暂停、日志和失败报告只关联到后一个 session。
- 键盘和鼠标消息交错。

必须双层防护：

- 前端在第一个 `await` 前创建 `starting` 占位 session。
- 运行按钮立即禁用。
- Rust 端维护 `HashMap<HWND, Arc<Mutex<WindowActorState>>>` 或 HWND actor。
- 所有输入、截图、OCR 和视觉动作通过该 HWND actor 串行。
- 添加快速双击和两个 IPC 并发调用测试。

### 6.2 P1：控制决策可能读取错误画面

当前截图使用 `GetDC(hwnd) + BitBlt`。非严格路径失败后可能回退到桌面区域。

风险：

- DirectX 游戏返回黑帧、旧帧或空帧。
- 最小化窗口无法可靠截图。
- 被遮挡时桌面回退可能截到用户前台应用。
- OCR 和图片识别对错误画面作出成功判断。
- 后续输入仍发送到游戏 HWND，形成识别与输入对象分离。

强制规则：

- 控制决策严禁桌面回退。
- 桌面回退只能用于人工预览，并必须显示“不可信预览”。
- 优先实现可插拔 capture provider：WGC、PrintWindow、GetDC。
- 每个 provider 输出来源、时间、尺寸、帧 hash、黑帧率和可靠性状态。
- 捕获不可靠时任务必须阻塞为 `capture_unavailable`。

### 6.3 P1：模板匹配复杂度不可控且不可取消

当前模板匹配为全帧逐位置、逐像素比较。100×100 模板在 1264×720 帧上可能产生数十亿次颜色通道比较。

当前普通步骤 `timeoutMs` 没有传到 Rust，进入后端后：

- 暂停无法中断。
- 停止无法中断。
- OCR 无真实 deadline。
- 模板匹配无真实 deadline。
- 五窗口并行可能把 CPU 打满。

必须实现：

- 强制 ROI 或可计算搜索区域。
- 图像匹配切换到成熟实现，例如 OpenCV `matchTemplate`。
- 支持分辨率变体和缩放变体，但必须有最大变体数。
- OCR 与图像匹配进入有界 worker pool。
- IPC 携带 `sessionId/stepId/deadlineMs/cancelTokenId`。
- Rust 提供 `cancel_session`。
- 每个后端循环定期检查 deadline 和取消状态。

### 6.4 P1：窗口身份仍不够稳定

现有身份字段应保留，但需增加：

- 完整 exe path。
- 窗口 class。
- 进程创建时间。
- 目标窗口线程 id。
- 客户区比例和 DPI。
- 可选视觉指纹。
- 用户定义的稳定窗口 profile。

单独 `IsWindow` 不足，因为 HWND 会被系统回收。每次输入前必须重新读取并比较完整身份。

### 6.5 P1：`retry_until` 可能假成功

当前 readiness 允许 `retry_until` 绑定图片、ROI 或坐标。Rust 在缺少模板、只有 ROI/坐标时会返回 `planned` 且 `matched=true`。前端随后认为等待成功。

必须修改：

- `retry_until` 只接受可实际判定的 predicate。
- predicate 类型必须是 `image_present/image_absent/ocr_contains/ocr_not_contains/page_state/custom_guard`。
- ROI 只是 predicate 的搜索区域，不能单独作为成功条件。
- 坐标不能作为等待条件。
- `planned` 永远不能映射为 matched success。

### 6.6 P1：恢复片段没有明确结束边界

自定义 `recoveryStepId` 可能从恢复入口继续执行后续普通业务步骤，直到遇到 `restore` 类型或任务末尾。

必须增加：

- `recoveryBlockId` 或显式 `recoveryEndStepId`。
- 恢复片段必须是独立 block。
- 正常路径永远跳过 recovery block。
- 失败路径只能在 block 内执行。
- block 完成后根据 `recoveryAction` 回到失败点、下一步或停止。
- readiness 必须验证 block 有入口、有结束、有验证步骤、无跳出非法边界。

### 6.7 P1：多个字段是虚假能力面

以下字段当前存在但没有完整驱动运行：

- `initialCheck`
- `targetPolicy.titleNeedle`
- `targetPolicy.inputMode`
- 普通步骤的 `expect`
- `snapshot` 的证据路径
- `restore` 类型本身

处理方式只有两种：

1. 完整接入 runner、readiness、报告和测试。
2. 在 UI 中标为“计划字段”并从默认编辑面板隐藏。

禁止继续显示为已可用的普通字段。

### 6.8 P2：键盘消息结构不完整

当前键盘消息的 lParam 过于简化。必须正确编码：

- repeat count
- scan code
- extended-key flag
- Alt context
- previous state
- transition state

消息发送中途失败时，必须 best-effort 释放已经按下的修饰键。状态名称必须从 `sent` 改成 `queued`，后置验证成功后才记为 `passed`。

### 6.9 P2：管理员重启存在单实例竞态

当前旧实例可能在管理员新实例完成接管前仍占用单实例端口，导致新实例唤醒旧实例后退出，随后旧实例也退出。

必须增加：

- `--elevation-handoff` 参数。
- 新实例在该模式下不走普通 wake 逻辑。
- 旧实例先释放端口和状态锁，再退出。
- 新实例等待端口释放后建立监听。
- handoff 过程写入明确日志和 UI 状态。

## 7. UI/UX 全面审计

### 7.1 当前界面的根本问题

当前界面不是单纯“不够美观”，而是把所有能力同时展开成工程配置面板。静态 HTML 已包含约：

- 49 个按钮
- 35 个输入框
- 21 个选择框
- 5 个文本域

动态渲染还会继续增加：

- 蓝图卡片
- 任务卡片
- 步骤卡片
- readiness 问题按钮
- 目标卡片
- 失败报告卡片
- 运行会话卡片
- 日志行

用户完成一个任务需要跨越顶部、左栏、中栏、右栏和底部运行区。界面围绕“把功能都展示出来”组织，而不是围绕“完成一次自动化任务”组织。

### 7.2 正确的信息架构

桌面版采用稳定三栏加底部抽屉：

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ 命令栏：应用状态 | 当前窗口 | 保存状态 | 观察运行 | 后台运行 | 暂停 | 停止 │
├───────────────┬─────────────────────────────────────┬────────────────────────┤
│ 窗口与队列     │ 当前任务步骤                         │ 属性 / 素材 / 测试        │
│               │                                     │ 三个标签页                │
│ 窗口 A         │ 01 检测主界面                       │ [属性] [素材] [测试]       │
│ 任务 1         │ 02 发送 ALT+N                      │                        │
│ 任务 2         │ 03 等待活动入口                     │ 当前步骤字段              │
│               │                                     │ 素材大图与匹配叠加        │
│ 窗口 B         │ 选中步骤                            │ 单步观察/单步后台测试      │
│ 任务 3         │                                     │                        │
├───────────────┴─────────────────────────────────────┴────────────────────────┤
│ 运行抽屉：会话 | 事件 | 步骤结果 | 前后截图 | OCR | 失败报告 | 原始日志       │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 7.3 顶部命令栏

高度目标：48 至 56px。只保留高频命令：

- 刷新窗口
- 保存状态
- 观察运行
- 后台运行
- 暂停/继续
- 停止
- 管理员状态

以下功能移出顶部：

- 启动客户端：放到窗口空状态。
- 选择全部：放到窗口列表批量菜单。
- 准备演练：放到“测试”视图。
- 工作区 JSON：放到设置/诊断视图。
- live 报告导入：放到运行记录视图。

### 7.4 左栏：窗口和队列

每个窗口卡片必须显示：

- 用户别名，例如“窗口 A”“账号 1”。
- 标题、PID、HWND。
- 客户区尺寸、DPI、权限。
- capture provider 和 capture readiness。
- input capability 探测结果。
- 队列任务数和当前任务。
- 运行、暂停、阻塞、丢失状态。

窗口卡片操作：

- 设为预览窗口。
- 加入/移出运行批次。
- 编辑窗口 profile。
- 清空队列，必须确认。
- 复制队列。
- 单窗口观察运行。
- 单窗口后台运行。

“预览窗口”和“运行批次”必须用不同图标和不同状态，不允许共用一个 `selectedHwnds` 集合。

### 7.5 中栏：步骤编辑器

步骤列表每行显示：

- 顺序号
- 类型图标
- 名称
- 关键目标或动作
- readiness 状态
- 最近一次测试状态
- 启用开关
- 拖拽柄
- 更多菜单

选中步骤后提供：

- 从此步骤观察运行
- 只测试此步骤
- 运行到此步骤
- 复制
- 禁用
- 删除
- 插入恢复块
- 设断点

任务列表和蓝图库不能同时长期展开。使用左栏上方标签：

- 窗口队列
- 用户任务
- 蓝图

用户任务和样例任务必须分区。默认不把 10 个样例伪装成用户任务。

### 7.6 右栏：属性、素材、测试

#### 属性标签

- 只显示当前步骤类型需要的字段。
- 高级兼容字段默认折叠。
- 类型切换必须先显示字段变化预览。
- 删除任务、删除步骤和类型重置必须支持撤销。

#### 素材标签

- 模板大图，最小可视尺寸 160×100。
- 当前窗口截图。
- ROI 框。
- 模板匹配框。
- 点击中心和最终偏移点。
- 置信度、阈值、尺寸、来源、hash。
- Ctrl+V 替换素材。
- 从当前截图重新框选。
- 使用共享目标。
- 新建共享目标。

34×34 缩略图只能用于列表，不得作为唯一验证界面。

#### 测试标签

固定提供：

- 只读识别
- 单步观察
- 单步后台测试
- 前后截图
- OCR 原文
- 识图得分和候选框
- 前台 HWND 前后值
- 鼠标坐标前后值
- 对照窗口状态
- 保存证据

### 7.7 底部运行抽屉

运行抽屉默认折叠，只显示一行摘要。展开后提供标签：

- 会话
- 事件
- 步骤结果
- 视觉证据
- 失败报告
- 原始日志

工作区 JSON 不应长期占据主界面。仅在诊断模式显示。

### 7.8 窗口尺寸策略

默认窗口仍可保持 1460×880，但必须保证：

- 顶部命令栏不换行。
- 三栏内容都有独立纵向滚动。
- 页面不使用会截断功能的全局 `overflow: hidden`。
- 任务列表和步骤列表在默认数据下至少各有 240px 可视高度。
- inspector 不允许横向滚动。

920×680 时：

- 左栏可折叠为窗口切换栏。
- 右栏改为可开关抽屉。
- 底部运行抽屉默认关闭。
- 中栏保持步骤列表可用。
- 不允许把五个固定区块纵向堆叠后继续隐藏溢出。

### 7.9 可访问性要求

- 所有 `select`、`textarea` 和输入框有可见 label 或 `aria-label`。
- 状态区使用 `aria-live="polite"`。
- 日志使用 `role="log"`。
- 错误摘要可通过键盘跳转到对应字段。
- ROI 必须提供数值输入作为鼠标操作的替代路径。
- 所有操作支持键盘。
- 默认正文不小于 12px，核心字段不小于 13px。
- 错误、警告、成功不能只靠颜色区分。

### 7.10 视觉语言

设计定位：安静、密集、可扫描、低误触的 Windows 专业工具。

- 设计变化度：4/10
- 动效强度：2/10
- 信息密度：8/10
- 保留深色主题，但减少网格背景和装饰层。
- 一个主强调色，用于选中、通过和主要动作。
- 错误和警告使用语义色。
- 卡片只用于窗口、任务和报告等真实实体，不把每个页面分区做成卡片。
- 圆角不超过 8px。
- 动效只用于抽屉、选中和状态变化反馈。
- 图标统一使用 Lucide，文字按钮保留清晰命令名称。

## 8. 数据持久化审计与目标方案

### 8.1 当前 JSON 方案的优点

- 人工可读。
- 容易导入导出。
- 原子替换逻辑已经比直接写文件安全。
- 当前规模下仍能加载。

### 8.2 当前 JSON 方案的主要风险

1. 图片以内联 Data URL 保存，每次编辑都重写全部图片。
2. 没有逐版本迁移链，当前迁移本质是 normalize。
3. 未来 schema 可能被旧版本规范化后覆盖未知字段。
4. 只有一代 `.bak`。
5. 没有保存 revision、单一 in-flight 协调器和关闭前 flush。
6. 多次并发保存可能出现乱序和临时文件冲突。
7. 运行历史与配置混在同一文件。
8. 队列绑定 HWND，游戏重启后无法稳定恢复逻辑窗口。
9. 导入缺少大小、schema、引用完整性和变更预览。

### 8.3 目标存储架构

采用混合存储：

- SQLite：任务、步骤、目标元数据、窗口 profile、队列、运行会话、事件、步骤结果、失败摘要和迁移记录。
- AppData 图片目录：内容寻址 PNG 文件。
- JSON/ZIP：导入、导出和人工备份格式，不作为运行时真源。
- 内置素材：保存资源 key、版本和 hash，不重复内联进用户库。

### 8.4 SQLite 表结构

```sql
meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)
schema_migrations(version INTEGER PRIMARY KEY, checksum TEXT NOT NULL, applied_at TEXT NOT NULL)
workflows(id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL, description TEXT NOT NULL, initial_check TEXT, policy_json TEXT NOT NULL, revision INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)
steps(id TEXT PRIMARY KEY, workflow_id TEXT NOT NULL, position INTEGER NOT NULL, type TEXT NOT NULL, name TEXT NOT NULL, enabled INTEGER NOT NULL, timeout_ms INTEGER NOT NULL, retry INTEGER NOT NULL, on_fail TEXT NOT NULL, params_json TEXT NOT NULL, target_step_id TEXT, else_target_step_id TEXT, recovery_block_id TEXT, jump_workflow_id TEXT, max_iterations INTEGER, recovery_action TEXT, FOREIGN KEY(workflow_id) REFERENCES workflows(id) ON DELETE CASCADE)
targets(id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL, asset_hash TEXT, roi_json TEXT, match_json TEXT, texts_json TEXT, click_json TEXT, source_json TEXT, note TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)
assets(hash TEXT PRIMARY KEY, relative_path TEXT NOT NULL, mime TEXT NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL, byte_length INTEGER NOT NULL, created_at TEXT NOT NULL)
window_profiles(id TEXT PRIMARY KEY, label TEXT NOT NULL, match_rule_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)
queue_items(id TEXT PRIMARY KEY, window_profile_id TEXT NOT NULL, workflow_id TEXT NOT NULL, position INTEGER NOT NULL, enabled INTEGER NOT NULL, start_delay_ms INTEGER NOT NULL, after_delay_ms INTEGER NOT NULL, added_at TEXT NOT NULL, FOREIGN KEY(window_profile_id) REFERENCES window_profiles(id), FOREIGN KEY(workflow_id) REFERENCES workflows(id))
last_window_bindings(profile_id TEXT PRIMARY KEY, hwnd TEXT, pid INTEGER, identity_json TEXT NOT NULL, observed_at TEXT NOT NULL, FOREIGN KEY(profile_id) REFERENCES window_profiles(id))
run_sessions(id TEXT PRIMARY KEY, profile_id TEXT NOT NULL, workflow_id TEXT, mode TEXT NOT NULL, status TEXT NOT NULL, identity_start_json TEXT NOT NULL, identity_end_json TEXT, failure_reason TEXT, started_at TEXT NOT NULL, ended_at TEXT, duration_ms INTEGER NOT NULL)
run_events(run_id TEXT NOT NULL, seq INTEGER NOT NULL, type TEXT NOT NULL, phase TEXT NOT NULL, status TEXT NOT NULL, detail_json TEXT NOT NULL, occurred_at TEXT NOT NULL, PRIMARY KEY(run_id, seq), FOREIGN KEY(run_id) REFERENCES run_sessions(id) ON DELETE CASCADE)
step_results(run_id TEXT NOT NULL, seq INTEGER NOT NULL, workflow_id TEXT NOT NULL, step_id TEXT NOT NULL, status TEXT NOT NULL, action TEXT NOT NULL, detail_json TEXT NOT NULL, started_at TEXT NOT NULL, ended_at TEXT NOT NULL, PRIMARY KEY(run_id, seq), FOREIGN KEY(run_id) REFERENCES run_sessions(id) ON DELETE CASCADE)
failure_reports(run_id TEXT PRIMARY KEY, failed_workflow_id TEXT, failed_step_id TEXT, category TEXT NOT NULL, summary_json TEXT NOT NULL, FOREIGN KEY(run_id) REFERENCES run_sessions(id) ON DELETE CASCADE)
```

SQLite 配置：

- `foreign_keys=ON`
- `journal_mode=WAL`
- `busy_timeout=5000`
- 配置保存使用 `BEGIN IMMEDIATE`
- 重要配置使用 `synchronous=FULL`
- 运行事件可批量提交，运行结束摘要必须事务提交

### 8.5 JSON 到 SQLite 的迁移要求

1. DB 不存在且 JSON 存在时才进入迁移。
2. 先验证 JSON 主文件和 `.bak`。
3. 主文件损坏时只提示可用备份，不自动覆盖。
4. 对原始 JSON 和 `.bak` 创建带时间戳、hash 的迁移前备份。
5. 在 `workspace.sqlite.tmp` 建库。
6. 单事务导入任务、步骤、目标、队列和历史。
7. Data URL 解码为 PNG，按 SHA-256 去重。
8. 图片先写临时文件，再原子 rename。
9. 校验数量、外键、`integrity_check` 和 `foreign_key_check`。
10. 全部通过后原子切换正式 DB。
11. 失败时保留原 JSON，不留下半迁移数据库。
12. 不长期双写 JSON 和 DB。

## 9. 目标运行时架构

### 9.1 总体分层

```text
UI Workbench
  -> Application Commands
    -> Workflow Domain
    -> Readiness Domain
    -> Scheduler
    -> Evidence Service
      -> Per-Window Actor
        -> Identity Guard
        -> Capture Provider
        -> Vision/OCR Worker Pool
        -> Input Dispatcher
      -> SQLite Repository
      -> Asset Store
```

### 9.2 前端职责

前端只负责：

- 编辑任务和步骤。
- 选择窗口和队列。
- 展示 readiness。
- 发出 run/pause/resume/stop 命令。
- 订阅运行事件。
- 展示视觉证据和失败报告。

前端不再负责：

- 长时间 runner 状态机。
- per-HWND 互斥。
- 后端超时和取消。
- 运行事件的唯一真源。
- 运行历史持久化。

### 9.3 Rust 每窗口 actor

每个当前绑定的窗口创建一个 actor：

- actor mailbox 串行处理该窗口所有请求。
- 同一 HWND 永远只有一个 active run。
- 不同 HWND actor 并行。
- actor 保存 generation，旧 generation 事件不能污染新会话。
- actor 拥有取消令牌、pause gate 和 deadline。
- actor 每个步骤前复核身份。
- actor 每个输入动作后执行后置验证。
- actor 通过 Tauri event 向前端推送事件。

### 9.4 OCR 和视觉 worker pool

- worker 数默认 2，不随窗口数线性增加。
- 队列有上限，超过上限进入 backpressure。
- 每个 job 有 deadline 和取消令牌。
- job 记录 ROI、输入尺寸、provider、耗时、结果和置信度。
- 五窗口并行时，actor 等待 worker，而不是创建五套无限线程。

### 9.5 CaptureProvider 接口

```rust
trait CaptureProvider {
    fn kind(&self) -> CaptureProviderKind;
    fn probe(&self, window: &WindowIdentity) -> CaptureProbe;
    fn capture(&self, request: CaptureRequest, cancel: &CancellationToken) -> Result<CapturedFrame, CaptureError>;
}
```

实现顺序：

1. Windows Graphics Capture
2. PrintWindow
3. GetDC/BitBlt，仅保留兼容探测
4. Desktop visible capture，仅人工预览，禁止控制决策

`CapturedFrame` 必须包含：

- provider
- hwnd
- expected identity hash
- capturedAt
- width/height
- pixel hash
- blackPixelRatio
- unchangedFrameCount
- reliability status

### 9.6 InputDispatcher 接口

```rust
trait InputDispatcher {
    fn probe(&self, window: &WindowIdentity) -> InputCapability;
    fn dispatch(&self, action: InputAction, window: &WindowIdentity) -> Result<QueuedInput, InputError>;
}
```

只允许 HWND 定向消息实现。明确禁止：

- `SendInput`
- `SetCursorPos`
- `BlockInput`
- `SetForegroundWindow`
- 移动游戏窗口
- 透明化或伪最小化窗口
- Maa `WithCursorPos`
- Maa `WithWindowPos`
- Mouse Lock Follow
- 任何全局输入兜底

如果目标游戏不消费定向消息，应用必须显示“该窗口不支持无干扰输入”，不能静默降级。

## 10. 统一任务与步骤模型

### 10.1 Workflow

```ts
type Workflow = {
  id: string;
  name: string;
  category: string;
  description: string;
  enabled: boolean;
  initialCheck?: Predicate;
  concurrency: "per-window-exclusive";
  defaultTimeoutMs: number;
  defaultRetry: number;
  steps: Step[];
  revision: number;
  createdAt: string;
  updatedAt: string;
};
```

`initialCheck` 必须成为真实 predicate，并在运行任务前执行。不能继续保存但不使用。

### 10.2 Step 公共字段

```ts
type StepBase = {
  id: string;
  type: StepType;
  name: string;
  enabled: boolean;
  preDelayMs: number;
  postDelayMs: number;
  timeoutMs: number;
  retry: RetryPolicy;
  onFail: FailurePolicy;
  evidence: EvidencePolicy;
  notes: string;
};
```

公共语义：

- `timeoutMs` 必须进入 Rust deadline。
- `retry` 必须说明总次数、间隔和 backoff。
- `onFail` 必须是 stop/skip/retry/recovery block。
- `evidence` 决定成功、失败和 always 是否保存截图/OCR/识图细节。
- 每步执行前和输入前都必须复核窗口身份。

### 10.3 Predicate

```ts
type Predicate =
  | { kind: "image_present"; targetId: string }
  | { kind: "image_absent"; targetId: string }
  | { kind: "ocr_contains"; targetId: string; texts: string[]; mode: "any" | "all" }
  | { kind: "ocr_not_contains"; targetId: string; texts: string[]; mode: "any" | "all" }
  | { kind: "last_step"; field: "status" | "matched" | "score"; op: string; value: unknown }
  | { kind: "variable"; name: string; op: string; value: unknown }
  | { kind: "window_state"; field: string; op: string; value: unknown };
```

禁止继续使用模糊字符串 `guard=true` 代表真实游戏状态。

### 10.4 15 类步骤的目标语义

#### 10.4.1 hotkey

配置：

- keys
- keyDownGapMs
- holdMs
- keyUpGapMs
- postcondition

执行：

- 生成正确 scan code 和 lParam。
- 修饰键按下顺序和释放顺序确定。
- 失败时释放已按下键。
- 返回 `queued`，后置 predicate 通过后返回 `passed`。

测试：

- 自建 Win32 测试窗口记录消息序列。
- 游戏安全快捷键单窗测试。
- 前台 HWND 和鼠标坐标不变。

#### 10.4.2 text_input

配置：

- text 或变量引用
- mode 固定为 hwnd-char
- charGapMs
- postcondition

执行：

- 保留用户文本，包括有意义的首尾空格时必须有显式选项。
- 限制字符数。
- 逐 UTF-16 单元投递。
- 后置 OCR 验证输入框内容。

测试：

- 自建编辑控件。
- 游戏安全搜索框唯一字符串。
- 用户同时在前台编辑器输入，对照前台内容不被污染。

#### 10.4.3 click

配置：

- x/y 或 target click point
- left/right
- clickCount=1
- postcondition

执行：

- 坐标必须在当前客户区。
- 点击前复核窗口身份。
- 不移动真实鼠标。
- 后置图像或 OCR 验证。

#### 10.4.4 double_click

配置和 click 相同，`clickCount=2`，增加 doubleClickGapMs。

测试必须验证消息顺序和游戏目标实际双击效果，不能只验证两组消息入队。

#### 10.4.5 image_click

配置：

- targetId
- ROI
- threshold
- scale variants
- point=center/corners/custom offset
- mouse button
- postcondition

执行：

- 在同一捕获帧上完成识别、候选框、点击点计算。
- 点击前复核窗口身份和客户区尺寸。
- 点击点必须仍在客户区。
- 保存匹配框、score、最终点和 frame hash。

#### 10.4.6 wait_image

配置：

- predicate=image_present/image_absent
- targetId
- intervalMs
- timeoutMs

执行：

- 轮询真实捕获。
- 不允许 ROI/坐标单独成功。
- deadline 到期返回 timeout。
- pause 时不继续捕获。

#### 10.4.7 detect_page

配置：

- 任意数量 predicate
- any/all/not 组合
- 页面名称

执行：

- 可组合图片和 OCR。
- 输出每个 predicate 的结果。
- 不发送输入。

#### 10.4.8 ocr_assert

配置：

- targetId/ROI
- language
- texts
- any/all
- normalize options
- postcondition 不需要额外设置

执行：

- 输出 OCR 原文、文本框和置信度。
- OCR 不可用与文本不匹配是不同错误。

#### 10.4.9 delay

配置：durationMs、reason。

执行：

- pause 时冻结计时。
- stop 时立即结束。

#### 10.4.10 condition

配置：Predicate、trueTarget、falseTarget。

执行：

- predicate 必须可重现。
- transition 记录输入、结果和目标。
- 未知 predicate 不得默认 true。

#### 10.4.11 loop

配置：

- blockStartStepId
- blockEndStepId
- maxIterations
- optional breakPredicate

执行：

- 必须有硬上限。
- 记录每次迭代。
- stop/pause/deadline 生效。

#### 10.4.12 retry_until

配置：Predicate、intervalMs、timeoutMs、maxAttempts。

执行：

- 只接受真实 predicate。
- 任何 `planned/no_input` 结果不得算成功。

#### 10.4.13 snapshot

配置：

- capture target
- ROI 或 full client
- saveOn=always/success/failure
- annotation policy

执行：

- 实际保存 PNG。
- 返回绝对路径、相对证据路径、尺寸、hash 和 provider。
- 可叠加 ROI、匹配框和点击点。

#### 10.4.14 task_jump

配置：workflowId、mode=insert/replace/after-current、maxJumps。

执行：

- 只修改当前 run plan，不隐式修改持久化队列。
- 检测跨任务循环。
- 记录 jump transition。

#### 10.4.15 recovery_block

替代当前计划态 `restore` 步骤。

配置：

- blockId
- entryStepId
- endStepId
- recoveryAction=stop/retry/continue
- maxEntries

执行：

- 正常路径跳过 recovery block。
- 失败路径在 block 内运行。
- block 必须包含至少一个验证步骤。
- 完成后按 recoveryAction 回到确定位置。

## 11. Readiness 统一规则

Readiness 分四层：

1. Schema readiness：字段、引用、类型和循环是否合法。
2. Asset readiness：图片、ROI、OCR 文本、坐标和共享目标是否完整。
3. Runtime readiness：窗口、身份、权限、capture provider、input capability、OCR backend 是否可用。
4. Plan readiness：队列、并发、恢复块、任务跳转、预计输入步骤是否安全。

状态只有：

- `ready`
- `warning`
- `blocked`
- `unsupported`
- `needs_live_validation`

禁止把以下状态显示为完成：

- `preflight_only`
- `planned`
- `no_input`
- `queued` 但没有后置验证
- 权限不足导致 ignored test 提前返回

## 12. 文件级重构方案

### 12.1 前端目录

在不迁移 React/Vue 的前提下，保留 vanilla ES modules，拆分为：

```text
src/
  app/
    bootstrap.js
    state.js
    commands.js
    events.js
  domain/
    workflow.js
    step.js
    predicates.js
    control-flow.js
    readiness.js
    queue-plan.js
    run-report.js
  services/
    tauri-api.js
    workspace-service.js
    target-service.js
    evidence-service.js
  ui/
    render.js
    dom.js
    command-bar.js
    window-queue-pane.js
    workflow-pane.js
    step-editor.js
    inspector-properties.js
    inspector-assets.js
    inspector-test.js
    run-drawer.js
    dialogs.js
    undo-stack.js
  styles/
    tokens.css
    shell.css
    controls.css
    panes.css
    steps.css
    evidence.css
    responsive.css
```

迁移顺序：

1. 先移动纯函数，不改行为。
2. 每移动一个模块，原测试改为直接导入新模块。
3. `main.js` 只保留 bootstrap，最终目标不超过 500 行。
4. `renderAll()` 拆成按 slice 渲染，输入时不重绘全部区域。

### 12.2 Rust 目录

```text
src-tauri/src/
  main.rs
  commands/
    mod.rs
    windows.rs
    workspace.rs
    runtime.rs
    targets.rs
    evidence.rs
  runtime/
    mod.rs
    manager.rs
    window_actor.rs
    session.rs
    cancellation.rs
    events.rs
  window/
    identity.rs
    enumerate.rs
    privilege.rs
  capture/
    mod.rs
    wgc.rs
    print_window.rs
    gdi.rs
    quality.rs
  input/
    mod.rs
    post_message.rs
    keyboard.rs
    mouse.rs
    capability.rs
  vision/
    mod.rs
    template_match.rs
    roi.rs
  ocr/
    mod.rs
    windows_ocr.rs
    backend.rs
  storage/
    mod.rs
    sqlite.rs
    migrations.rs
    asset_store.rs
    json_import.rs
  evidence/
    mod.rs
    run_bundle.rs
    screenshot.rs
```

`main.rs` 最终只负责：

- app 构建
- state 注入
- command 注册
- tray 和 single instance
- 启动迁移

### 12.3 当前函数到目标模块的映射

| 当前范围 | 目标 |
|---|---|
| `normalizeWorkspace`、保存调度 | `services/workspace-service.js`，随后迁入 Rust repository |
| readiness 系列函数 | `domain/readiness.js` |
| control-flow helper 包装 | `domain/control-flow.js` |
| `runSelected`、`runSession`、`executeRunPlan` | Rust `runtime/manager.rs` 和 `window_actor.rs` |
| 目标归一化和导入导出 | `services/target-service.js` 与 Rust asset store |
| render 系列 | `ui/` 各区域模块 |
| `execute_workflow_step` | 拆分为 typed command + runtime action executor |
| capture 函数 | `capture/` |
| PostMessage 函数 | `input/` |
| 模板匹配 | `vision/template_match.rs` |
| OCR | `ocr/` |
| workspace 读写 | `storage/` |

### 12.4 可清理候选

当前没有证据支持大规模删除 tracked 文件。以下仅列为候选：

- 未使用的前端包装函数：`completeRecoveryAsFailed`、`compareNumbers`、`isSuccessfulStepResult`、`stepLabelForExecution`。
- 未驱动运行的字段：`initialCheck`、部分 `targetPolicy`。
- 已失去源码对应项的历史 `.pyc`。
- 26 个重复 Rust target 目录。

处理规则：

1. tracked 候选必须先用 `rg`、测试、审计和运行路径证明无引用。
2. 兼容字段必须先完成迁移测试和导入 fixture。
3. ignored 构建目录属于历史会话，未获得单独清理授权前不得删除。
4. `.codex-window-*.png` 与项目无关但归属不明，保留。
5. 清理磁盘必须作为独立任务，先生成候选表、大小、创建时间和归属证据，再请求用户确认。

### 12.5 当前源码行号级改造表

以下行号以 `3eef34f` 为基线。修改前必须重新用 `rg -n` 复核，因为后续提交会改变行号。

| 文件与当前行号 | 当前职责/问题 | 下一步具体动作 |
|---|---|---|
| `src/styles.css:22-52` | body/main 固定 `100dvh` 且隐藏溢出 | 移除全局功能裁剪；只在明确 pane 内使用滚动 |
| `src/styles.css:179-239` | 顶部品牌、工具栏和六块 dashboard | 改成 48-56px 命令栏；dashboard 收敛成状态条 |
| `src/styles.css:282-358` | app-shell/workbench 固定三列三行 | 改为三栏 + 抽屉；每栏 `minmax(0,1fr)` 和独立滚动 |
| `src/styles.css:2333-2412` | 1120/820 断点，中间宽度不可达 | 920-1120 使用折叠栏，不堆叠五个隐藏区块 |
| `index.html:12-61` | 顶部命令和 dashboard | 删除低频顶栏入口，加入运行计划入口和保存状态 |
| `index.html:65-621` | 所有工作台功能同时展开 | 拆成窗口/队列、步骤、右侧标签、运行抽屉 |
| `index.html:211` | 新步骤和片段选择无明确 label | 增加 label/aria-label |
| `index.html:604-620` | 整队列运行、JSON、日志集中 | 加单步/从当前步骤；JSON 移到诊断；日志加 role=log |
| `src/main.js:970-1085` | workspace normalize 和加载 | 增加逐版本迁移与 future schema 只读保护 |
| `src/main.js:1300-1340` | 500ms debounce 保存 | 替换为 SaveCoordinator、revision、flush 和错误恢复 |
| `src/main.js:1641` | `renderAll()` 全量重绘入口 | 拆为按 state slice 增量渲染 |
| `src/main.js:2270` | 准备演练自动刷新和选择窗口 | 改成只生成计划，不自动加入 live 运行批次 |
| `src/main.js:2398` | 新建任务实际套用当前蓝图 | 新增真正空白任务；蓝图单独入口 |
| `src/main.js:2507` | 删除任务并清队列引用 | 加 undo transaction 和确认摘要 |
| `src/main.js:3605` | 删除步骤立即生效 | 加 undo stack，选中相邻步骤 |
| `src/main.js:4200-4210` | 类型切换重置字段 | 显示变更预览，确认后应用，支持撤销 |
| `src/main.js:4528-4624` | 目标验证只返回文字 | 返回并渲染 frame、ROI、候选框、score 和点击点 |
| `src/main.js:4960-5295` | 窗口切换和异步预览 | 增加 request id、来源身份和 stale response 丢弃 |
| `src/main.js:5338` | preview 只保存宽高 | 保存 hwnd、identity、provider、capturedAt 和 frameHash |
| `src/main.js:5596-5622` | ROI 保存使用当前 active window | 强制使用 preview source，并在保存前复核身份 |
| `src/main.js:5987-6223` | readiness 允许模糊目标 | 采用 typed predicate；ROI/坐标不能作为等待成功条件 |
| `src/main.js:6377-6388` | 已选窗口运行、空队列回退当前任务 | 分离 run batch；删除回退；生成执行计划 |
| `src/main.js:6442-6509` | session 检查和登记之间有 await | 第一个 await 前原子占位；后端再加锁 |
| `src/main.js:6738-7220` | 前端 runner 和运行记录 | 逐步迁入 Rust runtime manager/window actor |
| `src/main.js:7051-7055` | 恢复结束只靠 restore/任务末尾 | 使用 recovery block 显式结束边界 |
| `src/main.js:7339-7421` | retry_until 和后端调用 | deadline/cancel 进入 Rust；planned 不得 matched success |
| `src/main.js:7524-7547` | backend payload 不含通用 timeout | 增加 session/step/deadline/cancel/evidence 字段 |
| `src/main.js:8040-8060` | 工作区导入直接 normalize/save | 增加 schema/大小/引用预检、diff 和确认 |
| `src/live-validation-core.js:63` | preflight_only 映射为 done | 改成 preflight 状态，不进入真实通过统计 |
| `src-tauri/src/main.rs:249` | 管理员重启 | 实现 elevation handoff 和端口释放握手 |
| `src-tauri/src/main.rs:301-343` | 原子 JSON 保存 | 短期增加互斥/revision；长期迁入 SQLite |
| `src-tauri/src/main.rs:372` | 单步执行总入口 | 拆分 typed action executor，纳入 actor/deadline |
| `src-tauri/src/main.rs:397-408` | snapshot 只返回尺寸 | 保存 PNG、hash、provider、路径和叠加图 |
| `src-tauri/src/main.rs:619-744` | expected window identity | 增加 exe path/class/process start/thread/DPI |
| `src-tauri/src/main.rs:745` | 标题包含即可初次准入 | 使用允许规则和用户确认的 window profile |
| `src-tauri/src/main.rs:806` | 动作报告为 sent | 改为 queued；postcondition 通过后 passed |
| `src-tauri/src/main.rs:926-959` | 无模板 wait_image 可能 planned+matched | 返回 invalid predicate 或 blocked |
| `src-tauri/src/main.rs:1714` | 暴力模板匹配 | 替换成熟引擎，强制 ROI、预算和 benchmark |
| `src-tauri/src/main.rs:2060-2150` | live 只看帧差 | 使用明确页面 predicate、对照窗口、前台/鼠标见证 |
| `src-tauri/src/platform.rs:355-430` | HWND GDI 截图和回退 | 抽象 CaptureProvider；控制路径禁止桌面回退 |
| `src-tauri/src/platform.rs:449-496` | 键盘 lParam 简化 | 正确编码 scan code、Alt、keyup state，并释放修饰键 |
| `src-tauri/src/platform.rs:497` | PostMessage 成功即返回 | 只表示 queued，业务结果交给后置验证 |


## 13. 纠正后的开发流程

### 13.1 每个功能的固定循环

每个步骤类型和每个任务必须执行以下完整循环：

1. 写清真实用户动作和安全边界。
2. 写纯函数/模型单测。
3. 写 Rust 假窗口测试。
4. 实现 UI 和 IPC。
5. 启动当前 commit 的真实 Tauri release。
6. 在应用里选择窗口和当前步骤。
7. 先跑只读识别或观察模式。
8. 查看预览叠加、OCR、匹配框和最终点。
9. 在安全页面执行单步后台输入。
10. 验证前台 HWND、鼠标坐标和对照窗口不变。
11. 保存证据包。
12. 把失败点立即修正。
13. 重跑单步。
14. 加入完整任务。
15. 跑完整任务。
16. 跑双窗口并行。
17. 跑失败注入。
18. 跑打包 exe。
19. 更新文档。
20. 提交稳定切片。

没有完成第 5 至 18 步的功能，不得标记为“已完成”。

### 13.2 每个 commit 的要求

- 一个 commit 对应一个可验证的纵向切片。
- commit 前 tracked 工作树范围明确。
- 不混入历史 ignored 产物。
- Node、Python、Rust 和 UI 测试按风险执行。
- 若涉及输入，必须有真实应用证据包。
- commit message 使用动作和能力描述。
- 推送后记录完整 hash。

### 13.3 Definition of Done

功能完成必须同时满足：

- 模型字段稳定。
- UI 可操作。
- readiness 能阻断缺配置。
- 后端有 deadline 和取消。
- 同 HWND 互斥。
- 真实应用使用当前 commit 二进制。
- 后置验证证明业务效果。
- 前台无干扰证明通过。
- 失败报告可定位。
- 重启持久化通过。
- 文档和测试同步。

## 14. 分阶段实施计划

### 14.1 阶段 0：数据保护与可重复基线

目标：在不破坏真实 v6 工作区的前提下，为当前 HEAD 建立可重复启动和验收基线。

实施：

1. 新增只读基线脚本 `scripts/capture_validation_baseline.py`。
2. 脚本记录 git commit、exe hash、进程、窗口、权限、工作区 hash 和数据计数。
3. 在用户明确授权的验收目录中复制当前 `workspace.json` 和 `.bak`。
4. 复制文件名包含时间、schema 和 SHA-256 前 12 位。
5. 将 v6 文件纳入只读 migration fixture，不提交用户真实图片内容到公开仓库。
6. 新增匿名化 fixture 生成器，移除图片正文但保留长度和引用结构。
7. 用 fixture 测试 v6 -> v7 -> v8 -> v9。
8. 验证重复迁移幂等。
9. 验证迁移后关闭重开数据一致。

禁止：

- 在没有独立备份前启动最新应用。
- 覆盖当前 `.bak`。
- 把真实用户素材提交到 Git。

验证：

- fixture 数量保持 5 任务、63 步、27 目标。
- 断裂引用为 0。
- 迁移重复执行结果 hash 一致。
- 未来 schema 以只读模式打开。

建议 commit：`Protect legacy workspace migration baseline`

### 14.2 阶段 1：运行安全硬化

目标：在发送任何新 live 输入前消除可误操作窗口的 P0/P1 风险。

实施文件：

- `src/main.js`
- `src-tauri/src/main.rs`
- `src-tauri/src/platform.rs`
- 新增 `src-tauri/src/runtime/`
- 新增运行并发和取消测试

实施：

1. 前端运行前原子登记 `starting` session。
2. 后端增加 per-HWND actor/锁。
3. 删除空队列回退当前任务。
4. 预览窗口和运行批次分离。
5. 运行前生成明确计划。
6. 扩展窗口身份。
7. 修复键盘 lParam。
8. 状态从 `sent` 改为 `queued`。
9. 引入 deadline 和 cancellation token。
10. 修复 `retry_until` 假成功。
11. 为恢复片段增加结束边界。
12. 禁止控制决策使用桌面截图回退。

测试：

- 快速双击运行，只创建一个 session。
- 同 HWND 两个 IPC 并发，只按顺序执行。
- 不同 HWND 可以并行。
- stop 可取消等待和 worker job。
- timeout 对 OCR、模板匹配和截图生效。
- 只有 ROI/坐标的 `retry_until` readiness 阻塞。
- 捕获 provider 不可靠时零输入。

真实游戏输入：禁止，直到本阶段全部通过。

建议 commit：`Harden per-window runtime safety`

### 14.3 阶段 2：工作台可达性与单步调试

目标：让用户在默认和最小窗口尺寸下能完成完整操作，并能逐步骤看到效果。

实施文件：

- `index.html`
- `src/styles.css`
- `src/main.js`
- 新增 `src/ui/` 和 `src/styles/`
- 新增 Playwright 视觉测试

实施：

1. 重构为命令栏、三栏工作台、底部运行抽屉。
2. 默认尺寸任务列表和步骤列表不再为 0 高度。
3. inspector 使用标签页，消除横向滚动。
4. 用户任务和样例任务分区。
5. 新建按钮创建真正空白任务。
6. 增加单步只读测试。
7. 增加单步后台测试。
8. 增加从当前步骤观察和运行到当前步骤。
9. 识图结果叠加到预览。
10. OCR 文本框叠加到预览。
11. 点击点和偏移点叠加到预览。
12. 增加 Undo/Redo。
13. 删除任务和步骤支持撤销。
14. 类型切换显示字段重置确认。
15. 修复预览来源竞态。
16. 为所有控件补 label、aria-live 和 role=log。

视口测试：

- 1460×880
- 1280×720
- 1120×720
- 920×680
- 820×720

每个尺寸必须验证：

- 顶部命令不截断。
- 任务和步骤可滚动。
- inspector 可用。
- run drawer 可展开和关闭。
- 文本不重叠。
- 主要按钮可见。

建议 commit：`Rebuild the automation workbench layout`

### 14.4 阶段 3：严格捕获和视觉引擎

目标：识别和点击必须基于目标窗口真实画面，而不是桌面回退。

实施：

1. 定义 CaptureProvider。
2. 实现 WGC probe 和 capture。
3. 实现 PrintWindow probe 和 capture。
4. 保留 GDI provider 作为兼容探测。
5. 增加黑帧、静止帧和尺寸变化检测。
6. 每个窗口保存 provider capability。
7. 用 OpenCV 或等价成熟库替换暴力模板匹配。
8. 强制 ROI 和搜索预算。
9. 建立真实帧 benchmark。
10. 保存匹配叠加图。

测试矩阵：

- 窗口可见且无遮挡。
- 窗口被普通窗口遮挡。
- 窗口最小化。
- 窗口尺寸变化。
- 两个同标题窗口。
- 黑帧 provider。
- 旧帧重复 provider。
- 五窗口并发请求。

控制规则：

- provider 不可靠时阻塞输入。
- Desktop Duplication 只作人工预览。

建议 commit：`Add strict per-window capture providers`

### 14.5 阶段 4：第一个真实纵向任务“家园活力”

目标：通过当前应用 UI 完成第一个 10 步以上真实任务，并形成完整证据。

要求：

- 只使用一个游戏窗口。
- 另一个游戏窗口作为对照。
- 每个动作先单步验证。
- 不执行破坏性、购买、交易或不可逆动作。
- 用户前台继续可用。

详细步骤见第 15.1 节。

验证：

- 应用当前进程来自当前 commit release。
- 任务从 UI 创建或从蓝图实例化。
- 素材通过 Ctrl+V/ROI 绑定。
- 每步有前后证据。
- 完整任务成功。
- 失败场景可恢复。
- 应用重启后任务和素材保留。

建议 commit：`Validate the first end-to-end home workflow`

### 14.6 阶段 5：SQLite 和素材文件化

目标：把运行时真源迁移到 SQLite，并把图片从 workspace JSON 移出。

实施：

1. 先实现 JSON SaveCoordinator。
2. 完成 future schema 只读保护。
3. 完成主备文件恢复 UI。
4. 增加 SQLite repository。
5. 增加 asset store。
6. 实现 v6/v9 JSON 导入。
7. 实现 JSON/ZIP 导出。
8. 实现窗口 profile 和 last binding。
9. 运行事件写入独立表。
10. 失败证据写入独立目录。

验证：

- 100 次快速编辑不丢最后 revision。
- 保存中关闭可 flush。
- 磁盘满和权限拒绝明确失败。
- 图片 hash 去重。
- 数据库完整性检查通过。
- 导出再导入数据一致。
- 游戏重启后 profile 可重新绑定，但必须重新确认身份。

建议 commit：`Move workspace state to transactional storage`

### 14.7 阶段 6：第二至第五个真实任务

顺序：

1. 福利签到
2. 背包整理
3. 组队准备
4. 摊位搜索，只搜索不购买

每个任务必须重复阶段 4 的完整纵向验收，不得批量编码后统一测试。

建议每个任务独立 commit。

### 14.8 阶段 7：双窗口并行和队列控制

目标：窗口 A 跑 2 个任务，窗口 B 跑 5 个任务，同窗口串行、不同窗口并行。

实施：

- Rust scheduler 成为真源。
- 窗口 profile 替代 HWND 持久化主键。
- 单窗口暂停/继续/停止。
- 全局暂停/继续保留。
- 队列追加、插入、删除、重新排序。
- 已运行、待运行、失败、跳过状态可视化。
- 重启后只恢复队列配置，不自动恢复未完成输入会话。

验收：

- 两窗口事件时间轴有重叠。
- 同一窗口步骤时间轴不重叠。
- 一个窗口失败不影响另一个窗口。
- 一个窗口暂停不影响另一个窗口。
- 对照窗口不收到错误输入。
- 前台鼠标和键盘不受影响。

建议 commit：`Validate isolated multi-window queues`

### 14.9 阶段 8：5 至 10 个回归任务与发布门

目标：把样例从“模型演示”升级为“可运行回归资产”。

要求：

- 至少 5 个任务真实完成。
- 其余任务必须明确标注为 blueprint、needs_capture 或 unsupported。
- 每个任务至少 10 步。
- 每个任务有成功和失败 fixture。
- 每个任务有当前游戏版本素材 profile。
- 每个任务有证据包索引。

建议 commit：`Add validated workflow regression suite`

### 14.10 阶段 9：源码清理、稳定提交和发布

清理只在前述行为有测试保护后进行：

- 删除确认无引用的包装函数。
- 移除已完成迁移的 legacy 分支。
- 合并重复 readiness 文案和映射。
- 删除断链 UI 控件。
- 拆分单体文件。
- 补 LICENSE、第三方 NOTICE 和素材来源策略。
- 统一 `npm run validate`。
- 增加 CI。
- 生成 release 和 NSIS。

完整验证：

- Node tests
- Python audits
- ESLint
- TypeScript/JSDoc type check
- Playwright UI E2E
- Accessibility scan
- `npm run build`
- Rust fmt/check/test/clippy
- Tauri release build
- packaged app smoke
- v6 migration smoke
- 单窗口真实任务
- 双窗口并行任务
- 失败注入
- 重启持久化

建议 commit：`Release validated multi-window automation workbench`

## 15. 五个首批真实任务定义

以下任务是验收顺序，不是一次性全部实现。

### 15.1 家园活力

目标：打开相关功能入口，进入家园页面，读取活力文本，执行一个已确认安全的打理动作并返回主界面。

步骤：

1. `detect_page`：确认主界面，图片 + OCR 双 predicate。
2. `snapshot`：保存任务起始画面。
3. `hotkey`：发送 `ALT+N`。
4. `wait_image`：等待功能面板家园入口。
5. `ocr_assert`：确认面板包含“家园”。
6. `image_click`：点击家园入口。
7. `detect_page`：确认家园页面。
8. `ocr_assert`：读取并保存活力文本。
9. `wait_image`：等待打理按钮。
10. `image_click`：点击打理按钮，使用经过人工确认的目标和偏移。
11. `delay`：等待动画完成。
12. `ocr_assert`：确认活力或结果文本发生预期变化。
13. `snapshot`：保存成功画面和点击标注。
14. `hotkey`：发送 ESC 返回。
15. `detect_page`：确认主界面。

失败恢复块：

1. ESC
2. 等待 600ms
3. 检测主界面
4. 保存失败现场
5. stop

### 15.2 福利签到

目标：进入福利页，识别签到状态，只在可领取时点击，已领取时跳过。

步骤：

1. 检测主界面。
2. 保存起始截图。
3. 打开活动面板。
4. 等待福利入口。
5. 点击福利入口。
6. OCR 确认“福利”。
7. 检测“已领取”文本或签到按钮。
8. 条件分支：已领取走第 12 步，可领取走第 9 步。
9. 图片点击签到按钮。
10. 等待确认弹窗或结果文本。
11. 图片点击确认按钮。
12. OCR 确认最终状态为已领取。
13. 保存结果截图。
14. ESC 返回。
15. 检测主界面。

### 15.3 背包整理

目标：进入背包，检测整理按钮，执行一次安全整理并验证界面反馈。

步骤：

1. 检测主界面。
2. 打开背包。
3. 检测背包页面。
4. OCR 确认“包裹”。
5. 保存整理前截图。
6. 等待整理按钮。
7. 图片点击整理按钮。
8. 等待界面变化。
9. 检测确认弹窗。
10. 条件分支：有确认则点击，无确认则继续。
11. OCR 或图片确认整理完成。
12. 保存整理后截图。
13. ESC 关闭背包。
14. 检测主界面。

### 15.4 组队准备

目标：打开队伍界面，确认当前队伍状态，只进行安全的页面导航和状态检查，不自动接受未知队伍操作。

步骤：

1. 检测主界面。
2. 打开活动/队伍入口。
3. 等待队伍页面。
4. OCR 确认“组队”。
5. 保存队伍状态截图。
6. 检测“创建队伍”“申请加入”“已有队伍”三种状态。
7. 条件分支选择安全观察路径。
8. 已有队伍时读取队员数量。
9. 无队伍时只定位按钮，不点击申请或创建。
10. 保存目标框和 OCR 结果。
11. 等待 500ms，确认页面稳定。
12. ESC 返回。
13. 检测主界面。

### 15.5 摊位搜索

目标：进入摊位搜索，在安全搜索框后台输入唯一测试字符串，读取结果，不购买。

步骤：

1. 检测主界面。
2. 打开商城或摆摊入口。
3. 检测摆摊页面。
4. OCR 确认“摆摊”或搜索页面标题。
5. 等待搜索输入框目标。
6. 图片点击输入框。
7. 文本输入唯一测试字符串。
8. OCR 确认输入框包含该字符串。
9. 图片点击搜索按钮。
10. `retry_until` 等待结果列表 predicate。
11. OCR 读取第一条结果摘要。
12. 保存结果截图。
13. 明确断言本任务不存在购买点击步骤。
14. ESC 返回。
15. 检测主界面。

## 16. 真实验收矩阵

### 16.1 基线与迁移

| ID | 场景 | 通过条件 |
|---|---|---|
| A01 | 构建身份 | 记录 commit、exe SHA-256、构建时间；实际 PID 映射到该 exe |
| A02 | v6 备份 | 主文件和旧 bak 均有独立副本和 hash |
| A03 | v6 -> 当前迁移 | 5/63/27 数据不丢失，引用完整 |
| A04 | 重启回读 | 关闭重开后数据和 hash 语义一致 |
| A05 | 未来 schema | 只读打开，任何编辑和导入不能覆盖 |

### 16.2 UI 与工作台

| ID | 场景 | 通过条件 |
|---|---|---|
| U01 | 1460×880 | 所有主区域可达，任务和步骤列表有可用高度 |
| U02 | 1280×720 | 无横向裁剪，主命令可见 |
| U03 | 920×680 | 左右栏可折叠，中栏保持可用 |
| U04 | 键盘导航 | 可完成窗口选择、步骤选择和单步测试 |
| U05 | 撤销 | 删除任务、删除步骤、类型切换可撤销 |
| U06 | 预览竞态 | 快速切换窗口不会错绑截图和 ROI |

### 16.3 后端能力

| ID | 场景 | 通过条件 |
|---|---|---|
| B01 | 假窗口热键 | 消息序列和 lParam 正确 |
| B02 | 假窗口点击 | 坐标、按键、双击顺序正确 |
| B03 | 同 HWND 并发 | 第二会话被阻断或串行，不交错 |
| B04 | 不同 HWND 并发 | 事件时间有重叠 |
| B05 | timeout | OCR、识图、截图到期返回 timeout |
| B06 | cancel | stop 后 worker 和 actor 停止 |
| B07 | capture unreliable | 黑帧/旧帧时零输入 |

### 16.4 单窗口 live

| ID | 场景 | 通过条件 |
|---|---|---|
| L01 | 只读截图 | 保存严格目标窗口截图路径和 provider |
| L02 | OCR 成功 | 保存 OCR 原文、框和置信度 |
| L03 | OCR 失败 | 文本不匹配和 OCR 不可用分类明确 |
| L04 | 后台热键 | 指定页面 predicate 成功，不使用全屏帧差作为唯一判定 |
| L05 | 左键 | 正确窗口、正确点、后置状态成功 |
| L06 | 右键 | 正确窗口、正确点、后置状态成功 |
| L07 | 双击 | 真实目标出现双击效果 |
| L08 | 文本输入 | 游戏框出现唯一字符串，前台编辑器未收到字符 |
| L09 | image_click | 保存模板框、score 和最终偏移点 |
| L10 | 失败恢复 | 恢复块边界正确，原失败保留 |

### 16.5 前台无干扰

| ID | 场景 | 通过条件 |
|---|---|---|
| F01 | 鼠标静止 | 多次后台点击前后 `GetCursorPos` 完全一致 |
| F02 | 前台 HWND | 每个输入步骤前后 `GetForegroundWindow` 不变 |
| F03 | 用户打字 | 用户在第三方编辑器持续输入，字符不丢失、不串入游戏 |
| F04 | 用户拖动 | 用户拖动窗口或滚动时，游戏任务继续且不抢焦点 |
| F05 | 对照窗口 | 未分配窗口不发生目标页面变化 |

### 16.6 双窗口

| ID | 场景 | 通过条件 |
|---|---|---|
| M01 | A 两任务、B 五任务 | A/B 并行，各自内部串行 |
| M02 | A 失败 | B 继续执行 |
| M03 | A 暂停 | B 继续执行 |
| M04 | A 窗口关闭 | A 零后续输入，B 不受影响 |
| M05 | 身份漂移 | 旧绑定阻塞，必须重新确认 |

### 16.7 持久化和证据

| ID | 场景 | 通过条件 |
|---|---|---|
| P01 | 100 次快速编辑 | 最终 revision 为最新 |
| P02 | 保存中关闭 | close flush 成功或明确阻止关闭 |
| P03 | 磁盘满 | 保留旧数据并明确报错 |
| P04 | 图片去重 | 相同图片只保存一个 hash 文件 |
| P05 | 重启 | 任务、素材、窗口 profile、队列、报告保留 |
| P06 | 导出导入 | JSON/ZIP roundtrip 数据一致 |
| P07 | 失败证据 | 包含完整步骤、截图、窗口身份和外部路径 |

## 17. 每轮 live 证据包格式

目录：

```text
assets/resource/ShiKong/reports/runs/<run-id>/
  manifest.json
  summary.md
  workspace-before.sha256
  workspace-after.sha256
  foreground-cursor.jsonl
  events.jsonl
  step-results.json
  screenshots/
    0001-before.png
    0001-after.png
    0001-overlay.png
  ocr/
    0001.json
  vision/
    0001.json
  failure/
    report.json
```

`manifest.json` 必须包含：

```json
{
  "kind": "mhxy-shikong.run-evidence",
  "version": 1,
  "runId": "run-uuid",
  "generatedAt": "ISO-8601",
  "git": {
    "commit": "full-40-char-hash",
    "branch": "main",
    "dirty": false
  },
  "binary": {
    "path": "absolute-release-exe-path",
    "sha256": "hex",
    "builtAt": "ISO-8601"
  },
  "controller": {
    "pid": 0,
    "elevated": true,
    "integrityLevel": "high"
  },
  "windows": [],
  "workflowIds": [],
  "mode": "background",
  "allowInput": true,
  "foregroundWitness": true,
  "cursorWitness": true,
  "status": "passed"
}
```

每个目标窗口身份包含：

- profile id
- hwnd
- pid
- process path
- process creation time
- window class
- title
- client size
- DPI
- elevated/integrity
- capture provider
- identity hash

`foreground-cursor.jsonl` 每个输入步骤至少记录：

- before foreground hwnd
- after foreground hwnd
- before cursor x/y
- after cursor x/y
- sample timestamps
- assigned target hwnd
- unassigned control hwnd

失败判定：

- 前台 HWND 改变为目标游戏：失败。
- 鼠标坐标改变且不是用户本人操作证据：失败。
- 对照窗口发生任务目标状态变化：失败。
- input queued 但 postcondition 未通过：失败。
- capture provider 不可靠仍发送输入：失败。

## 18. 自动化测试结构

建议新增：

```text
tests/
  fixtures/
    workspace-v6-anonymized.json
    workspace-v8.json
    workspace-v9.json
    future-schema.json
    frames/
    templates/
  frontend/
    workbench-layout.spec.mjs
    workflow-editing.spec.mjs
    readiness.spec.mjs
    preview-race.spec.mjs
    run-plan-confirmation.spec.mjs
  rust/
    fake_window_harness/
  live/
    run_single_step.py
    run_workflow.py
    run_multi_window.py
    witness_foreground_cursor.py
```

### 18.1 统一命令

`package.json` 最终提供：

- `test:unit`
- `test:frontend`
- `test:rust`
- `audit:all`
- `validate:static`
- `validate:packaged`
- `validate:migration`
- `validate:live:readonly`
- `validate:live:single-step`
- `validate:live:workflow`
- `validate:live:multi-window`
- `validate:all`

默认 `validate:all` 不发送游戏输入。live 输入命令必须显式要求：

- 当前 commit release binary
- 管理员状态满足
- 目标窗口身份确认
- 用户授权开关
- 明确测试 case id
- 证据目录

### 18.2 CI

CI 只运行：

- Node 单元测试
- Python 审计
- ESLint/类型检查
- Playwright 静态 UI
- Rust fmt/check/test/clippy
- Vite build
- Tauri build smoke，可按 runner 成本分 nightly

真实游戏 live 测试只能在本机受控验收环境运行，不能伪装成普通 CI。

## 19. 成熟案例和官方依据

### 19.1 Windows 输入和身份

- [Microsoft PostMessage](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-postmessagea)：受 UIPI 限制，消息入队不代表业务成功。
- [Microsoft SendInput](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput)：写入系统全局输入流，不满足本项目无前台干扰要求。
- [Microsoft IsWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-iswindow)：HWND 可能被回收，不能单独作为身份依据。
- [Microsoft GetWindowThreadProcessId](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowthreadprocessid)
- [Microsoft QueryFullProcessImageName](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-queryfullprocessimagenamew)

### 19.2 Windows 截图

- [Microsoft PrintWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-printwindow)：同步且依赖目标应用处理，不保证游戏兼容。
- [Windows Graphics Capture CreateForWindow](https://learn.microsoft.com/en-us/windows/graphics/capture/screen-capture)：Windows 10 1903 起可定向窗口，必须做能力探测。
- [GraphicsCaptureSession IsBorderRequired](https://learn.microsoft.com/en-us/uwp/api/windows.graphics.capture.graphicscapturesession.isborderrequired)：取消边框涉及 capability 和用户同意。
- [Desktop Duplication API](https://learn.microsoft.com/en-us/windows/win32/direct3ddxgi/desktop-dup-api)：复制桌面，不是独立后台窗口捕获。

### 19.3 视觉和 OCR

- [OpenCV Template Matching](https://docs.opencv.org/4.x/de/da9/tutorial_template_matching.html)
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
- [Tesseract ImproveQuality](https://github.com/tesseract-ocr/tessdoc/blob/main/ImproveQuality.md)

选型要求：

- 使用真实梦幻西游 ROI 标注集比较。
- 比较准确率、召回率、耗时、内存、包体和 Windows 部署难度。
- 不凭主观选择 OCR 引擎。

### 19.4 Tauri 安全

- [Tauri Sidecar](https://v2.tauri.app/develop/sidecar/)
- [Tauri Capabilities](https://v2.tauri.app/security/capabilities/)
- [Tauri CSP](https://v2.tauri.app/security/csp/)

若使用 OCR sidecar：

- 只授权精确二进制。
- 固定允许参数。
- 不开放通用 shell。
- 不把凭据和用户素材写入命令行。

### 19.5 SQLite

- [SQLite Transactions](https://www.sqlite.org/lang_transaction.html)
- [SQLite WAL](https://www.sqlite.org/wal.html)
- [SQLite Atomic Commit](https://www.sqlite.org/atomiccommit.html)

### 19.6 自动化工作台参考

- [Power Automate Desktop Flow Designer](https://learn.microsoft.com/en-us/power-automate/desktop-flows/flow-designer)
- [Power Automate Desktop UI Elements](https://learn.microsoft.com/en-us/power-automate/desktop-flows/ui-elements)
- [Power Automate Desktop Errors](https://learn.microsoft.com/en-us/power-automate/desktop-flows/errors)

借鉴：动作面板、线性步骤工作区、元素库、子流程、单步运行、错误即时高亮。初期不做任意节点图。

### 19.7 MaaFramework

- [Maa Pipeline Protocol](https://github.com/MaaXYZ/MaaFramework/blob/main/docs/en_us/3.1-PipelineProtocol.md)
- [Maa Control Methods](https://github.com/MaaXYZ/MaaFramework/blob/main/docs/en_us/2.4-ControlMethods.md)
- [Maa issue #894](https://github.com/MaaXYZ/MaaFramework/issues/894)
- [Maa issue #1086](https://github.com/MaaXYZ/MaaFramework/issues/1086)
- [Maa PR #903](https://github.com/MaaXYZ/MaaFramework/pull/903)

借鉴：

- next/on_error/timeout/rate_limit/preDelay/postDelay/repeat/ROI/OCR/TemplateMatch 等语义。
- 资源 overlay。
- preset 任务组合。

禁止照搬：

- WithCursorPos，会移动真实鼠标。
- WithWindowPos，会移动窗口。
- Mouse Lock Follow。
- ADB/PlayCover 运行栈。
- 固定 1280×720 ROI。
- 启动时自动安装依赖。
- 明文 API key 注入任务参数。

### 19.8 AutoHotkey

- [ControlClick](https://www.autohotkey.com/docs/v2/lib/ControlClick.htm)
- [ControlSend](https://www.autohotkey.com/docs/v2/lib/ControlSend.htm)

官方也说明自定义控件和修饰键存在兼容性限制，进一步证明不能承诺所有游戏都支持无干扰后台输入。

### 19.9 许可证和合规

- Maa_MHXY_MG 当前本地仓库声明 MIT，但复制代码仍需保留声明。
- MaaFramework 为 LGPL，MaaAssistantArknights 为 AGPL，不能直接复制 AGPL 代码到未确认许可证的项目。
- OpenCV、Tesseract、PaddleOCR 常见发行采用 Apache 2.0，打包时仍需保留许可证和 NOTICE。
- 主项目当前没有根 LICENSE，公开分发前必须明确项目许可证。
- 游戏截图和模板的版权不因代码仓库许可证自动解决。
- 未找到足够可靠的梦幻西游官方自动化许可依据。无前台干扰不等于符合游戏条款或反作弊规则，账号风险必须单独披露。

## 20. 清理与磁盘策略

当前仓库约 48 至 52 GiB，主要由 26 个 `src-tauri/target*` 目录构成。另有：

- captures 约 130 MiB
- reports 约 100 MiB
- crop plans 约 56 MiB
- logs 约 2.3 MiB
- node_modules 约 37 MiB

本轮不得清理，因为大部分属于历史会话或验收证据，归属和保留需求不明确。

后续单独执行磁盘清理任务：

1. 生成所有 target 目录清单。
2. 记录大小、创建时间、最近写入、对应 commit 和是否有运行中 exe。
3. 检查是否包含唯一 release/NSIS 证据。
4. 检查是否被当前进程使用。
5. 把候选分成“可证明本轮产生”“历史但可由 commit 重建”“唯一证据”“归属不明”。
6. 只对用户明确确认的目录执行删除。
7. 不使用 `target-*` 宽泛模式批量删除。
8. 删除后重新核验运行进程和 git 状态。

长期构建策略：

- 使用一个共享 Cargo target 目录。
- release 证据只保留对应稳定 commit 的一份。
- 每个证据包记录 exe hash，不依赖保留全部编译中间文件。
- reports 有保留策略，失败报告和正式验收长期保留，临时 preflight 可归档。

## 21. 最终交付门槛

项目只有同时满足以下条件，才能称为“完全可用”：

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

## 22. 后续 agent 开工清单

后续 agent 开始任何编码前必须逐项确认：

- [ ] 已读本文件全部内容。
- [ ] 已读当前 `git status --short --ignored`。
- [ ] 已确认 HEAD 和 origin/main。
- [ ] 已确认当前控制器和游戏 PID。
- [ ] 已确认当前运行控制器是否为当前 commit。
- [ ] 已确认真实工作区 schema 和 hash。
- [ ] 已创建或确认迁移前独立备份。
- [ ] 已选择本轮唯一纵向切片。
- [ ] 已写安全边界和停止条件。
- [ ] 已限制子代理只读范围。
- [ ] 已准备单元测试和实机证据格式。
- [ ] 已确认不会使用全局输入或真实鼠标兼容方案。

开发完成后必须逐项确认：

- [ ] UI 使用当前源码真实启动验证。
- [ ] 当前二进制 hash 已记录。
- [ ] 单步观察通过。
- [ ] 单步后台测试通过或明确阻断。
- [ ] 前台 HWND 见证通过。
- [ ] 鼠标坐标见证通过。
- [ ] 对照窗口通过。
- [ ] 完整任务通过。
- [ ] 失败注入通过。
- [ ] 重启持久化通过。
- [ ] 所有测试按风险执行。
- [ ] 子代理已完成或中断。
- [ ] `git status --short --ignored` 已复核。
- [ ] 生成产物已列出。
- [ ] 没有清理归属不明内容。
- [ ] commit 已推送并记录完整 hash。

## 23. 当前建议的第一项编码任务

不要继续增加新步骤类型。第一项编码任务应是一个组合安全切片：

1. 保护真实 v6 工作区并建立迁移 fixture。
2. 修复 UI 默认尺寸下任务/步骤不可达。
3. 删除“空队列回退当前任务”。
4. 分离预览窗口和运行批次。
5. 修复预览来源竞态。
6. 前端原子占位 session。
7. 后端增加 per-HWND 互斥。
8. 新增运行计划确认。
9. 新增单步只读测试入口。
10. 完成当前 release 应用启动和截图证据。

这一切片完成后，才进入“家园活力”真实纵向任务。

## 24. 审计来源摘要

本方案合并了以下只读审计：

- 前端/UI/UX：布局不可达、误跑风险、预览竞态、缺少单步调试、可访问性和单体维护风险。
- Rust/输入安全：per-HWND 互斥、严格捕获、模板性能、取消、身份、键盘消息和管理员 handoff。
- 任务模型/runner：`retry_until` 假成功、恢复边界、timeout 失效、snapshot 占位和样例计划态。
- 持久化：future schema、迁移链、保存协调、SQLite、素材文件化和窗口 profile。
- 测试/验收：旧应用、旧 v6 工作区、无当前 HEAD 端到端证据和完整 live 矩阵。
- 仓库/运行态：tracked 干净、历史构建占用约 48 至 52 GiB、当前旧控制器和两个游戏窗口。
- 参考项目：screen-watch 的模块边界和证据体系，Maa 的声明式流程和资源 overlay。
- 外部官方资料：Win32、WGC、PrintWindow、OpenCV、OCR、Tauri、SQLite、Power Automate Desktop 和 MaaFramework。

所有子代理均未提交 commit。除外部资料审计访问官方网站和 GitHub 外，其余审计均无网络访问。子代理未修改、创建或删除项目文件，未启动或停止应用和游戏进程。

## 25. 当前实施进度补充（2026-07-12）

本文件最初完成时是审计和实施总方案，不是实时进度页。此后项目已经按 P0-P2 推进，第 23 节“当前建议的第一项编码任务”不能继续被理解为尚未开始。

当前权威停点是 `P2/P2-S2`：

- P0/P0-S1 已验证：两个真实 v6 文件分别完成不可覆盖备份和 SHA-256 校验；匿名 fixture、v6 到 v9 normalization、引用完整性和幂等验证通过。
- P1-S1 至 P1-S5 已验证：空队列误跑、session 占位、per-HWND FIFO、cancel/deadline、模板 checkpoint、严格捕获策略和有限 OCR worker/队列已完成代码与自动门禁。
- P2-S1 已验证：默认/最小窗口的布局裁切、列表轨道、检查器 tabs 和键盘焦点契约已修复。
- P2-S2 已完成 Playwright 基础设施、五个视口和 10 个测试发现，但尚未启动 localhost preview 并实际执行测试；四个验收条件仍 pending。
- P3-P9 尚未完成，当前 HEAD 应用、真实 AppData 迁移重启、真实游戏输入、双窗口隔离和完整任务后置状态均不得宣称通过。

恢复和交接请先读：

- `docs/execution/STATUS.md`：机器台账生成的当前停点。
- `docs/current-progress-and-handoff.md`：历史任务、累计实现、本轮交接和风险边界。
- `docs/next-agent-goal-prompt.md`：可直接放入长期 Goal 的完整执行提示词。

本补充不改写前文的目标架构和最终门槛。冲突时仍按“当前源码/Git/测试/构建/实际运行 > 当前证据和台账 > 本主方案 > 历史线程”裁决。
