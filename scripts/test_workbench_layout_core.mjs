import assert from "node:assert/strict";
import {
  INSPECTOR_TABS,
  WORKBENCH_VIEWPORTS,
  inspectorTabForFocusSelector,
  normalizeInspectorTab,
  workbenchViewportContract,
} from "../src/workbench-layout-core.js";

function testInspectorTabNormalization() {
  assert.deepEqual(INSPECTOR_TABS, ["workflow", "step", "target"]);
  assert.equal(normalizeInspectorTab("missing"), "workflow");
  assert.equal(normalizeInspectorTab("step", { hasStep: false }), "workflow");
  assert.equal(normalizeInspectorTab("target", { hasStep: false }), "target");
}

function testFocusSelectorsChooseReachableInspectorTabs() {
  assert.equal(inspectorTabForFocusSelector("#workflow-name"), "workflow");
  assert.equal(inspectorTabForFocusSelector("#step-expect"), "step");
  assert.equal(inspectorTabForFocusSelector("#param-image-button"), "step");
  assert.equal(inspectorTabForFocusSelector("#target-texts"), "target");
  assert.equal(inspectorTabForFocusSelector("#bind-selected-target"), "target");
}

function testRequiredViewportsHaveExplicitLayoutContracts() {
  const contracts = WORKBENCH_VIEWPORTS.map(({ width, height }) => ({
    width,
    height,
    ...workbenchViewportContract(width, height),
  }));
  assert.deepEqual(
    contracts.map(({ mode }) => mode),
    ["desktop", "desktop", "stacked", "stacked", "single"],
  );
  assert.equal(contracts[0].density, "compact");
  assert.equal(contracts[1].density, "compact");
  assert.equal(contracts[2].pageScroll, true);
  assert.equal(contracts[3].pageScroll, true);
  assert.equal(contracts[4].pageScroll, true);
  for (const contract of contracts) {
    assert.ok(contract.minimumWorkflowListHeight >= 96);
    assert.ok(contract.minimumStepListHeight >= 96);
  }
}

const tests = [
  testInspectorTabNormalization,
  testFocusSelectorsChooseReachableInspectorTabs,
  testRequiredViewportsHaveExplicitLayoutContracts,
];

for (const test of tests) test();
console.log(`workbench-layout-core: ${tests.length} tests passed`);
