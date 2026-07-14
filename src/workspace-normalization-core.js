import { normalizeRecoveryAction } from "./control-flow-core.js";
import { normalizeStepParams, syncStepParamsToLegacy } from "./step-params-core.js";
import { normalizeTarget as normalizeTargetLibraryCore } from "./target-library-core.js";

export const WORKSPACE_SCHEMA_VERSION = 9;
export const WORKSPACE_DEFAULT_IMAGE_THRESHOLD = 0.86;

export const WORKSPACE_STEP_DEFAULTS = {
  detect_page: { name: "检测页面", target: "page.home.ready", command: "match=image_or_ocr", expect: "ready=true", timeoutMs: 3000, retry: 2, onFail: "restore" },
  wait_image: { name: "等待图像", target: "target.image", command: "threshold=0.86", expect: "visible", timeoutMs: 5000, retry: 2, onFail: "retry" },
  image_click: { name: "图像点击", target: "button.target", command: "button=left; point=center", expect: "screen.changed", timeoutMs: 2600, retry: 1, onFail: "retry" },
  double_click: { name: "后台双击", target: "button.target", command: "button=left; point=center; mode=hwnd-message", expect: "double_click.accepted", timeoutMs: 1800, retry: 0, onFail: "stop" },
  ocr_assert: { name: "OCR 确认", target: "text.keyword", command: "lang=zh; roi=auto", expect: "text_found", timeoutMs: 4200, retry: 2, onFail: "restore" },
  click: { name: "后台点击", target: "x=0,y=0", command: "button=left; mode=hwnd-message", expect: "click.accepted", timeoutMs: 1300, retry: 0, onFail: "stop" },
  hotkey: { name: "快捷键", target: "ALT+N", command: "mode=hwnd-key", expect: "panel.open", timeoutMs: 1200, retry: 0, onFail: "stop" },
  text_input: { name: "文本输入", target: "要输入的文本", command: "mode=hwnd-char", expect: "text.sent", timeoutMs: 1200, retry: 0, onFail: "stop" },
  delay: { name: "延迟等待", target: "800ms", command: "reason=animation", expect: "time.elapsed", timeoutMs: 800, retry: 0, onFail: "skip" },
  condition: { name: "条件判断", target: "last.score", command: "guard=true", expect: "condition.checked", timeoutMs: 1000, retry: 0, onFail: "skip" },
  loop: { name: "有限循环", target: "control.loop", command: "mode=control-flow", expect: "bounded.repeat", timeoutMs: 0, retry: 0, onFail: "stop" },
  retry_until: { name: "重试直到", target: "page.target.ready", command: "interval=800ms", expect: "ready=true", timeoutMs: 8000, retry: 5, onFail: "restore" },
  snapshot: { name: "截图记录", target: "window.client", command: "dry-run log only", expect: "snapshot.recorded", timeoutMs: 1000, retry: 0, onFail: "skip" },
  task_jump: { name: "任务跳转", target: "workflow.next", command: "mode=same-window-queue", expect: "jump.workflow", timeoutMs: 0, retry: 0, onFail: "stop" },
  restore: { name: "恢复状态", target: "restore.home", command: "safe sequence", expect: "page.home.ready", timeoutMs: 6000, retry: 1, onFail: "stop" },
};

const stepFailActions = new Set(["stop", "retry", "skip", "restore"]);
const workflowConcurrencyOptions = new Set(["per-window-exclusive"]);
const targetBackedStepTypes = new Set(["image_click", "double_click", "wait_image", "detect_page", "click", "ocr_assert", "retry_until"]);
const controlFlowStepReferenceFields = ["targetStepId", "elseTargetStepId", "recoveryStepId"];
const controlFlowWorkflowReferenceFields = ["jumpWorkflowId"];

function now(options) {
  return typeof options.now === "function" ? options.now() : new Date().toISOString();
}

