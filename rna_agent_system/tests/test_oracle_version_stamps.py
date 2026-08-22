"""Oracle version-drift stamps (DECISIONS (w)) — pure-additive hardening.

Pins the 2026-08-22 version-stamp contract:

- every managed-oracle ToolSpec descriptor declares ``oracle_version``;
- every packaged SelfModel record carries a profiling-time ``oracle_version``
  matching the descriptor-declared version (zero drift on the shipped model);
- legacy records / JSON without the field still load (backward compatible);
- ``CalibratedRuntime.configure`` warns and audits ``oracle_version_mismatch``
  on drift — and the drift never changes a gate verdict or blocks a call
  (semantics unchanged; informational only);
- the audit event type is registered in the ``AuditEvent`` Literal (an
  unregistered type is silently dropped — the DECISIONS (s) defect class).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from agent_core.calibrated.audit_trail import AuditTrail
from agent_core.calibrated.models import AuditEvent, CapabilityRecord
from agent_core.calibrated.runtime import (
    DEFAULT_SELF_MODEL_PATH,
    ORACLE_VERSIONS,
    CalibratedRuntime,
)
from agent_core.calibrated.self_model import SelfModel
from agent_core.tool_specs import TOOL_SPECS


@pytest.fixture(scope="module")
def packaged_payload() -> dict:
    return json.loads(DEFAULT_SELF_MODEL_PATH.read_text(encoding="utf-8"))


def test_every_managed_oracle_descriptor_declares_a_version():
    oracle_specs = [s.oracle for s in TOOL_SPECS.values() if s.oracle is not None]
    assert oracle_specs, "managed-oracle set unexpectedly empty"
    for descriptor in oracle_specs:
        assert descriptor.oracle_version, (
            f"{descriptor.oracle_id} declares no oracle_version — every managed "
            "oracle must pin the deployed artifact version (DECISIONS (w))"
        )
    assert ORACLE_VERSIONS == {
        d.oracle_id: d.oracle_version for d in oracle_specs
    }


def test_packaged_records_are_stamped_and_match_descriptors(packaged_payload):
    records = packaged_payload["records"]
    assert records
    unstamped = [r["oracle"] for r in records if not r.get("oracle_version")]
    assert not unstamped, f"records without oracle_version: {unstamped}"
    mismatches = [
        (r["oracle"], r["oracle_version"])
        for r in records
        if r["oracle_version"] != ORACLE_VERSIONS[r["oracle"]]
    ]
    assert not mismatches, (
        f"packaged SelfModel stamps diverge from the declared descriptors: "
        f"{mismatches} — either re-anchor the generator literals (if the "
        "grades really were profiled on the declared version) or re-profile"
    )


def test_packaged_model_has_zero_drift(packaged_payload, tmp_path):
    runtime = CalibratedRuntime.configure(
        self_model_path=DEFAULT_SELF_MODEL_PATH,
        audit_path=tmp_path / "audit.jsonl",
    )
    try:
        assert runtime.oracle_version_drift() == []
        assert runtime.audit.events() == []
    finally:
        CalibratedRuntime.clear()


def test_legacy_records_without_stamp_load_and_never_fabricate_drift(tmp_path):
    legacy = CapabilityRecord.model_validate(
        {"oracle": "gemorna_5utr_mrl", "task_type": "t", "target_family": "f"}
    )
    assert legacy.oracle_version is None

    model = SelfModel(records=[legacy])
    runtime = CalibratedRuntime(
        model, AuditTrail(tmp_path / "audit.jsonl"), policy="enforce"
    )
    # No stamp on the record -> nothing to compare -> no drift, no event.
    assert runtime.oracle_version_drift() == []


def test_configure_warns_and_audits_on_version_drift(tmp_path, caplog):
    payload = json.loads(DEFAULT_SELF_MODEL_PATH.read_text(encoding="utf-8"))
    for record in payload["records"]:
        if record["oracle"] == "rnastop_stability":
            record["oracle_version"] = "0.0.9-simulated-upgrade"
    model_path = tmp_path / "drifted_self_model.json"
    model_path.write_text(json.dumps(payload), encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="agent_core.calibrated.runtime"):
        runtime = CalibratedRuntime.configure(
            self_model_path=model_path, audit_path=tmp_path / "audit.jsonl"
        )
    try:
        drift = runtime.oracle_version_drift()
        assert drift == [
            {
                "oracle": "rnastop_stability",
                "declared_version": "0.1.0",
                "record_version": "0.0.9-simulated-upgrade",
            }
        ]
        events = runtime.audit.events()
        mismatch = [e for e in events if e.event_type == "oracle_version_mismatch"]
        assert len(mismatch) == 1
        assert mismatch[0].payload["oracle"] == "rnastop_stability"
        assert mismatch[0].payload["record_version"] == "0.0.9-simulated-upgrade"
        assert any(
            "oracle_version_drift" in rec.message and "rnastop_stability" in rec.message
            for rec in caplog.records
        ), [rec.message for rec in caplog.records]
    finally:
        CalibratedRuntime.clear()


def test_drift_never_changes_gate_verdicts(tmp_path):
    """A drifted record gates exactly like an aligned one (semantics pinned)."""

    def verdicts(model: SelfModel):
        runtime = CalibratedRuntime(model, AuditTrail(tmp_path / "a.jsonl"))
        out = {}
        for tool in (
            "predict_5utr_mrl_with_gemorna",  # verified under the packaged model
            "predict_mrna_stability_with_rnastop",  # ranking failed
        ):
            decision = runtime.review_tool_call(tool)
            out[tool] = (decision.verdict, runtime.should_block(decision, tool))
        return out

    aligned = SelfModel.from_dict(
        json.loads(DEFAULT_SELF_MODEL_PATH.read_text(encoding="utf-8"))
    )
    drifted_records = []
    for record in aligned.records():
        record.oracle_version = "9.9.9-drifted"
        drifted_records.append(record)
    drifted = SelfModel(records=drifted_records)

    assert verdicts(drifted) == verdicts(aligned)


def test_mismatch_event_type_is_registered():
    # An unregistered Literal would raise here and be silently swallowed by
    # the best-effort writer (the DECISIONS (s) defect class).
    event = AuditEvent(event_type="oracle_version_mismatch", payload={"oracle": "x"})
    assert event.event_type == "oracle_version_mismatch"
