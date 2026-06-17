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
        allowed = set(row.get("input_fields") or [])
        ref_caps: dict[str, int] = row.get("reference_fields") or {}

        # Build the kie `input` from declared fields only (don't send keys the
        # model doesn't accept). prompt is always required.
        model_input: dict[str, Any] = {"prompt": inputs["prompt"]}
        for key in ("resolution", "aspect_ratio", "duration", "generate_audio",
                    "first_frame_url", "last_frame_url"):
            if key in inputs and (not allowed or key in allowed):
                model_input[key] = inputs[key]

        # Reference arrays with per-model arity enforcement (fail loud on overflow).
        for field, cap in ref_caps.items():
            vals = inputs.get(field)
            if vals:
                if len(vals) > cap:
                    return ToolResult(
                        success=False,
                        error=f"{kie_model} accepts at most {cap} {field}; got {len(vals)}",
                    )
                model_input[field] = list(vals)

        out_path = inputs.get(
            "output_path", f"kie_{row['canonical_id'].replace('.', '_')}.mp4"
        )

        start = time.time()
        try:
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
                "prompt": inputs["prompt"],
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
