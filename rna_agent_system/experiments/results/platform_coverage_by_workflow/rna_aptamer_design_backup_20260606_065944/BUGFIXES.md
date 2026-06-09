# Bug Fixes for rna_aptamer_design Workflow Run

## 1. EGARPS Service Health Check URL Mismatch

**Files modified:**
- `experiments/run_single_workflow_coverage.py`
- `experiments/run_platform_coverage.py`

**Problem:** The EGARPS microservice runs on port 8023 (as documented in `DEPLOYMENT.md` and configured in `microservices/egarps_service/start.sh`), but the health-check URLs in the runner scripts incorrectly pointed to port 8010.

**Fix:** Changed `http://127.0.0.1:8010/health` to `http://127.0.0.1:8023/health` in both files.

## 2. EGARPS Microservice Missing /health Endpoint

**File modified:**
- `microservices/egarps_service/main.py`

**Problem:** The EGARPS FastAPI service only exposed a `/score` endpoint. The `_check_service_health()` helper performs an HTTP GET to `/health`, which returned 404 even when the service was running.

**Fix:** Added a simple `@app.get("/health")` endpoint that returns `{"status": "ok"}`.

## 3. ODesign Service Startup Directory Issue (Operational)

**Problem:** ODesign service must be started from its own directory (`microservices/odesign_service/`) because `start.sh` does not `cd` into the script directory before launching `uvicorn main:app`.

**Resolution:** Started the service with `cd microservices/odesign_service && bash start.sh` instead of running it from the project root.

## 4. EGARPS Service Auto-Restart

**Resolution:** The EGARPS service was restarted after adding the `/health` endpoint so the new route would be registered.

---
All other services (ProteinX 8022, RhoFold 8005) started normally and passed health checks.
