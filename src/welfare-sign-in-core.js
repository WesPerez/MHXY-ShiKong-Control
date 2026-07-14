/** Offline readiness helpers for the welfare sign-in blueprint (no live input). */

export const WELFARE_SIGNIN_BLUEPRINT_ID = "welfare-sign-in";

export const WELFARE_SIGNIN_BLUEPRINT = {
  id: WELFARE_SIGNIN_BLUEPRINT_ID,
  label: "\u798f\u5229\u7b7e\u5230",
  category: "\u65e5\u5e38",
  defaultPrefix: "\u798f\u5229\u7b7e\u5230",
  autoRecovery: true,
  description:
    "\u4ece\u4e3b\u754c\u9762\u8fdb\u5165\u798f\u5229\u9875\uff0c\u4ec5\u5728\u53ef\u9886\u53d6\u65f6\u5904\u7406\u7b7e\u5230\uff0c\u5df2\u9886\u53d6\u5219\u8df3\u8fc7\u5e76\u6062\u590d\u4e3b\u754c\u9762\u3002",
  steps: [
    { type: "detect_page", name: "\u786e\u8ba4\u4e3b\u754c\u9762", target: "page.home.ready", command: "threshold=0.86", expect: "home.visible", onFail: "stop" },
    { type: "snapshot", name: "\u8bb0\u5f55\u4efb\u52a1\u8d77\u59cb\u753b\u9762", target: "window.client", command: "capture=strict; purpose=welfare_before", expect: "snapshot.observed", onFail: "stop" },
    { type: "hotkey", name: "\u6253\u5f00\u529f\u80fd\u9762\u677f", target: "ALT+N", command: "mode=hwnd-key", expect: "panel.open", onFail: "stop" },
    { type: "wait_image", name: "\u7b49\u5f85\u798f\u5229\u5165\u53e3", target: "button.welfare", command: "threshold=0.86", expect: "visible", onFail: "restore" },
    { type: "ocr_assert", name: "\u786e\u8ba4\u798f\u5229\u5165\u53e3\u6587\u5b57", target: "\u798f\u5229", command: "lang=zh; roi=top", expect: "text_found", onFail: "restore" },
    { type: "image_click", name: "\u8fdb\u5165\u798f\u5229\u9875", target: "button.welfare", command: "button=left; point=center; confirmation=manual-required", expect: "welfare.visible", onFail: "restore", requiresManualConfirmation: true },
    { type: "detect_page", name: "\u786e\u8ba4\u798f\u5229\u9875\u9762", target: "page.welfare.ready", command: "threshold=0.86", expect: "welfare.ready", onFail: "restore" },
    { type: "ocr_assert", name: "\u786e\u8ba4\u798f\u5229\u6807\u9898", target: "\u798f\u5229", command: "lang=zh; roi=top", expect: "text_found", onFail: "restore" },
    { type: "wait_image", name: "\u7b49\u5f85\u7b7e\u5230/\u7d2f\u8ba1\u5165\u53e3", target: "button.sign_in", command: "threshold=0.86", expect: "visible", onFail: "restore" },
    { type: "condition", name: "\u5224\u65ad\u662f\u5426\u53ef\u7b7e\u5230", target: "last.status", command: "guard=last.status==ok", expect: "sign_in.available", onFail: "skip", elseTargetStepId: "welfare-restore" },
    { type: "image_click", name: "\u70b9\u51fb\u7b7e\u5230", target: "button.sign_in", command: "button=left; point=center; confirmation=manual-required", expect: "reward.popup", onFail: "restore", requiresManualConfirmation: true },
    { type: "image_click", name: "\u786e\u8ba4\u5956\u52b1\u5f39\u7a97", target: "button.confirm", command: "button=left; point=center", expect: "popup.closed", onFail: "restore" },
    { type: "snapshot", name: "\u8bb0\u5f55\u7b7e\u5230\u7ed3\u679c", target: "window.client", command: "capture=strict; purpose=welfare_after", expect: "snapshot.observed", onFail: "restore" },
    { type: "hotkey", name: "\u8fd4\u56de\u4e3b\u754c\u9762", target: "ESC", command: "mode=hwnd-key", expect: "panel.closed", onFail: "stop", id: "welfare-restore" },
    { type: "detect_page", name: "\u786e\u8ba4\u5df2\u8fd4\u56de\u4e3b\u754c\u9762", target: "page.home.ready", command: "threshold=0.86", expect: "home.visible", onFail: "stop" },
  ],
};

