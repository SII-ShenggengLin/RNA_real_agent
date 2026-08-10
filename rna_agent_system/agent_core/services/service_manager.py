"""Centralized microservice health checking and auto-start for RNA workflows.

This module maps each capability (tool name) to the local microservice it needs,
provides health polling, and can launch missing services via their ``start.sh``
scripts.  It is consumed by:

* ``BaseDomainWorkflow`` — pre-flight check before ``run()`` / ``run_initial()``.
* ``cli/service_orchestrator.py`` — CLI-level service orchestration.

Keeping the mapping capability-driven means a workflow only needs to declare
``required_capabilities``; the service layer derives which microservices to check.
"""

from __future__ import annotations

import errno
import fcntl
import json
import logging
import os
import socket
import subprocess
import tempfile
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

_LOGGER = logging.getLogger("agent_core.services.service_manager")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class _ServiceLock:
    """Process-wide exclusive lock for starting a single microservice.

    Uses ``fcntl`` flock on a per-port lock file.  This prevents two concurrent
    workflows (or two callers of ``ensure_services_ready``) from launching the
    same microservice twice.
    """

    def __init__(
        self,
        port: int,
        host: str = "127.0.0.1",
        lock_dir: Optional[Path] = None,
    ):
        self.host = host
        self.port = port
        self.lock_path = (lock_dir or Path(tempfile.gettempdir())) / f"rna_agent_service_{host}_{port}.lock"
        self._fd: Optional[int] = None

    def acquire(self, timeout: int = 30) -> bool:
        """Try to acquire the exclusive lock, waiting up to *timeout* seconds."""
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(str(self.lock_path), os.O_CREAT | os.O_RDWR)
        deadline = time.time() + timeout
        while True:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except (IOError, OSError) as exc:
                if exc.errno not in (errno.EAGAIN, errno.EACCES):
                    return False
                if time.time() >= deadline:
                    return False
                time.sleep(0.5)

    def release(self) -> None:
        """Release the lock and close the file descriptor."""
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            finally:
                os.close(self._fd)
                self._fd = None

    def __enter__(self) -> "_ServiceLock":
        if not self.acquire():
            raise RuntimeError(f"Failed to acquire service lock for {self.host}:{self.port}")
        return self

    def __exit__(self, *exc: Any) -> None:
        self.release()


@dataclass(frozen=True)
class ToolServiceSpec:
    """Static description of the microservice behind one capability."""

    capability: str
    host: str
    port: int
    health_path: str
    start_script: Optional[str]
    """Path relative to the project root, e.g. ``microservices/lineardesign_service/start.sh``.

    ``None`` means the service cannot be auto-started by this module (e.g. no
    ``start.sh`` is provided).
    """

    @property
    def health_url(self) -> str:
        return f"http://{self.host}:{self.port}{self.health_path}"

    @property
    def service_key(self) -> str:
        return f"{self.host}:{self.port}"


