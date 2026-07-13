#!/usr/bin/env node
import assert from "node:assert/strict";

import {
  activateStartingSession,
  assignedQueueRunEntries,
  isActiveRunSession,
  releaseStartingSession,
  reserveStartingSession,
} from "../src/run-dispatch-core.js";


function normalizeQueueItem(item) {
  return { ...item, id: item.id || "queue-normalized" };
}

function testAssignedQueueNeverFallsBackToAnActiveWorkflow() {
  let workflowLookupCount = 0;
  const workflowById = (id) => {
    workflowLookupCount += 1;
    return id === "workflow-1" ? { id, name: "Assigned" } : null;
  };
  assert.deepEqual(assignedQueueRunEntries(null, workflowById, normalizeQueueItem), []);
  assert.deepEqual(assignedQueueRunEntries({ queue: [] }, workflowById, normalizeQueueItem), []);
  assert.deepEqual(
    assignedQueueRunEntries({ queue: [{ id: "disabled", workflowId: "workflow-1", enabled: false }] }, workflowById, normalizeQueueItem),
    [],
  );
  assert.equal(workflowLookupCount, 0);
}

function testAssignedQueueKeepsOnlyEnabledExistingWorkflows() {
  const workflows = new Map([["workflow-1", { id: "workflow-1", name: "Assigned", steps: [] }]]);
  const entries = assignedQueueRunEntries(
    { queue: [{ id: "queue-1", workflowId: "workflow-1", enabled: true }, { id: "queue-2", workflowId: "missing", enabled: true }] },
    (id) => workflows.get(id) || null,
    normalizeQueueItem,
  );
  assert.equal(entries.length, 1);
  assert.equal(entries[0].workflow.id, "workflow-1");
  assert.equal(entries[0].queueItem.id, "queue-1");
}

function testStartingReservationIsAtomicPerHwnd() {
  const sessions = {};
  const runPlan = [{ workflow: { id: "workflow-1", name: "Assigned" }, queueItem: { id: "queue-1" } }];
  const first = reserveStartingSession(sessions, {
    id: "run-1",
    mode: "background",
    hwnd: 100,
    display: "Window 100",
    runPlan,
    totalSteps: 3,
    startedAt: "2024-01-01T00:00:00.000Z",
  });
  const second = reserveStartingSession(sessions, {
    id: "run-2",
    mode: "background",
    hwnd: 100,
    display: "Window 100",
    runPlan,
    totalSteps: 3,
    startedAt: "2024-01-01T00:00:00.000Z",
  });
  assert.ok(first);
  assert.equal(first.status, "starting");
  assert.equal(first.source, "queue");
  assert.equal(second, null);
  assert.equal(sessions["100"], first);
  assert.equal(isActiveRunSession(first), true);
}

function testStartingReservationActivatesOrReleasesOnlyItsOwnSlot() {
  const sessions = {};
  const runPlan = [{ workflow: { id: "workflow-1", name: "Assigned" }, queueItem: { id: "queue-1" } }];
  const reservation = reserveStartingSession(sessions, {
    id: "run-1",
    mode: "dry",
    hwnd: 100,
    display: "Window 100",
    runPlan,
    totalSteps: 1,
    startedAt: "2024-01-01T00:00:00.000Z",
  });
  assert.equal(releaseStartingSession(sessions, 100, { status: "starting" }), false);
  assert.equal(activateStartingSession(sessions, 100, reservation, { hwnd: 100 }), true);
  assert.equal(reservation.status, "running");
  assert.deepEqual(reservation.windowIdentity, { hwnd: 100 });
  assert.equal(releaseStartingSession(sessions, 100, reservation), false);

  const cancelled = reserveStartingSession(sessions, {
    id: "run-2",
    mode: "dry",
    hwnd: 200,
    display: "Window 200",
    runPlan,
    totalSteps: 1,
    startedAt: "2024-01-01T00:00:00.000Z",
  });
  cancelled.cancelRequested = true;
  assert.equal(activateStartingSession(sessions, 200, cancelled, { hwnd: 200 }), false);
  assert.equal(releaseStartingSession(sessions, 200, cancelled), true);
}

const tests = [
  testAssignedQueueNeverFallsBackToAnActiveWorkflow,
  testAssignedQueueKeepsOnlyEnabledExistingWorkflows,
  testStartingReservationIsAtomicPerHwnd,
  testStartingReservationActivatesOrReleasesOnlyItsOwnSlot,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}

console.log(`${tests.length} run dispatch tests passed`);
