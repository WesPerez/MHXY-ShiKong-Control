# 时空任务编排模型

本文档记录当前重构方向：先做通用任务编排器，不急着搬 Maa 的具体任务。

## 结论

用户提出的方向是对的：任务不应该写成一串彼此复制的图片点击脚本，而应该抽象成“任务定义 + 步骤定义 + 识别目标 + 失败恢复”的通用模型。

但需要补强三点：

1. 任务应更像状态机/工作流，而不是线性图片链。
2. 图片、OCR、颜色、窗口控件等“识别目标”要从步骤里抽出来复用。
3. 每个步骤都要有明确的前置条件、成功确认、失败策略和恢复策略。

这能避免回到旧模式：每个任务独立写一遍，每一步绑定一张图，多个任务明明共享页面/按钮却互不复用。

## 参考模式

这些成熟系统给出的共同方向：

- Temporal 把工作流和活动分开，工作流负责编排，活动负责具体副作用；重试、超时、状态恢复是显式概念。
- UiPath 的 Retry Scope 把“要执行的动作”和“成功条件”分开，只有成功条件满足才算通过。
- Microsoft Power Automate Desktop 将 UI 元素作为可复用资产，而不是把每一步都写死成屏幕坐标。
- Playwright / Selenium 推荐 locator/page object，把页面元素抽象出来，减少重复和脆弱选择器。
- Robot Framework 用 keyword 组合业务流程，底层动作可复用。
- XState 这类状态机模型强调 state、guard、action、transition，适合表达“当前页面不对就恢复到初始界面”。

参考链接：

- Temporal Workflows: https://docs.temporal.io/workflows
- UiPath Retry Scope: https://docs.uipath.com/activities/other/latest/workflow/retry-scope
- Power Automate desktop UI elements: https://learn.microsoft.com/en-us/power-automate/desktop-flows/ui-elements
- Playwright locators: https://playwright.dev/docs/locators
- Playwright page object models: https://playwright.dev/docs/pom
- Selenium page object models: https://www.selenium.dev/documentation/test_practices/encouraged/page_object_models/
- Robot Framework User Guide: https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html
- XState states and transitions: https://stately.ai/docs/states

## 当前一阶段模型

当前前端先实现可编辑的草稿模型，不内置任何实际任务：

```json
{
  "schemaVersion": 1,
  "id": "local-draft",
  "name": "新任务",
  "description": "",
  "initialCheck": "detect_page",
  "restorePolicy": "none",
  "targetPolicy": {
    "titleNeedle": "梦幻西游：时空",
    "inputMode": "hwnd-message",
    "concurrency": "per-window-exclusive"
  },
  "steps": [
    {
      "id": "step-...",
      "name": "检测页面",
      "type": "detect_page",
      "target": "page.home",
      "expect": "page.home.ready",
      "timeoutMs": 3000,
      "retry": 2,
      "onFail": "restore",
      "onSuccess": "next"
    }
  ]
}
```

字段含义：

- `schemaVersion`: 后续任务格式升级时保留迁移空间。
- `initialCheck`: 执行任务前先确认当前页面或状态。
- `restorePolicy`: 页面不对或步骤失败时如何回到初始界面。
- `targetPolicy.inputMode`: 默认使用 hwnd 后台消息，不移动真实鼠标，不抢真实键盘焦点。
- `targetPolicy.concurrency`: 同一 hwnd 同时只允许一个任务，不同 hwnd 可以独立运行。
- `step.type`: 当前支持 `detect_page`、`image_click`、`mouse_move`、`hotkey`、`restore`。
- `step.target`: 动作目标，例如页面、按钮、图片、快捷键或坐标目标的逻辑 id。
- `step.expect`: 成功确认，避免“点了就算完成”。
- `step.onFail`: `stop`、`retry`、`skip`、`restore`。
- `step.onSuccess`: `next`、`finish`、`branch`。

## 下一阶段建议

后续补任务前，先补两个库：

1. `targets` 识别目标库：页面、按钮、图标、文字、颜色区域、快捷键目标。
2. `restore` 恢复库：从未知页面回到初始界面的通用流程。

建议形态：

```json
{
  "targets": {
    "page.home.ready": {
      "kind": "image_or_ocr",
      "roi": [0, 0, 1280, 720],
      "templates": ["home/ready.png"],
      "texts": ["长安", "任务"]
    },
    "button.confirm": {
      "kind": "image",
      "templates": ["common/confirm.png"],
      "click": "center"
    }
  }
}
```

这样多个任务可以引用同一个 `button.confirm`、`page.home.ready`，而不是每个任务复制一份图片和点击逻辑。

## 输入安全原则

默认运行路径必须满足：

- 不调用 `SendInput`、`SetCursorPos`、`mouse_event`、`keybd_event`。
- 不为了任务执行调用 `SetForegroundWindow` 或 `BringWindowToTop`。
- 鼠标、键盘、文本输入都走目标 hwnd 的 `PostMessageW`。
- 同一个 hwnd 只能运行一个任务；不同 hwnd 可以并行。
- 所有任务报告必须记录 hwnd、初始窗口身份、最终窗口身份、截图来源和失败原因。

只有用户明确要求查看或调试时，才考虑临时前台操作；默认应用界面不提供抢前台入口。
