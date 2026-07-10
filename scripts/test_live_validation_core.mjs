#!/usr/bin/env node
import assert from "node:assert/strict";

import {
  isLiveValidationEvidence,
  liveValidationFailureReason,
  liveValidationHistoryStatus,
  liveValidationRunHistoryEntry,
  mergeLiveValidationRunHistory,
} from "../src/live-validation-core.js";
import { failureEvidenceBundle } from "../src/failure-evidence-core.js";

const fixedNow = "2026-07-10T00:00:00.000Z";

function sampleEvidence(overrides = {}) {
  return {
    kind: "mhxy-shikong.live-background-hotkey-validation",
    version: 1,
    id: "live-background-hotkey-test",
    generatedAt: fixedNow,
    repoRoot: "E:\\Project\\Common\\MHXY-ShiKong-Control",
    admin: false,
    allowInput: false,
    requireExecuted: false,
    inputEnvVar: "MHXY_LIVE_GAME_TEST",
    inputEnvSet: false,
    tests: ["serial"],
    plannedCommands: [["cargo", "test", "tests::live_background_hotkey_changes_two_game_windows", "--", "--ignored", "--exact", "--nocapture"]],
    git: {
      head: "55ab75d",
      branch: "main",
      statusShort: "",
    },
    processSnapshot: {
      status: "ok",
      processes: [
        { ProcessId: 1, Name: "mhxy-shikong-control.exe", CommandLine: "very long command line" },
        { ProcessId: 2, Name: "MyGame_x64r.exe", CommandLine: null },
      ],
    },
    runs: [],
    jsonPath: "assets/resource/ShiKong/reports/live-background-hotkey-test.json",
    markdownPath: "assets/resource/ShiKong/reports/live-background-hotkey-test.md",
    status: "preflight_only",
    ...overrides,
  };
}

function testRecognizesLiveEvidence() {
  assert.equal(isLiveValidationEvidence(sampleEvidence()), true);
  assert.equal(isLiveValidationEvidence({ kind: "other" }), false);
}

function testPreflightBecomesLightweightRunHistory() {
  const entry = liveValidationRunHistoryEntry(sampleEvidence());
  assert.equal(entry.id, "live-background-hotkey-test");
  assert.equal(entry.status, "done");
  assert.equal(entry.source, "live-validation");
  assert.equal(entry.failureReason, "");
  assert.equal(entry.liveValidation.status, "preflight_only");
  assert.equal(entry.liveValidation.evidenceId, "live-background-hotkey-test");
  assert.equal(entry.liveValidation.processSnapshotCount, 2);
  assert.equal(entry.processSnapshot, undefined);
  assert.equal(entry.externalEvidence[0].kind, "live-json");
  assert.equal(entry.runEvents.length, 1);
  assert.match(entry.runEvents[0].detail, /--exact/);
}

function testRequireExecutedWithoutAllowInputBecomesStoppedFailureReport() {
  const entry = liveValidationRunHistoryEntry(
    sampleEvidence({
      allowInput: false,
      requireExecuted: true,
      status: "input_not_allowed",
    }),
  );
  assert.equal(entry.status, "stopped");
  assert.match(entry.failureReason, /--allow-input/);
  assert.equal(entry.failedStepName, "等待显式输入授权");
}

function testBlockedRunKeepsOnlyClippedOutput() {
  const longOutput = "x".repeat(200);
  const entry = liveValidationRunHistoryEntry(
    sampleEvidence({
      allowInput: true,
      inputEnvSet: true,
      status: "blocked_by_privilege_or_setup",
      runs: [
        {
          command: ["cargo", "test", "tests::live_background_hotkey_changes_two_game_windows"],
          exitCode: 0,
          startedAt: fixedNow,
          endedAt: fixedNow,
          durationMs: 123,
          output: longOutput,
          classification: "privilege_blocked",
          skippedByPrivilegeGate: true,
          skippedBySetupGate: false,
        },
      ],
    }),
    { outputLimit: 40 },
  );
  assert.equal(entry.status, "stopped");
  assert.match(entry.failureReason, /privilege_blocked/);
  assert.equal(entry.completedSteps, 0);
  assert.equal(entry.stepResults.length, 1);
  assert.equal(entry.stepResults[0].status, "stopped");
  assert.ok(entry.stepResults[0].detail.length < 140);
  assert.match(entry.stepResults[0].detail, /<truncated>/);
  assert.equal(entry.liveValidation.runCount, 1);
}

