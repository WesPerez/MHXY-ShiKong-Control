/** Offline readiness helpers for the home-vitality blueprint (no live input). */

export const HOME_VITALITY_BLUEPRINT_ID = 'home-vitality';

export const HOME_VITALITY_BLUEPRINT = {
  id: HOME_VITALITY_BLUEPRINT_ID,
  label: '\u5bb6\u56ed\u6d3b\u529b',
  category: '\u5bb6\u56ed',
  description:
    '\u6253\u5f00\u5bb6\u56ed/\u4eba\u7269\u76f8\u5173\u5165\u53e3\uff0c\u6309 OCR \u548c\u56fe\u50cf\u76ee\u6807\u5904\u7406\u6d3b\u529b\u3001\u6253\u7406\u4e0e\u786e\u8ba4\u52a8\u4f5c\u3002',
  steps: [
    { type: 'detect_page', name: '\u786e\u8ba4\u4e3b\u754c\u9762', target: 'page.home.ready', command: 'threshold=0.86', expect: 'home.visible' },
    { type: 'hotkey', name: '\u6253\u5f00\u529f\u80fd\u9762\u677f', target: 'ALT+N', command: 'mode=hwnd-key', expect: 'panel.open' },
    { type: 'delay', name: '\u7b49\u5f85\u754c\u9762\u52a8\u753b', target: '800ms', command: 'reason=panel_transition', expect: 'time.elapsed' },
    { type: 'ocr_assert', name: '\u786e\u8ba4\u529f\u80fd\u9762\u677f', target: '\u5bb6\u56ed', command: 'lang=zh; roi=top', expect: 'text_found' },
    { type: 'wait_image', name: '\u7b49\u5f85\u5bb6\u56ed\u5165\u53e3', target: 'entry.home', command: 'threshold=0.86', expect: 'visible' },
    { type: 'image_click', name: '\u8fdb\u5165\u5bb6\u56ed', target: 'entry.home', command: 'button=left; point=center', expect: 'home.panel.ready' },
    { type: 'retry_until', name: '\u7b49\u5f85\u5bb6\u56ed\u9875\u9762', target: 'page.home_yard.ready', command: 'interval=700ms', expect: 'ready=true', timeoutMs: 7000, retry: 3 },
    { type: 'wait_image', name: '\u7b49\u5f85\u6253\u7406\u6309\u94ae', target: 'button.home_clean', command: 'threshold=0.86', expect: 'visible' },
    { type: 'image_click', name: '\u6267\u884c\u6253\u7406', target: 'button.home_clean', command: 'button=left; point=center', expect: 'action.accepted' },
    { type: 'delay', name: '\u7b49\u5f85\u7ed3\u7b97', target: '1000ms', command: 'reason=server_response', expect: 'time.elapsed' },
    { type: 'ocr_assert', name: '\u786e\u8ba4\u6d3b\u529b\u72b6\u6001', target: '\u6d3b\u529b', command: 'lang=zh; roi=panel', expect: 'text_found' },
    { type: 'snapshot', name: '\u8bb0\u5f55\u5bb6\u56ed\u7ed3\u679c', target: 'window.client', command: 'dry-run log only', expect: 'snapshot.recorded' },
    { type: 'restore', name: '\u6062\u590d\u4e3b\u754c\u9762', target: 'restore.home', command: 'safe sequence', expect: 'page.home.ready' },
  ],
};

export const HOME_VITALITY_TEMPLATE_BINDINGS = [
  { target: 'page.home.ready', key: 'zonghe/jiahao.png', kind: 'page', name: '\u4e3b\u754c\u9762\u5224\u5b9a', threshold: 0.86 },
  { target: 'page.home_yard.ready', key: 'jiayuan/dali.png', kind: 'page', name: '\u5bb6\u56ed\u6253\u7406\u9875\u5224\u5b9a' },
  { target: 'button.home_clean', key: 'jiayuan/dali.png', kind: 'image', name: '\u5bb6\u56ed\u6253\u7406\u6309\u94ae' },
];

const VISUAL_STEP_TYPES = new Set(['detect_page', 'wait_image', 'image_click', 'double_click', 'retry_until']);

export function isLogicalVisualTarget(target) {
  const text = String(target || '').trim();
  if (!text || text.includes('=')) return false;
  if (/^[A-Z]+(?:\+[A-Z0-9]+)+$/i.test(text)) return false;
  if (/^\d+ms$/i.test(text)) return false;
  return /^[\p{Script=Han}A-Za-z][\p{Script=Han}A-Za-z0-9_.:-]*$/u.test(text);
}

export function requiredVisualTargets(blueprint = HOME_VITALITY_BLUEPRINT) {
  const targets = new Set();
  for (const step of blueprint.steps || []) {
    if (!VISUAL_STEP_TYPES.has(step.type)) continue;
    if (isLogicalVisualTarget(step.target)) targets.add(step.target);
  }
  return [...targets];
}

