from app.services.vision_response import extract_openai_compatible_content, summarize_vision_message_fields


def test_extract_content_prefers_content_field():
    msg = {"content": "hello", "reasoning": "ignored"}
    assert extract_openai_compatible_content(msg) == "hello"


def test_extract_content_falls_back_to_reasoning():
    msg = {"content": "", "reasoning": "vision result from qwen3"}
    assert extract_openai_compatible_content(msg) == "vision result from qwen3"


def test_extract_content_falls_back_to_thinking():
    msg = {"content": None, "thinking": "thinking channel text"}
    assert extract_openai_compatible_content(msg) == "thinking channel text"


def test_summarize_fields():
    msg = {"content": "abc", "reasoning": "12345"}
    summary = summarize_vision_message_fields(msg)
    assert summary == {"content": 3, "reasoning": 5}
