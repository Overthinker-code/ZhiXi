from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.recommendation_feedback_service import (
    aggregate_feedback,
    dimension_signed_weights,
    feedback_idempotency_key,
)
from app.services.recommendation_ranking_service import (
    Candidate,
    RecommendationContext,
    RankedCandidate,
    candidate_similarity,
    mmr_order,
    rank_candidates,
)


def test_external_metadata_label_cannot_bypass_title_relevance_gate() -> None:
    context = RecommendationContext(weak_points=["数据库事务隔离"])
    candidates = [
        Candidate("Python 入门教程", "编程", "example.edu", "数据库事务隔离", "video", "standard", "external"),
        Candidate("数据库事务隔离级别讲解", "数据库", "example.edu", "任意标签", "video", "standard", "external"),
    ]
    ranked = rank_candidates(candidates, context)
    assert ranked[0].external_relevant is False
    assert ranked[1].external_relevant is True


def test_external_gate_requires_concrete_title_overlap_even_for_single_candidate() -> None:
    context = RecommendationContext(goals=["掌握数据库"], mastery_gaps={"事务隔离": 0.32})
    candidates = [
        Candidate("Python 函数入门", "数据库", "数据库课程站", "事务隔离", "video", "standard", "external"),
        Candidate("事务隔离级别讲解", "数据库", "数据库课程站", "伪造标签", "video", "standard", "external"),
    ]
    ranked = rank_candidates(candidates, context)
    assert ranked[0].external_relevant is False
    assert ranked[1].external_relevant is True
    # A single weak same-subject result can no longer win by batch normalization.
    only_unrelated = rank_candidates([candidates[0]], context)[0]
    assert only_unrelated.external_relevant is False


def test_external_gate_matches_specific_topic_core_not_generic_course_prefix() -> None:
    context = RecommendationContext(weak_points=["数据库事务隔离"])
    ranked = rank_candidates(
        [
            Candidate("数据库入门", "数据库", "课程站", "伪造标签", "video", "standard", "external"),
            Candidate("事务隔离级别详解", "数据库", "课程站", "任意标签", "video", "standard", "external"),
            Candidate("事务通知公告", "数据库", "课程站", "事务隔离", "document", "standard", "external"),
        ],
        context,
    )
    assert [item.external_relevant for item in ranked] == [False, True, False]


def test_reason_uses_only_available_signals_and_practice_gap() -> None:
    context = RecommendationContext(
        practice_gaps={"事务隔离": 0.5}, goals=["完成数据库复习"], preferred_modalities={"video": 1.0}
    )
    detail = rank_candidates(
        [Candidate("事务隔离级别视频", "数据库", "课程站", "", "video", "foundation", "generated")], context
    )[0]
    assert "近期练习" in detail.reason
    assert "近期偏好" in detail.reason
    assert "掌握度" not in detail.reason


def test_reason_does_not_repeat_the_same_topic_from_multiple_profile_signals() -> None:
    context = RecommendationContext(
        practice_gaps={"事务隔离": 0.5},
        mastery_gaps={"事务隔离": 0.3},
        weak_points=["事务隔离"],
        preferred_modalities={"video": 1.0},
    )
    detail = rank_candidates(
        [Candidate("事务隔离级别视频", "数据库", "", "事务隔离", "video", "foundation", "generated")],
        context,
    )[0]
    assert detail.reason.count("事务隔离") == 1
    assert "近期偏好" in detail.reason


def test_mmr_reduces_duplicate_titles_without_hiding_much_higher_relevance() -> None:
    candidates = [
        Candidate("事务隔离级别讲解", "数据库", "", "", "document", "", "generated"),
        Candidate("事务隔离级别讲解练习", "数据库", "", "", "question", "", "generated"),
        Candidate("事务与索引关系图解", "数据库", "", "", "image", "", "generated"),
    ]
    ranked = [
        RankedCandidate(0.90, [], "", True),
        RankedCandidate(0.82, [], "", True),
        RankedCandidate(0.65, [], "", True),
    ]
    order = mmr_order(candidates, ranked, limit=3)
    assert order[0] in {0, 1}
    assert order.index(2) < 2  # diversity interrupts the two near-duplicates


def test_mmr_redundancy_uses_topic_and_modality_not_only_title() -> None:
    candidates = [
        Candidate("隔离级别概览", "数据库", "", "事务隔离", "document", "", "generated"),
        Candidate("并发控制讲解", "数据库", "", "事务隔离", "document", "", "generated"),
        Candidate("动画课程", "数据库", "", "事务隔离", "video", "", "generated"),
    ]
    assert candidate_similarity(candidates[0], candidates[1]) > 0.55
    ranked = [
        RankedCandidate(0.90, [], "", True),
        RankedCandidate(0.83, [], "", True),
        RankedCandidate(0.76, [], "", True),
    ]
    order = mmr_order(candidates, ranked, limit=3)
    assert order[:2] == [0, 2]