# Capability -> microservice mapping.  The port must match the default endpoint
# declared in ``agent_core/tool_specs.py`` for the corresponding tool.
CAPABILITY_SERVICE_MAP: dict[str, ToolServiceSpec] = {
    # ViennaRNA fold service (port 8003)
    "predict_rna_secondary_structure": ToolServiceSpec(
        "predict_rna_secondary_structure", "127.0.0.1", 8003, "/health",
        "microservices/viennarna_fold/start.sh",
    ),
    "compute_sirna_duplex_binding_vienna": ToolServiceSpec(
        "compute_sirna_duplex_binding_vienna", "127.0.0.1", 8003, "/health",
        "microservices/viennarna_fold/start.sh",
    ),
    "compute_rna_rna_interaction_vienna": ToolServiceSpec(
        "compute_rna_rna_interaction_vienna", "127.0.0.1", 8003, "/health",
        "microservices/viennarna_fold/start.sh",
    ),
    "compute_aso_target_accessibility_vienna": ToolServiceSpec(
        "compute_aso_target_accessibility_vienna", "127.0.0.1", 8003, "/health",
        "microservices/viennarna_fold/start.sh",
    ),
    "predict_rna_local_accessibility_profile_vienna": ToolServiceSpec(
        "predict_rna_local_accessibility_profile_vienna", "127.0.0.1", 8003, "/health",
        "microservices/viennarna_fold/start.sh",
    ),
    "inverse_fold_rna_secondary_structure_vienna": ToolServiceSpec(
        "inverse_fold_rna_secondary_structure_vienna", "127.0.0.1", 8003, "/health",
        "microservices/viennarna_fold/start.sh",
    ),
    # GEMORNA service (port 8004)
    "design_mrna_cds_with_gemorna": ToolServiceSpec(
        "design_mrna_cds_with_gemorna", "127.0.0.1", 8004, "/health",
        "microservices/gemorna_service/start.sh",
    ),
    "design_5utr_with_gemorna": ToolServiceSpec(
        "design_5utr_with_gemorna", "127.0.0.1", 8004, "/health",
        "microservices/gemorna_service/start.sh",
    ),
    "design_3utr_with_gemorna": ToolServiceSpec(
        "design_3utr_with_gemorna", "127.0.0.1", 8004, "/health",
        "microservices/gemorna_service/start.sh",
    ),
    "predict_5utr_mrl_with_gemorna": ToolServiceSpec(
        "predict_5utr_mrl_with_gemorna", "127.0.0.1", 8004, "/health",
        "microservices/gemorna_service/start.sh",
    ),
    "predict_3utr_stability_with_gemorna": ToolServiceSpec(
        "predict_3utr_stability_with_gemorna", "127.0.0.1", 8004, "/health",
        "microservices/gemorna_service/start.sh",
    ),
    # RhoFold service (port 8005)
    "predict_rna_tertiary_structure_with_rhofold": ToolServiceSpec(
        "predict_rna_tertiary_structure_with_rhofold", "127.0.0.1", 8005, "/health",
        "microservices/rhofold_service/start.sh",
    ),
    # RhoDesign service (port 8006)
    "design_rna_sequence_with_rhodesign": ToolServiceSpec(
        "design_rna_sequence_with_rhodesign", "127.0.0.1", 8006, "/health",
        "microservices/rhodesign_service/start.sh",
    ),
    # RNAsmol service (port 8007)
    "score_rna_ligand_binding_with_rnasmol": ToolServiceSpec(
        "score_rna_ligand_binding_with_rnasmol", "127.0.0.1", 8007, "/health",
        "microservices/rnasmol_service/start.sh",
    ),
    # RNARL service (port 8008)
    "design_mrna_cds_with_rnarl": ToolServiceSpec(
        "design_mrna_cds_with_rnarl", "127.0.0.1", 8008, "/health",
        "microservices/rnarl_service/start.sh",
    ),
    # RNASTOP service (port 8009)
    "predict_mrna_stability_with_rnastop": ToolServiceSpec(
        "predict_mrna_stability_with_rnastop", "127.0.0.1", 8009, "/health",
        "microservices/rnastop_service/start.sh",
    ),
    # GerNA-Bind service (port 8010)
    "score_rna_ligand_binding_with_gernabind": ToolServiceSpec(
        "score_rna_ligand_binding_with_gernabind", "127.0.0.1", 8010, "/health",
        "microservices/gernabind_service/start.sh",
    ),
    # CRISOT service (port 8011)
    "score_crispr_off_target_with_crisot": ToolServiceSpec(
        "score_crispr_off_target_with_crisot", "127.0.0.1", 8011, "/health",
        "microservices/crisot_service/start.sh",
    ),
    "calculate_crispr_specificity_with_crisot": ToolServiceSpec(
        "calculate_crispr_specificity_with_crisot", "127.0.0.1", 8011, "/health",
        "microservices/crisot_service/start.sh",
    ),
    "search_crispr_off_targets_with_crisot": ToolServiceSpec(
        "search_crispr_off_targets_with_crisot", "127.0.0.1", 8011, "/health",
        "microservices/crisot_service/start.sh",
    ),
    "optimize_sgrna_with_crisot": ToolServiceSpec(
        "optimize_sgrna_with_crisot", "127.0.0.1", 8011, "/health",
        "microservices/crisot_service/start.sh",
    ),
    "score_batch_crispr_off_targets_with_crisot": ToolServiceSpec(
        "score_batch_crispr_off_targets_with_crisot", "127.0.0.1", 8011, "/health",
        "microservices/crisot_service/start.sh",
    ),
    "rescore_sgrnas_with_crisot": ToolServiceSpec(
        "rescore_sgrnas_with_crisot", "127.0.0.1", 8011, "/health",
        "microservices/crisot_service/start.sh",
    ),
    "predict_crispr_off_target_with_crisot_fp": ToolServiceSpec(
        "predict_crispr_off_target_with_crisot_fp", "127.0.0.1", 8011, "/health",
        "microservices/crisot_service/start.sh",
    ),
    "generate_crispr_fingerprint_with_crisot": ToolServiceSpec(
        "generate_crispr_fingerprint_with_crisot", "127.0.0.1", 8011, "/health",
        "microservices/crisot_service/start.sh",
    ),
    # ODesign service (port 8012)
    "run_odesign_inference": ToolServiceSpec(
        "run_odesign_inference", "127.0.0.1", 8012, "/health",
        "microservices/odesign_service/start.sh",
    ),
    # IRESfinder service (port 8013)
    "predict_putative_ires_with_iresfinder": ToolServiceSpec(
        "predict_putative_ires_with_iresfinder", "127.0.0.1", 8013, "/health",
        "microservices/iresfinder_service/start.sh",
    ),
    # LinearDesign service (port 8014)
    "design_mrna_cds_with_lineardesign": ToolServiceSpec(
        "design_mrna_cds_with_lineardesign", "127.0.0.1", 8014, "/health",
        "microservices/lineardesign_service/start.sh",
    ),
    "design_mrna_cds_batch_with_lineardesign": ToolServiceSpec(
        "design_mrna_cds_batch_with_lineardesign", "127.0.0.1", 8014, "/health",
        "microservices/lineardesign_service/start.sh",
    ),
    # Junction-aware LinearDesign tool (2026-08): same service / port 8014.
    "design_mrna_cds_junction_aware_with_lineardesign": ToolServiceSpec(
        "design_mrna_cds_junction_aware_with_lineardesign", "127.0.0.1", 8014, "/health",
        "microservices/lineardesign_service/start.sh",
    ),
    # LinearFold service (port 8015)
    "predict_rna_secondary_structure_with_linearfold": ToolServiceSpec(
        "predict_rna_secondary_structure_with_linearfold", "127.0.0.1", 8015, "/health",
        "microservices/linearfold_service/start.sh",
    ),
    "evaluate_rna_structure_with_linearfold": ToolServiceSpec(
        "evaluate_rna_structure_with_linearfold", "127.0.0.1", 8015, "/health",
        "microservices/linearfold_service/start.sh",
    ),
    "predict_rna_secondary_structure_with_linearfold_zuker": ToolServiceSpec(
        "predict_rna_secondary_structure_with_linearfold_zuker", "127.0.0.1", 8015, "/health",
        "microservices/linearfold_service/start.sh",
    ),
    # Evitar service (port 8016)
    "design_sirna_with_evitar": ToolServiceSpec(
        "design_sirna_with_evitar", "127.0.0.1", 8016, "/health",
        "microservices/evitar_service/start.sh",
    ),
    # sgRNA design service (port 8017)
    "design_sgrna_handle_with_crgpt": ToolServiceSpec(
        "design_sgrna_handle_with_crgpt", "127.0.0.1", 8017, "/health",
        "microservices/sgrna_design_service/start.sh",
    ),
    "score_sgrna_handle_with_crgpt": ToolServiceSpec(
        "score_sgrna_handle_with_crgpt", "127.0.0.1", 8017, "/health",
        "microservices/sgrna_design_service/start.sh",
    ),
    # CodonW slim service (port 8018) — currently not referenced by any workflow,
    # but kept in the map for ad-hoc / future use.
    "analyze_cds_codon_metrics_with_codonw_slim": ToolServiceSpec(
        "analyze_cds_codon_metrics_with_codonw_slim", "127.0.0.1", 8018, "/health",
        "microservices/codonw_slim_service/start.sh",
    ),
    # BLAST service (port 8019)
    "run_blastn_similarity_search": ToolServiceSpec(
        "run_blastn_similarity_search", "127.0.0.1", 8019, "/health",
        "microservices/blast_service/start.sh",
    ),
    # RNA sequence metrics service (port 8020)
    "compute_rna_sequence_gc_content": ToolServiceSpec(
        "compute_rna_sequence_gc_content", "127.0.0.1", 8020, "/health",
        "microservices/rna_sequence_metrics_service/start.sh",
    ),
    "compute_dot_bracket_unpaired_fraction": ToolServiceSpec(
        "compute_dot_bracket_unpaired_fraction", "127.0.0.1", 8020, "/health",
        "microservices/rna_sequence_metrics_service/start.sh",
    ),
    "compute_rna_sequence_u_content": ToolServiceSpec(
        "compute_rna_sequence_u_content", "127.0.0.1", 8020, "/health",
        "microservices/rna_sequence_metrics_service/start.sh",
    ),
    # RiboDiffusion service (port 8021)
    "design_rna_inverse_fold_with_ribodiffusion": ToolServiceSpec(
        "design_rna_inverse_fold_with_ribodiffusion", "127.0.0.1", 8021, "/health",
        "microservices/ribodiffusion_service/start.sh",
    ),
    # ProteinX service (port 8022)
    "predict_protein_structure_with_proteinx": ToolServiceSpec(
        "predict_protein_structure_with_proteinx", "127.0.0.1", 8022, "/health",
        "microservices/proteinx_service/start.sh",
    ),
    "predict_rna_protein_complex_with_proteinx": ToolServiceSpec(
        "predict_rna_protein_complex_with_proteinx", "127.0.0.1", 8022, "/health",
        "microservices/proteinx_service/start.sh",
    ),
    # EGARPS service (port 8023)
    "score_rna_protein_complex_with_egarps": ToolServiceSpec(
        "score_rna_protein_complex_with_egarps", "127.0.0.1", 8023, "/health",
        "microservices/egarps_service/start.sh",
    ),
    # Bowtie2 service (port 8024)
    "run_bowtie2_short_alignment": ToolServiceSpec(
        "run_bowtie2_short_alignment", "127.0.0.1", 8024, "/health",
        "microservices/bowtie2_service/start.sh",
    ),
}

