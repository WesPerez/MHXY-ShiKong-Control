# mhxy-shikong-control Agent 执行规则

本仓库是一个会接触真实游戏窗口、真实 AppData 和后台 HWND 输入的长期项目。任何 agent 开始工作前，必须先建立可恢复、可核验的现场，不得只凭聊天摘要继续。

## 开工顺序

1. 阅读 `docs/execution/STATUS.md`，确认当前唯一切片、阻塞项和下一动作。
2. 运行只读 `npm run execution:resume-check`；退出码非 `0` 时禁止副作用动作。
3. 阅读 `docs/execution/PROTOCOL.md`，执行其中的恢复协议和安全门。
4. 只阅读 `docs/project-audit-and-master-plan.md` 中当前阶段相关章节；需要全局方案时再读全文。
5. 运行 `npm run audit:execution-state`。
6. 运行 `git status --short --ignored`，核对 HEAD、dirty 文件、ignored 产物和进程现场。
7. 历史 Codex task 只作为线索；冲突时使用以下权威顺序：

```text
当前源码、Git 和实际运行结果
> 已落盘测试、截图、报告和哈希证据
> docs/execution/state.json
> docs/execution/STATUS.md
> Codex task 历史或摘要
```

## 单写入器

- 只有主代理可以修改 `docs/execution/` 下的实时状态、账本和 checkpoint。
- 子代理默认只读；需要写代码时必须按文件明确所有权，但仍不得写进度账本。
- 通过 `python scripts/execution_progress.py ...` 更新状态。`STATUS.md` 是生成文件，禁止手工编辑。
- `events.jsonl` 和 `evidence.jsonl` 只追加，不修改旧行。
- 同一时间只允许一个产品纵向切片处于 `in_progress`。

## 进度与验收

- 开始切片前必须登记范围、非目标、安全边界、验收条件和唯一下一动作。
- 每个 20-30 分钟的持续工作窗口，或每次重要状态变化后，至少追加一条有信息量的事件；不要为每条只读命令制造日志噪声。
- 给用户的阶段汇报至少说明：完成了什么、当前在做什么、下一步、阻塞、风险、是否真实启动当前版本、是否真实发送游戏输入。
- 禁止用单一百分比表示完成。必须分开报告：代码表面能力、自动验证、当前提交构建、当前提交应用启动、真实 HWND 输入、游戏后置结果、前台无干扰、双窗口隔离、重启持久化。
- `preflight_only`、`input_not_allowed`、静态测试通过、`PostMessageW` 返回成功都不能单独证明游戏功能完成。

## 副作用动作

以下动作执行前必须运行 `action-start` 写入 intent，执行后必须运行 `action-finish`：

- 向游戏窗口发送后台输入。
- 启动或停止长期进程。
- 写入、迁移、覆盖 AppData。
- commit、push、发布或修改外部状态。
- 删除、移动、覆盖文件或清理产物。
- 修改配置、环境变量或凭据。

异常中断后，未完成动作必须视为 `unknown_after_interruption`，先 reconciliation，禁止盲目重试。
AppData 写入、进程启动/停止、push、配置变化和游戏输入使用同机 external lease；非 owner worktree/clone 没有 token，不能释放或接管。

## 游戏与前台安全

- 默认不发送真实游戏输入。
- 真实输入前必须有 `pre_live` 类型的 state snapshot、明确的目标 HWND 身份、管理员权限检查、用户授权、执行前后前台 HWND/鼠标位置证据和后置状态验证方案。
- 只允许定向 HWND 后台路径；禁止 `SendInput`、`SetCursorPos`、`mouse_event`、`keybd_event`、`SetForegroundWindow` 和抢焦点方案。
- 每步输入前复核 title、PID、process、client size、权限和启动时身份快照。
- 用户的前台鼠标键盘始终优先；证据不足时只能标记“部分验证”，不得写“完全不影响”。

## Git 与 checkpoint

- 未提交状态只能创建 `state_snapshot`，不能冒充可回滚的 Git checkpoint。
- 只有指向可解析 commit 且绑定验证证据的 checkpoint 才可标为 `git_checkpoint`。
- 不为每次编辑自动提交。一个纵向切片通过所需门禁、无未决副作用后再提交。
- commit、push、handoff、fork、上下文压缩、长时间暂停和真实输入前必须创建 checkpoint。
- ignored 的 AppData、截图、报告、构建目录不会自动随 worktree/handoff 移动，恢复时必须单独核对。

## 子代理与收尾

- 子代理必须返回完整审计摘要：只读/写入、文件、创建/删除、缓存/日志/构建物、下载、网络、配置/环境变量/凭据、进程/服务、测试、commit、需清理项；无则明确写 `none`。
- 主代理必须复核子代理报告，不能直接采信。
- 最终回复前等待或中断所有子代理，运行 `npm run audit:execution-state` 和 `git status --short --ignored`。
- 不能证明属于本轮的文件、目录、进程、窗口、页签和构建物不得清理或停止。
- 最终报告必须包含：文件改动、子代理改动、生成产物、下载、配置变化、运行进程、清理/保留、测试、commit hash 和 push 状态。

## 常用命令

```powershell
npm run execution:render
npm run execution:resume-check
npm run execution:preflight-p0
npm run audit:execution-state
python scripts/execution_progress.py reconcile --summary "..." --increment-attempt --next-action "..."
python scripts/execution_progress.py run-evidence --profile node-all --claim "..."
python scripts/execution_progress.py note --type decision --summary "..." --next-action "..."
python scripts/execution_progress.py begin-slice --phase P0 --slice P0-S1 --title "..." --next-action "..." --criterion "P0-S1-C1|test=..."
python scripts/execution_progress.py checkpoint --label handoff --type state_snapshot --reason "..." --safe-to-resume
python scripts/execution_progress.py repair-tail --ledger events --summary "隔离已确认的截断尾片段" --confirm-quarantine-truncated-tail
```
