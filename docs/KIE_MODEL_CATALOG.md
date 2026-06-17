# kie.ai Model Catalog (planning doc — build nothing yet)

Navigation map for the kie single-gateway build. Two ways in:

- **§A — By Category:** open a category, pick a model (ranked best-first). Compact pointers only.
- **§B — Model Index:** full card per model with **all** category tags, fields, strengths, "pick me when", cost, phase. Source of truth — shared models (Kling, Nano Banana, Seedance, Veo, Grok) live here ONCE and are tagged with every category they serve, so the build never duplicates a model.
- **§C — Build Phases:** what ships first, by effort/dependency.

**Status legend:** ✅ confirmed (read its docs.kie.ai page, id + fields quoted) · ⚠️ verify-at-build (id from a kie page/search, fields not fully read) · ❓ unconfirmed (exists on kie; slash-id/fields not located)
**Path:** `slash-id` = rides existing `kie_client` via `POST /api/v1/jobs/createTask` · 🔌 = **dedicated endpoint** (needs a new `kie_client` adapter)
**Phase tags:** `P1` confirmed slash-id (ships now) · `P2` dedicated-endpoint (adapter prereq) · `P3` unconfirmed id (verify first) · `P4` lip-sync (blocked on audio/TTS)
**Empirical cost:** measured via `/chat/credit` delta where known; else `TBD`.
**Scope:** technical strengths only — NOT content/niche strategy (that's Hermes).

---

## §A. BY CATEGORY (ranked best-first)

### 🖼️ text-to-image (t2i)
1. **Nano Banana Pro** — `nano-banana-pro` — ✅ P1 — *pick when:* top Google image quality, strong text-in-image + character consistency, up to 4K.
2. **Nano Banana 2** — `nano-banana-2` — ✅ P1 — *pick when:* you also need many edit/identity refs (≤14) at up to 4K.
3. **Seedream 4.5** — `seedream/4.5-text-to-image` — ✅ P1 — *pick when:* pure prompt→image, high-aesthetic, 2K/4K, no refs.
4. **GPT Image 2** — `gpt-image-2-text-to-image` — ✅ P1 — *pick when:* precise instruction/prompt adherence + reliable text.
5. **Grok Imagine** — `grok-imagine/text-to-image` — ✅ P1 *(in map)* — *pick when:* cheap/fast stills or quick variations.

### 🖼️ image-to-image / edit (i2i)
1. **Nano Banana 2** — `nano-banana-2` — ✅ P1 — *pick when:* compose/edit with the most refs (≤14).
2. **Nano Banana Pro** — `nano-banana-pro` — ✅ P1 — *pick when:* highest-fidelity edit with strong consistency (≤8 refs).
3. **GPT Image 2 (edit)** — `gpt-image-2-image-to-image` — ⚠️ P3→P1 — *pick when:* instruction-driven edits; verify ref fields first.
4. **Ideogram Character-Edit** — `ideogram/character-edit` — ✅ P1 — *pick when:* masked inpaint with one character ref + crisp text.

### 🖼️ identity / character edit (stills)
1. **Nano Banana 2** — `nano-banana-2` — ✅ P1 — *pick when:* lock identity across many refs (≤14).
2. **Nano Banana Pro** — `nano-banana-pro` — ✅ P1 — *pick when:* Gemini-3 character consistency (≤8 refs).
3. **Ideogram Character-Edit** — `ideogram/character-edit` — ✅ P1 — *pick when:* single-character inpaint with a mask.

### 🖼️ image upscale / enhance
1. **Recraft Crisp Upscale** — `recraft/crisp-upscale` — ✅ P1 — *pick when:* clean, detail-preserving still upscale.
2. **Topaz Image Upscale** — `topaz/image-upscale` — ⚠️ P3 — *pick when:* industry-grade still upscale; verify id first.
   *(video upscale: `topaz/video-upscale` ⚠️, `grok-imagine/upscale` ⚠️ — see Model Index)*

### 🎬 text-to-video (t2v)
1. **Veo 3.1** — 🔌 `veo3`/`veo3_fast`/`veo3_lite` — ⚠️ P2 — *pick when:* flagship cinematic + native audio, up to 4k (adapter).
2. **Sora 2** — `sora-2-text-to-video` (+ `…-pro-…`) — ⚠️ P3 — *pick when:* Sora realism/physics + audio; verify id.
3. **Kling 3.0** — `kling-3.0/video` — ✅ P1 — *pick when:* multi-shot + native audio + 4K mode, confirmed-ready.
4. **Seedance 2.0** — `bytedance/seedance-2` — ✅ P1 *(in map)* — *pick when:* cinematic w/ native audio + camera control.
> Phase-1-ready best: **Kling 3.0** / **Seedance 2.0**.

### 🎬 image-to-video (i2v)
1. **Veo 3.1** — 🔌 `veo3*` (FIRST_AND_LAST_FRAMES_2_VIDEO) — ⚠️ P2 — *pick when:* premium first/last-frame animate (adapter).
2. **Sora 2** — `sora-2-image-to-video` — ⚠️ P3 — *pick when:* Sora realism from a still; verify id.
3. **Kling 3.0** — `kling-3.0/video` — ✅ P1 — *pick when:* animate a still (`image_urls` 1-2) with audio/multi-shot.
4. **Seedance 2.0** — `bytedance/seedance-2` — ✅ P1 — *pick when:* first/last-frame cinematic animate.
   *(also: Runway Gen-4 Turbo 🔌 ⚠️ P2; Grok i2v `grok-imagine/image-to-video` ⚠️ P3)*

### 🎬 reference / character-to-video (identity lock) 🔒
1. **Seedance 2.0** — `bytedance/seedance-2` — ✅ P1 — *pick when:* strongest identity lock — `reference_image_urls` ≤9 (+ video ≤3, audio ≤3).
2. **Kling 3.0** — `kling-3.0/video` — ✅ P1 — *pick when:* element/identity refs (`kling_elements` ≤3) with multi-shot.
3. **Veo 3.1** — 🔌 `veo3*` (REFERENCE_2_VIDEO) — ⚠️ P2 — *pick when:* Google quality with reference images (adapter).
4. **Wan 2.7** — `wan/…` — ❓ P3 — *pick when:* one model spanning ref + t2v/i2v/v2v; verify id.

### 🎬 motion-control / animate 🔒
1. **Kling 3.0 Motion-Control** — `kling-3.0/motion-control` — ⚠️ P3→P1 — *pick when:* latest Kling motion transfer; verify fields.
2. **Kling 2.6 Motion-Control** — `kling-2.6/motion-control` — ✅ P1 — *pick when:* animate 1 character still from 1 driving video.
3. **Runway Act-Two** — `runway/act-two`? — ❓ P3 (likely 🔌) — *pick when:* performance→character transfer; verify.
4. **Wan 2.7 (animate)** — `wan/…` — ❓ P3 — *pick when:* Wan animate mode; verify.

### 🎬 video edit / video-to-video (v2v)
1. **Runway Aleph** — 🔌 `POST /api/v1/aleph/generate` — ⚠️ P2 — *pick when:* restyle/relight/VFX-edit existing footage (adapter).
2. **Wan 2.7 (video-edit)** — `wan/…` — ❓ P3 — *pick when:* multi-modal video edit; verify id.
> Thin category — Aleph is the headline true-v2v; most other "video" enhancers are upscale, not edit.

### 🎬 lip-sync / talking-video 🔒 — ⛔ all P4 (blocked on an audio input → couples with TTS, out of scope now)
1. **OmniHuman 1.5** (ByteDance) — `bytedance/omnihuman-1.5`? — ❓ P4 — *pick when:* realistic digital-human from image+audio.
2. **InfiniteTalk** (MeiGen) — `infinitetalk/…`? — ❓ P4 — *pick when:* infinite-length lip-sync, 480p/720p.
3. **Kling AI Avatar 2.0** — `kling/ai-avatar`? — ❓ P4 — *pick when:* up to 5-min talking avatar from one photo.
4. **Kling LipSync** — `kling/lip-sync`? — ❓ P4 — *pick when:* sync lips to audio on an existing head.

---

## §B. MODEL INDEX (each model once, tagged with ALL categories)

### Nano Banana Pro — `nano-banana-pro` ✅ · slash-id · P1
- **Categories:** `[t2i] [i2i] [identity-edit]`
- **Reference field:** `image_input` (array, **≤8**); also `aspect_ratio`, `resolution` 1K/2K/4K, `output_format` png/jpg, `prompt ≤10k`
- **Strengths:** Gemini 3 Pro Image — top-tier fidelity, strong **character consistency**, precise **text-in-image**, clean materials; 4K ceiling. Both gen + multi-ref edit.
- **Pick me when:** you want Google's best image quality with reliable text + identity at up to 4K.
- **Cost:** TBD

### Nano Banana 2 — `nano-banana-2` ✅ · slash-id · P1
- **Categories:** `[t2i] [i2i] [identity-edit]`
- **Reference field:** `image_input` (array, **≤14**); `prompt ≤20k`, `aspect_ratio` (many incl 21:9/auto), `resolution` 1K/2K/4K, `output_format`
- **Strengths:** most reference images of any image model (14) → best multi-subject/product/identity compositing; strong text rendering; 4K.
- **Pick me when:** you must compose/lock with MANY references, or need accurate text at up to 4K.
- **Cost:** TBD

### Seedream 4.5 — `seedream/4.5-text-to-image` ✅ · slash-id · P1
- **Categories:** `[t2i]`
- **Reference field:** none (text-only); `prompt ≤3000`, `aspect_ratio` (required), `quality` basic=2K/high=4K, `nsfw_checker`
- **Strengths:** high-aesthetic photoreal/stylized stills, 4K; no edit/reference path.
- **Pick me when:** pure prompt→image at up to 4K with no references.
- **Cost:** TBD

### GPT Image 2 — `gpt-image-2-text-to-image` ✅ · (edit sibling `gpt-image-2-image-to-image` ⚠️) · slash-id · P1 (edit = P3→P1)
- **Categories:** `[t2i]` ✅ · `[i2i]` ⚠️
- **Reference field:** edit-variant fields **unread** (verify); t2i: `prompt ≤20k`, `aspect_ratio`, `resolution` 1K/2K/4K
- **Strengths:** OpenAI image — excellent prompt/instruction adherence, dependable text, "clean" outputs.
- **Pick me when:** precise instruction following + reliable typography matter most.
- **Cost:** TBD

### Grok Imagine — `grok-imagine/text-to-image` ✅ *(in map)* · (siblings ⚠️) · slash-id · P1
- **Categories:** `[t2i]` ✅ · `[i2i]` (`grok-imagine/image-to-image` ⚠️) · `[i2v]` (`grok-imagine/image-to-video` ⚠️) · `[video-upscale]` (`grok-imagine/upscale` ⚠️)
- **Reference field:** t2i has none; `prompt ≤5000`, `aspect_ratio` (2:3/3:2/1:1/16:9/9:16), `enable_pro` (quality vs speed), `nsfw_checker`
- **Strengths:** fast + cheapest tested; returns multiple variations; lower quality ceiling than NB/Seedream.
- **Pick me when:** cheap/fast stills or quick variation sets.
- **Cost:** **~4 credits** (measured: 16:9, enable_pro off → returned 6 variants, 1280×720, ~30s)

### Ideogram Character-Edit — `ideogram/character-edit` ✅ · slash-id · P1
- **Categories:** `[i2i] [identity-edit]`
- **Reference field:** `reference_image_urls` (**1 only** — rest ignored) + `image_url` (base) + `mask_url`; `num_images 1-4`, `rendering_speed`, `style`, `seed`
- **Strengths:** Ideogram = best-in-class **text-in-image** + character consistency for masked inpaint edits.
- **Pick me when:** inpaint a region while locking one character's identity, or need typography in the edit.
- **Cost:** TBD

### Recraft Crisp Upscale — `recraft/crisp-upscale` ✅ · slash-id · P1
- **Categories:** `[upscale]` (image)
- **Input:** `image` (URL) → higher-res, denoised image
- **Strengths:** clean detail-preserving image upscale.
- **Pick me when:** upscale/clean a still.
- **Cost:** TBD

### Seedance 2.0 — `bytedance/seedance-2` ✅ *(in map)* · slash-id · P1
- **Categories:** `[t2v] [i2v] [reference-to-video]`
- **Reference fields:** `reference_image_urls` **≤9** + `reference_video_urls` **≤3** + `reference_audio_urls` **≤3** + `first_frame_url`/`last_frame_url`; `resolution` 480/720/1080, `aspect_ratio`, `duration` 4-15, `generate_audio`
- **Strengths:** cinematic, **native synchronized audio**, director-level camera + multi-shot, lip-sync from quoted dialogue; **best reference-conditioning → top character-lock**; 1080p ceiling.
- **Pick me when:** strongest identity/character-locked video, or cinematic multi-shot with native audio.
- **Cost:** **76 credits** (measured: 480p / 4s / audio off)

### Kling 3.0 — `kling-3.0/video` ✅ · slash-id · P1
- **Categories:** `[t2v] [i2v] [reference-to-video]`
- **Reference fields:** `image_urls` 1-2 (first/last frame) + `kling_elements` (array **≤3** referenced images); `prompt`, `sound`, `duration` 3-15, `aspect` 16:9/9:16/1:1, `mode` std/pro/4K, `multi_shots`, `multi_prompt`
- **Strengths:** multi-shot storytelling, native audio, **4K mode**, strong motion adherence (kie markets it ahead of Wan-Animate/Act-Two).
- **Pick me when:** multi-shot or 4K video with up to 3 element/identity refs.
- **Cost:** TBD

### Kling 2.6 Motion-Control — `kling-2.6/motion-control` ✅ · slash-id · P1
- **Categories:** `[motion-control]`
- **Reference fields:** `input_urls` (**1** character photo) + `video_urls` (**1** motion/driving video); `prompt ≤2500`, `character_orientation`, `mode` 720p/1080p, 3-30s
- **Strengths:** faithful motion transfer (kie win-rate claims lead Wan/Act-Two); animate a static character.
- **Pick me when:** you have a character still + a motion reference video.
- **Cost:** TBD

### Kling 3.0 Motion-Control — `kling-3.0/motion-control` ⚠️ · slash-id · P3→P1
- **Categories:** `[motion-control]`
- **Reference fields:** likely as 2.6 (char image + motion video) — **verify**
- **Strengths:** latest Kling motion-control generation.
- **Pick me when:** same as 2.6, newest gen.
- **Cost:** TBD

### Veo 3.1 — 🔌 `POST /api/v1/veo/generate` · models `veo3` (Quality) / `veo3_fast` / `veo3_lite` ⚠️ · P2
- **Categories:** `[t2v] [i2v] [reference-to-video]` via `generationType`: TEXT_2_VIDEO / FIRST_AND_LAST_FRAMES_2_VIDEO / REFERENCE_2_VIDEO
- **Reference field:** `imageUrls` (1-2); `prompt`, `aspect_ratio` 16:9/9:16/Auto, `duration` 4/6/8, `resolution` up to 4k — **camelCase, dedicated endpoint**
- **Strengths:** flagship cinematic quality, native audio, up to 4k, strong physics/scene understanding; Quality/Fast/Lite cost-speed tiers.
- **Pick me when:** premium cinematic video with native audio at up to 4k (accept the adapter).
- **Cost:** TBD · **Prereq:** Veo adapter in `kie_client`

### Sora 2 — `sora-2-text-to-video` / `sora-2-image-to-video` (+ `…-pro-…`) ⚠️ · likely slash-id (NOT dedicated) · P3
- **Categories:** `[t2v] [i2v]`
- **Reference field:** image input for i2v — **count unread** (doc fetch 404'd)
- **Strengths:** Sora 2 realism + physical accuracy + synced audio; Pro tier = higher fidelity.
- **Pick me when:** you want Sora-2 realism/physics with audio.
- **Cost:** TBD · **Note:** kie tutorials show it on `jobs/createTask` (market), so it's likely **slash-id, not a dedicated endpoint** — but the id/prefix is unverified (page 404'd), so it sits in P3 (verify), *not* P2.

### Runway (Gen-4 Turbo + Aleph) — 🔌 dedicated ⚠️ · P2
- **Categories:** Gen-4 Turbo `[i2v]` (`POST /api/v1/runway/generate`, `imageUrl`) · Aleph `[v2v]` (`POST /api/v1/aleph/generate`, `prompt` + source `videoUrl`)
- **Strengths:** Aleph = multi-task video **edit/relight/VFX/restyle** on source footage (Gen-4 architecture); Gen-4 Turbo = fast i2v.
- **Pick me when:** Aleph → edit existing footage; Turbo → fast image-to-video.
- **Cost:** TBD · **Prereq:** Runway + Aleph adapters in `kie_client`

### Wan 2.7 (Alibaba) — `wan/…` ❓ · slash-id (assumed) · P3
- **Categories:** `[t2v] [i2v] [reference-to-video] [v2v]` (4 modes; full-modality text/image/video/audio in; 720-1080p)
- **Reference field:** unconfirmed
- **Strengths:** most versatile single model — spans generation, reference, and **video-edit**.
- **Pick me when:** you want one model covering t2v/i2v/reference/v2v (esp. video-edit).
- **Cost:** TBD · **Verify:** exact slash-id + per-mode fields

### Topaz — `topaz/image-upscale` ⚠️ (image) · `topaz/video-upscale` ⚠️ (video) · slash-id · P3
- **Categories:** `[upscale]` (image + video)
- **Strengths:** industry-grade upscale/enhance, high fidelity, video upscale with factor.
- **Pick me when:** highest-quality upscale of a still or a clip.
- **Cost:** TBD · **Verify:** image-upscale id + fields

### Runway Act-Two — `runway/act-two`? ❓ · likely 🔌 · P3
- **Categories:** `[motion-control]` (performance→character: motion+speech+expression transfer)
- **Pick me when:** drive a character from a performance video.
- **Cost:** TBD · **Verify:** id + endpoint (kie markets Kling as outperforming it)

### Lip-sync family — ❓ · P4 (BLOCKED on audio/TTS)
Common inputs: `image_url` + `audio_url` (+ prompt, resolution). Category `[lip-sync]`.
- **OmniHuman 1.5** (ByteDance) — `bytedance/omnihuman-1.5`? — realistic digital human.
- **InfiniteTalk** (MeiGen) — `infinitetalk/…`? — infinite-length lip-sync, 480p/720p, seed control.
- **Kling AI Avatar 2.0** — `kling/ai-avatar`? — up to 5-min talking avatar from one photo.
- **Kling LipSync** — `kling/lip-sync`? — sync lips to audio on an existing head.
- **Cost:** TBD · **Blocked:** needs a TTS/audio source first (TTS is out of current scope).

---

## §C. BUILD PHASES (quality-confirmed ships first)

### Phase 1 — Confirmed slash-id models (ride existing `kie_client`, no new code)
- **Models:** `nano-banana-pro`, `nano-banana-2`, `seedream/4.5-text-to-image`, `gpt-image-2-text-to-image`, `grok-imagine/text-to-image` *(in map)*, `ideogram/character-edit`, `recraft/crisp-upscale`, `bytedance/seedance-2` *(in map)*, `kling-3.0/video`, `kling-2.6/motion-control`
- **Build:** add one `kie_models.yaml` row per model (fields already confirmed) + (for image models) ensure `kie_image` accepts each model's `input_fields`. No client changes.
- **Gating:** none. Covers t2i, i2i, identity-edit, image-upscale, t2v, i2v, reference-to-video, motion-control out of the box.

### Phase 2 — Dedicated-endpoint models (need a `kie_client` adapter first)
- **Models:** **Veo 3.1** (`/api/v1/veo/generate`), **Runway Gen-4 Turbo** (`/api/v1/runway/generate`), **Runway Aleph** (`/api/v1/aleph/generate`)
- **Build:** a second adapter path in `kie_client` (per-endpoint submit/poll; camelCase params, `generationType`, `videoUrl`). Then add rows flagged `endpoint: dedicated`.
- **Gating:** **adapter is the prerequisite.** Unlocks premium t2v/i2v/reference (Veo) and the only true **v2v** (Aleph). Tackle Veo first (also gives reference-to-video).

### Phase 3 — Unconfirmed-id models (need a doc-verify fetch first)
- **Models:** **Sora 2** (likely slash-id — verify prefix + i2v ref fields), **Wan 2.7** (id + 4 modes incl. v2v), **Topaz** image/video upscale (verify image id), **GPT Image 2 edit** (verify ref fields → then P1), **Kling 3.0 motion-control** (verify fields → then P1), **Runway Act-Two** (id + endpoint), **Grok siblings** (`image-to-image` / `image-to-video` / `upscale`).
- **Build:** one verify-fetch of each model's docs.kie.ai page → confirm slash-id + fields → most fall into P1 (slash-id) or P2 (if dedicated).
- **Gating:** doc verification per model. Cheap; do on demand when a category needs the extra option.

### Phase 4 — Lip-sync / talking-video (BLOCKED)
- **Models:** OmniHuman 1.5, InfiniteTalk, Kling AI Avatar 2.0, Kling LipSync
- **Build:** verify ids/fields + a `kie_lipsync`/avatar tool path.
- **Gating:** **needs an audio source (TTS) in scope.** Park until TTS lands. Note: lip-sync re-opens the persona/avatar surface.

---

### Phase summary
| Phase | Models | Build | Gate |
|---|---|---|---|
| **1** | 10 confirmed slash-id (image + video) | YAML rows only | none — ships now |
| **2** | Veo 3.1, Runway Turbo, Runway Aleph | `kie_client` dedicated-endpoint adapter | adapter prereq |
| **3** | Sora 2, Wan 2.7, Topaz, GPT-Image-2-edit, Kling-3.0-MC, Act-Two, Grok siblings | per-model doc verify → P1/P2 | doc verification |
| **4** | OmniHuman, InfiniteTalk, Kling Avatar/LipSync | lip-sync tool path | blocked on TTS/audio |

**Net:** Phase 1 alone covers every in-scope category except v2v (needs Aleph → P2) and lip-sync (P4). Confirmed quality ships first; adapters and verifications layer on without touching Phase-1 work.

> Research-only document. Slash-ids quoted from docs.kie.ai where marked ✅; ⚠️/❓ items must be doc-verified before a row is added. **Nothing built or committed.**
