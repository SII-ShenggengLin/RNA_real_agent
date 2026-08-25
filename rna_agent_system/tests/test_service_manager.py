"""Tests for agent_core.services.service_manager."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from agent_core.services.service_manager import (
    CAPABILITY_SERVICE_MAP,
    ToolServiceSpec,
    check_service_health,
    ensure_services_ready,
    get_services_for_capabilities,
    start_service,
)
from agent_core.workflow_models import Candidate, WorkflowResult
from agent_core.workflows.base import BaseDomainWorkflow


class _DummyWorkflow(BaseDomainWorkflow[dict[str, Any], WorkflowResult]):
    name = "dummy"
    required_capabilities = ["predict_rna_secondary_structure"]
    input_model = None

    def generate_candidates(self, inp: dict[str, Any]) -> list[Candidate]:
        return [Candidate(sequence="AUG", source="dummy")]

    def evaluate(self, candidate: Candidate) -> dict[str, Any]:
        return {"score": 1.0}

    def score(self, metrics: dict[str, Any]) -> dict[str, float]:
        return {"score": metrics["score"]}

    def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResult:
        return WorkflowResult(
            success=True,
            task_id="t1",
            best_candidate=candidates[0],
            all_candidates=candidates,
            summary="dummy ok",
        )


def test_get_services_for_capabilities_deduplicates_by_port():
    """Multiple ViennaRNA capabilities must map to a single service entry."""
    services = get_services_for_capabilities([
        "predict_rna_secondary_structure",
        "compute_sirna_duplex_binding_vienna",
        "predict_rna_local_accessibility_profile_vienna",
    ])
    assert len(services) == 1
    assert services[0].port == 8003
    assert "viennarna_fold" in services[0].start_script


def test_get_services_for_capabilities_returns_empty_for_local_tools():
    """Pure-Python tools have no microservice entry."""
    services = get_services_for_capabilities([
        "compute_cai_for_cds_sequence",
    ])
    assert services == []


def test_get_services_for_capabilities_warns_for_unknown(caplog):
    """Unknown capabilities must be logged so missing mappings are noticed."""
    with caplog.at_level(logging.WARNING, logger="agent_core.services.service_manager"):
        services = get_services_for_capabilities(["totally_unknown_capability"])
    assert services == []
    assert "totally_unknown_capability" in caplog.text


def test_required_capability_mappings_are_present():
    """Smoke test that key workflow capabilities are mapped to services."""
    assert "design_mrna_cds_with_lineardesign" in CAPABILITY_SERVICE_MAP
    assert CAPABILITY_SERVICE_MAP["design_mrna_cds_with_lineardesign"].port == 8014

    assert "run_odesign_inference" in CAPABILITY_SERVICE_MAP
    assert CAPABILITY_SERVICE_MAP["run_odesign_inference"].port == 8012

    assert "score_rna_protein_complex_with_egarps" in CAPABILITY_SERVICE_MAP
    assert CAPABILITY_SERVICE_MAP["score_rna_protein_complex_with_egarps"].port == 8023


def test_bowtie2_auto_start_script_registered():
    """Bowtie2 auto-starts via microservices/bowtie2_service/start.sh."""
    spec = CAPABILITY_SERVICE_MAP["run_bowtie2_short_alignment"]
    assert spec.start_script == "microservices/bowtie2_service/start.sh"


def test_check_service_health_false_for_unreachable():
    """Health check should fail fast for a non-listening port."""
    # Port 1 is typically unused and the call should time out quickly.
    assert check_service_health("http://127.0.0.1:1/health", timeout=1) is False


def _make_mock_http_response(status: int, body: bytes = b"") -> MagicMock:
    """Return a MagicMock that behaves like an ``addinfourl`` context manager."""
    mock_response = MagicMock()
    mock_response.status = status
    mock_response.read.return_value = body
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    return mock_response


def test_check_service_health_accepts_204_empty_body():
    """A 2xx response with an empty body is treated as healthy."""
    mock_response = _make_mock_http_response(204, body=b"")

    with patch(
        "agent_core.services.service_manager.urllib.request.urlopen",
        return_value=mock_response,
    ):
        assert check_service_health("http://127.0.0.1:8003/health") is True


def test_check_service_health_requires_ok_status_in_body():
    """HTTP 200 with ``{\"status\": \"degraded\"}`` must be treated as down."""
    mock_response = _make_mock_http_response(200, body=b'{"status": "degraded"}')

    with patch(
        "agent_core.services.service_manager.urllib.request.urlopen",
        return_value=mock_response,
    ):
        assert check_service_health("http://127.0.0.1:8003/health") is False


def test_check_service_health_accepts_ok_status_in_body():
    """HTTP 200 with ``{\"status\": \"ok\"}`` is treated as healthy."""
    mock_response = _make_mock_http_response(200, body=b'{"status": "ok"}')

    with patch(
        "agent_core.services.service_manager.urllib.request.urlopen",
        return_value=mock_response,
    ):
        assert check_service_health("http://127.0.0.1:8003/health") is True


def test_check_service_health_accepts_non_json_200():
    """A non-JSON 2xx body keeps legacy healthy behavior."""
    mock_response = _make_mock_http_response(200, body=b"ok")

    with patch(
        "agent_core.services.service_manager.urllib.request.urlopen",
        return_value=mock_response,
    ):
        assert check_service_health("http://127.0.0.1:8003/health") is True


def test_ensure_services_ready_no_services():
    """Empty service list is always ready."""
    ready, errors = ensure_services_ready([])
    assert ready is True
    assert errors == []


def test_ensure_services_ready_reports_missing_script():
    """A service without a start script and without health must be reported."""
    svc = ToolServiceSpec(
        capability="run_bowtie2_short_alignment",
        host="127.0.0.1",
        port=1,
        health_path="/health",
        start_script=None,
    )
    ready, errors = ensure_services_ready([svc], timeout=1)
    assert ready is False
    assert any("no auto-start script" in e for e in errors)


def test_ensure_services_ready_starts_service_and_polls():
    """If health is down and a start script is provided, launch and poll it."""
    svc = ToolServiceSpec(
        capability="test_service",
        host="127.0.0.1",
        port=9999,
        health_path="/health",
        start_script="microservices/test_service/start.sh",
    )

    with patch(
        "agent_core.services.service_manager.check_service_health",
        side_effect=[False, True],
    ) as mock_health:
        with patch(
            "agent_core.services.service_manager.start_service",
            return_value=MagicMock(),
        ) as mock_start:
            ready, errors = ensure_services_ready([svc], timeout=5, poll_interval=0)

    assert ready is True
    assert errors == []
    mock_start.assert_called_once_with(
        "microservices/test_service/start.sh",
        cwd=str(Path(__file__).resolve().parents[1]),
    )
    assert mock_health.call_count == 2


def test_ensure_services_ready_already_healthy():
    """No action needed when the service is already healthy."""
    svc = ToolServiceSpec(
        capability="test_service",
        host="127.0.0.1",
        port=9999,
        health_path="/health",
        start_script="microservices/test_service/start.sh",
    )

    with patch(
        "agent_core.services.service_manager.check_service_health",
        return_value=True,
    ) as mock_health:
        with patch("agent_core.services.service_manager.start_service") as mock_start:
            ready, errors = ensure_services_ready([svc])

    assert ready is True
    assert errors == []
    mock_health.assert_called_once_with(svc.health_url, timeout=30.0)
    mock_start.assert_not_called()


def test_ensure_services_ready_fallback_waits_for_remaining_startup_budget():
    """If lock acquisition fails, the fallback poll must use the startup budget.

    The original bug used ``lock_timeout`` (default 30s) for the fallback poll,
    so a second caller would give up while the first caller was still slowly
    starting the service.  After the fix the fallback waits for the remaining
    ``timeout`` budget (default 300s).
    """
    svc = ToolServiceSpec(
        capability="test_service",
        host="127.0.0.1",
        port=9997,
        health_path="/health",
        start_script="microservices/test_service/start.sh",
    )

    with patch(
        "agent_core.services.service_manager._ServiceLock.acquire",
        return_value=False,
    ):
        with patch(
            "agent_core.services.service_manager._poll_health",
            return_value=True,
        ) as mock_poll:
            ready, errors = ensure_services_ready(
                [svc], timeout=300, lock_timeout=30, health_timeout=1.0
            )

    assert ready is True
    assert errors == []
    mock_poll.assert_called_once()
    call_kwargs = mock_poll.call_args[1]
    # The fallback must wait for the service startup budget, not lock_timeout.
    assert call_kwargs["timeout"] > 30
    assert call_kwargs["timeout"] == pytest.approx(300, abs=10)



def test_ensure_services_ready_fallback_waits_for_slow_startup():
    """A caller that loses the startup lock must wait for the service, not lock_timeout."""
    import time as real_time

    svc = ToolServiceSpec(
        capability="test_service",
        host="127.0.0.1",
        port=9995,
        health_path="/health",
        start_script="microservices/test_service/start.sh",
    )

    start = real_time.time()

    def _fake_health(url: str, timeout: int = 5) -> bool:
        # Service becomes healthy after 2 seconds, which is longer than the
        # lock_timeout used below.  Before the fix, the fallback would have
        # given up after lock_timeout=1s and reported failure.
        return real_time.time() - start > 2.0

    with patch(
        "agent_core.services.service_manager._ServiceLock.acquire",
        return_value=False,
    ):
        with patch(
            "agent_core.services.service_manager.check_service_health",
            side_effect=_fake_health,
        ):
            ready, errors = ensure_services_ready(
                [svc],
                timeout=10,
                lock_timeout=1,
                health_timeout=0.5,
                poll_interval=0.2,
            )

    assert ready is True
    assert errors == []
    # The real elapsed time proves we waited beyond lock_timeout.
    assert real_time.time() - start >= 2.0


def test_ensure_services_ready_does_not_start_same_service_twice():
    """Concurrent callers must not launch the same service twice (flock guard)."""
    svc = ToolServiceSpec(
        capability="test_service",
        host="127.0.0.1",
        port=9998,
        health_path="/health",
        start_script="microservices/test_service/start.sh",
    )

    call_count = 0

    def _fake_health(url: str, timeout: int = 5) -> bool:
        nonlocal call_count
        call_count += 1
        # First health check sees down; second sees up.
        return call_count > 1

    with patch(
        "agent_core.services.service_manager.check_service_health",
        side_effect=_fake_health,
    ):
        with patch(
            "agent_core.services.service_manager.start_service",
            return_value=MagicMock(),
        ) as mock_start:
            ready, errors = ensure_services_ready([svc], timeout=5, poll_interval=0)

    assert ready is True
    assert errors == []
    mock_start.assert_called_once()


def test_base_workflow_preflight_disabled_by_default():
    """Direct workflow use does not auto-start services unless requested."""
    wf = _DummyWorkflow()
    assert wf.auto_start_services is False
    with patch("agent_core.services.service_manager.ensure_services_ready") as mock_ensure:
        result = wf.run({})

    assert result.success is True
    mock_ensure.assert_not_called()


def test_base_workflow_preflight_fails_when_service_down():
    """With auto_start_services=True, a down service aborts run() early."""
    wf = _DummyWorkflow()
    wf.auto_start_services = True

    with patch(
        "agent_core.services.service_manager.ensure_services_ready",
        return_value=(False, ["predict_rna_secondary_structure: connection refused"]),
    ):
        result = wf.run({})

    assert result.success is False
    assert "pre-flight failed" in result.summary
    assert "connection refused" in result.errors[0]


def test_base_workflow_partial_rerun_preflight_fails_when_service_down():
    """partial_rerun() also runs the service pre-flight."""
    wf = _DummyWorkflow()
    wf.auto_start_services = True

    with patch(
        "agent_core.services.service_manager.ensure_services_ready",
        return_value=(False, ["predict_rna_secondary_structure: connection refused"]),
    ):
        result = wf.partial_rerun({}, [Candidate(sequence="AUG", source="dummy")])

    assert result is not None
    assert result.success is False
    assert "pre-flight failed" in result.summary


def test_sirna_workflow_preflight_runs_before_generate():
    """SirnaDesignWorkflow.run() must call the base-class service pre-flight."""
    from agent_core.capabilities.base import CapabilityRegistry
    from agent_core.workflows.sirna_design import SirnaDesignWorkflow

    registry = CapabilityRegistry({})
    wf = SirnaDesignWorkflow(registry)
    wf.auto_start_services = True

    with patch(
        "agent_core.services.service_manager.ensure_services_ready",
        return_value=(False, ["design_sirna_with_evitar: connection refused"]),
    ):
        result = wf.run({
            "mode": "generic",
            "target_sequence": "AUGC" * 5,
            "target_structure": "",
            "target_organism": "human",
        })

    assert result.success is False
    assert "pre-flight failed" in result.summary


def test_full_length_workflow_covers_cds_services():
    """FullLengthMrnaDesignWorkflow must include CDS sub-workflow capabilities."""
    from agent_core.workflows.full_length_mrna_design import FullLengthMrnaDesignWorkflow
    from agent_core.workflows.mrna_cds_design import MrnaCdsDesignWorkflow

    cds_caps = set(MrnaCdsDesignWorkflow.required_capabilities)
    full_caps = set(FullLengthMrnaDesignWorkflow.required_capabilities)

    # Every *service-backed* CDS capability must be declared by the parent too.
    local_cds_caps = {"compute_cai_for_cds_sequence"}
    missing = (cds_caps - local_cds_caps) - full_caps
    assert not missing, f"Full-length workflow missing CDS capabilities: {missing}"


def test_all_workflow_capabilities_have_service_or_are_local():
    """Every required_capability is either mapped to a service or a known local tool."""
    from agent_core.workflows import (
        AsoTargetScreeningWorkflow,
        FullLengthMrnaDesignWorkflow,
        IresPredictionWorkflow,
        MrnaCdsDesignWorkflow,
        MrnaSequenceScoringWorkflow,
        RnaAptamerDesignWorkflow,
        RnaSecondaryStructureDesignWorkflow,
        RnaSmallMoleculeInteractionWorkflow,
        RnaTertiaryStructureDesignWorkflow,
        SgRnaDesignWorkflow,
        SirnaDesignWorkflow,
    )

    local_capabilities = {
        "build_odesign_aptamer_input_json",
        "extract_rna_sequence_from_cif",
        "analyze_rna_protein_interface",
        "identify_protein_binding_hotspots",
        "score_structure_alignment",
        "compute_cai_for_cds_sequence",
        "workflow_demo_echo",
    }

    workflows = [
        AsoTargetScreeningWorkflow,
        FullLengthMrnaDesignWorkflow,
        IresPredictionWorkflow,
        MrnaCdsDesignWorkflow,
        MrnaSequenceScoringWorkflow,
        RnaAptamerDesignWorkflow,
        RnaSecondaryStructureDesignWorkflow,
        RnaSmallMoleculeInteractionWorkflow,
        RnaTertiaryStructureDesignWorkflow,
        SgRnaDesignWorkflow,
        SirnaDesignWorkflow,
    ]

    missing: list[tuple[str, str]] = []
    for wf_cls in workflows:
        for cap in wf_cls.required_capabilities:
            if cap in CAPABILITY_SERVICE_MAP or cap in local_capabilities:
                continue
            missing.append((wf_cls.name, cap))

    assert not missing, f"Missing service mapping for capabilities: {missing}"


def test_cli_orchestrator_uses_workflow_required_capabilities():
    """CLI service orchestration must derive services from workflow capabilities,
    not the legacy hand-maintained mapping that included unused services."""
    from cli.service_orchestrator import _services_from_workflow_names

    services = _services_from_workflow_names(["mrna_cds_design"])
    ports = {svc.port for svc in services}
    # Legacy mapping erroneously included CodonW (8018); capability list does not.
    assert 8018 not in ports
    # Required services are still present.
    assert {8003, 8004, 8008, 8009, 8014, 8015, 8020}.issubset(ports)


def test_full_length_child_cds_workflow_inherits_auto_start():
    """CDS sub-workflow created by full-length should inherit auto_start_services."""
    from agent_core.workflows.full_length_mrna_design import FullLengthMrnaDesignWorkflow
    from agent_core.capabilities.base import CapabilityRegistry

    registry = CapabilityRegistry({})
    wf = FullLengthMrnaDesignWorkflow(registry)
    wf.auto_start_services = True
    wf._workflow_state = {}
    child = wf._create_cds_workflow()
    assert child.auto_start_services is True


def test_aptamer_run_preflight_failure_returns_result():
    """Aptamer pre-flight failure must return a WorkflowResult, not raise."""
    from agent_core.workflows.rna_aptamer_design import RnaAptamerDesignWorkflow
    from agent_core.capabilities.base import CapabilityRegistry

    registry = CapabilityRegistry({})
    wf = RnaAptamerDesignWorkflow(registry)
    wf.auto_start_services = True

    with patch.object(
        wf,
        "_ensure_required_services",
        return_value=(False, ["run_odesign_inference: down"]),
    ):
        result = wf.run({"protein_sequence": "MLV", "aptamer_length": 30})

    assert isinstance(result, WorkflowResult)
    assert result.success is False
    assert "pre-flight failed" in result.summary


def test_mrna_sequence_scoring_preflight_runs_before_evaluate():
    """MrnaSequenceScoringWorkflow.run() must call the service pre-flight."""
    from agent_core.capabilities.base import CapabilityRegistry
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
    from agent_core.workflows.mrna_sequence_scoring import MrnaSequenceScoringWorkflow

    registry = build_default_tool_registry()
    executor = ToolExecutor(registry)
    wf = MrnaSequenceScoringWorkflow(CapabilityRegistry(executor))
    wf.auto_start_services = True

    with patch(
        "agent_core.services.service_manager.ensure_services_ready",
        return_value=(False, ["predict_rna_secondary_structure_with_linearfold: connection refused"]),
    ):
        result = wf.run({"sequences": ["AUGC" * 10]})

    assert isinstance(result, WorkflowResult)
    assert result.success is False
    assert "pre-flight failed" in result.summary


def test_mrna_cds_partial_rerun_preflight_runs_before_evaluate():
    """MrnaCdsDesignWorkflow.partial_rerun() must call the service pre-flight."""
    from agent_core.capabilities.base import CapabilityRegistry
    from agent_core.workflows.mrna_cds_design import MrnaCdsDesignWorkflow

    registry = CapabilityRegistry({})
    wf = MrnaCdsDesignWorkflow(registry)
    wf.auto_start_services = True

    candidate = Candidate(sequence="AUGC" * 20, source="test")

    with patch(
        "agent_core.services.service_manager.ensure_services_ready",
        return_value=(False, ["design_mrna_cds_with_lineardesign: connection refused"]),
    ):
        result = wf.partial_rerun({"protein_sequence": "MLV"}, [candidate])

    assert isinstance(result, WorkflowResult)
    assert result.success is False
    assert "pre-flight failed" in result.summary


def test_start_service_raises_on_nonzero_exit(tmp_path):
    """start_service() must raise RuntimeError when start.sh exits non-zero."""
    script = tmp_path / "start.sh"
    script.write_text("#!/bin/bash\necho 'startup failed' >&2\nexit 42\n")
    script.chmod(0o755)

    with pytest.raises(RuntimeError) as exc_info:
        start_service(str(script.name), cwd=str(tmp_path))

    assert "exit code 42" in str(exc_info.value)
    assert "startup failed" in str(exc_info.value)


def test_start_service_returns_proc_on_zero_exit(tmp_path):
    """start_service() returns the Popen object when start.sh exits cleanly."""
    script = tmp_path / "start.sh"
    script.write_text("#!/bin/bash\necho 'server backgrounded'\nexit 0\n")
    script.chmod(0o755)

    proc = start_service(str(script.name), cwd=str(tmp_path))

    assert proc.returncode == 0


def test_ensure_services_ready_busy_service_not_restarted():
    """A busy-but-alive service (port held, /health starved) must NOT be restarted.

    Reproduces the 2026-07-22 fig4 incident: EGARPS single-worker crunching for
    another shard starved /health past the probe timeout; the pre-flight then
    started a duplicate that died on "address already in use" and failed the
    whole run. The fix: port-listening means busy — wait, then proceed anyway.
    """
    import socket

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    listener.listen(1)
    try:
        svc = ToolServiceSpec(
            capability="test_service",
            host="127.0.0.1",
            port=port,
            health_path="/health",
            # Nonexistent script: if a start were attempted it would raise and
            # the ensure would fail — so (True, []) proves no start happened.
            start_script="microservices/definitely_missing/start.sh",
        )
        ready, errors = ensure_services_ready(
            [svc], timeout=1, poll_interval=0, health_timeout=0.2
        )
    finally:
        listener.close()

    assert ready is True
    assert errors == []


def test_ensure_services_ready_starts_when_port_free():
    """Port free + failing health = genuinely down: the start path must run."""
    svc = ToolServiceSpec(
        capability="test_service",
        host="127.0.0.1",
        port=1,  # nothing can listen there; health check fails with refusal
        health_path="/health",
        start_script="microservices/test_service/start.sh",
    )

    with patch(
        "agent_core.services.service_manager.check_service_health",
        side_effect=[False, True],
    ):
        with patch(
            "agent_core.services.service_manager.start_service",
            return_value=MagicMock(),
        ) as mock_start:
            ready, errors = ensure_services_ready([svc], timeout=5, poll_interval=0)

    assert ready is True
    assert errors == []
    mock_start.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# 2026-08-22 Layer-3 fresh-data audit regressions
# ═══════════════════════════════════════════════════════════════════════════

def _serve_status_body(port: int, status: int, body: bytes):
    """Start a real local HTTP server answering /health with a fixed payload."""
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def test_ensure_services_ready_fails_on_listening_degraded_service():
    """A listening service whose /health *answers* with degraded status must
    fail pre-flight with a clear error instead of being waved through via the
    busy-port proceed-anyway path (2026-08-22 Layer-3 audit fix)."""
    import socket

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    listener.close()  # free the port; ThreadingHTTPServer will rebind it

    server = _serve_status_body(port, 200, b'{"status": "degraded", "missing": ["checkpoint"]}')
    try:
        svc = ToolServiceSpec(
            capability="degraded_service",
            host="127.0.0.1",
            port=port,
            health_path="/health",
            start_script="microservices/definitely_missing/start.sh",
        )
        ready, errors = ensure_services_ready(
            [svc], timeout=3, poll_interval=0, health_timeout=1
        )
    finally:
        server.shutdown()
        server.server_close()

    assert ready is False
    assert any("degraded status" in e for e in errors)
    # The degraded service is running: no restart must be attempted (the
    # missing start script would have raised if the start path ran).


def test_ensure_services_ready_fails_on_listening_http_error_service():
    """A listening service answering /health with HTTP 500 fails pre-flight."""
    import socket

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    listener.close()

    server = _serve_status_body(port, 500, b"boom")
    try:
        svc = ToolServiceSpec(
            capability="http_error_service",
            host="127.0.0.1",
            port=port,
            health_path="/health",
            start_script=None,
        )
        ready, errors = ensure_services_ready(
            [svc], timeout=3, poll_interval=0, health_timeout=1
        )
    finally:
        server.shutdown()
        server.server_close()

    assert ready is False
    assert any("degraded status (http_error)" in e for e in errors)


def test_all_mapped_start_scripts_are_executable():
    """Every registered start.sh must carry the executable bit.

    Regression for bowtie2_service/start.sh shipping as 100644 (all other
    services are 100755)."""
    import os

    project_root = Path(__file__).resolve().parents[1]
    for cap, svc in CAPABILITY_SERVICE_MAP.items():
        if not svc.start_script:
            continue
        script = project_root / svc.start_script
        assert script.exists(), f"{cap}: missing start script {svc.start_script}"
        assert os.access(script, os.X_OK), f"{cap}: {svc.start_script} not executable"


def test_cli_orchestrator_all_exports_resolvable():
    """Every name in cli.service_orchestrator.__all__ must be importable.

    Regression: ``check_service_health`` / ``start_service`` were listed in
    ``__all__`` but never imported, so ``from cli.service_orchestrator import
    check_service_health`` raised ImportError."""
    import cli.service_orchestrator as so

    for name in so.__all__:
        assert hasattr(so, name), f"cli.service_orchestrator.__all__ lists unimported {name!r}"

    from cli.service_orchestrator import check_service_health, start_service  # noqa: F401