export function templateBindingForTarget(target, bindings = HOME_VITALITY_TEMPLATE_BINDINGS) {
  return bindings.find((item) => item.target === target) || null;
}

export function assessHomeVitalityReadiness(options = {}) {
  const blueprint = options.blueprint || HOME_VITALITY_BLUEPRINT;
  const bindings = options.bindings || HOME_VITALITY_TEMPLATE_BINDINGS;
  const targetAssets = options.targetAssets || {};
  const availableKeys = new Set(options.availableTemplateKeys || []);

  const steps = (blueprint.steps || []).map((step, index) => {
    const base = {
      order: index + 1,
      type: step.type,
      name: step.name || step.type,
      target: step.target || '',
      liveInput: false,
      ready: false,
      status: 'unknown',
      detail: '',
    };

    if (step.type === 'hotkey') {
      return { ...base, status: 'planned_hotkey', ready: true, detail: 'hotkey is offline-defined; live HWND send is not claimed' };
    }
    if (step.type === 'delay') {
      return { ...base, status: 'planned_delay', ready: true, detail: 'delay is offline-defined' };
    }
    if (step.type === 'ocr_assert') {
      return { ...base, status: 'needs_ocr_backend', ready: false, detail: 'OCR text target is defined offline; OCR backend/live frame not verified' };
    }
    if (step.type === 'snapshot') {
      return { ...base, status: 'planned_snapshot', ready: true, detail: 'snapshot remains observational and never authorizes control input' };
    }
    if (step.type === 'restore') {
      return { ...base, status: 'planned_restore', ready: false, detail: 'restore is still plan-only semantics and not a live success claim' };
    }

    if (VISUAL_STEP_TYPES.has(step.type)) {
      const targetId = String(step.target || '').trim();
      const asset = targetAssets[targetId] || {};
      const binding = templateBindingForTarget(targetId, bindings);
      const hasUserAsset = Boolean(asset.dataUrl || asset.roi || asset.loaded === true);

      let ready = false;
      let status = 'needs_capture';
      let detail = '';

      if (hasUserAsset) {
        ready = true;
        status = 'asset_bound';
        detail = 'target has offline image/ROI asset';
      } else if (!binding) {
        ready = false;
        status = 'needs_capture';
        detail = 'no built-in template binding for ' + (targetId || '(missing target)');
      } else if (availableKeys.size > 0 && !availableKeys.has(binding.key)) {
        ready = false;
        status = 'needs_capture';
        detail = 'built-in template key missing: ' + binding.key;
      } else if (availableKeys.size > 0 && availableKeys.has(binding.key)) {
        ready = true;
        status = 'builtin_template_available';
        detail = 'built-in template available: ' + binding.key;
      } else {
        ready = false;
        status = 'needs_capture';
        detail = 'binding exists (' + binding.key + ') but offline asset load not proven';
      }

      return { ...base, ready, status, detail, templateKey: binding?.key || null };
    }

    return {
      ...base,
      status: 'unsupported_offline',
      ready: false,
      detail: 'offline classifier has no special rule for ' + step.type,
    };
  });

  const requiredTargets = requiredVisualTargets(blueprint);
  const missingTargets = requiredTargets.filter((targetId) => {
    const step = steps.find((item) => item.target === targetId && VISUAL_STEP_TYPES.has(item.type));
    return !step || !step.ready;
  });
  const visualReady = steps.filter((item) => VISUAL_STEP_TYPES.has(item.type)).every((item) => item.ready);

  return {
    blueprintId: blueprint.id,
    label: blueprint.label,
    stepCount: steps.length,
    requiredVisualTargets: requiredTargets,
    missingVisualTargets: missingTargets,
    steps,
    offlineScaffoldReady: visualReady && missingTargets.length === 0,
    liveReady: false,
    liveInputAuthorized: false,
    notes: [
      'Offline readiness never authorizes live HWND input.',
      'OCR and restore steps do not count as live success.',
    ],
  };
}

export function summarizeHomeVitalityGaps(assessment) {
  const source = assessment || assessHomeVitalityReadiness();
  const gaps = [];
  for (const target of source.missingVisualTargets || []) {
    gaps.push({ kind: 'visual_target', target, status: 'needs_capture' });
  }
  for (const step of source.steps || []) {
    if (step.status === 'needs_ocr_backend') {
      gaps.push({ kind: 'ocr', target: step.target, status: step.status, step: step.name });
    }
    if (step.status === 'planned_restore') {
      gaps.push({ kind: 'restore', target: step.target, status: step.status, step: step.name });
    }
  }
  return {
    blueprintId: source.blueprintId,
    offlineScaffoldReady: source.offlineScaffoldReady,
    liveReady: false,
    gapCount: gaps.length,
    gaps,
  };
}