# Capabilities that are implemented by local pure-Python helpers and therefore
# have no microservice.  Listing them here suppresses "no_service_mapping" warnings
# while keeping the capability → service mapping explicit.
KNOWN_LOCAL_CAPABILITIES: set[str] = {
    "build_odesign_aptamer_input_json",
    "extract_rna_sequence_from_cif",
    "analyze_rna_protein_interface",
    "identify_protein_binding_hotspots",
    "score_structure_alignment",
    "compute_cai_for_cds_sequence",
    "shuffle_cds_junction_codons",
    "workflow_demo_echo",
}


def get_services_for_capabilities(
    capabilities: list[str],
) -> list[ToolServiceSpec]:
    """Return the unique microservices required by a list of capabilities.

    The result is deduplicated by ``(host, port)`` so shared services (e.g.
    ViennaRNA on port 8003) appear only once.

    Unknown capabilities are logged as warnings so missing service mappings are
    surfaced during development instead of being silently skipped.
    """
    seen: set[str] = set()
    services: list[ToolServiceSpec] = []
    for cap in capabilities:
        spec = CAPABILITY_SERVICE_MAP.get(cap)
        if spec is None:
            if cap not in KNOWN_LOCAL_CAPABILITIES:
                _LOGGER.warning("no_service_mapping_for_capability cap=%s", cap)
            continue
        key = spec.service_key
        if key in seen:
            continue
        seen.add(key)
        services.append(spec)
    return services


