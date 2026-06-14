"""Tests for math_markdown normalization."""

from app.services.math_markdown import (
    looks_like_broken_math_markup,
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


def test_repair_bare_latex_fragments():
    out = repair_latex_backslashes("$infty cdot left right$")
    assert "\\infty" in out
    assert "\\cdot" in out
    assert "\\left" in out
    assert "\\right" in out


def test_wrap_prime_function():
    out = normalize_math_delimiters("导数 f'(x) 定义")
    assert "$f'(x)$" in out


def test_fix_subscript_exponent_in_frac():
    out = normalize_math_delimiters("$$\\frac{(x+h)_2 - x_2}{h}$$")
    assert "^{2}" in out or "^2" in out


def test_strip_incomplete_math():
    assert strip_incomplete_math_for_stream("a + b = $x") == "a + b = "
    assert strip_incomplete_math_for_stream("a + $b$") == "a + $b$"


def test_detect_broken_model_math_markup():
    assert looks_like_broken_math_markup('调和级数 class="math">')
    assert looks_like_broken_math_markup("<math><mrow>x</mrow></math>")
    assert not looks_like_broken_math_markup(
        r"调和级数 $\sum_{n=1}^{\infty}\frac1n$"
    )


def test_repairs_repeated_nested_and_unmatched_block_dollars():
    raw = r"""
$$$$
A_{ij} = \text{softmax}\left(\frac{F_i^T F_j}{\sqrt D}\right)
$$$$
$$
$W = A^T A$
$$
$$- **注意力一致性上下文**：$$
C = \phi(A, W)
$$
通过上述公式，ANA-Net 完成局部与全局建模。
"""
    out = normalize_math_delimiters(raw)

    assert "$$$$" not in out
    assert "\n$W = A^T A$\n" not in out
    assert "$$W = A^T A$$" in out.replace("\n", "")
    assert "- **注意力一致性上下文**：" in out
    assert "$$C = \\phi(A, W)$$" in out.replace("\n", "")
    assert "$$通过上述公式" not in out
