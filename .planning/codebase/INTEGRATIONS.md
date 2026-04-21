# External Integrations

**Analysis Date:** 2026-04-20

## APIs & External Services

**Vision-Language APIs:**
- Gemini API - Default VLM for object detection and predicate grounding in `tiptop/tiptop/perception/vlm.py`.
  - SDK/Client: `google-genai`
  - Auth: `GOOGLE_API_KEY`
  - Usage: detect-and-translate prompt pipeline using schema-constrained JSON output
- OpenAI API - Alternate VLM backend in `tiptop/tiptop/perception/vlm.py`.
  - SDK/Client: `openai`
  - Auth: OpenAI API key env var
  - Usage: same detection/grounding role as Gemini
- Local Codex CLI - Fallback VLM path if logged-in Codex tooling is present.
  - Integration method: subprocess invocation from `tiptop/tiptop/perception/vlm.py`
  - Auth: local `~/.codex/auth.json`
  - Usage: local workstation fallback when Gemini is configured but no API key is present

**Robotics / Perception Services:**
- Fast-FoundationStereo-compatible depth service - Depth inference for stereo wrist cameras.
  - Client: `tiptop/tiptop/perception/foundation_stereo.py`
  - Auth: none
  - Endpoints used: `GET /health`, `POST /infer`
- M2T2 grasp server - 6-DoF grasp proposals from point clouds.
  - Client: `tiptop/tiptop/perception/m2t2.py`
  - Auth: none
  - Endpoints used: `GET /health`, `POST /predict`
- Legacy SAM2 compatibility server - Optional only.
  - Client/server entry: `tiptop/tiptop/scripts/sam_server.py`
  - Auth: none
  - Endpoints used: `/health`, `/segment`

## Data Storage

**Databases:**
- None. There is no application database in this workspace.

**File Storage:**
- Local filesystem only.
  - Run outputs: timestamped folders such as `tiptop/tiptop/tiptop_server_outputs/`, `tiptop/tiptop/tiptop_h5_*`, and `d435_probe_outputs/`
  - Calibration: `tiptop/tiptop/config/assets/calibration_info.json`
  - Test assets: `tiptop/tests/assets/` populated on demand
  - Weights/checkpoints: local sibling repos such as `sam3/checkpoints/` and `Fast-FoundationStereo/weights/`

**Caching:**
- Local in-process caching via `functools.cache` and module-level caches, for example:
  - `tiptop/tiptop/config/__init__.py`
  - `tiptop/tiptop/utils.py`
  - `tiptop/tiptop/perception/m2t2.py`

## Authentication & Identity

**Auth Provider:**
- None for the robotics workspace itself.

**Credentialed Integrations:**
- Gemini / OpenAI VLM credentials are environment-driven.
- Codex local auth is read from the user home directory when the Codex fallback path is used.

## Monitoring & Observability

**Error Tracking:**
- None like Sentry/Datadog.

**Analytics:**
- None.

**Logs / Telemetry:**
- Python logging to stdout and optional run-specific log files via `tiptop/tiptop/utils.py`.
- Rerun visualization/telemetry is used extensively in `tiptop/tiptop/tiptop_run.py`, `tiptop/tiptop/tiptop_h5.py`, and `tiptop/tiptop/tiptop_websocket_server.py`.

## CI/CD & Deployment

**Hosting:**
- No centralized deploy target detected.
- Main “hosted” behavior is local service hosting on the workstation:
  - Fast-FoundationStereo server
  - M2T2 server
  - optional Tiptop websocket server

**CI Pipeline:**
- No `.github/workflows/` pipeline was found under `tiptop/.github/`.
- GitHub issue templates exist in `tiptop/.github/ISSUE_TEMPLATE/`, but no automation workflows were detected.

## Environment Configuration

**Development:**
- Required environment is mostly local-process config plus service URLs from `tiptop/tiptop/config/tiptop.yml`.
- API keys are expected as env vars, not committed config.
- The workspace assumes local sibling repo paths like `/home/user/tiptop/sam3` and `/home/user/tiptop/Fast-FoundationStereo`.

**Staging:**
- None detected.

**Production / Real Execution:**
- Real robot execution depends on:
  - robot host/ports for Bamboo or UR5
  - wrist/external camera serial numbers
  - running local or remote perception microservices

## Webhooks & Callbacks

**Incoming:**
- None in the web SaaS sense.

**Outgoing / RPC-like Calls:**
- `tiptop` sends HTTP requests to local perception services and receives structured inference responses.
- `droid-sim-evals` communicates with the TiPToP websocket planning server when running simulator-side plan queries.

---

*Integration audit: 2026-04-20*
*Update when adding/removing external services*