def check_service_health(url: str, timeout: int = 5) -> bool:
    """HTTP GET check on a service health endpoint.

    Returns ``True`` when the endpoint responds with 2xx **and** the JSON body
    reports ``"status": "ok"`` (when a ``status`` field is present).  This
    catches services that return HTTP 200 with ``{"status": "degraded"}``
    because a runtime dependency is missing.
    """
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            if not (200 <= resp.status < 300):
                return False
            body = resp.read()
            if not body:
                # Empty body with a 2xx status is treated as healthy for
                # backward compatibility with simple health endpoints.
                return True
            try:
                data = json.loads(body.decode("utf-8", errors="replace"))
            except Exception:
                # Non-JSON 2xx response: preserve legacy 2xx-is-healthy behavior.
                return True
            status = data.get("status") if isinstance(data, dict) else None
            if status is None:
                # No status field: preserve legacy 2xx-is-healthy behavior.
                return True
            return status == "ok"
    except Exception:
        return False


def _tail_text_file(path: Path, max_bytes: int = 4096, max_lines: int = 20) -> str:
    """Return the tail of a text file as a string."""
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            end = fh.tell()
            fh.seek(max(0, end - max_bytes), os.SEEK_SET)
            raw = fh.read()
        text = raw.decode("utf-8", errors="replace")
        lines = text.splitlines()
        return "\n".join(lines[-max_lines:])
    except Exception:
        return ""