function randomId(prefix, options) {
  if (typeof options.randomId === "function") return options.randomId(prefix);
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

function optionsWithDefaults(options = {}) {
  return {
    currentSchemaVersion: options.currentSchemaVersion || WORKSPACE_SCHEMA_VERSION,
    defaultImageThreshold: options.defaultImageThreshold ?? WORKSPACE_DEFAULT_IMAGE_THRESHOLD,
    stepDefaults: options.stepDefaults || WORKSPACE_STEP_DEFAULTS,
    targetTitle: options.targetTitle || "梦幻西游：时空",
    seedFactory: options.seedFactory,
    randomId: options.randomId,
    now: options.now,
  };
}

export function normalizeWorkspaceCore(value, rawOptions = {}) {
  const options = optionsWithDefaults(rawOptions);
  const source = value && typeof value === "object" ? value : {};
  const seed = typeof options.seedFactory === "function" ? options.seedFactory() : { workflows: [], targets: [] };
  const workflows = Array.isArray(source.workflows)
    ? source.workflows.map((item) => normalizeWorkflowCore(item, options))
    : seed.workflows || [];
  const activeWorkflowId = workflows.some((item) => item.id === source.activeWorkflowId)
    ? source.activeWorkflowId
    : workflows[0]?.id || null;
  const targetSource = [
    ...(Array.isArray(source.assets) ? source.assets : []),
    ...(Array.isArray(source.targets) ? source.targets : []),
  ];
  const targets = targetSource.length
    ? mergeTargetCatalogCore(targetSource.map((item) => normalizeTargetCore(item, options)), workflows, options)
    : createTargetCatalogFromWorkflowsCore(workflows, options);
  return {
    schemaVersion: options.currentSchemaVersion,
    activeWorkflowId,
    workflows,
    assignments: normalizeAssignmentsCore(source.assignments, workflows, options),
    targets,
    runHistory: Array.isArray(source.runHistory) ? source.runHistory.slice(0, 80) : [],
    createdAt: source.createdAt || now(options),
    updatedAt: source.updatedAt || now(options),
  };
}

export function normalizeWorkflowCore(value, rawOptions = {}) {
  const options = optionsWithDefaults(rawOptions);
  const steps = Array.isArray(value?.steps) ? value.steps.map((item) => normalizeStepCore(item, options)) : [];
  const concurrency = String(value?.targetPolicy?.concurrency || "per-window-exclusive");
  return {
    schemaVersion: options.currentSchemaVersion,
    id: String(value?.id || randomId("wf", options)),
    name: String(value?.name || "未命名任务"),
    category: String(value?.category || "未分类"),
    description: String(value?.description || ""),
    tags: Array.isArray(value?.tags) ? value.tags.map(String) : [],
    initialCheck: String(value?.initialCheck || "page.home.ready"),
    targetPolicy: {
      titleNeedle: String(value?.targetPolicy?.titleNeedle || options.targetTitle),
      inputMode: String(value?.targetPolicy?.inputMode || "hwnd-message"),
      concurrency: workflowConcurrencyOptions.has(concurrency) ? concurrency : "per-window-exclusive",
    },
    steps,
    createdAt: value?.createdAt || now(options),
    updatedAt: value?.updatedAt || now(options),
  };
}

export function normalizeStepCore(value, rawOptions = {}) {
  const options = optionsWithDefaults(rawOptions);
  const type = options.stepDefaults[value?.type] ? value.type : "detect_page";
  const defaults = options.stepDefaults[type];
  const item = {
    id: String(value?.id || randomId("step", options)),
    type,
    name: String(value?.name || defaults.name),
    target: String(value?.target || defaults.target),
    command: String(value?.command || defaults.command),
    expect: String(value?.expect || defaults.expect),
    timeoutMs: Number(value?.timeoutMs ?? defaults.timeoutMs),
    retry: Number(value?.retry ?? defaults.retry),
    onFail: normalizeStepFailAction(value?.onFail, defaults.onFail),
    recoveryAction: normalizeRecoveryAction(value?.recoveryAction),
    enabled: value?.enabled !== false,
    requiresManualConfirmation: value?.requiresManualConfirmation === true,
    targetId: value?.targetId ? String(value.targetId) : value?.assetId ? String(value.assetId) : "",
    notes: String(value?.notes || ""),
    params: normalizeStepParams({
      ...value,
      type,
      target: String(value?.target || defaults.target),
      command: String(value?.command || defaults.command),
      expect: String(value?.expect || defaults.expect),
      timeoutMs: Number(value?.timeoutMs ?? defaults.timeoutMs),
    }),
  };
  for (const field of controlFlowStepReferenceFields) item[field] = value?.[field] ? String(value[field]) : "";
  for (const field of controlFlowWorkflowReferenceFields) item[field] = value?.[field] ? String(value[field]) : "";
  const maxIterations = Number(value?.maxIterations ?? 0);
  item.maxIterations = Number.isFinite(maxIterations) && maxIterations >= 0 ? Math.floor(maxIterations) : 0;
  return Object.assign(item, syncStepParamsToLegacy(item));
}

export function normalizeTargetCore(value, rawOptions = {}) {
  const options = optionsWithDefaults(rawOptions);
  return normalizeTargetLibraryCore(value, {
    defaultImageThreshold: options.defaultImageThreshold,
    randomId: (prefix) => randomId(prefix, options),
    now: () => now(options),
  });
}

export function mergeTargetCatalogCore(targets, workflows, options = {}) {
  const byId = new Map();
  for (const target of createTargetCatalogFromWorkflowsCore(workflows, options)) byId.set(target.id, target);
  for (const target of targets) byId.set(target.id, target);
  return [...byId.values()];
}

export function createTargetCatalogFromWorkflowsCore(workflows, rawOptions = {}) {
  const options = optionsWithDefaults(rawOptions);
  const byId = new Map();
  for (const workflow of workflows || []) {
    for (const item of workflow.steps || []) {
      const id = catalogTargetIdForStep(item);
      if (!id || byId.has(id)) continue;
      byId.set(id, normalizeTargetCore({
        id,
        name: friendlyTargetName(id),
        kind: targetKindForStep(item),
        match: {
          threshold: commandValue(item.command, "threshold") || defaultThresholdForStep(item, options),
          scope: commandValue(item.command, "roi") || "window",
        },
        click: { button: normalizedButton(item.command), point: commandValue(item.command, "point") || "center" },
        texts: item.type === "ocr_assert" ? [item.target] : [],
        safety: { requiresManualConfirmation: item.requiresManualConfirmation === true },
        note: "由任务步骤生成的逻辑目标，可直接粘贴图片或绑定 ROI",
      }, options));
    }
  }
  return [...byId.values()];
}

export function normalizeAssignmentsCore(value, workflows = [], rawOptions = {}) {
  const options = optionsWithDefaults(rawOptions);
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  const workflowIds = new Set(workflows.map((item) => item.id));
  return Object.fromEntries(
    Object.entries(value)
      .map(([hwnd, assignment]) => [String(hwnd), normalizeAssignmentCore(hwnd, assignment, workflowIds, options)])
      .filter(([, assignment]) => assignment.queue.length > 0),
  );
}

export function normalizeAssignmentCore(hwnd, value, workflowIds = new Set(), rawOptions = {}) {
  const options = optionsWithDefaults(rawOptions);
  const source = value && typeof value === "object" ? value : {};
  const windowIdentity = normalizeWindowIdentityCore(source.windowIdentity || { ...source, hwnd });
  const legacyWorkflowId = source.workflowId ? String(source.workflowId) : "";
  const queue = Array.isArray(source.queue)
    ? source.queue.map((item) => normalizeQueueItemCore(item, options))
    : legacyWorkflowId
      ? [normalizeQueueItemCore({ workflowId: legacyWorkflowId, addedAt: source.assignedAt }, options)]
      : [];
  return {
    hwnd: source.hwnd ?? hwnd,
    title: String(source.title || ""),
    processId: source.processId ?? null,
    processName: String(source.processName || windowIdentity.processName || ""),
    clientWidth: Number(source.clientWidth || windowIdentity.clientWidth || 0),
    clientHeight: Number(source.clientHeight || windowIdentity.clientHeight || 0),
    elevated: typeof source.elevated === "boolean" ? source.elevated : windowIdentity.elevated,
    display: String(source.display || hwnd),
    windowIdentity,
    queue: queue.filter((item) => workflowIds.has(item.workflowId)).map((item, index) => ({ ...item, order: index + 1 })),
    assignedAt: String(source.assignedAt || now(options)),
    updatedAt: String(source.updatedAt || source.assignedAt || now(options)),
  };
}

export function normalizeWindowIdentityCore(value) {
  const source = value && typeof value === "object" ? value : {};
  return {
    hwnd: Number(source.hwnd) || 0,
    title: String(source.title || ""),
    processId: Number(source.processId) || 0,
    processName: String(source.processName || ""),
    clientWidth: Number(source.clientWidth) || 0,
    clientHeight: Number(source.clientHeight) || 0,
    elevated: typeof source.elevated === "boolean" ? source.elevated : null,
  };
}

export function normalizeQueueItemCore(value, rawOptions = {}) {
  const options = optionsWithDefaults(rawOptions);
  const source = value && typeof value === "object" ? value : {};
  return {
    id: String(source.id || randomId("queue", options)),
    workflowId: String(source.workflowId || ""),
    enabled: source.enabled !== false,
    order: Number(source.order || 0),
    startDelayMs: normalizedNonNegativeInteger(source.startDelayMs) ?? 0,
    afterDelayMs: normalizedNonNegativeInteger(source.afterDelayMs) ?? 0,
    addedAt: String(source.addedAt || now(options)),
  };
}

function normalizeStepFailAction(value, fallback = "stop") {
  const action = String(value || "").trim();
  if (stepFailActions.has(action)) return action;
  const fallbackAction = String(fallback || "").trim();
  return stepFailActions.has(fallbackAction) ? fallbackAction : "stop";
}

function catalogTargetIdForStep(item) {
  const explicitId = String(item.targetId || item.assetId || "").trim();
  if (explicitId) return explicitId;
  if (!targetBackedStepTypes.has(item?.type) || item.type === "retry_until") return "";
  return isLogicalTargetName(item.target) ? item.target.trim() : "";
}

function isLogicalTargetName(value) {
  const text = String(value || "").trim();
  if (!text || text.includes("=") || durationMsFromText(text) != null) return false;
  if (/^[A-Z]+(?:\+[A-Z0-9]+)+$/i.test(text)) return false;
  return /^[\p{Script=Han}A-Za-z][\p{Script=Han}A-Za-z0-9_.:-]*$/u.test(text);
}

function friendlyTargetName(id) {
  const text = String(id || "").trim();
  const names = { page: "页面", button: "按钮", target: "目标", text: "文本", state: "状态", item: "物品", tab: "页签", entry: "入口", grid: "格子", list: "列表", asset: "素材" };
  const [head, ...tail] = text.split(".");
  const prefix = names[head] || head || "目标";
  return tail.length ? `${prefix} · ${tail.join(".")}` : prefix;
}

function targetKindForStep(item) {
  if (item.type === "ocr_assert") return "ocr";
  if (item.type === "condition" || item.type === "retry_until") return "state";
  if (item.type === "detect_page") return "page";
  if (item.type === "click") return "click_target";
  if (item.type === "double_click") return parsePointText(item.target) ? "click_target" : "image";
  return "image";
}

function defaultThresholdForStep(item, options) {
  return ["image_click", "double_click", "wait_image", "detect_page"].includes(item.type)
    ? options.defaultImageThreshold
    : "";
}

function commandParts(value) {
  return String(value || "").split(";").map((item) => item.trim()).filter(Boolean).map((part) => {
    const splitAt = part.indexOf("=");
    if (splitAt < 0) return { raw: part };
    const key = part.slice(0, splitAt).trim();
    const partValue = part.slice(splitAt + 1).trim();
    return key ? { key, value: partValue } : { raw: part };
  });
}

function commandValue(command, key) {
  const expected = key.toLowerCase();
  for (const part of commandParts(command)) if (part.key?.toLowerCase() === expected && part.value) return part.value;
  return "";
}

function parsePointText(value) {
  let x = null;
  let y = null;
  for (const part of String(value || "").split(/[,\s;]+/).map((item) => item.trim()).filter(Boolean)) {
    const [rawKey, rawValue] = part.split("=");
    if (!rawKey || !/^\d+$/.test(rawValue || "")) continue;
    if (rawKey.toLowerCase() === "x") x = Number(rawValue);
    if (rawKey.toLowerCase() === "y") y = Number(rawValue);
  }
  return x != null && y != null ? { x, y } : null;
}

function durationMsFromText(value) {
  const text = String(value ?? "").trim().toLowerCase();
  if (!text) return null;
  let match = text.match(/^(\d+)ms$/);
  if (match) return Number(match[1]);
  match = text.match(/^(\d+(?:\.\d+)?)s$/);
  if (match) return Math.round(Number(match[1]) * 1000);
  return /^\d+$/.test(text) ? Number(text) : null;
}

function normalizedNonNegativeInteger(value) {
  if (String(value ?? "").trim() === "") return null;
  const number = Number(value);
  return Number.isInteger(number) && number >= 0 ? number : null;
}

function normalizedButton(command) {
  return ["right", "r", "secondary"].includes(commandValue(command, "button").toLowerCase()) ? "right" : "left";
}
