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
    corrupted = "$\tan x$"
    out = repair_latex_backslashes(corrupted)
    assert "\\tan" in out


def test_repair_formfeed_corrupted_frac():
    corrupted = "$\frac{a}{b}$"
    out = repair_latex_backslashes(corrupted)
    assert "\\frac" in out


def test_repair_bare_ext():
    out = repair_latex_backslashes("$ ext{lim}_{x o 0}$")
    assert "\\text{lim}" in out


def test_wrap_prime_function():
    out = normalize_math_delimiters("导数 f'(x) 定义")
    assert "$f'(x)$" in out


def test_fix_subscript_exponent_in_frac():
    out = normalize_math_delimiters("$$\\frac{(x+h)_2 - x_2}{h}$$")
    assert "^{2}" in out or "^2" in out


def test_strip_incomplete_math():
    assert strip_incomplete_math_for_stream("a + b = $x") == "a + b = "
    assert strip_incomplete_math_for_stream("a + $b$") == "a + $b$"
