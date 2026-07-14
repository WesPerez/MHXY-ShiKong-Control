export const MANUAL_CONFIRMATION_VERSION = 1;

export function normalizeManualConfirmationSafety(value) {
  const source = objectValue(value);
  return {
    requiresManualConfirmation: Boolean(
      source.requiresManualConfirmation || source.manualConfirmationRequired,
    ),
  };
}

export function requiresManualConfirmationForStep(step, target = null) {
  return Boolean(
    step?.requiresManualConfirmation ||
      target?.safety?.requiresManualConfirmation ||
      commandRequiresManualConfirmation(step?.command),
  );
}

export function manualConfirmationBindingFingerprint(target) {
  const source = objectValue(target);
  const payload = {
    id: text(source.id),
    kind: text(source.kind),
    dataUrl: text(source.dataUrl),
    roi: normalizedRoi(source.roi),
    match: {
      threshold: normalizedNumber(source.match?.threshold),
      scope: text(source.match?.scope),
    },
    click: {
      button: text(source.click?.button),
      point: text(source.click?.point),
    },
  };
  return `manual-binding-v1:${fnv1a32(stableJson(payload))}`;
}

export function manualConfirmationStatus(target, options = {}) {
  const source = objectValue(target);
  const required = options.required ?? Boolean(source.safety?.requiresManualConfirmation);
  const fingerprint = source.id ? manualConfirmationBindingFingerprint(source) : "";
  const confirmation = objectValue(source.manualConfirmation);

  if (!required) {
    return { required: false, valid: true, code: "not_required", fingerprint, confirmation: null };
  }
  if (!source.id) {
    return { required: true, valid: false, code: "target_missing", fingerprint, confirmation: null };
  }
  if (!confirmation.targetId || !confirmation.bindingFingerprint || !confirmation.approvedAt) {
    return { required: true, valid: false, code: "missing", fingerprint, confirmation: null };
  }
  if (String(confirmation.targetId) !== String(source.id)) {
    return { required: true, valid: false, code: "target_mismatch", fingerprint, confirmation: null };
  }
  if (String(confirmation.bindingFingerprint) !== fingerprint) {
    return { required: true, valid: false, code: "binding_changed", fingerprint, confirmation: null };
  }
  if (!isValidTimestamp(confirmation.approvedAt)) {
    return { required: true, valid: false, code: "invalid_timestamp", fingerprint, confirmation: null };
  }
  return {
    required: true,
    valid: true,
    code: "valid",
    fingerprint,
    confirmation: {
      version: Number(confirmation.version) || MANUAL_CONFIRMATION_VERSION,
      targetId: String(confirmation.targetId),
      bindingFingerprint: String(confirmation.bindingFingerprint),
      approvedAt: String(confirmation.approvedAt),
    },
  };
}

export function manualConfirmationStatusForStep(step, target = null) {
  return manualConfirmationStatus(target, {
    required: requiresManualConfirmationForStep(step, target),
  });
}

export function createManualConfirmation(target, options = {}) {
  const source = objectValue(target);
  if (!source.id) throw new Error("manual confirmation requires a target id");
  const approvedAt = typeof options.now === "function" ? options.now() : new Date().toISOString();
  if (!isValidTimestamp(approvedAt)) throw new Error("manual confirmation requires an ISO timestamp");
  return {
    version: MANUAL_CONFIRMATION_VERSION,
    targetId: String(source.id),
    bindingFingerprint: manualConfirmationBindingFingerprint(source),
    approvedAt: String(approvedAt),
  };
}

export function normalizedManualConfirmation(target, options = {}) {
  const status = manualConfirmationStatus(target, options);
  return status.valid && status.required ? status.confirmation : null;
}

export function manualConfirmationStatusText(status) {
  switch (status?.code) {
    case "valid":
      return "已确认当前素材、ROI 与点击语义";
    case "binding_changed":
      return "素材、ROI、匹配或点击语义已变化，需要重新人工确认";
    case "target_mismatch":
      return "确认记录绑定到其他目标，需要重新人工确认";
    case "invalid_timestamp":
      return "确认记录时间无效，需要重新人工确认";
    case "target_missing":
      return "受保护步骤缺少可确认的目标";
    case "missing":
      return "需要人工确认当前目标后才能进入后台队列";
    default:
      return "无需人工确认";
  }
}

function commandRequiresManualConfirmation(command) {
  return String(command || "")
    .split(/[;,]/)
    .map((part) => part.trim())
    .some((part) => {
      const splitAt = part.indexOf("=");
      if (splitAt < 0) return false;
      const key = part.slice(0, splitAt).trim().toLowerCase();
      const value = part.slice(splitAt + 1).trim().toLowerCase();
      return key === "confirmation" && ["manual-required", "manual_required"].includes(value);
    });
}

function normalizedRoi(value) {
  const source = objectValue(value);
  return {
    x: normalizedNumber(source.x),
    y: normalizedNumber(source.y),
    w: normalizedNumber(source.w),
    h: normalizedNumber(source.h),
  };
}

function normalizedNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function isValidTimestamp(value) {
  return typeof value === "string" && value.trim() && Number.isFinite(Date.parse(value));
}

function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${stableJson(value[key])}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
}

function fnv1a32(value) {
  let hash = 0x811c9dc5;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function text(value) {
  return String(value ?? "");
}
