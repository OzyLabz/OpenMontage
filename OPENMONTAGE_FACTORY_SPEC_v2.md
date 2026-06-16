# OpenMontage Video Factory — Master Architecture Spec (v2 — final)

**Status:** CONVERGED after Cursor's gap-check and final conflict-check. Ready to decompose into per-system build prompts, faceless channel first.
**Base repo:** OpenMontage (my fork, Python). Works today on fal.ai + direct vendors. **Stays fully working as-is — everything below is additive.**
**Donor repo:** Open-Generative-AI — retired, salvage-sweep then delete.

---

## 1. GOAL

A self-owned video tool an agent drives to mass-produce content in two modes:
- **Faceless mode** — multiple *channels* (AI-news, cartoons), each with its own style/voice/format profile.
- **Influencer mode** — multiple *personas* (Mia), each with reference images + look/voice/vibe, character-locked.

Request shape: "make X as channel/persona Y" → load entry → lock assets → run pipeline → finished MP4.

---

## 2. BOUNDARY (do not cross)

Tool's only job: request → character-consistent MP4. **NOT** the tool's job (= Hermes, later): niche knowledge, strategy, analytics, deciding what to make, posting/scheduling. Keep it dumb and clean.

---

## 3. CORE DESIGN PRINCIPLE — THE SWITCH (additive, off by default)

OpenMontage stays exactly as it is. My addition is a **mode switch**:

