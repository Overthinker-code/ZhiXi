"""Normalize LLM math output to KaTeX-friendly $...$ / $$...$$ delimiters."""

from __future__ import annotations

import re

_INLINE_PAREN = re.compile(r"\\\((.+?)\\\)", re.DOTALL)
_BLOCK_BRACKET = re.compile(r"\\\[(.+?)\\\]", re.DOTALL)
_DOLLAR_BLOCK = re.compile(r"(?<!\$)\$\$(.+?)\$\$(?!\$)", re.DOTALL)
_DOLLAR_INLINE = re.compile(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", re.DOTALL)


def normalize_math_delimiters(text: str) -> str:
    """Convert \\(\\), \\[\\] to $ / $$ and trim broken delimiters."""
    if not text or not str(text).strip():
        return text or ""

    out = str(text)
    out = _BLOCK_BRACKET.sub(lambda m: f"\n$${m.group(1).strip()}$$\n", out)
    out = _INLINE_PAREN.sub(lambda m: f"${m.group(1).strip()}$", out)

    # Fix unbalanced single $ at line ends (common LLM glitch)
    lines = out.split("\n")
    fixed: list[str] = []
    for line in lines:
        if line.count("$") % 2 == 1 and not line.strip().startswith("$$"):
            if line.rstrip().endswith("$") and line.count("$") == 1:
                line = line.rstrip()[:-1] + "$"
        fixed.append(line)
    out = "\n".join(fixed)
    return out


def strip_incomplete_math_for_stream(text: str) -> str:
    """During streaming, drop trailing unclosed $ to avoid broken partial formulas."""
    if not text:
        return ""
    s = str(text)
    if s.count("$") % 2 == 0:
        return s
    last = s.rfind("$")
    if last >= 0:
        return s[:last]
    return s
