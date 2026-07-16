from app.ai.course_agent_registry import (
    get_course_agent_contract,
    list_course_agent_contracts,
)


def test_course_agent_keys_are_unique_and_public_contracts_hide_internal_prompts() -> None:
    contracts = list_course_agent_contracts()
    assert len(contracts) >= 10
    assert len({item.key for item in contracts}) == len(contracts)

    public = [item.public_dict() for item in contracts]
    assert all("instruction" not in item for item in public)
    assert all("worker" not in item and "workerAgent" not in item for item in public)
    assert all("usage" not in item and "accuracy" not in item and "estimate" not in item for item in public)
    assert all(item["starterActions"] for item in public)
    assert all(item["outputs"] for item in public)


def test_specialized_agents_have_bounded_execution_contracts() -> None:
    practice = get_course_agent_contract("practice")
    assert practice is not None
    assert practice.worker_agent == "quiz_master"
    assert practice.allowed_tools == ("knowledge_base",)

    checker = get_course_agent_contract("checker")
    assert checker is not None
    assert checker.worker_agent == "safety_review_agent"
    assert "web_search" not in checker.allowed_tools
    assert "全网查重" in checker.instruction

    resource = get_course_agent_contract("resource")
    assert resource is not None
    assert resource.execution_kind == "resource_workflow"
    assert resource.worker_agent is None


def test_unknown_course_agent_is_rejected_by_registry() -> None:
    assert get_course_agent_contract("arbitrary_frontend_agent") is None


def test_research_practice_and_reader_have_distinct_workers_and_tool_boundaries() -> None:
    expected = {
        "research": ("web_research_agent", {"knowledge_base", "web_search", "search_uploaded_document"}),
        "practice": ("quiz_master", {"knowledge_base"}),
        "reader": ("doc_researcher", {"knowledge_base", "search_uploaded_document"}),
    }
    for key, (worker, tools) in expected.items():
        contract = get_course_agent_contract(key)
        assert contract is not None
        assert contract.execution_kind == "chat"
        assert contract.worker_agent == worker
        assert set(contract.allowed_tools) == tools


def test_reader_agent_keeps_course_retrieval_without_an_uploaded_file() -> None:
    from app.ai.chat_tools import get_tools_for_agent

    course_only = get_tools_for_agent(
        "doc_researcher",
        ["knowledge_base", "search_uploaded_document"],
        current_file_id=None,
    )
    assert [tool.name for tool in course_only] == ["query_knowledge_base"]

    with_attachment = get_tools_for_agent(
        "doc_researcher",
        ["knowledge_base", "search_uploaded_document"],
        current_file_id="file-1",
    )
    assert [tool.name for tool in with_attachment] == [
        "query_knowledge_base",
        "search_uploaded_document",
    ]
