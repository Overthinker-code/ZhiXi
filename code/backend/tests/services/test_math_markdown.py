"""Tests for math_markdown normalization."""

from app.services.math_markdown import (
    normalize_math_delimiters,
    repair_latex_backslashes,
    strip_incomplete_math_for_stream,
)


def test_paren_to_dollar_inline():
    text = "令 \\(x^2 + 1\\) 成立"
    out = normalize_math_delimiters(text)
    assert out == "令 $x^2 + 1$ 成立"


def test_bracket_to_dollar_block():
    text = "公式：\\[\\int_0^1 x dx\\]"
    out = normalize_math_delimiters(text)
    assert "$$\\int_0^1 x dx$$" in out.replace("\n", "")


def test_repair_tab_corrupted_tan():
    corrupted = "$\tan x$"  # \t is TAB in Python source
    out = repair_latex_backslashes(corrupted)
    assert "\\tan" in out
    assert "\tan" not in out or out.index("\\tan") >= 0


def test_repair_formfeed_corrupted_frac():
    corrupted = "$\frac{a}{b}$"  # \f is form feed
    out = repair_latex_backslashes(corrupted)
    assert "\\frac" in out


def test_repair_bare_ext():
    out = repair_latex_backslashes("$ ext{lim}_{x o 0}$")
    assert "\\text{lim}" in out


def test_strip_incomplete_math():
    assert strip_incomplete_math_for_stream("a + b = $x") == "a + b = "
    assert strip_incomplete_math_for_stream("a + $b$") == "a + $b$"
