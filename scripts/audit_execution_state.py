#!/usr/bin/env python3
"""Audit the repository-local long-task continuity contract."""

from __future__ import print_function

import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Dict, List

import execution_progress as progress


ROOT = Path(__file__).resolve().parents[1]


def fail(errors: List[str], message: str) -> None:
    errors.append(message)


def warn(warnings: List[str], message: str) -> None:
    warnings.append(message)


def parse_utc(value: str) -> dt.datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("timestamp must be UTC and end with Z")
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate_hash_chain(path: Path, kind: str, errors: List[str]) -> List[Dict[str, Any]]:
    try:
        records = progress.load_jsonl(path)
    except Exception as exc:
        fail(errors, "{} cannot be parsed: {}".format(path.relative_to(ROOT), exc))
        return []
    previous_hash = None
    expected_seq = 1
    seen_ids = set()
    for record in records:
        if record.get("kind") != kind:
            fail(errors, "{} seq {} has invalid kind".format(path.name, record.get("seq")))
        if record.get("schemaVersion") != 1:
            fail(errors, "{} seq {} has unsupported schemaVersion".format(path.name, record.get("seq")))
        if record.get("seq") != expected_seq:
            fail(errors, "{} expected seq {}, got {}".format(path.name, expected_seq, record.get("seq")))
        if record.get("id") in seen_ids:
            fail(errors, "{} contains duplicate id {}".format(path.name, record.get("id")))
        seen_ids.add(record.get("id"))
        if record.get("prevHash") != previous_hash:
            fail(errors, "{} seq {} prevHash mismatch".format(path.name, record.get("seq")))
        expected_hash = progress.object_hash(record)
        if record.get("hash") != expected_hash:
            fail(errors, "{} seq {} hash mismatch".format(path.name, record.get("seq")))
        previous_hash = record.get("hash")
        expected_seq += 1
    return records


def validate_tail(state: Dict[str, Any], key: str, records: List[Dict[str, Any]], errors: List[str]) -> None:
    expected = {"seq": 0, "id": None, "hash": None}
    if records:
        last = records[-1]
        expected = {"seq": last.get("seq"), "id": last.get("id"), "hash": last.get("hash")}
    actual = state.get(key)
    if actual != expected:
        fail(errors, "state.{} does not match ledger tail: expected {}, got {}".format(key, expected, actual))


def git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git"] + list(args),
        cwd=str(ROOT),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.stdout.strip()