def test_signed_feedback_decays_and_keeps_negative_affinity_negative() -> None:
    now = datetime(2026, 7, 16, tzinfo=timezone.utc)
    rows = [
        SimpleNamespace(event_type="resource_favorited", observed_at=now, display_name="事务", payload={"signed_preference_weight": 0.85, "resource_type": "video", "subject": "数据库"}),
        SimpleNamespace(event_type="resource_removed_from_library", observed_at=now - timedelta(days=42), display_name="事务", payload={"signed_preference_weight": -0.70, "resource_type": "document", "subject": "数据库"}),
    ]
    result = aggregate_feedback(rows, now=now)
    assert result["modalities"]["video"]["affinity"] > 0
    # Two half lives makes this less negative than its original -0.70.
    assert -0.2 < result["modalities"]["document"]["affinity"] < 0
    assert result["modalities"]["video"]["positive_weight"] > 0
    assert result["modalities"]["document"]["negative_weight"] > 0
    assert result["modalities"]["video"]["sample_count"] == 1


def test_feedback_handles_naive_and_aware_timestamps() -> None:
    now = datetime(2026, 7, 16, tzinfo=timezone.utc)
    result = aggregate_feedback([
        SimpleNamespace(event_type="resource_favorited", observed_at=datetime(2026, 7, 15), display_name="事务", payload={"signed_preference_weight": 0.85, "resource_type": "video"}),
        SimpleNamespace(event_type="recommendation_dismissed", observed_at=now, display_name="索引", payload={"signed_preference_weight": -0.8, "resource_type": "document"}),
    ], now=now)
    assert result["modalities"]["video"]["affinity"] > 0
    assert result["modalities"]["document"]["affinity"] < 0


def test_feedback_idempotency_key_fits_database_and_is_window_stable() -> None:
    observed = datetime(2026, 7, 16, 12, 5, tzinfo=timezone.utc)
    first = feedback_idempotency_key("resource-id", "resource_previewed", observed)
    repeated = feedback_idempotency_key(
        "resource-id", "resource_previewed", observed + timedelta(minutes=5)
    )
    assert len(first) == 64
    assert first == repeated


def test_feedback_audit_affinity_equals_bounded_positive_minus_negative() -> None:
    now = datetime(2026, 7, 16, tzinfo=timezone.utc)
    rows = [
        SimpleNamespace(
            event_type="resource_favorited",
            observed_at=now,
            display_name="事务",
            payload={"signed_preference_weight": 2.0, "resource_type": "video"},
        ),
        SimpleNamespace(
            event_type="resource_unfavorited",
            observed_at=now,
            display_name="事务",
            payload={"signed_preference_weight": -0.5, "resource_type": "video"},
        ),
    ]
    bucket = aggregate_feedback(rows, now=now)["modalities"]["video"]
    assert bucket["affinity"] == round(
        bucket["positive_weight"] - bucket["negative_weight"], 4
    )


def test_feedback_affinity_explains_next_round_modality_ranking() -> None:
    candidates = [
        Candidate("事务隔离视频讲解", "数据库", "", "事务隔离", "video", "foundation", "generated"),
        Candidate("事务隔离文字讲解", "数据库", "", "事务隔离", "document", "foundation", "generated"),
    ]
    context = RecommendationContext(weak_points=["事务隔离"], preferred_modalities={"video": 1.5})
    ranked = rank_candidates(candidates, context)
    assert ranked[0].score > ranked[1].score
    assert "近期偏好" in ranked[0].reason


def test_regeneration_keeps_topic_interest_but_reduces_modality_affinity() -> None:
    weights = dimension_signed_weights("generated_resource_regenerated")
    assert weights["topics"] > 0
    assert weights["modalities"] < 0
    assert abs(weights["subjects"]) < abs(weights["topics"])


def test_mastery_gap_changes_same_topic_ranking_without_exposing_value() -> None:
    context = RecommendationContext(mastery_gaps={"事务隔离": 0.35})
    candidates = [
        Candidate("事务隔离讲解", "数据库", "", "事务隔离", "document", "foundation", "generated"),
        Candidate("索引讲解", "数据库", "", "索引", "document", "foundation", "generated"),
    ]
    ranked = rank_candidates(candidates, context)
    assert ranked[0].score > ranked[1].score
    assert "需要巩固“事务隔离”" in ranked[0].reason
    assert "0.35" not in ranked[0].reason
