import {
  normalizeManualConfirmationSafety,
  normalizedManualConfirmation,
} from "./manual-confirmation-core.js";

export const TARGET_LIBRARY_KIND = "mhxy-target-library";

const DEFAULT_IMAGE_THRESHOLD = 0.86;

function timestamp(options = {}) {
  return typeof options.now === "function" ? options.now() : new Date().toISOString();
}

export function normalizeTarget(value, options = {}) {
  const threshold = normalizedThreshold(value?.match?.threshold ?? value?.threshold, options.defaultImageThreshold);
  const createdAt = String(value?.createdAt || timestamp(options));
  const target = {
    id: String(value?.id || randomTargetId(options)),
    name: String(value?.name || "未命名目标"),
    kind: String(value?.kind || (value?.dataUrl ? "image" : value?.roi ? "roi" : "unknown")),
    createdAt,
    updatedAt: String(value?.updatedAt || value?.createdAt || createdAt),
    dataUrl: value?.dataUrl ? String(value.dataUrl) : "",
    roi: value?.roi || null,
    match: {
      threshold,
      scope: String(value?.match?.scope || (value?.roi ? "roi" : "window")),
    },
    texts: Array.isArray(value?.texts) ? value.texts.map(String).filter(Boolean) : [],
    click: {
      button: normalizedTargetButton(value?.click?.button || value?.button || "left"),
      point: String(value?.click?.point || value?.point || "center"),
    },
    source: value?.source || null,
    width: Number(value?.width || 0),
    height: Number(value?.height || 0),
    note: String(value?.note || ""),
    safety: normalizeManualConfirmationSafety({
      ...(value?.safety || {}),
      requiresManualConfirmation:
        value?.safety?.requiresManualConfirmation ?? value?.requiresManualConfirmation,
    }),
    manualConfirmation: value?.manualConfirmation || null,
  };
  target.manualConfirmation = normalizedManualConfirmation(target);
  return target;
}

export function targetLibraryExportPayload(targets, options = {}) {
  const normalizedTargets = (targets || []).map((target) => normalizeTarget(cloneJson(target), options));
  return {
    kind: TARGET_LIBRARY_KIND,
    schemaVersion: options.schemaVersion || 1,
    exportedAt: timestamp(options),
    targetCount: normalizedTargets.length,
    targets: normalizedTargets,
  };
}

export function targetLibraryTargetsFromPayload(value, options = {}) {
  const hasTargets = Array.isArray(value) || Array.isArray(value?.targets);
  const source = Array.isArray(value) ? value : Array.isArray(value?.targets) ? value.targets : [];
  if (!hasTargets) {
    throw new Error("未找到 targets[]，请粘贴目标库包或完整工作区 JSON");
  }
  const byId = new Map();
  for (const raw of source) {
    const target = normalizeTarget(raw, options);
    if (!target.id.trim()) continue;
    byId.set(target.id, target);
  }
  return [...byId.values()];
}

export function mergeImportedTargetLibrary(existingTargets, importedTargets, options = {}) {
  const byId = new Map(existingTargets.map((target) => [target.id, target]));
  const result = { total: importedTargets.length, added: 0, updated: 0, skipped: 0 };
  for (const incoming of importedTargets) {
    const existing = byId.get(incoming.id);
    if (!existing) {
      existingTargets.unshift(incoming);
      byId.set(incoming.id, incoming);
      result.added += 1;
      continue;
    }
    if (mergeImportedTargetIntoExisting(existing, incoming, options)) {
      result.updated += 1;
    } else {
      result.skipped += 1;
    }
  }
  return result;
}

export function mergeImportedTargetIntoExisting(existing, incoming, options = {}) {
  let changed = false;
  const existingWasEmpty = !existing.dataUrl && !existing.roi && !(existing.texts || []).length;
  const fill = (field, value) => {
    if (existing[field] || value == null || value === "") return;
    existing[field] = value;
    changed = true;
  };

  if (existing.kind === "unknown" && incoming.kind && incoming.kind !== "unknown") {
    existing.kind = incoming.kind;
    changed = true;
  }
  fill("dataUrl", incoming.dataUrl);
  fill("roi", incoming.roi);
  fill("source", incoming.source);
  fill("width", incoming.width > 0 ? incoming.width : null);
  fill("height", incoming.height > 0 ? incoming.height : null);
  if (!(existing.texts || []).length && incoming.texts?.length) {
    existing.texts = incoming.texts.slice();
    changed = true;
  }
  if (existingWasEmpty && (incoming.dataUrl || incoming.roi || incoming.texts?.length)) {
    existing.match = { ...(incoming.match || existing.match || {}) };
    existing.click = { ...(incoming.click || existing.click || {}) };
    changed = true;
  }
  if (targetNoteIsGeneric(existing.note) && incoming.note) {
    existing.note = incoming.note;
    changed = true;
  }
  if (incoming.safety?.requiresManualConfirmation && !existing.safety?.requiresManualConfirmation) {
    existing.safety = {
      ...(existing.safety || {}),
      requiresManualConfirmation: true,
    };
    changed = true;
  }
  const manualConfirmation = normalizedManualConfirmation(existing);
  if (JSON.stringify(existing.manualConfirmation || null) !== JSON.stringify(manualConfirmation)) {
    existing.manualConfirmation = manualConfirmation;
    changed = true;
  }
  if (changed) existing.updatedAt = timestamp(options);
  return changed;
}

export function targetNoteIsGeneric(note) {
  const text = String(note || "");
  return !text || text.includes("由任务步骤生成") || text.includes("步骤片段自动创建");
}

function normalizedThreshold(value, fallback = DEFAULT_IMAGE_THRESHOLD) {
  const number = Number(value);
  const defaultValue = Number.isFinite(Number(fallback)) ? Number(fallback) : DEFAULT_IMAGE_THRESHOLD;
  return Number.isFinite(number) && number >= 0 && number <= 1 ? number : defaultValue;
}

function normalizedTargetButton(value) {
  return ["right", "r", "secondary"].includes(String(value || "").toLowerCase()) ? "right" : "left";
}

function randomTargetId(options = {}) {
  return typeof options.randomId === "function" ? options.randomId("target") : `target-${Math.random().toString(36).slice(2, 8)}`;
}

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value || {}));
}
