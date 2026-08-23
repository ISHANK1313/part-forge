"""Prompt file loader: renders prompts/<stage>.md with {{placeholders}}."""
from __future__ import annotations

import json
import re
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"

_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


def render_prompt(stage: str, context: dict) -> str:
    path = PROMPTS_DIR / f"{stage}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file missing: {path}")
    template = path.read_text(encoding="utf-8")

    def sub(m: re.Match) -> str:
        val = context.get(m.group(1), "")
        if isinstance(val, (dict, list)):
            return json.dumps(val, ensure_ascii=False, indent=1)
        return str(val)

    return _PLACEHOLDER.sub(sub, template)
