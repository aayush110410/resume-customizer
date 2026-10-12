"""Prompt templates (versioned .md files rendered with string.Template) and injection-safe wrapping."""

import hashlib
import re
from functools import cache
from pathlib import Path
from string import Template

PROMPTS_DIR = Path(__file__).parent / "prompts"


@cache
def _template(name: str) -> Template:
    text = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    return Template(re.sub(r"\A<!--.*?-->\s*", "", text, flags=re.S))


def render(name: str, **values: str) -> str:
    return _template(name).substitute(values)


def wrap(tag: str, content: str) -> str:
    """Delimit user content; a closing tag inside it is neutralised so it can't end the block early."""
    escaped = re.sub(rf"</(\s*{re.escape(tag)})", r"<\\/\1", content, flags=re.I)
    return f"<{tag}>\n{escaped}\n</{tag}>"


PROMPT_VERSION = hashlib.sha256(b"".join(p.read_bytes() for p in sorted(PROMPTS_DIR.glob("*.md")))).hexdigest()[:8]
