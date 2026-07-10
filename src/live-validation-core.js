const LIVE_VALIDATION_KIND = "mhxy-shikong.live-background-hotkey-validation";
const DEFAULT_OUTPUT_LIMIT = 1200;
const MAX_LIVE_RUN_EVENTS = 20;

export function isLiveValidationEvidence(value) {
  return objectValue(value).kind === LIVE_VALIDATION_KIND;
}

export function liveValidationRunHistoryEntry(evidence, options = {}) {
  const source = objectValue(evidence);
  if (!isLiveValidationEvidence(source)) {
    throw new Error("不是有效的 live 后台热键验收报告");
  }
  const outputLimit = finiteNumber(options.outputLimit, DEFAULT_OUTPUT_LIMIT);
  const runs = arrayValue(source.runs);
  const plannedCommands = arrayValue(source.plannedCommands);
  const tests = arrayValue(source.tests).map(text).filter(Boolean);
  const status = liveValidationHistoryStatus(source.status);
  const generatedAt = text(source.generatedAt || new Date().toISOString());
  const startedAt = text(runs[0]?.startedAt || generatedAt);
  const endedAt = text(runs.at(-1)?.endedAt || generatedAt);
  const durationMs = runs.reduce((sum, run) => sum + finiteNumber(run?.durationMs, 0), 0);
  const stepResults = liveValidationStepResults(source, outputLimit);
  const runEvents = liveValidationRunEvents(source, outputLimit);
  const failureReason = liveValidationFailureReason(source, runs);
  const record = {
    id: text(source.id || `live-validation-${Date.now()}`),
    mode: "live_validation",
    source: "live-validation",
    hwnd: "",
    display: "Live 后台热键验收",
    workflowId: "",
    workflowName: tests.length > 1 ? "Live 串行/并行热键验收" : "Live 后台热键验收",
    workflowIds: tests,
    workflowNames: tests.map(liveValidationTestLabel),
    queueLength: Math.max(1, tests.length || plannedCommands.length),
    status,
    totalSteps: Math.max(runs.length, plannedCommands.length, tests.length),
    completedSteps: runs.filter((run) => run?.classification === "passed").length,
    durationMs,
    pauseCount: 0,
    pausedDurationMs: 0,
    failureReason,
    failedWorkflowName: failureReason ? "Live 后台热键验收" : "",
    failedStepName: failureReason ? liveValidationFailedStepName(source, runs) : "",
    windowIdentity: null,
    endedWindowIdentity: null,
    endedWindowIdentityError: "",
    queuePlan: liveValidationQueuePlan(source),
    queueEvents: [],
    pauseEvents: [],
    runEvents,
    controlFlowTransitions: [],
    stepResults,
    startedAt,
    endedAt,
    liveValidation: liveValidationSummary(source),
    externalEvidence: liveValidationExternalEvidence(source),
  };
  return cloneJsonSafe(record);
}

export function liveValidationHistoryStatus(status) {
  if (status === "passed" || status === "preflight_only") return "done";
  if (status === "failed") return "failed";
  if (status === "input_not_allowed" || status === "blocked_by_privilege_or_setup") return "stopped";
  return "failed";
}

export function mergeLiveValidationRunHistory(runHistory, entry, options = {}) {
  const limit = Math.max(1, Math.floor(Number(options.limit) || 80));
  const value = objectValue(entry);
  const id = text(value.id);
  const evidenceId = text(value.liveValidation?.id || value.liveValidation?.evidenceId || "");
  const next = [value];
  for (const item of arrayValue(runHistory)) {
    const itemId = text(item?.id);
    const itemEvidenceId = text(item?.liveValidation?.id || item?.liveValidation?.evidenceId || "");
    if (id && itemId === id) continue;
    if (evidenceId && itemEvidenceId === evidenceId) continue;
    next.push(item);
    if (next.length >= limit) break;
  }
  return cloneJsonSafe(next);
}

