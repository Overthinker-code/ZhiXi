"""Normalize LLM math output to KaTeX-friendly $...$ / $$...$$ delimiters."""

from __future__ import annotations

import re

_INLINE_PAREN = re.compile(r"\\\((.+?)\\\)", re.DOTALL)
_BLOCK_BRACKET = re.compile(r"\\\[(.+?)\\\]", re.DOTALL)

# JSON/SSE may turn \t \f into TAB/FF — repair common LaTeX command prefixes
_LATEX_CTRL_REPAIRS: tuple[tuple[str, str], ...] = (
    ("\x0c" + "rac", "\\frac"),
    ("\t" + "frac", "\\frac"),
    ("\t" + "an", "\\tan"),
    ("\t" + "imes", "\\times"),
    ("\t" + "o", "\\to"),
    ("\t" + "ext", "\\text"),
    ("\t" + "heta", "\\theta"),
    ("\t" + "au", "\\tau"),
)

# Bare fragments after \t was eaten as whitespace in transit
_BARE_LATEX_FRAG_REPAIRS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?<![\\a-zA-Z])ext\{"), r"\\text{"),
    (re.compile(r"(?<![\\a-zA-Z])rac\{"), r"\\frac{"),
    (re.compile(r"(?<![\\a-zA-Z])imes\b"), r"\\times"),
)


def repair_latex_backslashes(text: str) -> str:
    """Restore LaTeX backslashes corrupted by JSON escape sequences (\\t, \\f, etc.)."""
    if not text:
        return text or ""
    out = str(text)
    for bad, good in _LATEX_CTRL_REPAIRS:
        out = out.replace(bad, good)
    for pattern, repl in _BARE_LATEX_FRAG_REPAIRS:
        out = pattern.sub(repl, out)
    return out


def normalize_math_delimiters(text: str) -> str:
    """Convert \\(\\), \\[\\] to $ / $$ and trim broken delimiters."""
    if not text or not str(text).strip():
        return text or ""

    out = repair_latex_backslashes(str(text))
    out = _BLOCK_BRACKET.sub(lambda m: f"\n$${m.group(1).strip()}$$\n", out)
    out = _INLINE_PAREN.sub(lambda m: f"${m.group(1).strip()}$", out)

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
    s = normalize_math_delimiters(str(text))
    if s.count("$") % 2 == 0:
        return s
    last = s.rfind("$")
    if last >= 0:
        s = s[:last]
    s = re.sub(r"\\[a-zA-Z]*$", "", s)
    return s
