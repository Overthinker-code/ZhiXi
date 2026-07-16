from datetime import datetime
from uuid import uuid4

from app.schemas.chat import Chat
from app.schemas.students import StudentCreate, StudentPublic


def test_chat_collection_defaults_are_isolated() -> None:
    first = Chat(id=1, user_input="first", created_at=datetime.now())
    second = Chat(id=2, user_input="second", created_at=datetime.now())

    first.citations.append({"title": "source"})
    first.suggestions.append("follow up")
    first.metrics["latency_ms"] = 10

    assert second.citations == []
    assert second.suggestions == []
    assert second.metrics == {}


def test_student_collection_defaults_are_isolated() -> None:
    first = StudentCreate(name="first", identifier="s-1", ud_id=uuid4())
    second = StudentCreate(name="second", identifier="s-2", ud_id=uuid4())
    first.tc_ids.append(uuid4())

    first_public = StudentPublic(
        id=uuid4(),
        name="first",
        identifier="s-1",
        ud_id=uuid4(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    second_public = StudentPublic(
        id=uuid4(),
        name="second",
        identifier="s-2",
        ud_id=uuid4(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    assert second.tc_ids == []
    assert first_public.tcs is not second_public.tcs
    assert second_public.tcs == []