export const WELFARE_SIGNIN_TEMPLATE_BINDINGS = [
  { target: "page.home.ready", key: "zonghe/jiahao.png", kind: "page", name: "\u4e3b\u754c\u9762\u5224\u5b9a", threshold: 0.86 },
  { target: "button.welfare", key: "qiandao/fuli.png", kind: "image", name: "\u798f\u5229\u5165\u53e3", threshold: 0.86, requiresManualConfirmation: true },
  { target: "page.welfare.ready", key: "qiandao/fuli.png", kind: "page", name: "\u798f\u5229\u754c\u9762\u5224\u5b9a", threshold: 0.86 },
  { target: "button.sign_in", key: "qiandao/leiji2.png", kind: "image", name: "\u7b7e\u5230/\u7d2f\u8ba1\u5165\u53e3", threshold: 0.84, requiresManualConfirmation: true },
  { target: "button.confirm", key: "zonghe/zhujiemian_shiyong_cha.png", kind: "image", name: "\u786e\u8ba4/\u5173\u95ed\u6309\u94ae", threshold: 0.84 },
];

export function requiredVisualTargets(blueprint = WELFARE_SIGNIN_BLUEPRINT) {
  const targets = new Set();
  for (const step of blueprint.steps || []) {
    if (!step || !step.target) continue;
    if (["hotkey", "delay", "text_input", "condition", "loop", "task_jump", "restore", "snapshot", "ocr_assert"].includes(step.type)) continue;
    if (String(step.target).includes("+") || /^\\d+ms$/i.test(String(step.target))) continue;
    targets.add(String(step.target));
  }
  return [...targets];
}

export function templateBindingForTarget(target, bindings = WELFARE_SIGNIN_TEMPLATE_BINDINGS) {
  return bindings.find((item) => item.target === target) || null;
}

export function assessWelfareSignInReadiness(options = {}) {
  const blueprint = options.blueprint || WELFARE_SIGNIN_BLUEPRINT;
  const bindings = options.bindings || WELFARE_SIGNIN_TEMPLATE_BINDINGS;
  const targetAssets = options.targetAssets || {};
  const manuallyConfirmedTargets = new Set(options.manuallyConfirmedTargets || []);
  const steps = Array.isArray(blueprint.steps) ? blueprint.steps : [];
  const gaps = [];
  const targetStatus = {};

  if (steps.length < 10) {
    gaps.push({ code: "insufficient_steps", detail: "blueprint requires at least 10 steps, got " + steps.length });
  }

  const hasRecovery = steps.some(
    (step) => step.onFail === "restore" || step.type === "restore" || String(step.id || "").includes("restore"),
  );
  if (!hasRecovery) {
    gaps.push({ code: "missing_recovery", detail: "blueprint lacks restore/onFail recovery path" });
  }

  for (const target of requiredVisualTargets(blueprint)) {
    const binding = templateBindingForTarget(target, bindings);
    const asset = targetAssets[target] || null;
    const hasAsset = Boolean(asset && (asset.loaded || asset.dataUrl || asset.roi || binding?.key));
    const needsManual = Boolean(binding?.requiresManualConfirmation || asset?.requiresManualConfirmation);
    const manualOk =
      !needsManual ||
      manuallyConfirmedTargets.has(target) ||
      asset?.manualConfirmed === true ||
      asset?.manualConfirmationValid === true;
    targetStatus[target] = {
      bound: hasAsset,
      bindingKey: binding?.key || null,
      needsManualConfirmation: needsManual,
      manualConfirmed: manualOk,
    };
    if (!hasAsset) gaps.push({ code: "missing_asset", target, detail: "missing template/asset for " + target });
    if (needsManual && !manualOk) {
      gaps.push({ code: "manual_confirmation_required", target, detail: "live click target not manually confirmed: " + target });
    }
  }

  const readyOffline = gaps.every((gap) => gap.code === "manual_confirmation_required");
  return {
    blueprintId: blueprint.id,
    stepCount: steps.length,
    readyOffline,
    liveAuthorized: false,
    gaps,
    targetStatus,
    notes: [
      "Offline readiness never authorizes live HWND input.",
      "Sign-in click remains blocked until manual confirmation and elevated gates pass.",
    ],
  };
}

export function summarizeWelfareSignInGaps(assessment) {
  const gaps = assessment?.gaps || [];
  if (!gaps.length) return "no offline gaps";
  return gaps.map((gap) => gap.code + (gap.target ? ":" + gap.target : "")).join(", ");
}
