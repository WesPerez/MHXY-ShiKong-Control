# 当前真实进度与交接

更新时间：2026-07-12

本页用于回答三个问题：历史任务做了什么、当前长期项目累计做到哪里、本轮交接做了什么。恢复时仍以 `docs/execution/STATUS.md`、当前源码、Git、测试、构建和实际运行结果为最高权威。

## 1. 用户最终目标

交付一个真正可用的 Windows 桌面任务编排器，用于对多个“梦幻西游：时空”窗口执行互不干扰的后台自动化：

- 用户可低成本创建、组合、排序和复用任务、步骤与识别目标。
- 每个游戏窗口拥有独立队列；同一 HWND 严格串行，不同 HWND 可并行。
- 输入只定向到经过身份复核的目标 HWND，不抢焦点、不移动真实鼠标、不污染用户正在使用的前台键盘。
- OCR、模板匹配、截图、条件、循环、恢复、任务跳转和失败报告形成可观察闭环。
- 页面在默认和最小窗口下功能可达，常用操作少、状态清楚、失败原因可定位。
- 真实工作区可迁移、可重启保留；最终有真实应用、至少两个游戏窗口、失败矩阵、构建、打包、commit 和 push 证据。

## 2. 历史任务 019f4aba 的工作

历史任务 `019f4aba-edef-76e2-9b65-0dac9a270872` 完成的是审计、方案和长期项目治理基础，不是最终产品实现：

- 读取更早任务线索并以当时源码、Git、测试、进程和运行结果校正历史描述。
- 并行审计前端、Rust/Tauri、任务模型、持久化、后台输入、多窗口、测试、参考项目和外部官方资料。
- 用真实浏览器渲染核验 `1460x880` 和 `920x680`，确认旧工作台存在固定高度和 `overflow: hidden` 导致的功能不可达。
- 当时验证 Node 63 项、Python 12 项、Rust 55 项通过；两个真实输入测试仍 ignored，最新 live 报告没有实际发送输入。
- 生成 2295 行、约 79 KB 的 `docs/project-audit-and-master-plan.md`，建立 P0-P9、15 类步骤语义、目标架构、首批真实任务和最终交付门槛。
- 创建并验证全局 `$orchestrate-long-projects` 技能；技能仓库提交 `1a551a4c544eaa9a460daf35c9ea800f932d7e41` 不属于本主项目。
- 没有修改主项目产品代码，没有形成当前 HEAD 应用接管游戏的端到端通过证据，也没有提交或推送主项目改动。

历史任务当时对“源码表面能力 60%-70%、可交付产品 30%-40%”的估计只是当时审计判断，不是当前百分比，也不能替代下面的逐阶段事实。

## 3. 此后累计实现进度

### P0/P0-S1：已验证

- 真实 `workspace.json` 和原有 `workspace.json.bak` 已分别创建不可覆盖备份。
- EVD-0029：主文件源/目标 SHA-256 均为 `445BE6550B813DCA8B783DB6DC2F61C633234B41C410703DE70BEB810B6DD8D3`。
- EVD-0030：旧 `.bak` 源/目标 SHA-256 均为 `912454620A3CFD57FF577EB5086B7AABFC8B1EED30A5671018BFC7EBFF3D59EC`。
- 已建立匿名 v6 fixture：`scripts/fixtures/workspace-v6-anonymized.json`，保持 5 workflows / 63 steps / 27 targets。
- v6 到当前 v9 normalization、引用完整性和幂等测试已通过。
- 这只能证明备份和离线迁移基线；真实 AppData 迁移、应用重启回读仍未验证。

禁止重复创建相同 P0 备份。`execution:preflight-p0` 的通用 `nextAction` 仍会建议创建新备份，它不感知阶段完成状态；以 EVD-0029、EVD-0030、CP-0005 和当前源 hash 为准。

### P1：已验证

- P1-S1：删除空队列隐式回退当前任务；starting session 使用原子占位。
- P1-S2：实现 per-HWND FIFO；同 HWND 串行、跨 HWND 并行，并加入 cancel/deadline。
- P1-S3：模板匹配加入周期 checkpoint；session 级 `commit_input`；取消或超时后零输入。
- P1-S4：自动控制严格绑定目标窗口捕获；桌面 fallback 只允许 preview；Window GDI 未验证时 fail closed。
- P1-S5：OCR 固定 2 workers、队列容量 8、`try_send` backpressure、queued/running 取消和超时、迟到结果丢弃。

