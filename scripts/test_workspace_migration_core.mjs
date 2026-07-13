#!/usr/bin/env node
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

import {
  countAssignmentQueueItems,
  numericSchemaVersion,
  workspaceMigrationAudit,
  workspaceMigrationSummaryText,
} from "../src/workspace-migration-core.js";
import { normalizeWorkspaceCore } from "../src/workspace-normalization-core.js";

const CURRENT_SCHEMA_VERSION = 9;
const FIXTURE_PATH = new URL("./fixtures/workspace-v6-anonymized.json", import.meta.url);
const FIXED_TIME = "2024-01-01T00:00:00.000Z";

function workspaceCounts(value) {
  return {
    workflows: value.workflows?.length || 0,
    steps: (value.workflows || []).reduce((count, workflow) => count + (workflow.steps?.length || 0), 0),
    targets: value.targets?.length || 0,
  };
}

function canonicalHash(value) {
  return createHash("sha256").update(JSON.stringify(value)).digest("hex");
}

function brokenWorkspaceReferences(value) {
  const findings = [];
  const workflowIds = new Set((value.workflows || []).map((workflow) => workflow.id));
  const targetIds = new Set((value.targets || []).map((target) => target.id));
  const targetTypes = new Set(["detect_page", "wait_image", "image_click", "double_click", "ocr_assert", "click"]);
  if (value.activeWorkflowId && !workflowIds.has(value.activeWorkflowId)) findings.push("activeWorkflowId");
  for (const workflow of value.workflows || []) {
    const stepIds = new Set((workflow.steps || []).map((step) => step.id));
    for (const step of workflow.steps || []) {
      if (targetTypes.has(step.type) && step.target && !targetIds.has(step.target) && !targetIds.has(step.targetId)) {
        findings.push(`${workflow.id}/${step.id}/target`);
      }
      for (const field of ["targetStepId", "elseTargetStepId", "recoveryStepId"]) {
        if (step[field] && !stepIds.has(step[field])) findings.push(`${workflow.id}/${step.id}/${field}`);
      }
      if (step.jumpWorkflowId && !workflowIds.has(step.jumpWorkflowId)) findings.push(`${workflow.id}/${step.id}/jumpWorkflowId`);
    }
  }
  for (const [hwnd, assignment] of Object.entries(value.assignments || {})) {
    for (const item of assignment.queue || []) {
      if (!workflowIds.has(item.workflowId)) findings.push(`${hwnd}/${item.id}/workflowId`);
    }
  }
  return findings;
}

function testNumericSchemaVersion() {
  assert.equal(numericSchemaVersion("9"), 9);
  assert.equal(numericSchemaVersion(9.9), 9);
  assert.equal(numericSchemaVersion("bad", 7), 7);
  assert.equal(numericSchemaVersion(-1, 7), 7);
}

function testAssignmentQueueCountingSupportsLegacyShape() {
  assert.equal(
    countAssignmentQueueItems({
      "100": { queue: [{ workflowId: "a" }, { workflowId: "b" }] },
      "200": { workflowId: "legacy" },
      "300": { queue: [] },
    }),
    3,
  );
}

function testMigrationAuditFlagsLegacyWorkspaceNormalization() {
  const source = {
    schemaVersion: 8,
    workflows: [{ id: "wf.keep" }],
    assets: [{ id: "button.old" }],
    targets: [{ id: "button.existing" }],
    assignments: {
      "100": { queue: [{ workflowId: "wf.keep" }, { workflowId: "wf.missing" }] },
      "200": { workflowId: "wf.missing" },
    },
    runHistory: Array.from({ length: 90 }, (_, index) => ({ id: `run.${index}` })),
  };
  const normalized = {
    schemaVersion: CURRENT_SCHEMA_VERSION,
    workflows: [{ id: "wf.keep" }],
    targets: [{ id: "button.old" }, { id: "button.existing" }],
    assignments: {
      "100": { queue: [{ workflowId: "wf.keep" }] },
    },
    runHistory: source.runHistory.slice(0, 80),
  };

  const audit = workspaceMigrationAudit(source, normalized, CURRENT_SCHEMA_VERSION);

  assert.equal(audit.upgraded, true);
  assert.equal(audit.shouldSave, true);
  assert.equal(audit.counts.legacyAssets, 1);
  assert.equal(audit.counts.droppedQueueItems, 2);
  assert.equal(audit.counts.droppedAssignments, 1);
  assert.equal(audit.counts.runHistoryTrimmed, 10);
  assert.deepEqual(audit.actions, [
    "schema_normalized",
    "legacy_assets_migrated",
    "run_history_trimmed",
    "invalid_assignments_dropped",
  ]);
}

