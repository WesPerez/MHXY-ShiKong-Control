import assert from "node:assert/strict";
import {
  WELFARE_SIGNIN_BLUEPRINT,
  assessWelfareSignInReadiness,
  requiredVisualTargets,
  summarizeWelfareSignInGaps,
} from "../src/welfare-sign-in-core.js";

function testBlueprintLength() {
  assert.ok(WELFARE_SIGNIN_BLUEPRINT.steps.length >= 10);
  assert.ok(requiredVisualTargets().includes("button.welfare"));
  assert.ok(requiredVisualTargets().includes("button.sign_in"));
}

function testOfflineReadinessWithBindings() {
  const assessment = assessWelfareSignInReadiness({
    targetAssets: {
      "page.home.ready": { loaded: true },
      "button.welfare": { loaded: true },
      "page.welfare.ready": { loaded: true },
      "button.sign_in": { loaded: true },
      "button.confirm": { loaded: true },
    },
  });
  assert.equal(assessment.liveAuthorized, false);
  assert.equal(assessment.readyOffline, true);
  assert.ok(summarizeWelfareSignInGaps(assessment).includes("manual_confirmation_required"));
}

function testManualConfirmedReady() {
  const assessment = assessWelfareSignInReadiness({
    targetAssets: {
      "page.home.ready": { loaded: true },
      "button.welfare": { loaded: true, manualConfirmed: true },
      "page.welfare.ready": { loaded: true },
      "button.sign_in": { loaded: true, manualConfirmed: true },
      "button.confirm": { loaded: true },
    },
    manuallyConfirmedTargets: ["button.welfare", "button.sign_in"],
  });
  assert.equal(assessment.readyOffline, true);
  assert.equal(assessment.gaps.length, 0);
  assert.equal(assessment.liveAuthorized, false);
}

testBlueprintLength();
testOfflineReadinessWithBindings();
testManualConfirmedReady();
console.log("welfare-sign-in-core: 3 tests passed");