def start_service(start_script: str, cwd: str) -> subprocess.Popen:
    """Launch a microservice via its ``start.sh`` script.

    Parameters
    ----------
    start_script:
        Path relative to *cwd* (e.g. ``"microservices/lineardesign_service/start.sh"``).
    cwd:
        Working directory — should be the project root so relative paths resolve.

    Returns
    -------
    A :class:`subprocess.Popen` instance.  The caller is responsible for polling
    the health endpoint; ``start.sh`` typically backgrounds the real server
    process, so this Popen returns immediately.

    Raises
    ------
    FileNotFoundError
        If ``start.sh`` does not exist.
    RuntimeError
        If ``start.sh`` exits with a non-zero status code, indicating it failed
        before backgrounding the real server process.
    """
    script_path = Path(cwd) / start_script
    if not script_path.exists():
        raise FileNotFoundError(f"Start script not found: {script_path}")

    service_dir = str(script_path.parent)
    service_name = script_path.parent.name
    log_dir = Path(cwd) / "microservices" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{service_name}.log"

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{cwd}{os.pathsep}{env.get('PYTHONPATH', '')}"
    with open(log_file, "ab") as log_fh:
        proc = subprocess.Popen(
            ["bash", str(script_path)],
            cwd=service_dir,
            env=env,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        # start.sh typically backgrounds the real server and exits immediately.
        # Wait briefly so startup errors are captured in the log before we return.
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _LOGGER.warning(
                "start_script_slow service=%s script=%s", service_name, start_script
            )
        else:
            if proc.returncode != 0:
                log_tail = _tail_text_file(log_file)
                raise RuntimeError(
                    f"Start script failed with exit code {proc.returncode}: "
                    f"{start_script}. Log tail ({log_file}):\n{log_tail}"
                )
    return proc


def _port_listening(host: str, port: int, timeout: float = 2.0) -> bool:
    """Return True when something accepts TCP connections on ``host:port``.

    Used to distinguish a busy-but-alive service (port held by a server whose
    ``/health`` is starved under load) from a genuinely down one (port free),
    so a healthy-but-busy service is never double-started.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _poll_health(
    url: str,
    timeout: float,
    poll_interval: float = 1.0,
    check_timeout: float = 2.0,
) -> bool:
    """Poll a health endpoint until it succeeds or *timeout* is reached."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if check_service_health(url, timeout=check_timeout):
            return True
        time.sleep(poll_interval)
    return False


def ensure_services_ready(
    services: list[ToolServiceSpec],
    timeout: int = 300,
    poll_interval: int = 5,
    project_root: Optional[Path] = None,
    health_timeout: float = 30.0,
    lock_timeout: int = 30,
) -> tuple[bool, list[str]]:
    """Ensure all *services* are healthy, starting any that are down.

    A per-service flock is acquired before the "check → start" sequence so that
    concurrent calls (e.g. two workflows sharing ViennaRNA) do not launch the
    same microservice twice.  The lock is held until the service either passes
    its health check or times out.

    Parameters
    ----------
    services:
        Microservice specifications to check/start.
    timeout:
        Maximum seconds to wait for newly-started services to become healthy.
    poll_interval:
        Seconds between health polls.
    project_root:
        Project root used to resolve ``start_script`` paths.  Defaults to the
        repository root containing ``agent_core/``.
    health_timeout:
        HTTP timeout for each individual health check.  Smaller values prevent
        the first-pass serial checks from accumulating when many services are
        requested at once.  NOTE (2026-07-19): raised from 2 s to 30 s because a
        busy single-worker service (e.g. EGARPS mid-scoring) can take seconds to
        answer ``/health``; 2 s falsely declared it down and double-started it,
        causing "address already in use" restart loops under concurrent shards.
    lock_timeout:
        Maximum seconds to wait for the per-port startup lock.  If acquisition
        fails (another process holds the lock), the caller falls back to polling
        the health endpoint on the assumption that the other process is starting
        the same service.

    Returns
    -------
    ``(all_ready, error_list)``.  ``all_ready`` is ``True`` only when every
    service responds on its health endpoint.  Services without a ``start_script``
    are reported as errors if they are not already healthy.
    """
    if not services:
        return True, []

    if project_root is None:
        project_root = _PROJECT_ROOT

    cwd = str(project_root)
    errors: list[str] = []
    started: set[str] = set()
    locks: dict[str, _ServiceLock] = {}

    # Deduplicate and sort by service key so concurrent calls always acquire
    # locks in the same order, avoiding deadlocks when two calls request a
    # different subset of services.
    seen: set[str] = set()
    unique_services: list[ToolServiceSpec] = []
    for svc in services:
        if svc.service_key in seen:
            continue
        seen.add(svc.service_key)
        unique_services.append(svc)
    unique_services.sort(key=lambda s: s.service_key)
    services = unique_services

    # Global budget for this ensure_services_ready call.  The fallback poll
    # when lock acquisition fails must wait for the *remaining* startup budget,
    # not just lock_timeout, otherwise a second caller can give up while the
    # first caller is still slowly starting the service.
    ensure_start = time.time()
    ensure_deadline = ensure_start + timeout

    def _release_all() -> None:
        for lock in locks.values():
            lock.release()
        locks.clear()

    def _remaining_budget() -> float:
        return max(0.0, ensure_deadline - time.time())

    try:
        # First pass: acquire locks in deterministic order; health-check under
        # lock and start any unhealthy services that have a start script.
        for svc in services:
            lock = _ServiceLock(svc.port, host=svc.host)
            if not lock.acquire(timeout=lock_timeout):
                # Fallback: another process may be starting this service. Poll
                # health before giving up so we don't fail unnecessarily.  Use
                # the remaining startup budget, not lock_timeout.
                if _poll_health(
                    svc.health_url,
                    timeout=_remaining_budget(),
                    poll_interval=1.0,
                    check_timeout=health_timeout,
                ):
                    continue
                errors.append(
                    f"{svc.capability}: timeout acquiring startup lock for {svc.host}:{svc.port}"
                )
                _release_all()
                return False, errors
            locks[svc.service_key] = lock

            if check_service_health(svc.health_url, timeout=health_timeout):
                _LOGGER.debug("service_ready cap=%s url=%s", svc.capability, svc.health_url)
                lock.release()
                del locks[svc.service_key]
                continue

            # NOTE (2026-07-22): a listening port with a starved health endpoint
            # means the service is BUSY (single-worker under sustained load,
            # e.g. EGARPS mid-scoring for another shard), not down. Starting a
            # duplicate then dies on "address already in use" and fails the
            # whole run for no reason (observed: fig4 shards burning ~20-min
            # jobs in waves of cli_failure). When the port is held, wait for
            # health within the remaining budget; if the busy spell outlasts
            # it, proceed anyway — the tool's own HTTP calls carry their own
            # long timeouts and will simply queue on the busy service.
            if _port_listening(svc.host, svc.port):
                _LOGGER.warning(
                    "service_busy_health_starved cap=%s url=%s; waiting instead of restarting",
                    svc.capability,
                    svc.health_url,
                )
                if _poll_health(
                    svc.health_url,
                    timeout=_remaining_budget(),
                    poll_interval=poll_interval,
                    check_timeout=health_timeout,
                ):
                    _LOGGER.info(
                        "service_busy_recovered cap=%s url=%s",
                        svc.capability,
                        svc.health_url,
                    )
                else:
                    _LOGGER.warning(
                        "service_busy_proceeding_anyway cap=%s url=%s; "
                        "health still starved after budget",
                        svc.capability,
                        svc.health_url,
                    )
                lock.release()
                del locks[svc.service_key]
                continue

            if not svc.start_script:
                errors.append(
                    f"{svc.capability}: service not running on {svc.host}:{svc.port} "
                    "and no auto-start script is available"
                )
                lock.release()
                del locks[svc.service_key]
                continue

            _LOGGER.warning(
                "service_down_auto_starting cap=%s url=%s script=%s",
                svc.capability, svc.health_url, svc.start_script,
            )
            try:
                start_service(svc.start_script, cwd=cwd)
                started.add(svc.service_key)
            except Exception as exc:
                errors.append(f"{svc.capability}: failed to start {svc.start_script}: {exc}")
                lock.release()
                del locks[svc.service_key]

        if errors:
            _release_all()
            return False, errors

        # Second pass: poll until all started services are ready or we exhaust
        # the original startup budget.
        deadline = ensure_deadline
        pending = [svc for svc in services if svc.service_key in started]

        while pending and time.time() < deadline:
            still_pending: list[ToolServiceSpec] = []
            for svc in pending:
                if check_service_health(svc.health_url, timeout=health_timeout):
                    _LOGGER.info("service_started cap=%s url=%s", svc.capability, svc.health_url)
                    locks[svc.service_key].release()
                    del locks[svc.service_key]
                    continue
                still_pending.append(svc)
            pending = still_pending
            if pending:
                time.sleep(poll_interval)

        if pending:
            for svc in pending:
                errors.append(
                    f"{svc.capability}: health check timeout ({svc.health_url})"
                )
                locks[svc.service_key].release()
                del locks[svc.service_key]

        return len(errors) == 0, errors
    finally:
        _release_all()


def ensure_workflow_services_ready(
    workflow: Any,
    timeout: int = 300,
    poll_interval: int = 5,
    project_root: Optional[Path] = None,
) -> tuple[bool, list[str]]:
    """Convenience wrapper: check/start services for a workflow instance/class.

    The workflow must expose ``required_capabilities``.
    """
    capabilities: list[str] = getattr(workflow, "required_capabilities", [])
    services = get_services_for_capabilities(capabilities)
    return ensure_services_ready(
        services,
        timeout=timeout,
        poll_interval=poll_interval,
        project_root=project_root,
    )
