"""Deterministic, local ranking helpers for student resource recommendations.

The functions in this module intentionally use no embedding/model dependency:
character n-grams are robust for short Chinese/English mixed titles and make the
cold-start behaviour inspectable in tests.
"""
from __future__ import annotations

import math
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable


BM25_K1 = 1.2
BM25_B = 0.75
EXTERNAL_RELEVANCE_FLOOR = 0.16
EXTERNAL_TITLE_SIMILARITY_FLOOR = 0.08
# Candidate sets are small and the first relevant item is already selected.
# At later positions, make room for another useful modality/topic while the
# relevance-priority guard in ``mmr_order`` protects a clear relevance winner.
MMR_LAMBDA = 0.60


def normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return "".join(character for character in text if character.isalnum())


def char_ngrams(value: object) -> list[str]:
    text = normalize_text(value)
    if len(text) < 2:
        return [text] if text else []
    # Bigrams preserve Chinese concepts (事务、隔离、acid) without relying on a
    # dictionary. Unigrams make short acronym matches possible.
    return [*text, *(text[index : index + 2] for index in range(len(text) - 1))]


def bm25_scores(query: object, documents: Iterable[object]) -> list[float]:
    """Return normalized BM25 scores for a small in-memory candidate set."""
    docs = [char_ngrams(document) for document in documents]
    terms = char_ngrams(query)
    if not docs or not terms:
        return [0.0] * len(docs)
    document_frequency: Counter[str] = Counter()
    for document in docs:
        document_frequency.update(set(document))
    average_length = sum(len(document) for document in docs) / len(docs) or 1.0
    raw_scores: list[float] = []
    for document in docs:
        frequencies = Counter(document)
        score = 0.0
        for term in set(terms):
            frequency = frequencies.get(term, 0)
            if not frequency:
                continue
            idf = math.log(1 + (len(docs) - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
            denominator = frequency + BM25_K1 * (1 - BM25_B + BM25_B * len(document) / average_length)
            score += idf * frequency * (BM25_K1 + 1) / denominator
        raw_scores.append(score)
    maximum = max(raw_scores, default=0.0)
    return [round(score / maximum, 6) if maximum else 0.0 for score in raw_scores]


def lexical_similarity(left: object, right: object) -> float:
    left_terms, right_terms = set(char_ngrams(left)), set(char_ngrams(right))
    if not left_terms or not right_terms:
        return 0.0
    return len(left_terms & right_terms) / len(left_terms | right_terms)


def modality_matches_style(style: str, modality: str) -> bool:
    style = normalize_text(style)
    if any(token in style for token in ("视觉", "图", "动画", "视频")):
        return modality in {"knowledge_graph", "image", "video"}
    if any(token in style for token in ("练习", "实践", "做题")):
        return modality in {"question", "code"}
    if any(token in style for token in ("阅读", "文字", "讲义")):
        return modality == "document"
    return False


@dataclass(frozen=True)
class RecommendationContext:
    weak_points: list[str] = field(default_factory=list)
    practice_gaps: dict[str, float] = field(default_factory=dict)
    mastery_gaps: dict[str, float] = field(default_factory=dict)
    goals: list[str] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)
    kb_topics: list[str] = field(default_factory=list)
    learning_style: str = ""
    preferred_modalities: dict[str, float] = field(default_factory=dict)
    topic_affinity: dict[str, float] = field(default_factory=dict)
    subject_affinity: dict[str, float] = field(default_factory=dict)
    seen_topics: list[str] = field(default_factory=list)
    difficulty: str = ""
    # Explicit catalog-query aliases for a small reviewed course vocabulary.
    # They are not model-generated translations and are used only to evaluate
    # public-catalog titles against the originating profile topic.
    external_topic_aliases: dict[str, str] = field(default_factory=dict)

    @property
    def query_topics(self) -> list[str]:
        values = [*self.weak_points, *self.practice_gaps, *self.mastery_gaps, *self.goals, *self.interests, *self.kb_topics, *self.external_topic_aliases.values()]
        return list(dict.fromkeys(value.strip() for value in values if value and value.strip()))[:12]

    @property
    def query(self) -> str:
        return " ".join(self.query_topics)

    @property
    def concrete_topics(self) -> list[str]:
        """Topics suitable for the external title gate, excluding generic goals."""
        values = [*self.weak_points, *self.practice_gaps, *self.mastery_gaps, *self.kb_topics, *self.interests, *self.external_topic_aliases.values()]
        cores = [_topic_core(value) for value in dict.fromkeys(values)]
        return [value for value in cores if len(value) >= 2]


@dataclass(frozen=True)
class Candidate:
    title: str
    subject: str
    source: str
    knowledge_point: str
    modality: str
    difficulty: str
    origin: str
    # This is set only for records returned by a fixed, reviewed catalog.  It
    # contains the server-selected catalog query, never arbitrary user content.
    trusted_catalog_context: str = ""

    @property
    def external_document(self) -> str:
        # Do not use knowledge_point here: external metadata can be stale or
        # maliciously labelled. Title/subject/source are what the user can see.
        return f"{self.title} {self.subject} {self.source} {self.trusted_catalog_context}"

    @property
    def internal_document(self) -> str:
        return f"{self.title} {self.subject} {self.knowledge_point}"


@dataclass(frozen=True)
class RankedCandidate:
    score: float
    evidence: list[str]
    reason: str
    external_relevant: bool


def _topic_core(value: str) -> str:
    """Remove generic learning/course words before matching an external title."""

    normalized = normalize_text(value)
    for generic in ("数据库", "课程", "学习", "掌握", "复习", "知识", "基础", "目标", "当前"):
        normalized = normalized.replace(generic, "")
    return normalized


def _title_matches_concrete_topic(title: str, context: RecommendationContext) -> bool:
    normalized_title = normalize_text(title)
    title_terms = set(char_ngrams(title))
    for topic in context.concrete_topics:
        if topic in normalized_title:
            return True
        topic_bigrams = {term for term in char_ngrams(topic) if len(term) == 2}
        shared_bigrams = title_terms & topic_bigrams
        # One shared bigram is too weak for a multi-part topic: for example,
        # "事务通知" must not satisfy "事务隔离". Short two-character topics
        # still remain discoverable through the exact-substring branch above.
        required = min(3, max(2, math.ceil(len(topic_bigrams) * 0.5)))
        if (
            len(shared_bigrams) >= required
            and lexical_similarity(topic, title) >= EXTERNAL_TITLE_SIMILARITY_FLOOR
        ):
            return True
    return False


def _topic_similarity(topic: str, searchable: str, context: RecommendationContext) -> float:
    """Compare a profile topic and its reviewed public-catalog alias.

    The alias is used for matching only.  Explanations continue to reference
    the learner's original topic, so a Chinese profile is never replaced by a
    machine-translated label in the UI.
    """
    alias = context.external_topic_aliases.get(topic, "")
    return max(
        lexical_similarity(topic, searchable),
        lexical_similarity(alias, searchable) if alias else 0.0,
    )


def rank_candidates(candidates: list[Candidate], context: RecommendationContext) -> list[RankedCandidate]:
    documents = [candidate.external_document if candidate.origin == "external" else candidate.internal_document for candidate in candidates]
    lexical = bm25_scores(context.query, documents)
    ranked: list[RankedCandidate] = []
    for candidate, lexical_score in zip(candidates, lexical, strict=True):
        evidence: list[tuple[float, str]] = []
        score = 0.08 + 0.52 * lexical_score
        searchable = candidate.external_document if candidate.origin == "external" else candidate.internal_document
        for topic, gap in context.practice_gaps.items():
            if _topic_similarity(topic, searchable, context) >= 0.18:
                amount = 0.18 + min(0.12, max(0.0, gap) * 0.12)
                score += amount
                evidence.append((amount, f"近期练习在“{topic}”正确率偏低"))
                break
        for topic, gap in context.mastery_gaps.items():
            if _topic_similarity(topic, searchable, context) >= 0.18:
                amount = 0.10 + min(0.12, max(0.0, gap) * 0.16)
                score += amount
                evidence.append((amount, f"需要巩固“{topic}”"))
                break
        for topic in context.weak_points:
            if _topic_similarity(topic, searchable, context) >= 0.18:
                score += 0.16
                evidence.append((0.16, f"需要巩固“{topic}”"))
                break
        for goal in context.goals:
            if _topic_similarity(goal, searchable, context) >= 0.14:
                score += 0.11
                evidence.append((0.11, f"贴合当前目标“{goal}”"))
                break
        for topic in context.kb_topics:
            if _topic_similarity(topic, searchable, context) >= 0.16:
                score += 0.07
                evidence.append((0.07, f"关联课程知识库主题“{topic}”"))
                break
        modality_affinity = context.preferred_modalities.get(candidate.modality, 0.0)
        if modality_affinity > 0:
            bonus = min(0.10, modality_affinity * 0.08)
            score += bonus
            evidence.append((bonus, "符合近期偏好的资料形式"))
        elif modality_matches_style(context.learning_style, candidate.modality):
            score += 0.06
            evidence.append((0.06, "符合你的学习形式偏好"))
        topic_affinity = max((
            value
            for topic, value in context.topic_affinity.items()
            if _topic_similarity(topic, searchable, context) >= 0.18
        ), default=0.0)
        score += max(-0.12, min(0.10, topic_affinity * 0.08))
        score += max(-0.08, min(0.06, context.subject_affinity.get(candidate.subject, 0.0) * 0.05))
        # A small novelty prior only breaks near ties: relevance remains the
        # dominant term and previously explored topics are not punished.
        if context.seen_topics and not any(
            _topic_similarity(topic, searchable, context) >= 0.22
            for topic in context.seen_topics
        ):
            score += 0.035
        if context.difficulty and candidate.difficulty == context.difficulty:
            score += 0.04
        external_relevant = candidate.origin != "external" or (
            lexical_score >= EXTERNAL_RELEVANCE_FLOOR
            and _title_matches_concrete_topic(
                f"{candidate.title} {candidate.trusted_catalog_context}", context
            )
        )
        if candidate.origin == "external" and not external_relevant:
            score = 0.0
        # A practice gap, mastery gap and weak-point label can all describe the
        # same concept. Keep the strongest explanation once instead of showing
        # three near-identical reasons to the student.
        strongest: list[str] = []
        explained_topics: set[str] = set()
        for _, text in sorted(evidence, reverse=True):
            quoted_topic = text.split("“", 1)[1].split("”", 1)[0] if "“" in text and "”" in text else ""
            topic_key = normalize_text(quoted_topic)
            if topic_key and topic_key in explained_topics:
                continue
            strongest.append(text)
            if topic_key:
                explained_topics.add(topic_key)
            if len(strongest) == 3:
                break
        reason = "；".join(strongest) if strongest else "根据当前可用学习信息整理，建议先预览判断是否适合"
        ranked.append(RankedCandidate(round(max(0.0, min(0.99, score)), 4), strongest, reason + "。", external_relevant))
    return ranked


def mmr_order(candidates: list[Candidate], ranked: list[RankedCandidate], limit: int) -> list[int]:
    """Relevant-first MMR. A clearly stronger candidate cannot be displaced."""
    remaining = list(range(len(candidates)))
    chosen: list[int] = []
    while remaining and len(chosen) < limit:
        best_index = remaining[0]
        best_value = -1.0
        for index in remaining:
            relevance = ranked[index].score
            redundancy = max((candidate_similarity(candidates[index], candidates[prior]) for prior in chosen), default=0.0)
            value = MMR_LAMBDA * relevance - (1 - MMR_LAMBDA) * redundancy
            # Relevance priority guard prevents diversity from hiding a large
            # relevance gap (e.g. the only truly on-topic item).
            if chosen and relevance >= max(ranked[prior].score for prior in chosen) + 0.18:
                value += 0.25
            if value > best_value or (value == best_value and relevance > ranked[best_index].score):
                best_index, best_value = index, value
        chosen.append(best_index)
        remaining.remove(best_index)
    return chosen


def candidate_similarity(left: Candidate, right: Candidate) -> float:
    """Topic and modality-aware redundancy for small MMR candidate sets."""
    title = lexical_similarity(left.title, right.title)
    topic = lexical_similarity(left.knowledge_point, right.knowledge_point)
    modality = 1.0 if left.modality == right.modality else 0.0
    return round(min(1.0, 0.40 * title + 0.48 * topic + 0.12 * modality), 6)
