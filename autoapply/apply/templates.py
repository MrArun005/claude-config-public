"""apply/templates.py — render TEMPLATE-policy answers, strictly.

`StrictUndefined` is the whole point. A cover-letter template with a
`{{ company }}` the runner cannot supply must *fail*, not quietly render
"I would love to join ." — a silently empty sentence is worse than a park,
because it gets submitted.

A template still containing a TODO marker counts as unapproved and is refused
for the same reason: the design says you write the prose, the agent only
selects it.
"""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, StrictUndefined, TemplateError, UndefinedError

from state.answers import PLACEHOLDER

_ENV = Environment(undefined=StrictUndefined, keep_trailing_newline=False,
                   autoescape=False, trim_blocks=True, lstrip_blocks=True)


class Unrenderable(Exception):
    """Template missing, unapproved, or short a variable. Park, never submit."""


def render(template_path: Path, context: dict) -> str:
    if not template_path.exists():
        raise Unrenderable(f"template not found: {template_path}")

    source = template_path.read_text()
    if PLACEHOLDER.search(source):
        raise Unrenderable(
            f"{template_path.name} still contains a TODO marker — write the real "
            f"text before this can be submitted"
        )

    try:
        out = _ENV.from_string(source).render(**context).strip()
    except UndefinedError as exc:
        raise Unrenderable(f"{template_path.name}: {exc}") from exc
    except TemplateError as exc:
        raise Unrenderable(f"{template_path.name}: {exc}") from exc

    if not out:
        raise Unrenderable(f"{template_path.name} rendered empty")
    return out
