"""apply/adapter.py — the execution ladder (plan §4).

Rung 1: deterministic adapter (first matches() wins)
Rung 2: adapter raises UnknownField -> agent resolves JUST that field,
        resolution cached by (platform, field_signature)
Rung 3: no adapter matches -> full LLM agent (engine chosen at P3 gate)
Rung 4: headed handoff
"""
from __future__ import annotations
import json
from pathlib import Path

import paths
from typing import Protocol

CACHE = paths.under("field-resolutions.json")


class UnknownField(Exception):
    def __init__(self, field_signature: str, label: str):
        self.field_signature = field_signature
        self.label = label
        super().__init__(f"unknown field: {label} ({field_signature})")


class Adapter(Protocol):
    name: str
    def matches(self, url: str, html: str) -> bool: ...
    async def apply(self, page, profile: dict, ckpt) -> dict: ...


def load_resolutions() -> dict:
    return json.loads(CACHE.read_text()) if CACHE.exists() else {}


def cache_resolution(platform: str, field_signature: str, answer_key: str) -> None:
    """Rung-2 result -> next run is rung 1 again. This is the Stagehand idea."""
    data = load_resolutions()
    data[f"{platform}::{field_signature}"] = answer_key
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(data, indent=2))


def dispatch(adapters: list[Adapter], url: str, html: str) -> Adapter | None:
    for a in adapters:
        if a.matches(url, html):
            return a
    return None  # -> rung 3