function testMigrationAuditRecognizesStableWorkspace() {
  const source = {
    schemaVersion: CURRENT_SCHEMA_VERSION,
    workflows: [{ id: "wf.keep" }],
    targets: [{ id: "button.existing" }],
    assignments: {
      "100": { queue: [{ workflowId: "wf.keep" }] },
    },
    runHistory: [{ id: "run.1" }],
  };
  const audit = workspaceMigrationAudit(source, source, CURRENT_SCHEMA_VERSION);

  assert.equal(audit.shouldSave, false);
  assert.equal(audit.upgraded, false);
  assert.equal(audit.futureSchema, false);
  assert.deepEqual(audit.actions, []);
}

function testMigrationAuditWarnsOnFutureSchema() {
  const audit = workspaceMigrationAudit(
    { schemaVersion: 99 },
    { schemaVersion: CURRENT_SCHEMA_VERSION },
    CURRENT_SCHEMA_VERSION,
  );

  assert.equal(audit.futureSchema, true);
  assert.equal(audit.shouldSave, false);
  assert.ok(audit.warnings.includes("future_schema"));
}

function testMigrationSummaryMentionsUserVisibleEvidence() {
  const audit = workspaceMigrationAudit(
    { schemaVersion: 8, assets: [{ id: "a" }], runHistory: [{}, {}] },
    { schemaVersion: CURRENT_SCHEMA_VERSION, targets: [{ id: "a" }], runHistory: [{}] },
    CURRENT_SCHEMA_VERSION,
  );
  const summary = workspaceMigrationSummaryText(audit, { backupPath: "workspace.json.bak" });

  assert.match(summary, /schema 8 -> 9/);
  assert.match(summary, /迁移旧 assets 1/);
  assert.match(summary, /裁剪运行记录 1/);
  assert.match(summary, /备份 workspace\.json\.bak/);
}

function testAnonymizedV6FixtureKeepsRequiredBaselineWithoutUserContent() {
  const source = JSON.parse(readFileSync(FIXTURE_PATH, "utf8"));
  assert.equal(source.schemaVersion, 6);
  assert.deepEqual(workspaceCounts(source), { workflows: 5, steps: 63, targets: 27 });
  assert.equal(source.targets.every((target) => target.dataUrl === ""), true);
  assert.equal(source.workflows.every((workflow) => /^Workflow \d{2}$/.test(workflow.name)), true);
  assert.equal(source.fixtureMetadata.kind, "mhxy-anonymized-workspace-v6");
  assert.deepEqual(brokenWorkspaceReferences(source), []);
}

function testRealNormalizationMigratesV6FixtureWithoutLossAndIsIdempotent() {
  const source = JSON.parse(readFileSync(FIXTURE_PATH, "utf8"));
  const options = { now: () => FIXED_TIME, randomId: (prefix) => `${prefix}-deterministic` };
  const normalized = normalizeWorkspaceCore(source, options);
  const reopened = normalizeWorkspaceCore(JSON.parse(JSON.stringify(normalized)), options);
  const audit = workspaceMigrationAudit(source, normalized, CURRENT_SCHEMA_VERSION);

  assert.equal(normalized.schemaVersion, CURRENT_SCHEMA_VERSION);
  assert.equal(audit.upgraded, true);
  assert.equal(audit.shouldSave, true);
  assert.deepEqual(workspaceCounts(normalized), { workflows: 5, steps: 63, targets: 27 });
  assert.deepEqual(brokenWorkspaceReferences(normalized), []);
  assert.equal(canonicalHash(reopened), canonicalHash(normalized));
}

const tests = [
  testNumericSchemaVersion,
  testAssignmentQueueCountingSupportsLegacyShape,
  testMigrationAuditFlagsLegacyWorkspaceNormalization,
  testMigrationAuditRecognizesStableWorkspace,
  testMigrationAuditWarnsOnFutureSchema,
  testMigrationSummaryMentionsUserVisibleEvidence,
  testAnonymizedV6FixtureKeepsRequiredBaselineWithoutUserContent,
  testRealNormalizationMigratesV6FixtureWithoutLossAndIsIdempotent,
];

for (const test of tests) {
  test();
  console.log(`ok ${test.name}`);
}

console.log(`${tests.length} workspace migration tests passed`);