export function liveValidationFailureReason(evidence, runs = arrayValue(evidence?.runs)) {
  const status = text(evidence?.status);
  if (status === "passed" || status === "preflight_only") return "";
  if (status === "input_not_allowed") return "Live 验收未执行：未显式允许后台输入（缺少 --allow-input）";
  if (status === "blocked_by_privilege_or_setup") {
    const classifications = uniqueTexts(runs.map((run) => run?.classification).filter(Boolean));
    return `Live 验收未执行：权限、窗口或环境门禁阻断${classifications.length ? `（${classifications.join(", ")}）` : ""}`;
  }
  if (status === "failed") {
    const failed = runs.filter((run) => run?.classification === "failed" || finiteNumber(run?.exitCode, 0) !== 0).length;
    return `Live 后台热键验收失败${failed ? `：${failed} 个命令失败` : ""}`;
  }
  return `Live 验收状态未知：${status || "unknown"}`;
}

function liveValidationStepResults(evidence, outputLimit) {
  const runs = arrayValue(evidence.runs);
  if (!runs.length) return [];
  return runs.map((run, index) => {
    const classification = text(run?.classification || "unknown");
    return {
      order: index + 1,
      workflowId: text(arrayValue(evidence.tests)[index] || ""),
      workflowName: liveValidationTestLabel(arrayValue(evidence.tests)[index] || `test-${index + 1}`),
      stepId: `live-test-${index + 1}`,
      stepName: "Rust ignored live test",
      stepType: "live_hotkey",
      status: liveValidationStepStatus(classification),
      action: "background_hotkey_validation",
      detail: liveValidationRunDetail(run, outputLimit),
      inputSent: classification === "passed" && Boolean(evidence.allowInput),
      matched: classification === "passed",
      score: null,
      x: null,
      y: null,
      startedAt: text(run?.startedAt || ""),
      endedAt: text(run?.endedAt || ""),
      durationMs: finiteNumber(run?.durationMs, 0),
    };
  });
}

function liveValidationRunEvents(evidence, outputLimit) {
  const planned = arrayValue(evidence.plannedCommands).map((command, index) => ({
    order: index + 1,
    type: "planned_command",
    phase: "preflight",
    status: "planned",
    detail: commandText(command),
    startedAt: text(evidence.generatedAt || ""),
    endedAt: text(evidence.generatedAt || ""),
    durationMs: 0,
  }));
  const runs = arrayValue(evidence.runs).map((run, index) => ({
    order: planned.length + index + 1,
    type: "live_command",
    phase: "execute",
    status: text(run?.classification || "unknown"),
    detail: liveValidationRunDetail(run, outputLimit),
    startedAt: text(run?.startedAt || ""),
    endedAt: text(run?.endedAt || ""),
    durationMs: finiteNumber(run?.durationMs, 0),
  }));
  return [...planned, ...runs].slice(-MAX_LIVE_RUN_EVENTS);
}

function liveValidationQueuePlan(evidence) {
  const tests = arrayValue(evidence.tests);
  const plannedCommands = arrayValue(evidence.plannedCommands);
  const count = Math.max(tests.length, plannedCommands.length);
  return Array.from({ length: count }, (_, index) => ({
    order: index + 1,
    workflowId: text(tests[index] || `live-${index + 1}`),
    workflowName: liveValidationTestLabel(tests[index] || `live-${index + 1}`),
    command: commandText(plannedCommands[index] || []),
  }));
}

