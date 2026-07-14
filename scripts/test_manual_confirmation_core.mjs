import assert from "node:assert/strict";
import {
  createManualConfirmation,
  manualConfirmationBindingFingerprint,
  manualConfirmationStatus,
  manualConfirmationStatusForStep,
  requiresManualConfirmationForStep,
} from "../src/manual-confirmation-core.js";

function baseTarget(overrides = {}) {
  return {
    id: "button.home_clean",
    kind: "image",
    dataUrl: "data:image/png;base64,abc",
    roi: { x: 1, y: 2, w: 3, h: 4 },
    match: { threshold: 0.86, scope: "window" },
    click: { button: "left", point: "center" },
    safety: { requiresManualConfirmation: true },
    ...overrides,
  };
}

function testFingerprintStableAndSensitive() {
  const left = manualConfirmationBindingFingerprint(baseTarget());
  const right = manualConfirmationBindingFingerprint(baseTarget());
  assert.equal(left, right);
  assert.match(left, /^manual-binding-v1:[0-9a-f]{8}$/);
  const changed = manualConfirmationBindingFingerprint(baseTarget({ dataUrl: "data:image/png;base64,def" }));
  assert.notEqual(left, changed);
}

function testCreateAndValidate() {
  const target = baseTarget();
  const confirmation = createManualConfirmation(target, { now: () => "2026-07-14T02:00:00.000Z" });
  assert.equal(confirmation.targetId, "button.home_clean");
  assert.equal(confirmation.bindingFingerprint, manualConfirmationBindingFingerprint(target));
  const status = manualConfirmationStatus({ ...target, manualConfirmation: confirmation }, { required: true });
  assert.equal(status.valid, true);
  assert.equal(status.code, "valid");
}

function testBindingChangeInvalidates() {
  const target = baseTarget();
  const confirmation = createManualConfirmation(target, { now: () => "2026-07-14T02:00:00.000Z" });
  const status = manualConfirmationStatus(
    { ...target, dataUrl: "data:image/png;base64,changed", manualConfirmation: confirmation },
    { required: true },
  );
  assert.equal(status.valid, false);
  assert.equal(status.code, "binding_changed");
}

function testStepCommandRequiresConfirmation() {
  const step = {
    type: "image_click",
    command: "button=left; confirmation=manual-required",
    target: "entry.home",
  };
  assert.equal(requiresManualConfirmationForStep(step, null), true);
  const missing = manualConfirmationStatusForStep(step, { id: "entry.home", safety: {} });
  assert.equal(missing.required, true);
  assert.equal(missing.valid, false);
  assert.equal(missing.code, "missing");
}

function testMissingTargetIdFailsClosed() {
  const status = manualConfirmationStatus({ safety: { requiresManualConfirmation: true } }, { required: true });
  assert.equal(status.valid, false);
  assert.equal(status.code, "target_missing");
}

for (const fn of [
  testFingerprintStableAndSensitive,
  testCreateAndValidate,
  testBindingChangeInvalidates,
  testStepCommandRequiresConfirmation,
  testMissingTargetIdFailsClosed,
]) {
  fn();
  console.log(`ok - ${fn.name}`);
}
