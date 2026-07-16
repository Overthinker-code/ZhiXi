from __future__ import annotations

import re
from dataclasses import dataclass


_QUIZ_REVEAL_HEADING = re.compile(
    r"(?:思考提示|思考方向|解题思路|核心概念解析|理解场景|回顾\s*ACID|匹配场景|"
    r"常见误区|下一步练习建议|延伸问题|答案解析|参考答案|标准答案|正确答案|"
    r"ACID\s*特性回顾|知识点回顾|在你作答之前|作答前提示)",
    re.IGNORECASE,
)

_QUIZ_QUESTION_HEADING = re.compile(
    r"(?im)^(?:#{1,4}\s*)?(?:[一二三四五六七八九十0-9]+[、.．]\s*)?"
    r"(?:基础|入门|单项|多项)?(?:选择题|判断题|填空题|简答题|练习题|题目)\s*[:：]?\s*$"
)
_QUIZ_QUESTION_SIGNAL = re.compile(
    r"[？?]|请判断|(?:^|\n)\s*[A-DＡ-Ｄ][.．、:：)]\s*|(?:正确|错误|对|错)\s*[？?]?\s*$",
    re.IGNORECASE,
)
_QUIZ_FALLBACK = (
    "## 基础题\n\n"
    "请用自己的话说明本章最核心的一个概念，并举出一个实际例子。\n\n"
    "请先作答并说明理由，我会根据你的回答继续追问。"
)


def is_initial_quiz_request(agent_key: str | None, message: str) -> bool:
    if (agent_key or "").strip().lower() != "practice":
        return False
    text = (message or "").strip()
    asks_for_question = bool(re.search(r"出题|一道.{0,8}题|练习|测验|陪练", text))
    contains_answer = bool(re.search(r"我选|我的答案|答案是|作答[:：]|选择\s*[A-D]", text, re.IGNORECASE))
    return asks_for_question and not contains_answer


@dataclass
class CourseAgentOutputGuard:
    hide_quiz_solution: bool = False
    _line_buffer: str = ""
    _quiz_buffer: str = ""
    _blocked: bool = False
    _sanitized: bool = False

    @property
    def sanitized(self) -> bool:
        return self._blocked or self._sanitized

    def push(self, text: str) -> str:
        if not text or self._blocked:
            return ""
        if not self.hide_quiz_solution:
            return text
        # 首轮陪练必须在完整回答边界上校验。逐行透传无法阻止模型先讲课、
        # 后出题，或在没有标准标题时提前泄露答案。
        self._quiz_buffer += text
        return ""

    def finish(self) -> str:
        if self.hide_quiz_solution:
            raw = self._quiz_buffer
            self._quiz_buffer = ""
            visible = self._initial_quiz_only(raw)
            self._sanitized = visible.strip() != raw.strip()
            return visible
        if self._blocked:
            self._line_buffer = ""
            return ""
        pending = self._line_buffer
        self._line_buffer = ""
        return self._accept_line(pending)

    def _initial_quiz_only(self, text: str) -> str:
        raw = (text or "").replace("\r\n", "\n").strip()
        if not raw:
            self._blocked = True
            return _QUIZ_FALLBACK

        reveal = _QUIZ_REVEAL_HEADING.search(raw)
        safe_prefix = raw[: reveal.start()].strip() if reveal else raw
        if reveal:
            self._blocked = True

        question_heading = _QUIZ_QUESTION_HEADING.search(safe_prefix)
        candidate = safe_prefix[question_heading.start() :].strip() if question_heading else safe_prefix

        kept_lines: list[str] = []
        for line in candidate.splitlines():
            if _QUIZ_REVEAL_HEADING.search(line):
                self._blocked = True
                break
            kept_lines.append(line)
        candidate = "\n".join(kept_lines).strip()

        if not _QUIZ_QUESTION_SIGNAL.search(candidate) or (
            question_heading is None and len(candidate) > 600
        ):
            self._blocked = True
            return _QUIZ_FALLBACK

        if not re.search(r"请.{0,16}(?:作答|回复|选择|判断)", candidate):
            candidate += "\n\n请先给出你的答案和理由，我会在你作答后再提供提示与解析。"
        return candidate

    def _accept_line(self, line: str) -> str:
        if self._blocked or not line:
            return ""
        if _QUIZ_REVEAL_HEADING.search(line):
            self._blocked = True
            return ""
        return line
