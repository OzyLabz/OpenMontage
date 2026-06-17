"""Registry loader (faceless-mode channel entries).

Loads, validates, lists, and matches channel entries from registry/channels/.
This resolves PRE-PIPELINE config (style + voice + format) — it is NOT a
generation tool and is deliberately not a BaseTool, so it is never discovered
or scored by the selectors. Mirrors lib/pipeline_loader.py and
styles/playbook_loader.py.

Switch stays OFF: a channel locks style/voice/format only and never names a
model or pins a gateway. `style_prompt` / `niche` are conditioning-only.
Request matching uses `match.keywords` only (dead-simple for this build).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import yaml
import jsonschema

CHANNELS_DIR = Path(__file__).resolve().parent.parent / "registry" / "channels"
SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent
    / "schemas"
    / "registry"
    / "channel.schema.json"
)
PERSONAS_DIR = Path(__file__).resolve().parent.parent / "registry" / "personas"
PERSONA_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent
    / "schemas"
    / "registry"
    / "persona.schema.json"
)


def _load_channel_schema() -> dict:
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def validate_channel(entry: dict) -> None:
    """Validate a channel entry dict against the schema."""
    schema = _load_channel_schema()
    jsonschema.validate(instance=entry, schema=schema)


def load_channel(name: str, channels_dir: Optional[Path] = None) -> dict[str, Any]:
    """Load and validate a channel entry by id (filename without .yaml).

    Args:
        name: Channel id / filename stem.
        channels_dir: Override directory for channel entries.

    Returns:
        Validated channel entry dict.
    """
    channels_dir = channels_dir or CHANNELS_DIR
    path = channels_dir / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Channel entry not found: {path}")

    with open(path) as f:
        entry = yaml.safe_load(f)

    validate_channel(entry)
    return entry


def list_channels(channels_dir: Optional[Path] = None) -> list[str]:
    """List all available channel entry ids."""
    channels_dir = channels_dir or CHANNELS_DIR
    if not channels_dir.exists():
        return []
    return sorted(p.stem for p in channels_dir.glob("*.yaml"))


def match_channel(
    request: str, channels_dir: Optional[Path] = None
) -> Optional[dict[str, Any]]:
    """Match a request to a channel entry by keyword (dead-simple).

    A request matches a channel if its (lowercased) text contains any of that
    channel's `match.keywords`. Matching uses keywords ONLY — never `niche` or
    `style_prompt`. Returns the first matching, validated channel entry, or None
    when no channel matches (caller falls through to default behavior).

    Args:
        request: The user's request text.
        channels_dir: Override directory for channel entries.

    Returns:
        Validated channel entry dict, or None if nothing matches.
    """
    text = (request or "").lower()
    for name in list_channels(channels_dir):
        entry = load_channel(name, channels_dir)
        keywords = entry.get("match", {}).get("keywords", [])
        if any(kw.lower() in text for kw in keywords):
            return entry
    return None


def validate_visuals_providers(
    entry: dict[str, Any], available_providers
) -> list[tuple[str, str]]:
    """Check a channel's `visuals.*` provider ids against real registry providers.

    Returns a list of (slot, provider_id) for any visuals provider that is NOT a
    discovered tool `provider` id. Empty list == all good. Decoupled from the
    registry (caller passes the available provider ids) so channel loading never
    forces tool discovery. Use in preflight/tests to fail fast on
    channel<->registry provider-id drift (the `google` vs `google_tts` class of bug).
    """
    visuals = (entry or {}).get("visuals") or {}
    avail = set(available_providers or [])
    bad: list[tuple[str, str]] = []
    for slot in ("image_provider", "video_provider"):
        pid = visuals.get(slot)
        if pid and pid not in avail:
            bad.append((slot, pid))
    return bad


# ---------------------------------------------------------------------------
# Persona entries (influencer mode) — sibling of the channel loader above.
#
# A persona locks a character identity (reference image set) + NAMED generation
# model(s) for character-consistent output (switch-ON + named model, NOT
# preferred_provider). look/vibe/niche are conditioning-only; reference_images
# role/use_for are selection metadata only. Matching uses match.keywords only.
# Mirrors the channel functions byte-for-byte (different dir + schema). Adding a
# persona = drop registry/personas/<id>.yaml (+ its asset dir) — auto-discovered.
# ---------------------------------------------------------------------------


def _load_persona_schema() -> dict:
    with open(PERSONA_SCHEMA_PATH) as f:
        return json.load(f)


def validate_persona(entry: dict) -> None:
    """Validate a persona entry dict against the schema."""
    schema = _load_persona_schema()
    jsonschema.validate(instance=entry, schema=schema)


def load_persona(name: str, personas_dir: Optional[Path] = None) -> dict[str, Any]:
    """Load and validate a persona entry by id (filename without .yaml)."""
    personas_dir = personas_dir or PERSONAS_DIR
    path = personas_dir / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Persona entry not found: {path}")

    with open(path) as f:
        entry = yaml.safe_load(f)

    validate_persona(entry)
    return entry


def list_personas(personas_dir: Optional[Path] = None) -> list[str]:
    """List all available persona entry ids."""
    personas_dir = personas_dir or PERSONAS_DIR
    if not personas_dir.exists():
        return []
    return sorted(p.stem for p in personas_dir.glob("*.yaml"))


def match_persona(
    request: str, personas_dir: Optional[Path] = None
) -> Optional[dict[str, Any]]:
    """Match a request to a persona entry by keyword (dead-simple).

    A request matches a persona if its (lowercased) text contains any of that
    persona's `match.keywords`. Matching uses keywords ONLY — never `niche`,
    `look`, or `vibe`. Returns the first matching, validated persona entry, or
    None when no persona matches (caller falls through to the channel check,
    then default behavior).
    """
    text = (request or "").lower()
    for name in list_personas(personas_dir):
        entry = load_persona(name, personas_dir)
        keywords = entry.get("match", {}).get("keywords", [])
        if any(kw.lower() in text for kw in keywords):
            return entry
    return None
