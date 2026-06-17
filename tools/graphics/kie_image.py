"""kie.ai image generation — single-gateway tool.

Parametrized text-to-image tool routed through kie.ai's unified jobs API; the
image sibling of tools/video/kie_video.py. The `model` input selects which kie
image model (canonical id, e.g. `grok-image`, or kie slash-id, e.g.
`grok-imagine/text-to-image`), resolved against lib/providers/model_map.

Mirrors flux_image's `image_generation` contract and kie_video's
submit -> poll -> download flow (via lib/providers/kie_client).
"""

from __future__ import annotations

import os
import time
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


class KieImage(BaseTool):
    name = "kie_image"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "image_generation"
    provider = "kie"  # canonical gateway provider-id — matches kie_video + channel wiring
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = ["env:KIE_API_KEY"]
    install_instructions = (
        "Set KIE_API_KEY to your kie.ai API key (one key reaches all kie models).\n"
        "  Get one at https://kie.ai (API Key management)."
    )
    agent_skills = []

    capabilities = ["generate_image", "text_to_image"]
    supports = {
        "text_to_image": True,
        "aspect_ratio": True,
        "single_gateway": "kie",
    }
    best_for = [
        "image generation routed through the kie.ai single gateway",
        "text-to-image stills for faceless channels (clean backgrounds, hero cards)",
    ]
    not_good_for = [
        "offline generation",
        "running without KIE_API_KEY",
        "verbatim text inside the image (use a Remotion text card instead)",
    ]
    fallback_tools = ["flux_image", "google_imagen", "recraft_image"]

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "model": {
                "type": "string",
                "description": "Canonical id (e.g. grok-image) or kie slash-id (e.g. grok-imagine/text-to-image). Defaults to the map's default image model.",
            },
            "prompt": {"type": "string"},
            "aspect_ratio": {
                "type": "string",
                "enum": ["2:3", "3:2", "1:1", "16:9", "9:16"],
                "default": "1:1",
            },
            "enable_pro": {
                "type": "boolean",
                "default": False,
                "description": "grok: true = quality mode, false = speed mode.",
            },
            "nsfw_checker": {"type": "boolean", "default": False},
            # --- Model-specific image params (forwarded per the model_map input_fields) ---
            "resolution": {"type": "string", "description": "Nano Banana / GPT-Image-2: 1K | 2K | 4K."},
            "output_format": {"type": "string", "description": "Nano Banana: png | jpg."},
            "quality": {"type": "string", "description": "Seedream: basic (2K) | high (4K)."},
            "image_input": {"type": "array", "items": {"type": "string"}, "description": "Nano Banana reference/input images (<=14 NB2 / <=8 NB Pro)."},
            "image": {"type": "string", "description": "Recraft upscale: source image URL."},
            "image_url": {"type": "string", "description": "Ideogram: base image to edit."},
            "mask_url": {"type": "string", "description": "Ideogram: inpaint mask."},
            "reference_image_urls": {"type": "array", "items": {"type": "string"}, "description": "Ideogram character reference (<=1)."},
            "rendering_speed": {"type": "string", "description": "Ideogram: TURBO | BALANCED | QUALITY."},
            "style": {"type": "string", "description": "Ideogram: AUTO | REALISTIC | FICTION."},
            "num_images": {"type": "integer", "description": "Ideogram: 1-4."},
            "seed": {"type": "integer"},
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=512, vram_mb=0, disk_mb=100, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["rate_limit", "timeout"])
    idempotency_key_fields = ["model", "prompt", "aspect_ratio", "enable_pro"]
    side_effects = ["writes image file to output_path", "calls kie.ai API (spends credits)"]
    user_visible_verification = ["Inspect generated image for relevance, style, and quality"]

    def get_status(self) -> ToolStatus:
        from lib.env_loader import env_present

        return ToolStatus.AVAILABLE if env_present("KIE_API_KEY") else ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        from lib.providers.model_map import resolve

        row = resolve(inputs.get("model"), "image_generation") or {}
        cost = row.get("est_cost_usd")
        return float(cost) if cost else 0.0  # credit-metered; read /chat/credit for truth

    def estimate_runtime(self, inputs: dict[str, Any]) -> float:
        return 30.0

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        from lib.env_loader import env_present

        if not env_present("KIE_API_KEY"):
            return ToolResult(
                success=False, error="KIE_API_KEY not set. " + self.install_instructions
            )

        from lib.providers import kie_client
        from lib.providers.model_map import resolve

        row = resolve(inputs.get("model"), "image_generation")
        if not row:
            return ToolResult(
                success=False,
                error=(
                    f"Unknown kie image model: {inputs.get('model')!r}. "
                    "Add a row to lib/providers/kie_models.yaml (confirm its slash-id "
                    "and input fields from docs.kie.ai first)."
                ),
            )

        kie_model = row["kie_model"]
        allowed = list(row.get("input_fields") or [])
        ref_caps: dict[str, int] = row.get("reference_fields") or {}

        # Build the kie `input` GENERICALLY from the model's declared input_fields
        # (the model_map is the source of truth). Scalars forwarded as-is;
        # reference arrays go through the arity-capped path. Only declared params sent.
        model_input: dict[str, Any] = {}
        for key in allowed:
            if key in ref_caps:
                continue
            val = inputs.get(key)
            if val is not None:
                model_input[key] = val
        for field, cap in ref_caps.items():
            vals = inputs.get(field)
            if vals:
                if not isinstance(vals, list):
                    vals = [vals]
                if len(vals) > cap:
                    return ToolResult(
                        success=False,
                        error=f"{kie_model} accepts at most {cap} {field}; got {len(vals)}",
                    )
                model_input[field] = list(vals)

        out_path = inputs.get(
            "output_path", f"kie_{row['canonical_id'].replace('.', '_')}"
        )

        start = time.time()
        try:
            path, record, urls = kie_client.run_job(kie_model, model_input, out_path)
        except Exception as e:
            return ToolResult(success=False, error=f"kie image generation failed: {e}")

        size = os.path.getsize(path) if os.path.exists(path) else 0
        dims: dict[str, Any] = {}
        try:
            from PIL import Image

            with Image.open(path) as im:
                dims = {
                    "image_width": im.width,
                    "image_height": im.height,
                    "image_format": im.format,
                }
        except Exception:
            pass

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
                "output": path,
                "output_path": path,
                "file_size_bytes": size,
                **dims,
            },
            artifacts=[path],
            cost_usd=self.estimate_cost(inputs),
            duration_seconds=round(time.time() - start, 2),
            model=kie_model,
        )
