# Persona Catalog (influencer mode)

Browse layer for the persona registry — the influencer-mode sibling of
[`KIE_MODEL_CATALOG.md`](KIE_MODEL_CATALOG.md). Two ways in:

- **§A — Roster:** the one-line catalog (id · pick-me-when · keywords · models · status). Pick a persona.
- **§B — Persona Index:** the full data-sheet card per persona. Source of truth is the YAML in `registry/personas/<id>.yaml` (validated by `schemas/registry/persona.schema.json`); this doc mirrors it for humans.
- **§C — Add a Persona:** drop a folder + data sheet → auto-discovered (no code change).
- **§D — Known Limits.**

**Status legend:** ✅ `proven` (character-lock paid-verified) · ✍️ `draft` (added, not yet verified). The `status` lives in each entry's data sheet — the roster is **data-driven**, read at runtime via `lib/registry_loader.persona_catalog()` (id + pick_me_when + keywords + status + models), so it never drifts from the registry.

**Scope:** **visuals-only** — `voice` is schema-only/deferred (TTS out of scope). Character-lock is **proven for subtle motion** (stills + a short slow-push-in clip); large-motion / new-environment / longer clips are **un-stress-tested** (see §D). `look`/`vibe`/`niche` are **conditioning-only**; `role`/`use_for` are **selection-only**. No Hermes (no strategy/analytics/posting). Channel path untouched.

**Lock mechanism:** a persona pins **named canonical model(s)** (`models.still` / `models.video`) — switch-ON + named model, **NOT** `preferred_provider`. Reference images thread into that model's declared reference field (`image_input` / `reference_image_urls` / `reference_image` / `kling_elements`), looked up from `lib/providers/model_map`.

---

## §A. ROSTER

> Runtime equivalent: `registry_loader.persona_catalog()`. Matching uses `match.keywords` only.

| Persona | `id` | pick me when | match keywords | still model | clip model | status |
|---|---|---|---|---|---|---|
| **Mia** | `mia` | warm, candid late-20s lifestyle creator for vertical reels/stills | `mia`, `make a mia`, `mia reel`, `mia still` | `nano-banana-2` | `wan-2.7-r2v` | ✅ proven |

---

## §B. PERSONA INDEX

### Mia — `mia` ✅ proven · visuals-only
- **pick me when:** A warm, candid late-20s lifestyle creator for vertical reels and stills — natural daylight, approachable energy.
- **Match keywords:** `mia`, `make a mia`, `mia reel`, `mia still`
- **Models (named lock):** still = `nano-banana-2` (ref field `image_input`, ≤14) · video = `seedance-2.0` declared (ref field `reference_image_urls`, ≤9); **clip proven on `wan-2.7-r2v`** (`reference_image`, combined ≤5).
- **Reference set (data sheet):**
  | role | use_for | note |
  |---|---|---|
  | face | identity-lock | front portrait, navy crew sweater (default wardrobe) |
  | three-quarter | identity-lock, scene | 3/4 angle, soft window light |
  | expression | scene | candid smile |
  - Stored as `path` (local copy under `registry/personas/mia/refs/`) + `url` (kie-hosted; what the model consumes).
- **look / vibe / niche** (conditioning-only): late-20s, brown eyes, dark wavy hair, freckles, gold hoops / upbeat candid lifestyle, soft daylight, shallow DoF / `lifestyle-creator`.
- **Format:** `media_profile: tiktok` (1080×1920, 9:16).
- **Proof:** still (new sunlit-café scene) ✅ identity held · clip (`wan-2.7-r2v`, 720p/2s, slow push-in + smile) ✅ identity held across frames. Both = 32 credits each (nano-banana-2 = 8 cr/still ×4 for the data sheet + still; wan-2.7-r2v = 32 cr). Proof artifact: `registry/personas/mia/clips/`.
- **Known limits:** see the entry's `known_limits` field + §D.

---

## §C. ADD A PERSONA

Adding a persona is **pure data** — the loader/wiring contain zero persona-specific logic (verified), so a new entry is auto-discovered with no code change.

1. **Choose identity:** `id` (kebab-case), `match.keywords` (lowercase phrases), one-line `pick_me_when`.
2. **Get reference images** (one of):
   - **Generate** (the Mia recipe): kie t2i a canonical **face** (`nano-banana-2`, prompt = `look`), then **chain** `image_input=[face]` to produce three-quarter / expression / body / outfit views — keeps them the same person. Outputs are kie URLs (no upload needed).
   - **Supply** real photos: needs `upload_image_kie` (local→URL) — **deferred** — or pre-host the images yourself and use the URLs.
3. **Create the data sheet:** `registry/personas/<id>/` + `<id>.yaml` with `models` (still/video), `reference_images` (`path`+`url`+`role`+`use_for`), `look`/`vibe`/`niche`, `media_profile`, and (once verified) `status: proven` + `known_limits`.
4. **Validate:** `load_persona("<id>")` (schema-validates) and `match_persona("make a <id> …")` returns it; `persona_catalog()` lists it.
5. **Live:** auto-discovered at Rule Zero (persona entry point in `AGENT_GUIDE.md`). No loader/wiring/code edit.

### Wardrobe convention (the Mia finding — refs are sticky)
`image_input`/`reference_image` condition on the **whole** reference, so a ref's clothing carries into outputs (Mia's navy sweater persisted). For **scene-appropriate wardrobe**, use either:
- a **`role: outfit` reference** — add an outfit ref and include it with the identity-lock refs when a scene calls for that look (the reliable path); or
- an **emphatic prompt override** — state the outfit explicitly and prominently in the generation prompt (e.g. *"wearing a tailored red blazer"*). Because refs are sticky, the override must be explicit; a faint mention loses to the reference's clothing.

This is conditioning/selection metadata only — never branch logic.

### Proven model defaults vs. alternatives
- **Proven (use by default):** still = **`nano-banana-2`** (`image_input`) · clip = **`wan-2.7-r2v`** (`reference_image`). Both paid-verified for character-lock this build.
- **Alternatives (valid, not yet persona-proven):** `seedance-2.0` `reference_to_video` (`reference_image_urls` ≤9, docs-confirmed) · `nano-banana-pro` (`image_input` ≤8) · `kling-3.0` (`kling_elements` ≤3). Pick per arity/quality need; verify on first real use.

---

## §D. KNOWN LIMITS (recorded, not solved)

1. **Motion drift un-tested at scale.** In-motion identity is proven only for **subtle** motion (2s, slow push-in, neutral→smile). **Large-motion, new-environment, and longer clips** are the classic reference-to-video drift zone and remain un-stress-tested.
2. **Wardrobe stickiness.** References carry clothing into outputs; mitigations (§C) are documented, not auto-enforced.
3. **`upload_image_kie` deferred.** Durable local-file refs aren't supported yet; personas currently rely on kie-hosted URLs, which **expire** (~days–weeks). Keep local `path` copies; re-host/regenerate if a `url` 404s.
4. **Voice/TTS deferred.** Personas are visuals-only; `voice` is schema-only/forward-compat.
5. **Single gateway.** Cheapest-gateway routing for persona-named models (System C) is deferred — kie is the only gateway today, so naming the model and calling the kie tool *is* the lock.

> Browse/spec doc. Source of truth for matching/loading is the YAML data sheets + `registry_loader`. Adding/maturing a persona = edit data, not code.
