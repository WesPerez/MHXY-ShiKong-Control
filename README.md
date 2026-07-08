# 时空任务编排器

`MHXY-ShiKong-Control` 是放在 `E:\Project\Common` 下的独立 Tauri/Rust 项目。当前阶段已经不再把首屏做成 Maa 迁移控制台，而是改成通用任务/步骤编排器，用来逐步补充“梦幻西游：时空”的自动化任务。

历史保留已经推到 GitHub：

- `dec5823`：保留前 20 多小时形成的旧接管台代码。
- `676884a`：新增图标、托盘、关闭隐藏、单实例唤醒。
- `44ce5cd`：把界面改成通用任务编排器。
- `e18c3fa`：移除前台置顶入口，收紧输入安全。

## 当前能力

- 应用标题和托盘提示为“时空任务编排器”。
- Windows bundle 图标、任务栏图标、标题栏图标、托盘图标已配置。
- 点窗口关闭按钮默认隐藏到托盘，不退出进程。
- 托盘右键菜单提供“显示主窗口”和“退出”，其中“退出”才是真退出。
- 多次启动同一个 exe 会唤醒已运行实例，不会保留多个主进程。
- 界面保留目标窗口列表、窗口预览、截图/ROI、任务定义、步骤编排、步骤属性和运行记录。
- 当前不内置任何实际任务，后续按任务逐个补。
- 默认输入路径使用 hwnd 后台消息，不移动真实鼠标，不占用真实键盘焦点。
- 同一个 hwnd 有运行锁，避免一个游戏窗口被两个任务同时接管；不同 hwnd 可以独立运行。

## 任务模型

当前方向见 [docs/workflow-model.md](docs/workflow-model.md)。

核心原则：

- 任务是可版本化的工作流定义，不是一串写死的截图点击。
- 步骤由 `detect_page`、`image_click`、`mouse_move`、`hotkey`、`restore` 等类型组成。
- 每步都要有目标、成功确认、超时、重试、失败策略和成功流转。
- 图片、OCR、颜色、按钮、页面等识别目标后续应抽成共享目标库。
- 恢复到初始界面应成为通用能力，而不是每个任务各写一遍。

## 输入安全

默认运行路径必须避免影响用户正在操作的鼠标和键盘：

- 禁止 `SendInput`、`SetCursorPos`、`mouse_event`、`keybd_event` 这类真实输入注入。
- 任务执行不调用 `SetForegroundWindow` 或 `BringWindowToTop`。
- 点击、拖拽、文本、快捷键通过目标 hwnd 的 `PostMessageW` 投递。
- 需要管理员权限时由应用提示并通过 UAC 重启，不通过鼠标键盘绕过。

可运行审计：

```powershell
python scripts\audit_input_safety.py --json
```

## 开发命令

```powershell
cd E:\Project\Common\MHXY-ShiKong-Control
npm install
npm run build
cd src-tauri
cargo check
cargo test
```

打包：

```powershell
cd E:\Project\Common\MHXY-ShiKong-Control
npm run tauri:build
```

release exe:

```text
src-tauri\target\release\mhxy-shikong-control.exe
```

NSIS 安装包：

```text
src-tauri\target\release\bundle\nsis\时空任务编排器_0.1.0_x64-setup.exe
```

## 目录关系

```text
E:\Project\Common
├─ Maa_MHXY_MG              # 原 Maa 项目，仅作为历史参考/迁移来源
├─ screen-watch-ocr-tauri   # OCRRUST 参考项目
└─ MHXY-ShiKong-Control     # 当前项目
```

## 后续路线

1. 先补共享 `targets` 识别目标库。
2. 再补共享 `restore` 恢复流程。
3. 然后按一个任务一个任务接入，每个任务只组合已有目标和步骤。
4. 每补一个任务都保留 dry-run、运行报告和输入安全审计。
