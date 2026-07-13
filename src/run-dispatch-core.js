const ACTIVE_SESSION_STATUSES = new Set(["starting", "running", "paused"]);

export function isActiveRunSession(session) {
  return Boolean(session && ACTIVE_SESSION_STATUSES.has(session.status));
}

export function assignedQueueRunEntries(assignment, workflowById, normalizeQueueItem) {
  if (!assignment || !Array.isArray(assignment.queue)) return [];
  return assignment.queue
    .filter((item) => item?.enabled !== false)
    .map((item) => ({
      queueItem: normalizeQueueItem(item),
      workflow: workflowById(item.workflowId),
    }))
    .filter((entry) => entry.workflow);
}

export function reserveStartingSession(sessions, details) {
  const key = String(details.hwnd);
  if (isActiveRunSession(sessions[key])) return null;
  const session = {
    id: details.id,
    mode: details.mode,
    source: "queue",
    hwnd: details.hwnd,
    display: details.display,
    windowIdentity: null,
    workflowIds: details.runPlan.map((entry) => entry.workflow.id),
    workflowNames: details.runPlan.map((entry) => entry.workflow.name),
    workflowId: details.runPlan[0]?.workflow.id || "",
    workflowName: details.runPlan.length === 1 ? details.runPlan[0].workflow.name : `${details.runPlan.length} 个任务`,
    queuePlan: details.runPlan.map((entry, index) => ({
      queueItemId: entry.queueItem.id,
      workflowId: entry.workflow.id,
      workflowName: entry.workflow.name,
      order: index + 1,
      startDelayMs: entry.queueItem.startDelayMs || 0,
      afterDelayMs: entry.queueItem.afterDelayMs || 0,
    })),
    queueEvents: [],
    controlFlowTransitions: [],
    controlFlowTransitionSerial: 0,
    currentWorkflowName: "",
    status: "starting",
    currentStep: 0,
    totalSteps: details.totalSteps,
    startedAt: details.startedAt,
    logs: [],
    stepResults: [],
    failureReason: "",
    failedWorkflowName: "",
    failedStepName: "",
    endedWindowIdentity: null,
    endedWindowIdentityError: "",
    controlFlowCounts: {},
    workflowJumpCount: 0,
    workflowJumpRequest: null,
    cancelRequested: false,
    pauseRequested: false,
    pauseRequestedAt: "",
    pauseStartedAt: "",
    pausedDurationMs: 0,
    pauseCount: 0,
    activePauseEvent: null,
    runEvents: [],
    runEventSerial: 0,
  };
  sessions[key] = session;
  return session;
}

export function releaseStartingSession(sessions, hwnd, reservation) {
  const key = String(hwnd);
  if (sessions[key] !== reservation || reservation?.status !== "starting") return false;
  delete sessions[key];
  return true;
}

export function activateStartingSession(sessions, hwnd, reservation, windowIdentity) {
  const key = String(hwnd);
  if (sessions[key] !== reservation || reservation?.status !== "starting" || reservation.cancelRequested) return false;
  reservation.windowIdentity = windowIdentity;
  reservation.status = "running";
  return true;
}
