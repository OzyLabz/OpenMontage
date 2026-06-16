# Setup & Run

Practical setup notes captured from build sessions — the things a fresh machine
or future session would otherwise have to rediscover. Keep this current.

## 1. Prerequisites

- **Python 3.10+**
- **Node 18+** (Remotion render path; tested on Node 24)
- **`numpy`** — `pip install numpy`
  - **Required for registry discovery.** `tools/video/green_screen_composite.py`
    imports numpy at module load; without it `registry.discover()` fails. (Not in
    `requirements.txt`.) Discovery is now hardened to log-and-skip a single
    un-importable tool, but numpy is needed for a full tool inventory.
- **ffmpeg** — `winget install Gyan.FFmpeg` (Windows). Required by ~15 tools and
  by every render path (Remotion/HyperFrames/ffmpeg all encode via ffmpeg).
  - ⚠️ **Fresh shell needed after install.** winget adds ffmpeg to the persistent
    User PATH, but already-running shells/agent sessions keep their old
    environment. Open a **new terminal / restart the agent** so `ffmpeg` resolves;
    verify with `ffmpeg -version`.
- **Remotion** — `cd remotion-composer && npm install`
  - Renders stills/components into the final MP4. Without it the compose stage
    has no render engine.

Quick render sanity check (no API keys, no paid calls):
`python render_demo.py --list` then `python render_demo.py focusflow-pitch`
→ writes a valid 1920×1080 h264 MP4 under `projects/demos/renders/`.

## 2. Keys (.env)

`.env` is **gitignored** — never commit real keys. Copy `.env.example` to `.env`
and fill in. For a **faceless channel** run you need at minimum:

- `FAL_KEY` — image/video generation gateway (FLUX, Kling, Veo, MiniMax, Seedance)
- `GOOGLE_API_KEY` — Google Cloud TTS (the ai-news voice) + Imagen

Optional/recommended: `ELEVENLABS_API_KEY`, `OPENAI_API_KEY`, `PEXELS_API_KEY`,
`PIXABAY_API_KEY`. (List only — do not record values anywhere tracked.)

## 3. How to run

**There is no `run_pipeline.py`. The agent IS the orchestrator.** It reads
`AGENT_GUIDE.md`, drives the pipeline stage by stage, and calls tools.

1. Open the repo in a **fresh** agent session (Cursor / Claude Code) so ffmpeg
   resolves on PATH.
2. Send a plain request, e.g.:
   > Make an AI-news video about <topic>.
3. The agent matches the request to a channel entry (`registry/channels/*.yaml`)
   via the **Channel / Persona Entry Point** in `AGENT_GUIDE.md`, locks the
   channel's playbook + voice + media profile (switch OFF — scorer still picks
   generation models), and runs the channel's pipeline.

- **Output:** `projects/<slug>/renders/final.mp4`
- **Budget:** default cap **$10** total with a **$0.50 single-action approval
  threshold**; first use of any paid tool prompts for confirmation. Checkpoint
  policy is `guided` — expect approval gates at key creative stages. Paid calls
  begin at the **assets** stage (a short faceless explainer is roughly
  ~$0.20–0.60 via the FLUX-stills + Remotion route; AI video gen costs more).

## 4. Current state

- **Faceless channel registry (System E + System F)** — built & committed at
  **`ff37f5d`**. One channel entry: `registry/channels/ai-news.yaml`. Loader:
  `lib/registry_loader.py`. Schema: `schemas/registry/channel.schema.json`.
  Wiring + discovery hardening in `AGENT_GUIDE.md` / `tools/tool_registry.py`.
  Loader-level tests pass. End-to-end paid run not yet executed.
- **Remaining systems** — per `OPENMONTAGE_FACTORY_SPEC_v2.md` build order:
  **A** (model-identity layer) → **B** (kie.ai gateway tool) → **C**
  (price-first switch/router) → **D** (weekly price-list builder) → **persona**
  (System E personas + System F persona lock, Seedance reference_to_video).
  **Not yet started.**

See also: `OPENMONTAGE_FACTORY_SPEC_v2.md` (architecture) and
`docs/reference/donor-imagefield-pattern.md` (salvaged image-field convention).
