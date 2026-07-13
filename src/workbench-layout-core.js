export const INSPECTOR_TABS = Object.freeze(["workflow", "step", "target"]);

export const WORKBENCH_VIEWPORTS = Object.freeze([
  Object.freeze({ width: 1460, height: 880 }),
  Object.freeze({ width: 1280, height: 720 }),
  Object.freeze({ width: 1120, height: 720 }),
  Object.freeze({ width: 920, height: 680 }),
  Object.freeze({ width: 820, height: 720 }),
]);

export function normalizeInspectorTab(value, options = {}) {
  const requested = INSPECTOR_TABS.includes(value) ? value : "workflow";
  if (requested === "step" && options.hasStep === false) return "workflow";
  return requested;
}

export function inspectorTabForFocusSelector(selector) {
  const value = String(selector || "").trim();
  if (/^#(?:target-|bind-selected-target|unbind-step-target|verify-selected-target|delete-target)/.test(value)) {
    return "target";
  }
  if (/^#(?:step-|param-|insert-recovery-fragment|mark-recovery-entry)/.test(value)) return "step";
  return "workflow";
}

export function workbenchViewportContract(width, height) {
  const viewportWidth = Math.max(0, Number(width) || 0);
  const viewportHeight = Math.max(0, Number(height) || 0);
  const mode = viewportWidth <= 820 ? "single" : viewportWidth <= 1120 ? "stacked" : "desktop";
  return {
    mode,
    density: mode === "desktop" && viewportHeight <= 900 ? "compact" : "comfortable",
    pageScroll: mode !== "desktop",
    minimumWorkflowListHeight: 96,
    minimumStepListHeight: 96,
  };
}
