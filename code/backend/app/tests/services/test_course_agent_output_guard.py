from app.services.course_agent_output_guard import (
    CourseAgentOutputGuard,
    is_initial_quiz_request,
)


def test_initial_quiz_request_detection_distinguishes_answer_turn() -> None:
    assert is_initial_quiz_request("practice", "请出一道 ACID 判断题")
    assert not is_initial_quiz_request("practice", "我选 A，这是我的答案")
    assert not is_initial_quiz_request("planner", "请出一道题")


def test_quiz_guard_streams_question_and_hides_solution_section() -> None:
    guard = CourseAgentOutputGuard(hide_quiz_solution=True)
    chunks = [
        "## 判断题\n事务失败后回滚，对应哪项特性？\n",
        "A. 原子性\nB. 一致性\n请作答。\n### 思考",
        "提示\nUndo 通常对应原子性。\n",
    ]
    streamed = "".join(guard.push(chunk) for chunk in chunks)
    visible = streamed + guard.finish()
    assert streamed == ""
    assert "判断题" in visible
    assert "请作答" in visible
    assert "思考提示" not in visible
    assert "Undo" not in visible
    assert guard.sanitized


def test_quiz_guard_hides_pre_answer_thinking_direction() -> None:
    guard = CourseAgentOutputGuard(hide_quiz_solution=True)
    visible = guard.push(
        "请判断以上说法。\n请直接回复你的答案。\n在你作答之前，我先说明思考方向：\n注意绝对化措辞。\n"
    ) + guard.finish()
    assert "请直接回复你的答案" in visible
    assert "思考方向" not in visible
    assert "绝对化措辞" not in visible


def test_quiz_guard_hides_full_solution_even_when_model_labels_it_as_reasoning() -> None:
    guard = CourseAgentOutputGuard(hide_quiz_solution=True)
    visible = guard.push(
        "**题目：** 事务执行一半后回滚，主要体现哪项特性？\n"
        "A. 原子性 B. 一致性 C. 隔离性 D. 持久性\n"
        "**解题思路与核心概念解析：**\n"
        "回滚体现原子性，正确答案为 A。\n"
    ) + guard.finish()
    assert "事务执行一半后回滚" in visible
    assert "解题思路" not in visible
    assert "正确答案" not in visible
    assert guard.sanitized


def test_quiz_guard_drops_lecture_before_first_question() -> None:
    guard = CourseAgentOutputGuard(hide_quiz_solution=True)
    raw = (
        "## 核心概念分层讲解\n事务是逻辑工作单元，ACID 包含四项性质。\n\n"
        "## 基础选择题\n事务执行一半失败后应全部回滚，主要体现哪项特性？\n"
        "A. 原子性\nB. 一致性\nC. 隔离性\nD. 持久性\n\n"
        "## 完整解析\n正确答案是 A，因为原子性要求全部成功或全部失败。"
    )

    assert guard.push(raw[:37]) == ""
    assert guard.push(raw[37:]) == ""
    visible = guard.finish()

    assert "核心概念分层讲解" not in visible
    assert "事务执行一半失败" in visible
    assert "A. 原子性" in visible
    assert "正确答案" not in visible
    assert "请先给出你的答案" in visible


def test_quiz_guard_uses_safe_fallback_when_model_never_asks_a_question() -> None:
    guard = CourseAgentOutputGuard(hide_quiz_solution=True)
    guard.push("下面先完整讲解 ACID，再进入练习。原子性表示要么全做要么全不做。")

    visible = guard.finish()

    assert "完整讲解 ACID" not in visible
    assert "## 基础题" in visible
    assert "请先作答" in visible
    assert guard.sanitized
