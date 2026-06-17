"""kie.ai video generation — single-gateway tool.

One parametrized video tool routed through kie.ai's unified jobs API. The
`model` input selects which kie video model (canonical id, e.g. `seedance-2.0`,
or kie slash-id, e.g. `bytedance/seedance-2`), resolved against
lib/providers/model_map. Mirrors the Seedance fal tool's contract and
submit->poll->download shape, but goes through lib/providers/kie_client.

Reference-image / video / audio arrays are declared (with per-model arity caps)
so persona character-lock slots in later with no schema change — but they are
optional and unused on the default text_to_video path.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)


class KieVideo(BaseTool):
    name = "kie_video"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "video_generation"
    provider = "kie"  # canonical gateway provider-id — used by selectors + channel wiring
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = ["env:KIE_API_KEY"]
    install_instructions = (
        "Set KIE_API_KEY to your kie.ai API key (one key reaches all kie models).\n"
        "  Get one at https://kie.ai (API Key management)."
    )
    agent_skills = ["seedance-2-0", "ai-video-gen"]

    capabilities = ["text_to_video", "image_to_video", "reference_to_video"]
    supports = {
        "text_to_video": True,
        "image_to_video": True,
        "reference_to_video": True,
        "multiple_reference_images": True,
        "native_audio": True,
        "aspect_ratio": True,
        "single_gateway": "kie",
    }
    best_for = [
        "video generation routed through the kie.ai single gateway",
        "Seedance 2.0 clips (text / image / reference-to-video) when KIE_API_KEY is set",
        "reference-conditioned identity lock (up to 9 images + 3 video + 3 audio) — persona path",
    ]
    not_good_for = ["offline generation", "running without KIE_API_KEY"]
    fallback_tools = ["seedance_video", "veo_video", "kling_video"]

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "model": {
                "type": "string",
                "description": "Canonical id (e.g. seedance-2.0) or kie slash-id (e.g. bytedance/seedance-2). Defaults to the map's default video model.",
            },
            "prompt": {"type": "string"},
            "operation": {
                "type": "string",
                "enum": ["text_to_video", "image_to_video", "reference_to_video"],
                "default": "text_to_video",
            },
            "resolution": {"type": "string", "enum": ["480p", "720p", "1080p"], "default": "720p"},
            "aspect_ratio": {
                "type": "string",
                "enum": ["1:1", "4:3", "3:4", "16:9", "9:16", "21:9", "adaptive"],
                "default": "16:9",
            },
            "duration": {"type": ["integer", "string"], "description": "4-15 seconds (default 5)"},
            "generate_audio": {"type": "boolean", "default": True},
            "nsfw_checker": {"type": "boolean", "description": "Seedance: false disables content filtering (default false)."},
            "web_search": {"type": "boolean", "description": "Seedance: use online search to ground generation."},
            # --- Kling 3.0 video params (forwarded per the model_map input_fields) ---
            "mode": {"type": "string", "description": "Kling quality/resolution mode: std | pro | 4K."},
            "sound": {"type": "boolean", "description": "Kling native-audio toggle."},
            "image_urls": {"type": "array", "items": {"type": "string"}, "description": "Kling first/last frame image URLs (1-2)."},
            "kling_elements": {"type": "array", "items": {"type": "object"}, "description": "Kling element/identity references (<=3 element objects)."},
            "multi_shots": {"type": "boolean"},
            "multi_prompt": {
                "type": "array",
                "description": "Kling multi-shot prompts (when multi_shots=true): <=5 shot OBJECTS.",
                "items": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "Shot prompt (<=500 chars)."},
                        "duration": {"type": "integer", "description": "Shot duration 1-12s."},
                    },
                    "required": ["prompt", "duration"],
                },
            },
            # --- Veo 3.1 dedicated-endpoint params (camelCase wire names; routed by endpoint:veo) ---
            "veo_model": {"type": "string", "enum": ["veo3", "veo3_fast", "veo3_lite"], "description": "Veo tier (aliased to the wire `model`; the tool's `model` input selects the row)."},
            "imageUrls": {"type": "array", "items": {"type": "string"}, "description": "Veo: 1-3 image URLs (REFERENCE_2_VIDEO) or 1-2 first/last frame."},
            "generationType": {"type": "string", "enum": ["TEXT_2_VIDEO", "FIRST_AND_LAST_FRAMES_2_VIDEO", "REFERENCE_2_VIDEO"], "description": "Veo: auto-determined from inputs if omitted."},
            "watermark": {"type": "string", "description": "Veo: watermark text."},
            "enableTranslation": {"type": "boolean", "description": "Veo: translate non-English prompts (default false)."},
            # --- Runway Gen-4 Turbo dedicated-endpoint params (endpoint:runway) ---
            "imageUrl": {"type": "string", "description": "Runway: i2v source image URL."},
            "quality": {"type": "string", "enum": ["720p", "1080p"], "description": "Runway: 720p | 1080p (1080p blocks 10s)."},
            "waterMark": {"type": "string", "description": "Runway/Aleph: watermark text."},
            "callBackUrl": {"type": "string", "description": "Runway/Aleph: optional async callback (we poll synchronously)."},
            # --- Runway Aleph dedicated-endpoint params (endpoint:aleph; v2v) ---
            "videoUrl": {"type": "string", "description": "Aleph: source video URL for v2v edit/restyle/relight."},
            "referenceImage": {"type": "string", "description": "Aleph: reference image URL to influence style/content."},
            "seed": {"type": "integer", "description": "Aleph / Wan: random seed for reproducible generation."},
            "uploadCn": {"type": "boolean", "description": "Aleph: storage region (false=S3/R2, true=Alibaba OSS)."},
            # --- Phase 3 video params (forwarded per each model's input_fields) ---
            "negative_prompt": {"type": "string", "description": "Wan: things to avoid (<=500 chars)."},
            "audio_url": {"type": "string", "description": "Wan t2v: audio input URL (full-modality)."},
            "prompt_extend": {"type": "boolean", "description": "Wan: prompt rewriting (default true)."},
            "first_clip_url": {"type": "string", "description": "Wan i2v: source clip for video-continuation mode."},
            "driving_audio_url": {"type": "string", "description": "Wan i2v: audio input (full-modality)."},
            "reference_image": {"type": ["array", "string"], "items": {"type": "string"}, "description": "Wan r2v: image refs (array, combined <=5 with reference_video) / Wan videoedit: single reference image."},
            "reference_video": {"type": "array", "items": {"type": "string"}, "description": "Wan r2v: video refs (combined <=5 with reference_image)."},
            "first_frame": {"type": "string", "description": "Wan r2v: single frame image URL."},
            "reference_voice": {"type": "string", "description": "Wan r2v: voice-timbre reference audio (lip-sync)."},
            "video_url": {"type": "string", "description": "Wan videoedit / Topaz video upscale: source video URL (snake_case)."},
            "audio_setting": {"type": "string", "enum": ["auto", "origin"], "description": "Wan videoedit: audio handling."},
            "upscale_factor": {"type": "string", "enum": ["1", "2", "4"], "description": "Topaz video upscale factor (video: 1/2/4, no 8)."},
            "task_id": {"type": "string", "description": "Grok i2v (XOR image_urls) / Grok upscale: prior kie task id."},
            "index": {"type": "integer", "description": "Grok i2v: image index 0-5 from task_id."},
            "input_urls": {"type": "array", "items": {"type": "string"}, "description": "Kling motion-control: character image (<=1)."},
            "video_urls": {"type": "array", "items": {"type": "string"}, "description": "Kling motion-control: driving motion video (<=1)."},
            "character_orientation": {"type": "string", "enum": ["video", "image"], "description": "Kling motion-control: orientation reference source."},
            "background_source": {"type": "string", "enum": ["input_video", "input_image"], "description": "Kling 3.0 motion-control: background source (NEW in 3.0)."},
            # --- Reserved for persona character-lock (optional; unused on text_to_video) ---
            "first_frame_url": {"type": "string"},
            "last_frame_url": {"type": "string"},
            "reference_image_urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "<=9 identity / wardrobe / style anchors (Seedance).",
            },
            "reference_video_urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "<=3 motion / camera anchors.",
            },
            "reference_audio_urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "<=3 voice / music anchors.",
            },
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=512, vram_mb=0, disk_mb=500, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["rate_limit", "timeout"])
    idempotency_key_fields = ["model", "prompt", "operation", "duration", "resolution"]
    side_effects = ["writes video file to output_path", "calls kie.ai API (spends credits)"]
    user_visible_verification = [
        "Watch generated clip for motion coherence, audio sync, and visual quality"
    ]

    # ---- availability: real key only (env_present strips empty/comment-only) ----
    def get_status(self) -> ToolStatus:
        from lib.env_loader import env_present

        return ToolStatus.AVAILABLE if env_present("KIE_API_KEY") else ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        from lib.providers.model_map import resolve

        row = resolve(inputs.get("model"), "video_generation") or {}
        cost = row.get("est_cost_usd")
        return float(cost) if cost else 0.0  # credit-metered; read /chat/credit for truth

    def estimate_runtime(self, inputs: dict[str, Any]) -> float:
        return 120.0

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        from lib.env_loader import env_present

        if not env_present("KIE_API_KEY"):
            return ToolResult(
                success=False, error="KIE_API_KEY not set. " + self.install_instructions
            )

        from lib.providers import kie_client
        from lib.providers.model_map import resolve
        from tools.video._shared import probe_output

        row = resolve(inputs.get("model"), "video_generation")
        if not row:
            return ToolResult(
                success=False,
                error=(
                    f"Unknown kie video model: {inputs.get('model')!r}. "
                    "Add a row to lib/providers/kie_models.yaml (confirm its slash-id "
                    "and input fields from docs.kie.ai first)."
                ),
            )

        kie_model = row["kie_model"]
        endpoint = row.get("endpoint")          # None = slash-id path; else dedicated adapter
        allowed = list(row.get("input_fields") or [])
        ref_caps: dict[str, int] = row.get("reference_fields") or {}
        aliases: dict[str, str] = row.get("field_aliases") or {}

        # Build the kie `input`/body GENERICALLY from the model's declared input_fields
        # (the model_map is the source of truth — input_fields ARE the exact wire param
        # names, camelCase included). Scalars are forwarded as-is; reference arrays go
        # through the arity-capped path below. Only declared params are sent.
        # `field_aliases` lets a wire field read from a different caller key when its
        # API name collides with a reserved tool input (e.g. Veo body `model`).
        model_input: dict[str, Any] = {}
        for key in allowed:
            if key in ref_caps:
                continue
            val = inputs.get(aliases.get(key, key))
            if val is not None:
                model_input[key] = val

        # Reference arrays with per-model arity enforcement (fail loud on overflow).
        for field, cap in ref_caps.items():
            vals = inputs.get(aliases.get(field, field))
            if vals:
                if not isinstance(vals, list):
                    vals = [vals]
                if len(vals) > cap:
                    return ToolResult(
                        success=False,
                        error=f"{kie_model} accepts at most {cap} {field}; got {len(vals)}",
                    )
                model_input[field] = list(vals)

        # Fill model-declared required-defaults for any accepted field the caller
        # omitted (schema-driven, not a per-model branch). An explicit caller
        # value always wins. Covers API-required-but-looks-optional params like
        # kling-3.0's multi_shots (422 "multi_shots cannot be empty" if absent).
        for key, val in (row.get("defaults") or {}).items():
            if key in allowed and key not in ref_caps:
                model_input.setdefault(key, val)

        # Required-input validation (clear error instead of a confusing API 422):
        # require_one_of -> each group needs >=1 field present; mutually_exclusive
        # -> each group allows <=1. No-op for rows that declare neither.
        for group in (row.get("require_one_of") or []):
            if not any(g in model_input for g in group):
                return ToolResult(
                    success=False,
                    error=f"{kie_model} requires at least one of: {', '.join(group)}",
                )
        for group in (row.get("mutually_exclusive") or []):
            present = [g for g in group if g in model_input]
            if len(present) > 1:
                return ToolResult(
                    success=False,
                    error=f"{kie_model}: {' and '.join(present)} are mutually exclusive — provide only one",
                )

        out_path = inputs.get(
            "output_path", f"kie_{row['canonical_id'].replace('.', '_')}"
        )

        start = time.time()
        try:
            if endpoint:
                # Dedicated endpoint (own submit/poll paths, flat camelCase body).
                path, record, urls = kie_client.run_dedicated(endpoint, model_input, out_path)
            else:
                # Slash-id path (jobs/createTask) — unchanged for the 10 Phase-1 models.
                path, record, urls = kie_client.run_job(kie_model, model_input, out_path)
        except Exception as e:
            return ToolResult(success=False, error=f"kie video generation failed: {e}")

        probed = probe_output(Path(path))
        return ToolResult(
            success=True,
            data={
                "provider": "kie",
                "gateway": "kie",
                "model": kie_model,
                "canonical_id": row["canonical_id"],
                "task_id": record.get("taskId"),
                "credits_consumed": record.get("creditsConsumed"),
                "result_urls": urls,
                "prompt": inputs.get("prompt"),
                "operation": inputs.get("operation", "text_to_video"),
                "resolution": inputs.get("resolution", "720p"),
                "aspect_ratio": inputs.get("aspect_ratio", "16:9"),
                "output": path,
                "output_path": path,
                "format": "mp4",
                **probed,
            },
            artifacts=[path],
            cost_usd=self.estimate_cost(inputs),
            duration_seconds=round(time.time() - start, 2),
            model=kie_model,
        )