def audit_unlocked() -> int:
    errors: List[str] = []
    warnings: List[str] = []
    required = [
        ROOT / "AGENTS.md",
        ROOT / "docs" / "project-audit-and-master-plan.md",
        progress.EXECUTION_DIR / "PROTOCOL.md",
        progress.STATE_PATH,
        progress.STATUS_PATH,
        progress.EVENTS_PATH,
        progress.EVIDENCE_PATH,
    ]
    for path in required:
        if not path.exists():
            fail(errors, "missing required file: {}".format(path.relative_to(ROOT)))
    if errors:
        for message in errors:
            print("ERROR: " + message)
        return 1

    try:
        state = progress.load_json(progress.STATE_PATH)
    except Exception as exc:
        print("ERROR: state.json cannot be parsed: {}".format(exc))
        return 1

    if state.get("kind") != "mhxy-shikong.execution-state":
        fail(errors, "state.kind is invalid")
    if state.get("schemaVersion") != 1:
        fail(errors, "state.schemaVersion must be 1")
    if not isinstance(state.get("revision"), int) or state.get("revision", 0) < 1:
        fail(errors, "state.revision must be a positive integer")
    try:
        updated_at = parse_utc(state.get("updatedAt"))
        if updated_at > dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5):
            fail(errors, "state.updatedAt is in the future")
    except Exception as exc:
        fail(errors, "state.updatedAt invalid: {}".format(exc))

    if state.get("overallStatus") not in {"active", "blocked", "completed", "cancelled"}:
        fail(errors, "state.overallStatus is invalid")
    if state.get("phaseStatus") not in progress.PHASE_STATUSES:
        fail(errors, "state.phaseStatus is invalid")
    if state.get("actionStatus") not in progress.ACTION_STATUSES:
        fail(errors, "state.actionStatus is invalid")
    in_flight = state.get("inFlightAction")
    if in_flight and state.get("actionStatus") not in {"running", "unknown_after_interruption"}:
        fail(errors, "inFlightAction exists but actionStatus is neither running nor unknown_after_interruption")
    if in_flight and in_flight.get("status") != state.get("actionStatus"):
        fail(errors, "inFlightAction.status does not match state.actionStatus")
    if not in_flight and state.get("actionStatus") in {"running", "unknown_after_interruption"}:
        fail(errors, "actionStatus requires an unresolved inFlightAction")
    if state.get("overallStatus") == "completed" and (in_flight or state.get("actionStatus") == "unknown_after_interruption"):
        fail(errors, "completed state cannot contain an unresolved action")

    phase_ids = [phase.get("id") for phase in state.get("phases", [])]
    expected_phase_ids = ["P{}".format(index) for index in range(10)]
    if phase_ids != expected_phase_ids:
        fail(errors, "phases must be exactly P0 through P9 in order")
    for phase in state.get("phases", []):
        if phase.get("status") not in progress.PHASE_STATUSES:
            fail(errors, "phase {} has invalid status".format(phase.get("id")))
    current_phase = state.get("currentPhaseId")
    if current_phase not in expected_phase_ids:
        fail(errors, "currentPhaseId is invalid")
    active_slice = state.get("activeSlice") or {}
    if not str(active_slice.get("id", "")).startswith(str(current_phase) + "-"):
        fail(errors, "activeSlice.id must belong to currentPhaseId")
    if active_slice.get("status") not in {"ready", "in_progress", "verifying", "verified", "blocked"}:
        fail(errors, "activeSlice.status is invalid")
    for criterion in active_slice.get("acceptanceCriteria", []):
        if criterion.get("status") not in progress.CRITERION_STATUSES:
            fail(errors, "criterion {} has invalid status".format(criterion.get("id")))
        categories = criterion.get("requiredEvidenceCategories", [])
        if not categories or any(category not in progress.EVIDENCE_CATEGORIES for category in categories):
            fail(errors, "criterion {} has no valid evidence category policy".format(criterion.get("id")))
    current_phase_record = next((phase for phase in state.get("phases", []) if phase.get("id") == current_phase), None)
    if current_phase_record and current_phase_record.get("status") != state.get("phaseStatus"):
        fail(errors, "current phase record status differs from phaseStatus")
    if state.get("phaseStatus") == "verified" and active_slice.get("status") != "verified":
        fail(errors, "a verified phase requires its active slice to be verified")
    if active_slice.get("status") == "verified" or state.get("phaseStatus") == "verified":
        unfinished = [criterion.get("id") for criterion in active_slice.get("acceptanceCriteria", []) if criterion.get("status") not in {"passed", "not_required"}]
        if unfinished:
            fail(errors, "verified phase/slice has unfinished criteria: {}".format(", ".join(unfinished)))
    completed_slice_ids = set()
    for completed_slice in state.get("completedSlices", []):
        completed_id = completed_slice.get("id")
        if not completed_id or completed_id in completed_slice_ids:
            fail(errors, "completedSlices contains a missing or duplicate id")
            continue
        completed_slice_ids.add(completed_id)
        if completed_slice.get("status") != "verified" or not completed_slice.get("phaseId") or not completed_slice.get("verifiedAt"):
            fail(errors, "completed slice {} lacks verified status/phase/time".format(completed_id))
        unfinished = [
            criterion.get("id") for criterion in completed_slice.get("acceptanceCriteria", [])
            if criterion.get("status") not in {"passed", "not_required"}
        ]
        if unfinished:
            fail(errors, "completed slice {} has unfinished criteria: {}".format(completed_id, ", ".join(unfinished)))

    for gate_name, gate in state.get("projectVerification", {}).items():
        if gate.get("status") not in progress.GATE_STATUSES:
            fail(errors, "verification gate {} has invalid status".format(gate_name))
    live_gate = state.get("projectVerification", {}).get("gamePostconditionObserved", {})
    if live_gate.get("status") == "passed":
        live_evidence_ids = set(live_gate.get("evidenceIds", []))
        if not live_evidence_ids:
            fail(errors, "gamePostconditionObserved cannot pass without evidence")

    for process in state.get("runtime", {}).get("observedExternalProcesses", []):
        if process.get("cleanupAllowed"):
            fail(errors, "observed external process {} cannot be cleanupAllowed".format(process.get("pid")))
    for process in state.get("runtime", {}).get("managedProcesses", []):
        if process.get("cleanupAllowed") and (process.get("ownership") != "created_by_current_run" or process.get("createdByRunId") != state.get("run", {}).get("runId") or len(process.get("ownershipEvidence", [])) < 2):
            fail(errors, "managed process {} permits cleanup without strong current-run ownership evidence".format(process.get("pid")))
    for artifact in state.get("runtime", {}).get("observedArtifacts", []):
        if artifact.get("cleanupAllowed"):
            fail(errors, "observed artifact {} cannot be cleanupAllowed".format(artifact.get("path")))
    for artifact in state.get("runtime", {}).get("managedArtifacts", []):
        if artifact.get("cleanupAllowed") and (artifact.get("ownership") != "created_by_current_run" or artifact.get("createdByRunId") != state.get("run", {}).get("runId") or len(artifact.get("ownershipEvidence", [])) < 2):
            fail(errors, "managed artifact {} permits cleanup without strong current-run ownership evidence".format(artifact.get("path")))

    events = validate_hash_chain(progress.EVENTS_PATH, "mhxy-shikong.execution-event", errors)
    evidence = validate_hash_chain(progress.EVIDENCE_PATH, "mhxy-shikong.execution-evidence", errors)
    validate_tail(state, "eventTail", events, errors)
    validate_tail(state, "evidenceTail", evidence, errors)

    evidence_by_id = {record.get("id"): record for record in evidence}
    any_input_sent = False
    for record in evidence:
        if record.get("category") not in progress.EVIDENCE_CATEGORIES:
            fail(errors, "evidence {} has an unknown category".format(record.get("id")))
        command_required_categories = {"source_audit", "test", "build", "app_runtime", "live_preflight", "multi_window", "persistence", "appdata_backup", "cleanup_audit"}
        artifact_required_categories = {"build", "app_runtime", "live_preflight", "live_outcome", "multi_window", "persistence", "appdata_backup"}
        if record.get("status") == "passed" and record.get("category") in command_required_categories:
            if not record.get("command") or record.get("exitCode") != 0:
                fail(errors, "passed evidence {} lacks a successful command".format(record.get("id")))
        if record.get("status") == "passed" and record.get("category") in artifact_required_categories and not record.get("artifacts"):
            fail(errors, "passed evidence {} lacks required artifacts".format(record.get("id")))
        if record.get("status") == "passed" and not progress.evidence_provenance_valid(record):
            warn(warnings, "legacy/manual passed evidence {} cannot satisfy gates or criteria".format(record.get("id")))
        record_git = record.get("git", {})
        state_git = state.get("git", {})
        artifact_must_match = (
            record.get("status") == "passed"
            and progress.evidence_provenance_valid(record)
            and record_git.get("observedHead") == state_git.get("observedHead")
            and (
                record.get("category") == "appdata_backup"
                or record_git.get("workingTreeFingerprint") == state_git.get("workingTreeFingerprint")
            )
        )
        for artifact in record.get("artifacts", []):
            artifact_path = Path(str(artifact.get("path", "")))
            absolute = artifact_path if artifact_path.is_absolute() else ROOT / artifact_path
            if artifact.get("exists"):
                if not absolute.is_file():
                    message = "evidence {} artifact is missing: {}".format(record.get("id"), artifact.get("path"))
                    fail(errors, message) if artifact_must_match else warn(warnings, message)
                else:
                    if artifact.get("sha256") != progress.file_sha256(absolute):
                        message = "evidence {} artifact hash mismatch: {}".format(record.get("id"), artifact.get("path"))
                        fail(errors, message) if artifact_must_match else warn(warnings, message)
                    if artifact.get("size") != absolute.stat().st_size:
                        message = "evidence {} artifact size mismatch: {}".format(record.get("id"), artifact.get("path"))
                        fail(errors, message) if artifact_must_match else warn(warnings, message)
            elif record.get("status") == "passed":
                fail(errors, "passed evidence {} records a missing artifact".format(record.get("id")))
        safety = record.get("safety", {})
        any_input_sent = any_input_sent or bool(safety.get("inputSent"))
        if record.get("category") in {"live_preflight", "live_input", "live_outcome"} and record.get("status") == "passed":
            window_record = evidence_by_id.get(record.get("windowEvidenceId"), {})
            has_window_link = (
                record.get("targetIdentity")
                and window_record.get("category") == "window_identity"
                and window_record.get("targetIdentity") == record.get("targetIdentity")
                and window_record.get("safety", {}).get("windowIdentityVerified")
                and progress.evidence_provenance_valid(window_record)
                and (window_record.get("windowIdentity") or {}).get("privilege") in {"same", "elevated"}
            )
            if not has_window_link:
                fail(errors, "passed live evidence {} lacks a valid window identity evidence link".format(record.get("id")))
            if record.get("category") == "live_preflight" and safety.get("inputSent") is not False:
                fail(errors, "passed live_preflight evidence {} must explicitly report inputSent=false".format(record.get("id")))
            if record.get("category") in {"live_input", "live_outcome"} and not safety.get("inputSent"):
                fail(errors, "passed live input evidence {} lacks inputSent".format(record.get("id")))
        if record.get("category") == "live_outcome" and record.get("status") == "passed" and not record.get("outcome", {}).get("postconditionObserved"):
            fail(errors, "passed live_outcome evidence {} lacks postcondition proof".format(record.get("id")))
        if record.get("category") == "appdata_backup" and record.get("status") == "passed":
            verification = record.get("verification") or {}
            required = [
                verification.get("actionId"),
                verification.get("idempotencyKey"),
                verification.get("sourcePath"),
                verification.get("destinationPath"),
                verification.get("sourceSha256Before"),
                verification.get("sourceSha256After"),
                verification.get("destinationSha256"),
                verification.get("sourceSize"),
                verification.get("destinationSize"),
            ]
            if any(value in {None, ""} for value in required) or verification.get("destinationWasAbsentAtIntent") is not True:
                fail(errors, "passed appdata_backup evidence {} lacks structured verifier fields".format(record.get("id")))
            hashes = {
                verification.get("sourceSha256Before"),
                verification.get("sourceSha256After"),
                verification.get("destinationSha256"),
            }
            if len(hashes) != 1 or verification.get("sourceSize") != verification.get("destinationSize"):
                fail(errors, "passed appdata_backup evidence {} does not prove matching source/destination identity".format(record.get("id")))
            artifacts = record.get("artifacts", [])
            if len(artifacts) != 1 or artifacts[0].get("path") != verification.get("destinationPath") or artifacts[0].get("sha256", "").upper() != verification.get("destinationSha256"):
                fail(errors, "passed appdata_backup evidence {} destination artifact does not match verification".format(record.get("id")))
        if record.get("category") == "window_identity" and record.get("status") in {"passed", "observed"}:
            identity = record.get("windowIdentity") or {}
            required_identity_fields = [record.get("targetIdentity"), identity.get("hwnd"), identity.get("pid"), identity.get("title"), identity.get("process"), identity.get("clientWidth"), identity.get("clientHeight"), identity.get("privilege")]
            if not safety.get("windowIdentityVerified") or any(value in {None, ""} for value in required_identity_fields):
                fail(errors, "window identity evidence {} is incomplete".format(record.get("id")))
    if any_input_sent != bool(state.get("safety", {}).get("realInputSent")):
        fail(errors, "state.safety.realInputSent does not match the evidence ledger")
    last_window_identity = state.get("runtime", {}).get("lastWindowIdentity")
    if last_window_identity:
        identity_record = evidence_by_id.get(last_window_identity.get("evidenceId"), {})
        if identity_record.get("category") != "window_identity" or identity_record.get("targetIdentity") != last_window_identity.get("targetIdentity"):
            fail(errors, "runtime.lastWindowIdentity is not backed by matching evidence")

    for gate_name, gate in state.get("projectVerification", {}).items():
        for evidence_id in gate.get("evidenceIds", []):
            if evidence_id not in evidence_by_id:
                fail(errors, "verification gate {} references missing evidence {}".format(gate_name, evidence_id))
        if gate.get("status") == "passed":
            if not gate.get("evidenceIds"):
                fail(errors, "passed verification gate {} has no evidence".format(gate_name))
            elif not any(progress.evidence_satisfies_gate(gate_name, evidence_by_id.get(evidence_id, {}), state) for evidence_id in gate.get("evidenceIds", [])):
                fail(errors, "passed verification gate {} lacks semantically valid evidence".format(gate_name))
    for criterion in active_slice.get("acceptanceCriteria", []):
        if criterion.get("status") == "passed":
            records = [evidence_by_id.get(evidence_id) for evidence_id in criterion.get("evidenceIds", [])]
            if not records or not any(record and progress.evidence_satisfies_criterion(criterion, record, state) for record in records):
                fail(errors, "passed criterion {} lacks current valid evidence".format(criterion.get("id")))
            required_categories = set(criterion.get("requiredEvidenceCategories", []))
            if required_categories and not any(record and record.get("status") == "passed" and record.get("category") in required_categories for record in records):
                fail(errors, "passed criterion {} lacks evidence in its required categories".format(criterion.get("id")))

    checkpoint_files = sorted(progress.CHECKPOINT_DIR.glob("CP-*.json")) if progress.CHECKPOINT_DIR.exists() else []
    checkpoint_ids = set()
    checkpoint_values: Dict[str, Dict[str, Any]] = {}
    for checkpoint_file in checkpoint_files:
        try:
            value = progress.load_json(checkpoint_file)
            checkpoint_id = value.get("id")
            if checkpoint_id in checkpoint_ids:
                fail(errors, "duplicate checkpoint id {}".format(checkpoint_id))
            checkpoint_ids.add(checkpoint_id)
            checkpoint_values[str(checkpoint_id)] = value
            if value.get("kind") != "mhxy-shikong.execution-checkpoint":
                fail(errors, "checkpoint {} kind mismatch".format(checkpoint_file.name))
            if value.get("hash"):
                if value.get("hash") != progress.object_hash(value):
                    fail(errors, "checkpoint {} hash mismatch".format(checkpoint_file.name))
            else:
                warn(warnings, "legacy checkpoint {} has no self-hash".format(checkpoint_file.name))
        except Exception as exc:
            fail(errors, "checkpoint {} cannot be parsed: {}".format(checkpoint_file.name, exc))
    if checkpoint_files:
        highest = max(int(match.group(1)) for path in checkpoint_files for match in [re.match(r"CP-(\d{4})-", path.name)] if match)
        if int(state.get("checkpointCounter", 0)) < highest:
            fail(errors, "checkpointCounter is behind checkpoint files")

    checkpoint = state.get("lastCheckpoint")
    if checkpoint:
        checkpoint_path = ROOT / checkpoint.get("path", "")
        if not checkpoint_path.exists():
            fail(errors, "last checkpoint file is missing: {}".format(checkpoint.get("path")))
        else:
            try:
                checkpoint_value = progress.load_json(checkpoint_path)
                if checkpoint_value.get("id") != checkpoint.get("id"):
                    fail(errors, "checkpoint id mismatch")
                if checkpoint_value.get("kind") != "mhxy-shikong.execution-checkpoint":
                    fail(errors, "checkpoint kind mismatch")
                if checkpoint_value.get("hash") != checkpoint.get("hash") or checkpoint_value.get("hash") != progress.object_hash(checkpoint_value):
                    fail(errors, "last checkpoint hash mismatch")
                if checkpoint_value.get("safeToResume") != checkpoint.get("safeToResume") or checkpoint_value.get("safeToRunLiveInput") != checkpoint.get("safeToRunLiveInput"):
                    fail(errors, "last checkpoint safety flags differ from state")
                if checkpoint_value.get("type") == "git_checkpoint":
                    if checkpoint_value.get("git", {}).get("observedHead") != state.get("git", {}).get("verifiedHead"):
                        fail(errors, "git_checkpoint is not bound to verifiedHead")
                if checkpoint_value.get("safeToRunLiveInput"):
                    gates = state.get("projectVerification", {})
                    if gates.get("currentCommitBuilt", {}).get("status") != "passed" or gates.get("currentCommitAppLaunched", {}).get("status") != "passed":
                        fail(errors, "safeToRunLiveInput checkpoint lacks build/app gates")
                    if not state.get("runtime", {}).get("lastWindowIdentity", {}).get("verified"):
                        fail(errors, "safeToRunLiveInput checkpoint lacks verified window identity")
                    window_evidence_id = state.get("runtime", {}).get("lastWindowIdentity", {}).get("evidenceId")
                    if not progress.evidence_provenance_valid(evidence_by_id.get(window_evidence_id, {})):
                        fail(errors, "safeToRunLiveInput checkpoint window identity lacks specialized verifier provenance")
                    live_scope = checkpoint_value.get("liveScope") or {}
                    if not live_scope.get("targetIdentity") or not live_scope.get("windowEvidenceId") or live_scope.get("privilege") not in {"same", "elevated"}:
                        fail(errors, "safeToRunLiveInput checkpoint has an invalid live scope")
                    if checkpoint_value.get("git", {}).get("observedHead") != state.get("git", {}).get("verifiedHead"):
                        fail(errors, "safeToRunLiveInput checkpoint is not bound to verifiedHead")
            except Exception as exc:
                fail(errors, "checkpoint cannot be parsed: {}".format(exc))
    safe_resume_id = state.get("resume", {}).get("lastSafeResumeSnapshotId")
    if safe_resume_id:
        safe_checkpoint = checkpoint_values.get(str(safe_resume_id))
        if not safe_checkpoint or not safe_checkpoint.get("safeToResume"):
            fail(errors, "lastSafeResumeSnapshotId does not reference a safe checkpoint")

    try:
        external_lease = progress.load_external_action_lease()
        if external_lease:
            leased_action = external_lease.get("action") or {}
            if not in_flight or in_flight.get("actionId") != leased_action.get("actionId"):
                fail(errors, "machine-level external action lease is not represented by inFlightAction")
            if in_flight and in_flight.get("leaseTokenHash") != external_lease.get("leaseTokenHash"):
                fail(errors, "inFlightAction lease token hash differs from machine lease")
            if in_flight:
                local_token = progress.load_action_token(in_flight.get("actionId"))
                if local_token:
                    if hashlib.sha256(local_token.encode("utf-8")).hexdigest() != in_flight.get("leaseTokenHash"):
                        fail(errors, "local action token does not match inFlightAction")
                elif state.get("actionStatus") == "running":
                    fail(errors, "running external action has no local owner token")
                else:
                    warn(warnings, "unresolved external action is owned by another worktree/clone; this checkout cannot release it")
        elif in_flight and in_flight.get("kind") in progress.MACHINE_LEASE_ACTION_KINDS:
            fail(errors, "inFlight external action is missing its machine-level lease")
    except Exception as exc:
        fail(errors, "machine-level external action lease cannot be audited: {}".format(exc))

    git_state = state.get("git", {})
    try:
        observed_head = git_output("rev-parse", "HEAD")
        if git_state.get("observedHead") != observed_head:
            fail(errors, "state observedHead differs from current HEAD")
        verified_head = git_state.get("verifiedHead")
        if not re.fullmatch(r"[0-9a-f]{40}", str(verified_head or "")):
            fail(errors, "verifiedHead is not a 40-character commit hash")
        else:
            try:
                git_output("cat-file", "-e", verified_head + "^{commit}")
            except subprocess.CalledProcessError:
                fail(errors, "verifiedHead is not a resolvable commit")
        snapshot = progress.current_git_snapshot()
        if git_state.get("dirtyPaths") != snapshot.get("dirtyPaths"):
            fail(errors, "state dirtyPaths differs from current git status")
        if not isinstance(git_state.get("dirtyEntries"), list):
            fail(errors, "state git.dirtyEntries is required for rename-safe classification")
        elif git_state.get("dirtyEntries") != snapshot.get("dirtyEntries"):
            fail(errors, "state dirtyEntries differs from current git status")
        if git_state.get("workingTreeFingerprint") != snapshot.get("workingTreeFingerprint"):
            fail(errors, "state workingTreeFingerprint differs from current workspace")
        if git_state.get("upstreamHead") != snapshot.get("upstreamHead"):
            fail(errors, "state upstreamHead differs from origin/main")
    except subprocess.CalledProcessError as exc:
        fail(errors, "git audit failed: {}".format(exc))

    try:
        expected_status = progress.render_status(state, events, evidence)
        actual_status = progress.STATUS_PATH.read_text(encoding="utf-8")
        if actual_status != expected_status:
            fail(errors, "STATUS.md is not the exact projection of state and ledgers; run npm run execution:render")
    except Exception as exc:
        fail(errors, "STATUS.md validation failed: {}".format(exc))

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if "docs/project-audit-and-master-plan.md" not in readme:
        fail(errors, "README.md does not link the master plan")
    if "docs/execution/STATUS.md" not in readme:
        fail(errors, "README.md does not link the execution status")

    observed_at = state.get("runtime", {}).get("observedAt")
    stale_after = int(state.get("runtime", {}).get("staleAfterSeconds", 300))
    try:
        age = (dt.datetime.now(dt.timezone.utc) - parse_utc(observed_at)).total_seconds()
        if age > stale_after:
            warn(warnings, "runtime observation is stale ({:.0f}s old); re-observe before process or window actions".format(age))
    except Exception as exc:
        fail(errors, "runtime.observedAt invalid: {}".format(exc))

    if state.get("safety", {}).get("realInputSent"):
        warn(warnings, "state records that real game input was sent; verify live evidence and postcondition")

    if state.get("overallStatus") == "completed":
        if any(phase.get("status") != "verified" for phase in state.get("phases", [])):
            fail(errors, "completed state requires every phase to be verified")
        if any(criterion.get("status") not in {"passed", "not_required"} for criterion in active_slice.get("acceptanceCriteria", [])):
            fail(errors, "completed state contains unfinished criteria")
        required_gates = ["automated", "currentCommitBuilt", "currentCommitAppLaunched", "gamePostconditionObserved", "foregroundUnaffected", "secondWindowIsolationVerified", "restartPersistenceVerified"]
        if any(state.get("projectVerification", {}).get(name, {}).get("status") != "passed" for name in required_gates):
            fail(errors, "completed state lacks required product verification gates")
        git_state = state.get("git", {})
        if not (git_state.get("observedHead") == git_state.get("verifiedHead") == git_state.get("upstreamHead")):
            fail(errors, "completed state requires observedHead == verifiedHead == upstreamHead")
        non_metadata_dirty = progress.non_metadata_dirty_paths(git_state)
        if non_metadata_dirty:
            fail(errors, "completed state contains uncommitted non-metadata paths")
        if not checkpoint or checkpoint.get("type") != "git_checkpoint":
            fail(errors, "completed state requires a final git_checkpoint")
        if not any(event.get("eventType") == "commit" for event in events) or not any(event.get("eventType") == "push" for event in events):
            fail(errors, "completed state requires commit and push events")

    for message in warnings:
        print("WARN: " + message)
    if errors:
        for message in errors:
            print("ERROR: " + message)
        print("execution state audit failed: {} error(s), {} warning(s)".format(len(errors), len(warnings)))
        return 1
    print("execution state audit passed: {} event(s), {} evidence record(s), {} warning(s)".format(len(events), len(evidence), len(warnings)))
    return 0


def main() -> int:
    try:
        with progress.ProgressLock(progress.progress_lock_path()):
            return audit_unlocked()
    except Exception as exc:
        print("ERROR: execution state audit could not acquire/read a consistent snapshot: {}".format(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
