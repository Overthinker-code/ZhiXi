from app.services.student_profile_agent import student_profile_agent


def test_mastery_update_uses_required_history_weight() -> None:
    assert student_profile_agent._update_mastery(0.5, 1) == 0.65
    assert student_profile_agent._update_mastery(0.5, 0) == 0.35


def test_knowledge_graph_exposes_mastery_nodes_and_edges() -> None:
    graph = student_profile_agent._knowledge_graph(
        {"database.transaction": 0.45, "network.tcp": 0.82}
    )
    assert graph["nodes"][0]["id"] == "learner"
    assert any(node["name"] == "transaction" and node["mastery"] == 0.45 for node in graph["nodes"])
    assert any(edge["source"] == "learner" for edge in graph["edges"])
