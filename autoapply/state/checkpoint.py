"""state/checkpoint.py — never lose 80% again.

Written after EVERY successful field, not every page. Resume contract:
reopen url, replay completed_fields, continue at pending_fields[0].
"""
from __future__ import annotations
import json, time
from dataclasses import dataclass, field, asdict
from pathlib import Path

import paths

ROOT = paths.under("checkpoints")


@dataclass
class Checkpoint:
    app_id: str
    url: str = ""
    completed_fields: dict = field(default_factory=dict)
    pending_fields: list = field(default_factory=list)
    last_action: str = ""
    ts: str = ""

    @property
    def path(self) -> Path:
        return ROOT / f"{self.app_id}.json"

    def record(self, field_name: str, value, action: str | None = None) -> None:
        """Call after every successful fill. This IS the crash-proofing."""
        self.completed_fields[field_name] = value
        if field_name in self.pending_fields:
            self.pending_fields.remove(field_name)
        self.last_action = action or f"fill:{field_name}"
        self.ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        self.save()

    def save(self) -> None:
        ROOT.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False))
        tmp.replace(self.path)  # atomic — a crash mid-write can't corrupt

    @classmethod
    def load(cls, app_id: str) -> "Checkpoint | None":
        p = ROOT / f"{app_id}.json"
        if not p.exists():
            return None
        return cls(**json.loads(p.read_text()))

    def done(self) -> None:
        if self.path.exists():
            self.path.unlink()
