import pytest
from pydantic import ValidationError

from app.api.v1.endpoints.ai_chat import AIChatStreamRequest
from app.api.v1.endpoints.rag import QueryRequest


@pytest.mark.parametrize(
    ("payload", "error_fragment"),
    [
        ({"query": "   "}, "query must not be blank"),
        ({"query": "ACID", "k": 0}, "greater than or equal to 1"),
        ({"query": "ACID", "k": 21}, "less than or equal to 20"),
        ({"query": "学" * 2001}, "at most 2000 characters"),
    ],
)
def test_rag_query_rejects_invalid_boundaries(payload: dict, error_fragment: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        QueryRequest.model_validate({**payload, "course_id": "course-a"})
    assert error_fragment in str(exc_info.value)


def test_rag_query_normalizes_surrounding_whitespace() -> None:
    request = QueryRequest.model_validate(
        {"query": "  ACID  ", "k": 4, "course_id": "course-a"}
    )
    assert request.query == "ACID"


def test_ai_chat_rejects_empty_input_before_model_execution() -> None:
    with pytest.raises(ValidationError, match="message, attachment, or resource target"):
        AIChatStreamRequest.model_validate({"message": "  ", "attachments": []})


def test_ai_chat_accepts_attachment_only_and_bounded_resource_target() -> None:
    attachment_request = AIChatStreamRequest.model_validate(
        {
            "message": "",
            "attachments": [{"fileId": "owned-file", "type": "image"}],
        }
    )
    assert attachment_request.message == ""

    resource_request = AIChatStreamRequest.model_validate(
        {
            "message": "",
            "mode": "resource_generation",
            "resourceRequest": {"target": "事务与并发控制"},
        }
    )
    assert resource_request.resource_request.target == "事务与并发控制"


def test_ai_chat_rejects_oversized_unicode_message() -> None:
    with pytest.raises(ValidationError, match="at most 8000 characters"):
        AIChatStreamRequest.model_validate({"message": "界" * 8001})
