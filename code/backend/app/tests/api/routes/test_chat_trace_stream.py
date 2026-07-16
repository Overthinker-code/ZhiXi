import json

from fastapi.testclient import TestClient

from app.core.config import settings


def _data_events(body: str) -> list[dict]:
    return [
        json.loads(line.removeprefix("data: "))
        for line in body.splitlines()
        if line.startswith("data: ")
    ]


def test_legacy_chat_stream_emits_safe_auditable_trace(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/chat/stream",
        headers=normal_user_token_headers,
        json={
            "user_input": "解释数据库事务",
            "thread_id": "trace-contract-test",
            "force_cache": True,
            "reasoning_enabled": True,
        },
    )
    assert response.status_code == 200
    events = _data_events(response.text)
    types = [event.get("type") for event in events]
    assert types[0] == "run_started"
    assert "phase_started" in types
    assert "phase_finished" in types
    assert "token" in types
    assert "final" in types
    assert types[-1] == "run_finished"

    sequences = [int(event["sequence"]) for event in events]
    assert sequences == sorted(sequences)
    assert len(sequences) == len(set(sequences))
    assert all(event["traceVersion"] == "1.0" for event in events)
    assert all(event["runId"] == events[0]["runId"] for event in events)
    assert all(event.get("type") not in {"reasoning_token", "thought"} for event in events)
    assert all("<think>" not in json.dumps(event, ensure_ascii=False) for event in events)
    token_events = [event for event in events if event.get("type") == "token"]
    assert token_events and all(event.get("streamingMode") == "replayed" for event in token_events)
