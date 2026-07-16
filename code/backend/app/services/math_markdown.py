"""Normalize LLM math output to KaTeX-friendly $...$ / $$...$$ delimiters."""

from __future__ import annotations

import re

_INLINE_PAREN = re.compile(r"\\\((.+?)\\\)", re.DOTALL)
_BLOCK_BRACKET = re.compile(r"\\\[(.+?)\\\]", re.DOTALL)

# JSON/SSE may turn control escapes such as \t, \f, and \r into real control
# characters before Markdown reaches KaTeX. Repair the common LaTeX commands.
_LATEX_CTRL_REPAIRS: tuple[tuple[str, str], ...] = (
    ("\x0c" + "rac", "\\frac"),
    ("\t" + "frac", "\\frac"),
    ("\t" + "an", "\\tan"),
    ("\t" + "imes", "\\times"),
    ("\t" + "o", "\\to"),
    ("\t" + "ext", "\\text"),
    ("\t" + "heta", "\\theta"),
    ("\t" + "au", "\\tau"),
    ("\t" + "lim", "\\lim"),
    ("\t" + "sqrt", "\\sqrt"),
    ("\t" + "sum", "\\sum"),
    ("\t" + "int", "\\int"),
    ("\r" + "ight", "\\right"),
)

_BARE_LATEX_FRAG_REPAIRS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?<![\\a-zA-Z])ext\{"), r"\\text{"),
    (re.compile(r"(?<![\\a-zA-Z])rac\{"), r"\\frac{"),
    (re.compile(r"(?<![\\a-zA-Z])imes\b"), r"\\times"),
    (re.compile(r"(?<![\\a-zA-Z])cdot\b"), r"\\cdot"),
    (re.compile(r"(?<![\\a-zA-Z])infty\b"), r"\\infty"),
    (re.compile(r"(?<![\\a-zA-Z])left\b"), r"\\left"),
    (re.compile(r"(?<![\\a-zA-Z])right\b"), r"\\right"),
)

# LLM often writes (x+h)_2 instead of (x+h)^2 in derivative expansions.
_SUBSCRIPT_AS_EXPONENT = re.compile(r"\(([^)]+)\)_(\d+)")

# f'(x) outside math delimiters.
_PRIME_FUNC = re.compile(r"(?<!\$)\bf'\(([^)]+)\)(?!\$)")
_MODEL_MATH_HTML_ARTIFACT = re.compile(
    r"(?:class\s*=\s*[\"']math[\"']|<(?:math|mrow|annotation|semantics)\b)",
    re.IGNORECASE,
)
_CJK = re.compile(r"[\u3400-\u9fff]")
_STANDALONE_BLOCK_DELIMITER = re.compile(r"^\s*\${2,}\s*$")


def looks_like_broken_math_markup(text: str) -> bool:
    """Reject model-generated HTML/MathML fragments before Markdown rendering."""
    return bool(_MODEL_MATH_HTML_ARTIFACT.search(str(text or "")))


def repair_latex_backslashes(text: str) -> str:
    """Restore LaTeX backslashes corrupted by JSON escape sequences."""
    if not text:
        return text or ""
    out = str(text)
    for bad, good in _LATEX_CTRL_REPAIRS:
        out = out.replace(bad, good)
    for pattern, repl in _BARE_LATEX_FRAG_REPAIRS:
        out = pattern.sub(repl, out)
    return out


def _fix_subscript_exponents(segment: str) -> str:
    if "^" in segment or "\\frac" not in segment and "lim" not in segment:
        return segment
    return _SUBSCRIPT_AS_EXPONENT.sub(r"(\1)^{\2}", segment)


def _is_math_only_line(value: str) -> bool:
    body = str(value or "").strip()
    if not body or _CJK.search(body) or "**" in body or "`" in body:
        return False
    if re.search(
        r"\\(?:frac|lim|sum|int|sqrt|tan|sin|cos|log|text|phi)(?![A-Za-z])",
        body,
    ):
        return True
    return bool(
        re.match(r"^[A-Za-z\\][A-Za-z0-9_{}\\^().,\s]*\s*(?:=|≈|≤|≥|<|>)\s*.+$", body)
    )


def _strip_nested_inline_dollars(body: str) -> str:
    value = str(body or "").strip()
    if (
        value.startswith("$")
        and value.endswith("$")
        and not value.startswith("$$")
        and not value.endswith("$$")
    ):
        return value[1:-1].strip()
    return value


def _normalize_block_dollars(text: str) -> str:
    """Repair repeated, nested and unmatched block delimiters from LLM output."""
    source = re.sub(r"\${3,}", "$$", str(text or ""))
    output: list[str] = []
    block: list[str] = []
    in_block = False

    for line in source.split("\n"):
        same_line = re.fullmatch(r"\s*\$\$(.*?)\$\$\s*", line)
        if same_line and in_block:
            previous = _strip_nested_inline_dollars("\n".join(block))
            if previous:
                if _is_math_only_line(previous):
                    output.extend(["$$", previous, "$$"])
                else:
                    output.extend(block)
            block = []
            in_block = False
            body = _strip_nested_inline_dollars(same_line.group(1))
            if _is_math_only_line(body):
                output.append(f"$${body}$$")
            elif body:
                output.append(body)
            continue

        if _STANDALONE_BLOCK_DELIMITER.match(line):
            if not in_block:
                in_block = True
                block = []
                continue
            body = _strip_nested_inline_dollars("\n".join(block))
            if body:
                if _is_math_only_line(body):
                    output.extend(["$$", body, "$$"])
                else:
                    output.extend(block)
            block = []
            in_block = False
            continue

        if same_line and not in_block:
            body = _strip_nested_inline_dollars(same_line.group(1))
            if _is_math_only_line(body):
                output.append(f"$${body}$$")
            elif body:
                output.append(body)
            continue

        if in_block:
            block.append(line)
        else:
            output.append(line)

    if in_block:
        # Drop the unmatched opening delimiter but keep its text. A later pass
        # can safely wrap formula-only lines without swallowing normal prose.
        output.extend(block)
    return "\n".join(output)


def _wrap_orphan_math_lines(text: str) -> str:
    lines: list[str] = []
    in_block = False
    for line in text.split("\n"):
        if line.strip() == "$$":
            in_block = not in_block
            lines.append(line)
            continue
        if in_block:
            lines.append(line)
            continue
        if "$" in line:
            lines.append(line)
            continue
        stripped = line.strip()
        if not stripped:
            lines.append(line)
            continue
        if _is_math_only_line(stripped):
            body = _fix_subscript_exponents(stripped)
            if (
                "=" in body
                or len(body) > 48
                or "\\frac" in body
                or "\\lim" in body
                or "lim_" in body
            ):
                lines.append(f"$${body}$$")
            else:
                lines.append(f"${body}$")
        else:
            lines.append(line)
    return "\n".join(lines)


def normalize_math_delimiters(text: str) -> str:
    """Convert delimiters, repair escapes, and wrap bare LaTeX for KaTeX."""
    if not text or not str(text).strip():
        return text or ""

    out = repair_latex_backslashes(str(text))
    out = _PRIME_FUNC.sub(r"$f'(\1)$", out)
    out = _BLOCK_BRACKET.sub(lambda m: f"\n$${m.group(1).strip()}$$\n", out)
    out = _INLINE_PAREN.sub(lambda m: f"${m.group(1).strip()}$", out)
    out = _normalize_block_dollars(out)
    out = _wrap_orphan_math_lines(out)

    def _fix_dollars(match: re.Match[str]) -> str:
        body = _fix_subscript_exponents(match.group(1))
        return f"${body}$"

    def _fix_dollars_block(match: re.Match[str]) -> str:
        body = _fix_subscript_exponents(match.group(1).strip())
        return f"\n$${body}$$\n"

    out = re.sub(r"\$\$([^$]+)\$\$", _fix_dollars_block, out, flags=re.DOTALL)
    out = re.sub(r"(?<!\$)\$(?!\$)([^$]+)\$(?!\$)", _fix_dollars, out)

    lines = out.split("\n")
    fixed: list[str] = []
    for line in lines:
        if line.count("$") % 2 == 1 and not line.strip().startswith("$$"):
            if line.rstrip().endswith("$") and line.count("$") == 1:
                line = line.rstrip()[:-1] + "$"
        fixed.append(line)
    return "\n".join(fixed)


def strip_incomplete_math_for_stream(text: str) -> str:
    """During streaming, drop trailing unclosed $ to avoid broken partial formulas."""
    if not text:
        return ""
    s = normalize_math_delimiters(str(text))
    if s.count("$$") % 2 == 1:
        last = s.rfind("$$")
        if last >= 0:
            s = s[:last]
    if s.replace("$$", "").count("$") % 2 == 1:
        last = s.rfind("$")
        if last >= 0:
            s = s[:last]
    s = re.sub(r"\\[a-zA-Z]*$", "", s)
    return s
