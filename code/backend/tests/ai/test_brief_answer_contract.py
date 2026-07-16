from app.ai.chat_engine import _honor_explicit_brief_contract


def test_normal_teaching_answer_is_not_shortened():
    answer = "第一段。第二段。" * 80
    assert _honor_explicit_brief_contract("详细解释数据库事务", answer) == answer


def test_one_sentence_request_keeps_only_first_sentence():
    answer = "索引是帮助数据库快速定位记录的数据结构。它会增加写入和存储开销。"
    assert _honor_explicit_brief_contract("用一句话解释索引", answer) == "索引是帮助数据库快速定位记录的数据结构。"


def test_explicit_character_limit_is_enforced():
    answer = "事务保证一组操作作为整体执行。" * 20
    result = _honor_explicit_brief_contract("请在50字以内概括事务", answer)
    assert len(result) <= 50
    assert result.endswith("。")