- **Switch OFF (default):** tool behaves 100% as today — the existing quality scorer picks the model and provider. Nothing I built can break the working tool.
- **Switch ON (my version):** *I* name the model. The router then picks the **cheapest gateway** that serves that model. No quality scorer involved (I've already made the model choice myself).

This cleanly separates the two decisions that the v1 spec wrongly merged:
- **Decision 1 — which model fits the brief?** → switch OFF, existing scorer. Unchanged.
- **Decision 2 — which gateway to buy the chosen model through?** → switch ON, pure price + availability. New path.

Because the two never run at the same time, the provider-vs-model conflict Cursor found disappears.

**Implementation shape (locked):** the switch is a **new selection mode in the selector, not a reweight**. The ON path is an early-return guard at the top of `execute()` — above the existing rank-mode return and before `_select_best_tool` / `rank_providers`. OFF falls through to today's code byte-for-byte, so the existing scorer is 100% untouched.

**Fail behaviour (locked):** Switch ON + named model + no gateway serves it or all are down → **FAIL LOUD, tell the user. No silent fallback to the scorer.** The ON branch returns a failed `ToolResult` and must NOT fall through to the existing scored-selection loop.

**Known caveat (deferred):** the selector chokepoint is enforced by instruction (Markdown convention), not code — the agent can bypass it by calling a generation tool directly, in which case neither OFF nor ON applies. System C's build prompt should decide whether to make direct generation tools internal/non-agent-facing so the chokepoint is real.

---

## 4. CONFIRMED FACTS (verified against code — do not re-litigate)

1. Seedance 2.0 (`tools/video/seedance_video.py`, via fal) does `reference_to_video`: up to 9 ref images + 3 video + 3 audio, local-path auto-upload. **Mia persona = config, not a build.**
2. The selector IS already the chokepoint and already executes the chosen tool (`video_selector.execute()` calls `tool.execute()` and stamps `selected_provider`). System C modifies this, doesn't replace it. *Caveat: chokepoint is enforced by instruction (Markdown convention), not code — agent can bypass by calling a tool directly.*
3. Selector ranks by **provider/vendor** ("kling", "seedance"), de-duped by provider ("first available per provider"); gateway is hard-baked per tool. **No concept of "same model via two gateways" exists today** — this is the gap the model-identity layer fills. (Consequence: OFF mode cannot do cheapest-gateway routing even for a pinned provider — only switch ON can.)
4. Cost is already a scoring dimension (`cost_efficiency`) but weighted only 0.10; quality bonuses (e.g. reference support +0.18, cinematic premium +0.15) would distort price-only routing. → reason the switch-ON path must bypass the scorer entirely, not just reweight.
5. No kie.ai integration exists (full grep → only "cookie" false-positives).
6. `preferred_provider` is a HARD lock in code (returned unconditionally if available) in BOTH `video_selector` and `image_selector` — but it lives on the OFF/scorer path only; the ON path never consults it.
7. `video_selector` already accepts `reference_image_paths` / `reference_to_video` and routes reference-capable providers; reference params thread through to the chosen tool regardless of selection mode (OFF or ON) — persona reference images need no selector rewrite.
8. Provider-add = subclass `BaseTool`, drop in `tools/<category>/`, auto-discovered via `pkgutil.walk_packages()`.
9. Repo conventions: schema-validated artifacts (`schemas/`), YAML configs (`pipeline_defs/*.yaml`, `styles/*.yaml`), shared helpers in `_shared.py`, runtime lookup-table modules in `lib/` (`lib/media_profiles.py`), reserved `lib/providers/` "for future provider abstractions".

---

## 5. THE SYSTEMS

### System A — Model-Identity Layer (the keystone)
A canonical model id (e.g. `seedance-2.0`, `kling-v3`) mapping to every `{gateway, tool, endpoint, version}` that serves it, plus that combination's current price. This is what the switch-ON router reads: "given model M, which gateways serve it, which is cheapest." Does not exist today; everything price-related depends on it. Switch OFF never touches it.

**Confirmed home:** `lib/providers/` — ARCHITECTURE.md marks it "reserved for future provider abstractions," and `lib/media_profiles.py` is an existing lookup-table module of the same shape to follow.

**Two files, joined at load (locked):**
- **Stable structural map** — model id → list of `{gateway, tool, endpoint, version}`. Hand-maintained; changes only when a tool/gateway is added. Lives in `lib/providers/` (loader) + a data file it reads; validated by a schema in `schemas/`. Image-capable model entries additionally carry `image_field` (and optional `last_image_field`) for correct per-model payload construction.
- **Volatile price file** — System D's weekly output: `model + version + gateway + price`. Lives under `lib/pricing/`.
- System A's loader **joins the two at load time** (structural map ⨝ price file on model+version+gateway). This keeps System D from ever rewriting structural data (drift risk) and is what lets price feed `estimate_cost()` from one source.

The kie tool's `model` param AND the router both resolve against System A.

**Ordering:** System A is the true first build of the gateway half — BOTH the switch (System C) and the kie tool (System B) depend on it. It must precede both. Its kie rows can only be finalized once System B confirms kie's per-model id, so A is populated incrementally (fal/existing-vendor rows first, kie rows when B lands).

### System B — kie.ai Gateway Tool
One parametrized `kie_video` + `kie_image` tool (takes a `model` param), mirroring the fal tool pattern. `provider="kie"`, `dependencies=["env:KIE_API_KEY"]`, async submit→poll→download. Add `upload_image_kie` helper in `_shared.py` if kie needs local-image upload.

**OPEN — confirm from kie.ai's real docs before building:** base URL, auth header, submit/poll endpoints, response field names, how a model is named, whether it accepts reference-image arrays, and whether kie exposes a stable per-model id (needed for System A mapping). **Do not guess.**

### System C — Price-First Gateway Router (the switch)
The switch-ON path. Input = named model + params. Reads System A map → ranks gateways serving that model by price → calls cheapest → falls through to next gateway on failure → if none, FAIL LOUD. Implemented as a new selection mode in the selector (not a reweight). Switch OFF = existing scorer untouched. Testable immediately against a hand-authored minimal price list (does not hard-depend on System D).

### System D — Price-List Builder (weekly scraper)
Weekly offline job → writes the volatile price file System A reads (`model + version + gateway + price`). Prefer gateway pricing APIs over HTML scraping where they exist. **Mandatory: keep-last-good-list on scrape failure** (never zero out routing). Stored as versioned JSON/YAML in-repo under `lib/pricing/`.

**Hard-walled to price + catalog-presence only.** "Availability" here means *does gateway X currently sell model M* (a fact about the price sheet) — **never uptime, latency, success-rate, engagement, or any performance metric.** Runtime availability (gateway down) is handled separately by System C's fail-through, not by D, so D never needs uptime data. The moment D touches performance/engagement it's Hermes.

Feeds `estimate_cost()` via System A's join (one source of truth) — does not sit parallel.

### System E — The Registry
Two entry types, YAML + per-entry asset dir, validated by a JSON Schema in `schemas/`.
- **Channel (faceless):** maps onto existing `styles/*.yaml` playbook + voice id + media profile. No reference images.
- **Persona (influencer):** reference image set (→ Seedance), look/voice/vibe, optional ref audio/video. `niche` = **descriptor/conditioning only, no logic branches on it** — it may only be concatenated into prompt/style text, never read in a conditional, selector input, or routing decision (else it's Hermes leaking in).

### System F — Registry → Pipeline Wiring
Attaches at AGENT_GUIDE "Rule Zero" as a pre-pipeline step, mirroring the existing Reference-Video entry point. Per-pipeline `persona_input:` / `channel_profile:` blocks in manifests declare which entry types each pipeline accepts and what gets locked.

**Channel → OFF-path.** A channel locks the playbook + voice + format and runs the existing scorer (switch OFF). `preferred_provider` may be used to bias the scorer where a channel wants a specific vendor without naming an exact model.

**Persona → switch-ON + named model (NOT `preferred_provider`).** Persona pinning is expressed as **switch-ON with `model` = the persona's pinned canonical model id** (e.g. `seedance-2.0`), so the router buys it through the cheapest gateway. Identity threads through via `operation="reference_to_video"` + locked `reference_image_paths` (orthogonal to selection mode — works in ON). `preferred_provider` is explicitly NOT the persona lock mechanism: it is OFF-path only and cannot do cheapest-gateway routing (Confirmed Fact #3). One mechanism per mode so persona lock and the cost-router don't fight.

**Image-parity sub-task (CONFIRMED gap — not a freebie):** `image_selector` mirrors `video_selector` for *selection/locking* (same scoring, same `preferred_provider` hard lock) but NOT for *reference passing*. Three differences for persona STILLS:
1. Different vocabulary — images use `generation_mode="edit"` + `image_url/image_path/image_urls/image_paths`, not `reference_to_video` + `reference_image_*`.
2. No local-path→URL auto-upload (video has it via `upload_image_fal`; image selector passes local paths straight through).
3. Silently strips image keys the chosen tool doesn't declare (only logs a warning) — persona reference images can vanish, yielding an unconditioned image with no error.
→ Persona stills need: an edit-capable image tool that declares the multi-image keys, plus an explicit local→URL upload step. Treat as its own sub-task in the persona build, NOT assumed to work like the video path. Persona *video* (Seedance) is unaffected — that path is confirmed working.

**Resolve the image-field mismatch with per-model metadata, not guessing:** each image/edit-capable model in System A's structural map declares its `image_field` (e.g. `image_url`, `images_list`, `model_image_url`) and optional `last_image_field`. The image generation path fills that exact key — single URL for scalar fields, array for `images_list` — instead of relying on `image_selector`'s strip-on-mismatch behavior. (Pattern confirmed in donor `muapi.js` `generateI2I`/`generateI2V`; rebuild is a metadata field + ~5 lines, no donor code ported.)

---

## 6. BUILD ORDER (faceless ships first)

1. **System E (channels only) + System F (channel wiring)** — faceless channel video end-to-end on existing fal tools, switch OFF. Hits milestone fastest, zero gateway risk, validates Rule-Zero insertion.
2. **System A (model-identity layer)** — the keystone; both the kie tool and the switch depend on it, so it lands first in the gateway half. Build alongside confirming the kie API contract.
3. **System B (kie tool)** — resolves against System A's map.
4. **System C (switch/router)** with a hand-authored minimal price list so it's testable immediately.
5. **System D (weekly scraper)** — replaces the hand-authored stub.
6. **System E (personas) + System F (persona lock)** via switch-ON + named model + Seedance `reference_to_video` → one Mia video. Includes the image-parity sub-task for persona stills.

Net: kie/router/pricing is an optimization layered onto a working faceless factory, not a prerequisite for first light.

---

## 7. NEXT STEP

Final conflict-check complete. Next: write per-system build prompts, one at a time, **faceless channel first** (System E channels + System F channel wiring). No building until the per-system prompt for that system is written and approved.
