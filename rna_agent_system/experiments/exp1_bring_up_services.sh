#!/bin/bash
# GPU-pinned bring-up of all 21 platform microservices for the experiment
# programme (usable GPUs: 0, 1, 2 — GPU 3 is occupied by another user).
#
# Services not listed under a GPU are CPU-only. Already-healthy services are
# skipped, so this script is safe to re-run. Platform workflows' pre-flight
# finds the healthy endpoints and skips auto-start.
set -u
cd "$(dirname "$0")/.."
# Some services import agent_core / microservices.* — mirror the
# ServiceManager's env (project root on PYTHONPATH).
export PYTHONPATH="$PWD:${PYTHONPATH:-}"

# service → GPU (load-balanced by expected experiment load:
# GPU0 aptamer lane, GPU1 tertiary lane, GPU2 light oracles)
declare -A GPU_MAP=(
    [odesign_service]=0
    [egarps_service]=0
    [proteinx_service]=0
    [ribodiffusion_service]=1
    [rhodesign_service]=1
    [rhofold_service]=1
    [gemorna_service]=2
    [rnasmol_service]=2
    [rnarl_service]=2
    [rnastop_service]=2
    [gernabind_service]=2
    [sgrna_design_service]=2
)
declare -A PORT_MAP=(
    [viennarna_fold]=8003
    [gemorna_service]=8004
    [rhofold_service]=8005
    [rhodesign_service]=8006
    [rnasmol_service]=8007
    [rnarl_service]=8008
    [rnastop_service]=8009
    [gernabind_service]=8010
    [crisot_service]=8011
    [odesign_service]=8012
    [iresfinder_service]=8013
    [lineardesign_service]=8014
    [linearfold_service]=8015
    [evitar_service]=8016
    [sgrna_design_service]=8017
    [proteinx_service]=8022
    [egarps_service]=8023
    [ribodiffusion_service]=8021
    [blast_service]=8019
    [rna_sequence_metrics_service]=8020
    [bowtie2_service]=8024
)

SERVICES=(
    viennarna_fold gemorna_service rhofold_service rhodesign_service
    rnasmol_service rnarl_service rnastop_service gernabind_service
    crisot_service odesign_service iresfinder_service lineardesign_service
    linearfold_service evitar_service sgrna_design_service proteinx_service
    egarps_service ribodiffusion_service blast_service
    rna_sequence_metrics_service bowtie2_service
)

healthy() {  # service → 0 if /health answers within 3s
    local port="${PORT_MAP[$1]}"
    curl -sf -m 3 "http://127.0.0.1:${port}/health" >/dev/null 2>&1
}

start_one() {
    local svc="$1"
    if healthy "$svc"; then
        echo "[skip] $svc already healthy (port ${PORT_MAP[$svc]})"
        return 0
    fi
    local gpu="${GPU_MAP[$svc]:-}"
    echo "[start] $svc on port ${PORT_MAP[$svc]}${gpu:+ (GPU $gpu)}"
    (
        cd "microservices/$svc"
        if [ -n "$gpu" ]; then
            CUDA_VISIBLE_DEVICES="$gpu" nohup bash start.sh >/dev/null 2>&1 &
        else
            nohup bash start.sh >/dev/null 2>&1 &
        fi
    )
}

for svc in "${SERVICES[@]}"; do
    [ -f "microservices/$svc/start.sh" ] || { echo "[warn] no start.sh for $svc"; continue; }
    start_one "$svc"
done

echo "waiting for health endpoints (up to 15 min for GPU model loads)..."
deadline=$(( $(date +%s) + 900 ))
pending=("${SERVICES[@]}")
while [ ${#pending[@]} -gt 0 ]; do
    next=()
    for svc in "${pending[@]}"; do
        healthy "$svc" || next+=("$svc")
    done
    pending=("${next[@]+"${next[@]}"}")
    [ ${#pending[@]} -eq 0 ] && break
    if [ "$(date +%s)" -ge "$deadline" ]; then
        echo "[timeout] still not healthy: ${pending[*]}"
        exit 1
    fi
    sleep 15
done
echo "all ${#SERVICES[@]} services healthy."