这些是代码、单元/集成测试和静态安全门证据。真实游戏输入测试仍 ignored，不能写成“游戏实测已通过”。

### P2-S1：已验证

- 修复固定高度和外层隐藏溢出造成的裁切。
- 修复步骤面板存在 5 个子项但只分配 4 行的问题。
- 任务列表和步骤列表拥有非零最小轨道。
- 新增任务、步骤、目标 inspector tabs 和键盘焦点契约。

### P2-S2：当前停点

已完成：

- 锁定 `@playwright/test@1.61.1`。
- 新增 `playwright.workbench.config.mjs`。
- 新增 5 个视口 x 2 类，共 10 个 Playwright tests。
- 覆盖 `1460x880`、`1280x720`、`1120x720`、`920x680`、`820x720`。
- 测试发现、Node、Python 和 Vite 静态门通过，对应 EVD-0074、EVD-0075、EVD-0076。

未完成：

- 尚未启动当前工作树的 localhost preview。
- 尚未实际运行 `npm run test:ui-viewports`。
- 尚未生成并人工复核当前工作树截图和 viewport metrics。
- P2-S2-C1 至 P2-S2-C4 均为 pending。

唯一下一动作：启动本任务拥有的 localhost preview，实际运行五视口 Playwright，复核截图和指标，修复发现的问题并完成 P2-S2 闭环。

### P3-P9：未完成

- P3：health-verified WGC/PrintWindow provider、黑帧/旧帧检测和严格视觉引擎。
- P4：首个“家园活力”真实纵向任务，从 UI 配置到游戏后置状态的完整闭环。
- P5：持久化方案落地、素材文件化、真实迁移和重启验证。
- P6：第二至第五个真实任务。
- P7：两个真实窗口不同队列并行隔离、暂停/继续/取消。
- P8：5-10 个可重复真实任务、失败注入和完整 release gate。
- P9：有证据的源码清理、打包、稳定提交和推送。

## 4. 本轮交接任务做了什么

本轮没有继续产品编码，完成的是恢复、纠错和下一 Agent 交接：

- 完整读取 `$orchestrate-long-projects` 及其恢复、台账和真实运行规则。
- 复核历史任务原文、当前 STATUS/state、主方案、Git、P0 preflight 和当前进程。
- 重新运行 `execution:resume-check` 与 `audit:execution-state`：205 events、76 evidence、34 个历史 warning，审计通过。
- 确认 `HEAD == origin/main == 3eef34f8c4b115c94e2c3cd6adb93cf329a60ef9`。
- 当前未发现 `mhxy-shikong-control.exe` 或 `MyGame_x64r.exe`；STATUS 中旧 PID 已过期，只能作为历史线索。
- 新增本页和 `docs/next-agent-goal-prompt.md`，并补充 README、主方案和执行台账入口。
- 未启动应用或游戏、未发送输入、未修改 AppData、未停止进程、未清理 ignored 产物、未 commit/push。

## 5. 当前风险和证据边界

- 工作树包含 P0-P2 的大量未提交改动；主项目 HEAD 仍是旧基线，不能只按 commit 判断当前实现。
- 当前有效自动证据只证明到 P2-S2 静态门，真实 UI、Tauri、真实游戏均未在当前工作树上完成验证。
- P0 备份已完成，但 STATUS 曾有过期文案；不要因此重复备份或覆盖已有备份。
- 当前没有游戏进程。下一 Agent 若要做双窗口验收，必须先枚举并复用合法实例；少于两个时才按授权补启动到两个。
- `reports/`、`captures/`、`target*/`、`dist/`、`node_modules/` 等 ignored 产物归属不完全明确，全部保留。
- 后台技术可行不等于符合游戏条款或反作弊规则；真实动作必须最小、可观察、可恢复，并披露账号风险。
- 不允许使用 `SendInput`、`SetCursorPos`、抢前台焦点或广播输入作为兼容回退。

## 6. 下一 Agent 入口

把 `docs/next-agent-goal-prompt.md` 的完整内容放入 Codex Goal。该提示词已经提供完成 P0-P9 所需的仓库写入、应用运行、游戏实例、经验证 HWND 后台输入、commit 和 push 授权，同时保留目标身份、数据、凭据和不可逆动作的 fail-closed 门禁。