function testPassedParallelLiveRunIsDoneAndInputSent() {
  const entry = liveValidationRunHistoryEntry(
    sampleEvidence({
      allowInput: true,
      inputEnvSet: true,
      status: "passed",
      tests: ["serial", "parallel"],
      runs: [
        { exitCode: 0, startedAt: fixedNow, endedAt: fixedNow, durationMs: 10, output: "ok", classification: "passed" },
        { exitCode: 0, startedAt: fixedNow, endedAt: fixedNow, durationMs: 20, output: "ok", classification: "passed" },
      ],
    }),
  );
  assert.equal(entry.status, "done");
  assert.equal(entry.workflowName, "Live 串行/并行热键验收");
  assert.equal(entry.completedSteps, 2);
  assert.equal(entry.durationMs, 30);
  assert.equal(entry.stepResults.every((item) => item.inputSent), true);
}

function testStatusAndFailureReasonMappings() {
  assert.equal(liveValidationHistoryStatus("passed"), "done");
  assert.equal(liveValidationHistoryStatus("preflight_only"), "done");
  assert.equal(liveValidationHistoryStatus("failed"), "failed");
  assert.equal(liveValidationHistoryStatus("blocked_by_privilege_or_setup"), "stopped");
  assert.match(liveValidationFailureReason({ status: "failed" }, [{ classification: "failed", exitCode: 101 }]), /失败/);
}

function testMergesByEvidenceIdAndTrimsHistory() {
  const entry = liveValidationRunHistoryEntry(sampleEvidence());
  const oldHistory = Array.from({ length: 90 }, (_, index) => ({
    id: index === 0 ? entry.id : `run-${index}`,
    liveValidation: index === 1 ? { evidenceId: entry.liveValidation.evidenceId } : null,
  }));
  const merged = mergeLiveValidationRunHistory(oldHistory, entry, { limit: 80 });
  assert.equal(merged.length, 80);
  assert.equal(merged[0].id, entry.id);
  assert.equal(merged.filter((item) => item.id === entry.id).length, 1);
  assert.equal(merged.some((item) => item.id === "run-1"), false);
}

function testLiveValidationEntryWorksWithFailureEvidenceBundle() {
  const entry = liveValidationRunHistoryEntry(
    sampleEvidence({
      requireExecuted: true,
      status: "input_not_allowed",
    }),
  );
  const bundle = failureEvidenceBundle(entry, { now: () => fixedNow, schemaVersion: 9 });
  assert.equal(bundle.summary.status, "stopped");
  assert.match(bundle.summary.failureReason, /--allow-input/);
  assert.equal(bundle.fullReport.liveValidation.status, "input_not_allowed");
  assert.equal(bundle.fullReport.externalEvidence[0].kind, "live-json");
}

function testRejectsInvalidEvidenceKind() {
  assert.throws(() => liveValidationRunHistoryEntry({ kind: "wrong" }), /live 后台热键验收报告/);
}

const tests = [
  testRecognizesLiveEvidence,
  testPreflightBecomesLightweightRunHistory,
  testRequireExecutedWithoutAllowInputBecomesStoppedFailureReport,
  testBlockedRunKeepsOnlyClippedOutput,
  testPassedParallelLiveRunIsDoneAndInputSent,
  testStatusAndFailureReasonMappings,
  testMergesByEvidenceIdAndTrimsHistory,
  testLiveValidationEntryWorksWithFailureEvidenceBundle,
  testRejectsInvalidEvidenceKind,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}

console.log(`${tests.length} live validation tests passed`);