function liveValidationSummary(evidence) {
  const processSnapshot = objectValue(evidence.processSnapshot);
  const processes = arrayValue(processSnapshot.processes);
  return {
    kind: LIVE_VALIDATION_KIND,
    version: finiteNumber(evidence.version, 1),
    id: text(evidence.id || ""),
    evidenceId: text(evidence.id || ""),
    status: text(evidence.status || "unknown"),
    generatedAt: text(evidence.generatedAt || ""),
    repoRoot: text(evidence.repoRoot || ""),
    admin: Boolean(evidence.admin),
    allowInput: Boolean(evidence.allowInput),
    requireExecuted: Boolean(evidence.requireExecuted),
    inputEnvVar: text(evidence.inputEnvVar || "MHXY_LIVE_GAME_TEST"),
    inputEnvSet: Boolean(evidence.inputEnvSet),
    git: objectValue(evidence.git),
    runClassifications: uniqueTexts(arrayValue(evidence.runs).map((run) => run?.classification).filter(Boolean)),
    reportPaths: {
      jsonPath: text(evidence.jsonPath || ""),
      markdownPath: text(evidence.markdownPath || ""),
    },
    processSnapshotStatus: text(processSnapshot.status || ""),
    processSnapshotCount: processes.length,
    tests: arrayValue(evidence.tests).map(text),
    plannedCommandCount: arrayValue(evidence.plannedCommands).length,
    runCount: arrayValue(evidence.runs).length,
  };
}

function liveValidationExternalEvidence(evidence) {
  return [
    { kind: "live-json", path: text(evidence.jsonPath || ""), required: true },
    { kind: "live-markdown", path: text(evidence.markdownPath || ""), required: false },
  ].filter((item) => item.path);
}

function liveValidationFailedStepName(evidence, runs) {
  if (evidence.status === "input_not_allowed") return "等待显式输入授权";
  const blocked = runs.find((run) => ["privilege_blocked", "missing_live_windows", "live_env_not_enabled"].includes(run?.classification));
  if (blocked) return liveValidationClassificationLabel(blocked.classification);
  return "Rust ignored live test";
}

function liveValidationRunDetail(run, outputLimit) {
  const parts = [
    `classification=${text(run?.classification || "unknown")}`,
    `exit=${finiteNumber(run?.exitCode, 0)}`,
    run?.skippedByPrivilegeGate ? "privilege gate" : "",
    run?.skippedBySetupGate ? "setup gate" : "",
  ].filter(Boolean);
  const output = clippedText(run?.output, outputLimit);
  return output ? `${parts.join("; ")}; output=${output}` : parts.join("; ");
}

function liveValidationStepStatus(classification) {
  if (classification === "passed") return "ok";
  if (classification === "failed") return "error";
  if (["privilege_blocked", "missing_live_windows", "live_env_not_enabled"].includes(classification)) return "stopped";
  return "unsupported";
}

function liveValidationTestLabel(value) {
  const key = text(value);
  if (key === "serial") return "串行后台热键";
  if (key === "parallel") return "并行后台热键";
  return key || "Live 后台热键";
}

function liveValidationClassificationLabel(value) {
  if (value === "privilege_blocked") return "权限门禁阻断";
  if (value === "missing_live_windows") return "缺少两个 live 游戏窗口";
  if (value === "live_env_not_enabled") return "环境变量未启用";
  return text(value || "Live 门禁阻断");
}

function commandText(command) {
  return arrayValue(command).map(text).join(" ");
}

function clippedText(value, limit) {
  const source = text(value).trim();
  const count = Math.max(0, Math.floor(Number(limit) || 0));
  if (!source || !count) return "";
  if (source.length <= count) return source;
  const marker = "...<truncated>...";
  if (count <= marker.length + 4) return `${source.slice(0, count)}...<truncated>`;
  const available = count - marker.length;
  const head = Math.ceil(available / 2);
  const tail = Math.floor(available / 2);
  return `${source.slice(0, head)}${marker}${source.slice(-tail)}`;
}

function uniqueTexts(values) {
  return [...new Set(values.map(text).filter(Boolean))];
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}

function finiteNumber(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function text(value) {
  return String(value ?? "");
}

function cloneJsonSafe(value) {
  return JSON.parse(JSON.stringify(value ?? null));
}
