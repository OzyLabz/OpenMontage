"""Gateway model-identity map (slim System A) loader.

Structural map only — canonical model id -> {gateway, kie slash-id, capability,
operations, per-model input fields, reference-field arities}. Single gateway
(kie) means no price layer to join (System D dropped). Mirrors the lookup-table
shape of lib/media_profiles.py; validated against
schemas/providers/model_map.schema.json on load.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import jsonschema
import yaml

_DATA_PATH = Path(__file__).resolve().parent / "kie_models.yaml"
_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "schemas" / "providers" / "model_map.schema.json"
)


@lru_cache(maxsize=1)
def _load() -> dict[str, Any]:
    with open(_DATA_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    with open(_SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)
    jsonschema.validate(instance=data, schema=schema)
    return data


def all_models() -> list[dict[str, Any]]:
    return list(_load()["models"])


def get_model(canonical_id: str) -> Optional[dict[str, Any]]:
    for m in _load()["models"]:
        if m["canonical_id"] == canonical_id:
            return m
    return None


def get_by_kie_id(kie_model: str) -> Optional[dict[str, Any]]:
    for m in _load()["models"]:
        if m["kie_model"] == kie_model:
            return m
    return None


def default_for_capability(capability: str) -> Optional[dict[str, Any]]:
    rows = [m for m in _load()["models"] if m["capability"] == capability]
    for m in rows:
        if m.get("default_for_capability"):
            return m
    return rows[0] if rows else None


def resolve(model: Optional[str], capability: str) -> Optional[dict[str, Any]]:
    """Resolve a `model` arg (canonical id OR kie slash-id) to a row.

    Falls back to the capability's default row when `model` is None/empty.
    """
    if not model:
        return default_for_capability(capability)
    return get_model(model) or get_by_kie_id(model)
