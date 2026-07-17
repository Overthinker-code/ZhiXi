import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session, select

from app.api.v1.endpoints.ai_chat import (
    CourseContext,
    _is_quiz_generation_intent,
    _prior_owned_resource_package_context,
    _quiz_context,
)
from app.db.base_class import Base
from app.models import (
    CourseKnowledgeNode,
    LearningEvidence,
    LearningPath,
    PracticeRecord,
    Question,
    QuizAttempt,
    Resource,
    WrongQuestion,
)
from app.models.user import User  # noqa: F401
from app.models.chat import Chat
from app.models.chat_artifact import ChatArtifact
from app.models.chat_thread import ChatThread
from app.models.user_memory_profile import UserMemoryProfile
from app.schemas.quiz import QuizDraft
from app.services.chat_model_factory import ChatModelFactory
from app.services.quiz_service import QuizGenerationError, quiz_service


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    Base.metadata.create_all(engine)
    return Session(engine)


def test_chat_quiz_intent_extracts_topic_count_and_difficulty() -> None:
    assert _is_quiz_generation_intent("给我出10道数据库事务练习题")
    assert _quiz_context("给我出10道数据库事务练习题") == ("数据库", "事务", 10, "standard")
    assert _quiz_context("生成5道TCP拥塞控制基础练习题") == (
        "计算机网络",
        "拥塞控制",
        5,
        "foundation",
    )
    assert not _is_quiz_generation_intent("解释数据库事务")
    request = "帮我生成一套计算机组成原理的期末题目，生成word，保存在我的资料中心"
    assert _is_quiz_generation_intent(request)
    assert _quiz_context(request) == ("计算机组成原理", "期末综合", 10, "standard")


def test_quiz_context_prefers_trusted_course_and_latest_owned_user_topic_for_follow_up() -> None:
    course, topic, count, difficulty = _quiz_context(
        "基于上一轮问答，围绕“生成一份数据库图谱”生成一组针对性练习题",
        course_context=CourseContext(
            courseId="c1111111-1111-4111-9111-111111111101",
            chapterId="ch4",
        ),
        prior_user_messages=["请围绕数据库范式与 BCNF 生成一份数据库图谱"],
    )

    assert (course, topic, count, difficulty) == ("数据库系统原理", "范式与BCNF", 10, "standard")


def test_quiz_context_finds_known_course_tokens_anywhere_without_prior_turns() -> None:
    course, _topic, count, difficulty = _quiz_context("请围绕关系代数为数据库生成 6 道进阶练习题")

    assert (course, count, difficulty) == ("数据库", 6, "challenge")


def test_quiz_context_uses_owned_generated_package_when_prior_user_request_is_generic() -> None:
    db = _session()
    user_id = uuid4()
    thread = ChatThread(thread_id="owned-thread", title="数据库学习", user_id=str(user_id))
    db.add(thread)
    db.flush()
    chat = Chat(thread_id=thread.thread_id, user_input="生成一份数据库图谱", response="通用回复")
    db.add(chat)
    db.flush()
    db.add(
        ChatArtifact(
            chat_id=chat.id,
            metrics_json=json.dumps(
                {
                    "resourcePackage": {
                        "title": "数据库知识图谱",
                        "artifacts": [
                            {
                                "kind": "knowledge_graph",
                                "course": "数据库系统原理",
                                "knowledge_point": "范式与 BCNF",
                                "title": "范式与 BCNF 知识图谱",
                            }
                        ],
                    }
                },
                ensure_ascii=False,
            ),
        )
    )
    db.commit()

    package = _prior_owned_resource_package_context(db, thread.thread_id, str(user_id))
    context = _quiz_context(
        "基于上一轮问答生成一组针对性练习题",
        course_context=CourseContext(courseId="c1111111-1111-4111-9111-111111111101"),
        prior_user_messages=["生成一份数据库图谱"],
        prior_resource_package=package,
    )

    assert package == {"knowledge_point": "范式与 BCNF", "course": "数据库系统原理", "title": "范式与 BCNF 知识图谱"}
    assert context == ("数据库系统原理", "范式与 BCNF", 10, "standard")


def test_normal_form_hierarchy_stem_is_repaired_only_when_key_is_unique_highest() -> None:
    draft = QuizDraft.model_validate(
        {
            "title": "范式层次练习",
            "questions": [
                {
                    "knowledge_point": "范式级别",
                    "content": "设关系模式 R 已满足题设条件，下列说法正确的是？",
                    "options": [
                        {"key": "A", "text": "R 属于 1NF"},
                        {"key": "B", "text": "R 属于 2NF"},
                        {"key": "C", "text": "R 属于 3NF"},
                        {"key": "D", "text": "R 属于 BCNF"},
                    ],
                    "answer": "D",
                    "analysis": "题设条件满足 BCNF，因此其也是最高满足的范式。",
                }
            ],
        }
    )

    quiz_service._repair_safe_normal_form_hierarchy_stems(draft)

    assert "最高满足的范式" in draft.questions[0].content
    quiz_service._validate_quiz_quality(draft)


def test_normal_form_hierarchy_repair_keeps_ambiguous_ladder_fail_closed() -> None:
    draft = QuizDraft.model_validate(
        {
            "title": "范式层次练习",
            "questions": [
                {
                    "knowledge_point": "范式级别",
                    "content": "设关系模式 R 已满足题设条件，下列说法正确的是？",
                    "options": [
                        {"key": "A", "text": "R 属于 1NF"},
                        {"key": "B", "text": "R 属于 2NF"},
                        {"key": "C", "text": "R 属于 3NF"},
                        {"key": "D", "text": "R 属于 BCNF"},
                    ],
                    "answer": "C",
                    "analysis": "题设条件满足第三范式。",
                }
            ],
        }
    )

    quiz_service._repair_safe_normal_form_hierarchy_stems(draft)

    assert "最高满足的范式" not in draft.questions[0].content
    with pytest.raises(ValueError, match="可同时为真"):
        quiz_service._validate_quiz_quality(draft)


def test_quiz_payload_normalizes_common_model_field_variants() -> None:
    payload = {
        "questions": [
            {
                "question": "CPU 执行一条指令通常需要哪些阶段？",
                "options": {"A": "取指、译码、执行", "B": "只取指", "C": "只访存", "D": "只写回"},
                "answer": "A",
                "explanation": "指令周期通常包含取指、译码和执行等阶段。",
                "topic": "CPU 指令周期",
            },
            {
                "stem": "Cache 的主要作用是什么？",
                "choices": ["提高访存速度", "增大指令长度", "替代CPU", "关闭主存"],
                "correct_answer": "A",
                "rationale": "Cache 缓解 CPU 与主存速度差异。",
            },
            {
                "content": "总线仲裁解决什么问题？",
                "options": [
                    {"label": "A", "content": "多个设备竞争总线使用权"},
                    {"label": "B", "content": "文件命名"},
                    {"label": "C", "content": "程序编译"},
                    {"label": "D", "content": "页面布局"},
                ],
                "answer": "A",
                "analysis": "总线仲裁决定竞争设备的使用次序。",
            },
        ]
    }
    draft = quiz_service._normalize_draft_payload(
        payload,
        course="计算机组成原理",
        knowledge_point="期末综合",
        difficulty="standard",
        count=3,
    )
    quiz_service._validate_topic_alignment(draft, course="计算机组成原理")
    assert draft.title == "计算机组成原理期末综合专项练习"
    assert draft.questions[0].content.startswith("CPU")
    assert draft.questions[0].options[0].key == "A"
    assert draft.questions[1].options[0].text == "提高访存速度"


def test_normalize_draft_removes_duplicated_course_prefix_from_title() -> None:
    payload = {
        "title": "数据库数据库专项练习",
        "questions": [
            {
                "content": "数据库事务的原子性表示什么？",
                "options": {
                    "A": "事务中的操作全部成功或全部回滚",
                    "B": "事务提交后数据永久保存",
                },
                "answer": "A",
                "analysis": "原子性要求事务不可分割，故选 A。",
            }
        ],
    }

    draft = quiz_service._normalize_draft_payload(
        payload,
        course="数据库",
        knowledge_point="数据库",
        difficulty="standard",
        count=1,
    )

    assert draft.title == "数据库专项练习"


@pytest.mark.parametrize(
    ("analysis", "expected_message"),
    [
        ("正确答案：A。但综上，正确答案是 B。", "与答案键 A 冲突"),
        ("题目不恰当，需要重新检查题干后才能回答。", "否定了题目有效性"),
        ("根据现有条件无法确定正确答案。", "否定了题目有效性"),
    ],
)
def test_quiz_quality_guard_rejects_conflicting_or_self_negating_analysis(
    analysis: str, expected_message: str
) -> None:
    draft = QuizDraft.model_validate(
        {
            "title": "ACID 练习",
            "questions": [
                {
                    "knowledge_point": "ACID",
                    "content": "事务原子性的含义是什么？",
                    "options": [
                        {"key": "A", "text": "全部成功或全部失败"},
                        {"key": "B", "text": "允许一部分操作独立提交"},
                    ],
                    "answer": "A",
                    "analysis": analysis,
                }
            ],
        }
    )

    with pytest.raises(ValueError, match=expected_message):
        quiz_service._validate_quiz_quality(draft)


def test_quiz_quality_guard_allows_explaining_why_a_distractor_is_wrong() -> None:
    draft = QuizDraft.model_validate(
        {
            "title": "ACID 练习",
            "questions": [
                {
                    "knowledge_point": "ACID",
                    "content": "事务原子性的含义是什么？",
                    "options": [
                        {"key": "A", "text": "全部成功或全部失败"},
                        {"key": "B", "text": "允许一部分操作独立提交"},
                    ],
                    "answer": "A",
                    "analysis": "A 项正确；B 选项不正确，因为原子性不允许部分提交。",
                }
            ],
        }
    )

    quiz_service._validate_quiz_quality(draft)


@pytest.mark.parametrize(
    ("second_question", "expected_message"),
    [
        (
            {
                "knowledge_point": "ACID",
                "content": "事务原子性的含义是什么。",
                "options": [
                    {"key": "A", "text": "将事务视为不可分割单元"},
                    {"key": "B", "text": "只要保证查询速度"},
                ],
                "answer": "A",
                "analysis": "原子性要求事务的操作整体成功或整体回滚。",
            },
            "题干重复",
        ),
        (
            {
                "knowledge_point": "一致性",
                "content": "事务一致性关注什么？",
                "options": [
                    {"key": "A", "text": "数据从一个有效状态转到另一个有效状态"},
                    {"key": "B", "text": "数据从一个有效状态转到另一个有效状态！"},
                ],
                "answer": "A",
                "analysis": "一致性要求事务前后都满足数据约束。",
            },
            "选项内容",
        ),
    ],
)
def test_quiz_quality_guard_rejects_duplicate_stems_and_options(
    second_question: dict, expected_message: str
) -> None:
    draft = QuizDraft.model_validate(
        {
            "title": "ACID 练习",
            "questions": [
                {
                    "knowledge_point": "ACID",
                    "content": "事务原子性的含义是什么？",
                    "options": [
                        {"key": "A", "text": "全部成功或全部失败"},
                        {"key": "B", "text": "允许部分提交"},
                    ],
                    "answer": "A",
                    "analysis": "原子性将事务视为不可分割的工作单元。",
                },
                second_question,
            ],
        }
    )

    with pytest.raises(ValueError, match=expected_message):
        quiz_service._validate_quiz_quality(draft)


def test_quiz_quality_guard_rejects_equivalent_subset_and_universal_options() -> None:
    draft = QuizDraft.model_validate(
        {
            "title": "范式练习",
            "questions": [
                {
                    "knowledge_point": "BCNF",
                    "content": "关于 BCNF 与 3NF 的关系，下列说法正确的是？",
                    "options": [
                        {"key": "A", "text": "BCNF 与 3NF 完全无关"},
                        {"key": "B", "text": "任何满足 BCNF 的关系模式都满足 3NF"},
                        {"key": "C", "text": "3NF 是 BCNF 的子集"},
                        {"key": "D", "text": "BCNF 是 3NF 的子集"},
                    ],
                    "answer": "B",
                    "analysis": "满足 BCNF 的关系模式也满足 3NF。",
                }
            ],
        }
    )

    with pytest.raises(ValueError, match=r"选项 D 与 B 语义等价"):
        quiz_service._validate_quiz_quality(draft)


def test_implication_normalizer_preserves_direction_and_negation() -> None:
    assert quiz_service._canonical_implication("BCNF 是 3NF 的子集") == ("BCNF", "3NF")
    assert quiz_service._canonical_implication("任何满足 BCNF 的关系模式都满足 3NF") == (
        "BCNF",
        "3NF",
    )
    assert quiz_service._canonical_implication("3NF 是 BCNF 的子集") == ("3NF", "BCNF")
    assert quiz_service._canonical_implication("BCNF 不是 3NF 的子集") is None


def test_quiz_quality_guard_rejects_bcnf_dependency_preservation_overclaim() -> None:
    draft = QuizDraft.model_validate(
        {
            "title": "BCNF 分解练习",
            "questions": [
                {
                    "knowledge_point": "BCNF 分解",
                    "content": "关于 BCNF 分解，下列说法正确的是？",
                    "options": [
                        {"key": "A", "text": "必须同时保证无损连接并保持所有函数依赖"},
                        {"key": "B", "text": "可以通过分解消除特定异常"},
                    ],
                    "answer": "A",
                    "analysis": "BCNF 分解总能保证无损连接和函数依赖保持。",
                }
            ],
        }
    )

    with pytest.raises(ValueError, match="BCNF 分解错写为必然保持函数依赖"):
        quiz_service._validate_quiz_quality(draft)


def test_quiz_quality_guard_accepts_qualified_bcnf_dependency_statement() -> None:
    draft = QuizDraft.model_validate(
        {
            "title": "BCNF 分解练习",
            "questions": [
                {
                    "knowledge_point": "BCNF 分解",
                    "content": "关于 BCNF 分解，下列说法正确的是？",
                    "options": [
                        {"key": "A", "text": "可以做到无损连接，但不一定保持全部函数依赖"},
                        {"key": "B", "text": "BCNF 分解必须保持所有函数依赖"},
                    ],
                    "answer": "A",
                    "analysis": "BCNF 分解可以保证无损连接，但不一定保持函数依赖。",
                }
            ],
        }
    )

    quiz_service._validate_quiz_quality(draft)


def test_quiz_quality_guard_rejects_original_2nf_equivalent_options() -> None:
    draft = QuizDraft.model_validate(
        {
            "title": "2NF 定义练习",
            "questions": [
                {
                    "knowledge_point": "2NF",
                    "content": "一个关系模式 R 属于第二范式（2NF），当且仅当它满足什么条件？",
                    "options": [
                        {"key": "A", "text": "R 属于 1NF，且每个非主属性都完全函数依赖于候选键"},
                        {"key": "B", "text": "R 属于 1NF，且不存在非主属性对候选键的部分函数依赖"},
                        {"key": "C", "text": "R 属于 1NF，且不存在非主属性对候选键的传递函数依赖"},
                        {"key": "D", "text": "R 属于 1NF，且每个属性都是不可分的原子值"},
                    ],
                    "answer": "B",
                    "analysis": "完全函数依赖等价于不存在部分函数依赖。",
                }
            ],
        }
    )

    with pytest.raises(ValueError, match=r"选项 B 与 A 对 2NF 定义语义等价"):
        quiz_service._validate_quiz_quality(draft)


def test_quiz_quality_guard_rejects_original_3nf_equivalent_options() -> None:
    draft = QuizDraft.model_validate(
        {
            "title": "3NF 定义练习",
            "questions": [
                {
                    "knowledge_point": "3NF",
                    "content": "关系模式 R 属于第三范式（3NF）的充分必要条件是？",
                    "options": [
                        {"key": "A", "text": "R 中不存在非主属性对候选键的部分函数依赖和传递函数依赖"},
                        {"key": "B", "text": "R 中每个非主属性都完全且直接函数依赖于候选键"},
                        {"key": "C", "text": "R 中不存在非主属性对候选键的传递函数依赖"},
                        {"key": "D", "text": "R 中每个属性都不传递依赖于候选键"},
                    ],
                    "answer": "A",
                    "analysis": "3NF 排除非主属性对候选键的部分和传递依赖。",
                }
            ],
        }
    )

    with pytest.raises(ValueError, match=r"选项 B 与 A 对 3NF 定义语义等价"):
        quiz_service._validate_quiz_quality(draft)


def test_quiz_quality_guard_rejects_original_bcnf_candidate_key_overclaim() -> None:
    draft = QuizDraft.model_validate(
        {
            "title": "BCNF 定义练习",
            "questions": [
                {
                    "knowledge_point": "BCNF",
                    "content": "关于 BCNF（Boyce-Codd 范式），下列描述正确的是？",
                    "options": [
                        {"key": "A", "text": "若关系模式 R 属于 BCNF，则 R 中每个非平凡函数依赖的决定因素都是候选键"},
                        {"key": "B", "text": "若关系模式 R 属于 BCNF，则 R 中不存在任何函数依赖"},
                        {"key": "C", "text": "若关系模式 R 属于 BCNF，则 R 中所有属性都是主属性"},
                        {"key": "D", "text": "若关系模式 R 属于 BCNF，则 R 必然属于 2NF，但不一定属于 3NF"},
                    ],
                    "answer": "A",
                    "analysis": "BCNF 要求任意非平凡函数依赖的决定因素是候选键或超键。",
                }
            ],
        }
    )

    with pytest.raises(ValueError, match="错写为候选键；应为超键或包含候选键"):
        quiz_service._validate_quiz_quality(draft)


@pytest.mark.parametrize(
    "definition",
    [
        "BCNF 中每个非平凡函数依赖的决定因素都是超键",
        "BCNF 中每个非平凡函数依赖的决定因素都包含某个候选键",
    ],
)
def test_quiz_quality_guard_accepts_correct_bcnf_definition(definition: str) -> None:
    draft = QuizDraft.model_validate(
        {
            "title": "BCNF 定义练习",
            "questions": [
                {
                    "knowledge_point": "BCNF",
                    "content": "BCNF 定义中对决定因素的要求是？",
                    "options": [
                        {"key": "A", "text": definition},
                        {"key": "B", "text": "BCNF 中不存在函数依赖"},
                    ],
                    "answer": "A",
                    "analysis": "超键等价于包含至少一个候选键的属性集。",
                }
            ],
        }
    )

    quiz_service._validate_quiz_quality(draft)


def test_bcnf_candidate_key_overclaim_is_allowed_only_as_a_distractor() -> None:
    draft = QuizDraft.model_validate(
        {
            "title": "BCNF 辨析练习",
            "questions": [
                {
                    "knowledge_point": "BCNF",
                    "content": "关于 BCNF，下列说法正确的是？",
                    "options": [
                        {"key": "A", "text": "每个非平凡函数依赖的决定因素都是候选键"},
                        {"key": "B", "text": "满足 BCNF 的关系模式也满足 3NF"},
                    ],
                    "answer": "B",
                    "analysis": "BCNF 是比 3NF 更强的范式；A 项把超键错写成了候选键。",
                }
            ],
        }
    )

    quiz_service._validate_quiz_quality(draft)


@pytest.mark.parametrize(
    "question_payload",
    [
        {
            "knowledge_point": "范式级别",
            "content": "关系模式 R(A, B, C, D)，函数依赖集 F = {A→B, B→C, C→D}。R 的候选键是 A。关于 R 的范式级别，下列说法正确的是？",
            "options": [
                {"key": "A", "text": "R 属于 2NF，但不属于 3NF"},
                {"key": "B", "text": "R 属于 3NF，但不属于 BCNF"},
                {"key": "C", "text": "R 属于 BCNF"},
                {"key": "D", "text": "R 属于 1NF"},
            ],
            "answer": "A",
            "analysis": "R 的最高范式是 2NF。",
        },
        {
            "knowledge_point": "范式级别",
            "content": "关系模式 R(A, B, C, D)，函数依赖集 F = {A→B, B→C, C→D, D→A}。关于 R 的范式级别，下列说法正确的是？",
            "options": [
                {"key": "A", "text": "R 属于 3NF，但不属于 BCNF"},
                {"key": "B", "text": "R 属于 BCNF"},
                {"key": "C", "text": "R 属于 2NF，但不属于 3NF"},
                {"key": "D", "text": "R 属于 1NF"},
            ],
            "answer": "B",
            "analysis": "R 的最高范式是 BCNF。",
        },
    ],
)
def test_quiz_quality_guard_rejects_original_overlapping_normal_form_levels(
    question_payload: dict,
) -> None:
    draft = QuizDraft.model_validate({"title": "范式级别练习", "questions": [question_payload]})

    with pytest.raises(ValueError, match=r"范式层次选项 .* 可同时为真；题干需明确询问最高范式"):
        quiz_service._validate_quiz_quality(draft)


def test_quiz_quality_guard_accepts_exclusive_normal_form_options_without_highest_wording() -> None:
    draft = QuizDraft.model_validate(
        {
            "title": "范式级别练习",
            "questions": [
                {
                    "knowledge_point": "范式级别",
                    "content": "关系模式 R 的范式级别，下列说法正确的是？",
                    "options": [
                        {"key": "A", "text": "R 属于 1NF，但不属于 2NF"},
                        {"key": "B", "text": "R 属于 2NF，但不属于 3NF"},
                        {"key": "C", "text": "R 属于 3NF，但不属于 BCNF"},
                        {"key": "D", "text": "R 属于 BCNF"},
                    ],
                    "answer": "B",
                    "analysis": "四个选项分别限定了互斥的最高范式区间。",
                }
            ],
        }
    )

    quiz_service._validate_quiz_quality(draft)


def test_quiz_quality_guard_accepts_highest_normal_form_stem_with_nested_membership_options() -> None:
    draft = QuizDraft.model_validate(
        {
            "title": "最高范式练习",
            "questions": [
                {
                    "knowledge_point": "范式级别",
                    "content": "关系模式 R 最高满足哪个范式？",
                    "options": [
                        {"key": "A", "text": "R 属于 1NF"},
                        {"key": "B", "text": "R 属于 2NF"},
                        {"key": "C", "text": "R 属于 3NF"},
                        {"key": "D", "text": "R 属于 BCNF"},
                    ],
                    "answer": "C",
                    "analysis": "题干询问最高范式，因此选项按最高级别排他。",
                }
            ],
        }
    )

    quiz_service._validate_quiz_quality(draft)


def test_quiz_quality_guard_rejects_original_two_true_bcnf_decomposition_properties() -> None:
    draft = QuizDraft.model_validate(
        {
            "title": "BCNF 分解练习",
            "questions": [
                {
                    "knowledge_point": "BCNF 分解",
                    "content": "将一个关系模式 R 分解为多个 BCNF 子模式，下列关于该分解过程的说法，正确的是？",
                    "options": [
                        {"key": "A", "text": "分解一定能保持所有函数依赖"},
                        {"key": "B", "text": "分解一定是无损连接的"},
                        {"key": "C", "text": "分解一定既无损连接又保持函数依赖"},
                        {"key": "D", "text": "分解可能丢失某些函数依赖"},
                    ],
                    "answer": "D",
                    "analysis": "BCNF 分解保证无损连接，但可能无法保持某些函数依赖。",
                }
            ],
        }
    )

    with pytest.raises(ValueError, match=r"选项 B 与 D 均为 BCNF 分解的真性质"):
        quiz_service._validate_quiz_quality(draft)


def test_quiz_quality_guard_accepts_single_bcnf_decomposition_property() -> None:
    draft = QuizDraft.model_validate(
        {
            "title": "BCNF 分解练习",
            "questions": [
                {
                    "knowledge_point": "BCNF 分解",
                    "content": "按照标准 BCNF 分解算法，下列哪项性质可以保证？",
                    "options": [
                        {"key": "A", "text": "保证无损连接"},
                        {"key": "B", "text": "保证保持所有函数依赖"},
                    ],
                    "answer": "A",
                    "analysis": "标准 BCNF 分解算法保证无损连接，但不保证依赖保持。",
                }
            ],
        }
    )

    quiz_service._validate_quiz_quality(draft)


def test_curated_database_normal_form_bank_has_exact_scope() -> None:
    assert quiz_service._supports_curated_quiz_bank(
        course="数据库系统",
        knowledge_point="范式与 BCNF",
    )
    assert quiz_service._supports_curated_quiz_bank(
        course="高级数据库原理",
        knowledge_point="BCNF 分解",
    )
    assert not quiz_service._supports_curated_quiz_bank(
        course="数据库系统",
        knowledge_point="事务 ACID",
    )
    assert not quiz_service._supports_curated_quiz_bank(
        course="计算机网络",
        knowledge_point="BCNF",
    )


def test_curated_bank_signature_expected_answers_and_each_question_quality() -> None:
    bank = quiz_service._read_curated_quiz_bank()
    assert bank["questions_sha256"] == quiz_service._CURATED_BANK_SHA256
    assert bank["bank_id"] == "database_systems.normal_forms.verified.v1"
    assert len(bank["questions"]) == 10
    assert [item["answer"] for item in bank["questions"]] == [
        "B", "B", "A", "A", "A", "A", "A", "A", "A", "B"
    ]

    draft = quiz_service._load_curated_quiz_fallback(
        course="数据库系统",
        knowledge_point="范式与 BCNF",
        count=10,
        difficulty="standard",
    )
    assert draft is not None
    assert len(draft.questions) == 10
    for question in draft.questions:
        single_question = QuizDraft(title=draft.title, questions=[question])
        quiz_service._validate_quiz_quality(single_question)
        option_keys = {option.key for option in question.options}
        assert question.answer in option_keys


def test_two_llm_failures_use_six_curated_questions_and_record_origin(
    monkeypatch, tmp_path: Path
) -> None:
    db = _session()
    generation_calls = 0

    class BrokenGenerationModel:
        def invoke(self, _messages):
            nonlocal generation_calls
            generation_calls += 1
            return SimpleNamespace(content="not valid json")

    model = BrokenGenerationModel()
    monkeypatch.setattr(ChatModelFactory, "create", lambda **_: model)

    def write_word_file(**_) -> Path:
        target = tmp_path / "curated-normal-forms.docx"
        target.write_bytes(b"curated-docx")
        return target

    monkeypatch.setattr(quiz_service, "_write_word_file", write_word_file)

    quiz = quiz_service.generate(
        db,
        owner_id=uuid4(),
        course="数据库系统",
        knowledge_point="范式与 BCNF",
        count=6,
        difficulty="standard",
    )

    assert generation_calls == 2
    assert quiz.title == "数据库系统范式与 BCNF 专项练习"
    assert len(quiz.questions) == 6
    resource = db.exec(select(Resource)).one()
    assert resource.content["quality_origin"] == "curated_course_bank"
    assert resource.content["quality_bank_id"] == "database_systems.normal_forms.verified.v1"
    assert resource.content["quality_bank_version"] == "1.0.0"
    assert resource.content["quality_bank_sha256"] == quiz_service._CURATED_BANK_SHA256
    assert resource.content["quality_gate"] == "curated_signature_and_deterministic_rules"


@pytest.mark.parametrize(
    ("course", "knowledge_point"),
    [
        ("数据库系统", "事务 ACID"),
        ("计算机网络", "BCNF"),
    ],
)
def test_unsupported_scope_remains_fail_closed_without_curated_fallback(
    monkeypatch, course: str, knowledge_point: str
) -> None:
    generation_calls = 0

    class BrokenGenerationModel:
        def invoke(self, _messages):
            nonlocal generation_calls
            generation_calls += 1
            return SimpleNamespace(content="not valid json")

    monkeypatch.setattr(ChatModelFactory, "create", lambda **_: BrokenGenerationModel())

    with pytest.raises(QuizGenerationError, match="结构化题目生成失败"):
        quiz_service._generate_with_llm(
            course=course,
            knowledge_point=knowledge_point,
            count=6,
            difficulty="standard",
        )

    assert generation_calls == 2


def test_targeted_repair_replaces_only_the_deterministically_failing_question(monkeypatch) -> None:
    original_second = {
        "knowledge_point": "范式级别",
        "content": "数据库关系模式满足题设条件，下列说法正确的是？",
        "options": [
            {"key": "A", "text": "R 属于 1NF"},
            {"key": "B", "text": "R 属于 2NF"},
            {"key": "C", "text": "R 属于 3NF"},
            {"key": "D", "text": "R 属于 BCNF"},
        ],
        "answer": "C",
        "analysis": "题设条件满足第三范式。",
    }
    source = {
        "title": "数据库专项练习",
        "questions": [
            {
                "knowledge_point": "事务",
                "content": "数据库事务原子性表示什么？",
                "options": {"A": "整体成功或回滚", "B": "允许部分提交"},
                "answer": "A",
                "analysis": "原子性要求事务整体成功或整体回滚，因此答案为 A。",
            },
            original_second,
        ],
    }
    replacement = {
        "knowledge_point": "范式级别",
        "content": "数据库关系模式满足题设条件，其最高满足的范式是？",
        "options": {"A": "3NF", "B": "BCNF"},
        "answer": "A",
        "analysis": "题设仅能推出 3NF，不能推出 BCNF，因此选择 A。",
        "difficulty": "standard",
    }
    calls = {"generation": 0, "targeted": 0, "review": 0}

    class Model:
        def __init__(self, kind: str):
            self.kind = kind

        def invoke(self, _messages):
            calls[self.kind] += 1
            if self.kind == "generation":
                return SimpleNamespace(content=json.dumps(source, ensure_ascii=False))
            if self.kind == "targeted":
                return SimpleNamespace(content=json.dumps(replacement, ensure_ascii=False))
            return SimpleNamespace(
                content=json.dumps(
                    {
                        "reviewed_question_count": 2,
                        "questions": [
                            {"question_index": 1, "verdict": "pass", "correct_option_keys": ["A"], "issues": []},
                            {"question_index": 2, "verdict": "pass", "correct_option_keys": ["A"], "issues": []},
                        ],
                        "issues": [],
                    },
                    ensure_ascii=False,
                )
            )

    def create_model(**kwargs):
        if kwargs.get("max_tokens") == quiz_service._TARGETED_REPAIR_MAX_TOKENS:
            return Model("targeted")
        if kwargs.get("temperature") == 0.0:
            return Model("review")
        return Model("generation")

    monkeypatch.setattr(ChatModelFactory, "create", create_model)

    draft = quiz_service._generate_with_llm(
        course="数据库", knowledge_point="范式", count=2, difficulty="standard"
    )

    assert calls == {"generation": 1, "targeted": 1, "review": 1}
    assert draft.questions[0].content == source["questions"][0]["content"]
    assert draft.questions[1].content == replacement["content"]


def test_targeted_repair_rejects_unparseable_or_incomplete_replacement(monkeypatch) -> None:
    draft = QuizDraft.model_validate(
        {
            "title": "数据库专项练习",
            "questions": [
                {
                    "knowledge_point": "范式级别",
                    "content": "数据库关系模式满足题设条件，下列说法正确的是？",
                    "options": [{"key": "A", "text": "R 属于 1NF"}, {"key": "B", "text": "R 属于 BCNF"}],
                    "answer": "A",
                    "analysis": "题设条件满足第一范式。",
                }
            ],
        }
    )

    class InvalidRepairModel:
        def invoke(self, _messages):
            return SimpleNamespace(content='{"content":"不完整"}')

    monkeypatch.setattr(ChatModelFactory, "create", lambda **_: InvalidRepairModel())

    with pytest.raises(ValueError, match="有效题目不足"):
        quiz_service._repair_single_invalid_question(
            draft,
            reason="第 1 题范式层次选项 A 与 B 可同时为真；题干需明确询问最高范式",
            course="数据库",
            knowledge_point="范式",
            difficulty="standard",
        )
    assert draft.questions[0].content == "数据库关系模式满足题设条件，下列说法正确的是？"


def test_quiz_generation_retries_with_concise_quality_failure_reason(monkeypatch) -> None:
    responses = [
        {
            "title": "数据库事务练习",
            "questions": [
                {
                    "knowledge_point": "事务",
                    "content": "数据库事务原子性表示什么？",
                    "options": {"A": "整体成功或回滚", "B": "允许部分提交"},
                    "answer": "A",
                    "analysis": "题目不恰当，需要重新检查题干。",
                }
            ],
        },
        {
            "title": "数据库事务练习",
            "questions": [
                {
                    "knowledge_point": "事务",
                    "content": "数据库事务原子性表示什么？",
                    "options": {"A": "整体成功或回滚", "B": "允许部分提交"},
                    "answer": "A",
                    "analysis": "原子性要求事务整体成功或整体回滚，因此答案为 A。",
                }
            ],
        },
    ]
    generation_prompts: list[str] = []
    review_prompts: list[str] = []
    targeted_prompts: list[str] = []

    class GenerationModel:
        def invoke(self, messages):
            generation_prompts.append(messages[0].content)
            return SimpleNamespace(
                content=json.dumps(responses[len(generation_prompts) - 1], ensure_ascii=False)
            )

    class ReviewModel:
        def invoke(self, messages):
            review_prompts.append(messages[0].content)
            return SimpleNamespace(
                content=json.dumps(
                    {
                        "reviewed_question_count": 1,
                        "questions": [
                            {
                                "question_index": 1,
                                "verdict": "pass",
                                "correct_option_keys": ["A"],
                                "issues": [],
                            }
                        ],
                        "issues": [],
                    },
                    ensure_ascii=False,
                )
            )

    class InvalidTargetedRepairModel:
        def invoke(self, messages):
            targeted_prompts.append(messages[0].content)
            return SimpleNamespace(content="not valid json")

    generation_model = GenerationModel()
    review_model = ReviewModel()
    targeted_model = InvalidTargetedRepairModel()
    monkeypatch.setattr(
        ChatModelFactory,
        "create",
        lambda **kwargs: targeted_model
        if kwargs.get("max_tokens") == quiz_service._TARGETED_REPAIR_MAX_TOKENS
        else review_model
        if kwargs.get("temperature") == 0.0
        else generation_model,
    )

    draft = quiz_service._generate_with_llm(
        course="数据库",
        knowledge_point="事务",
        count=1,
        difficulty="standard",
    )

    assert draft.questions[0].answer == "A"
    assert len(generation_prompts) == 2
    assert len(targeted_prompts) == 1
    assert len(review_prompts) == 1
    assert "失败原因：第 1 题的解析否定了题目有效性" in generation_prompts[1]
    assert "不要复用上一版题目" in generation_prompts[1]


def test_independent_reviewer_blocks_multiple_correct_and_regenerates(monkeypatch) -> None:
    generated_payloads = [
        {
            "title": "函数依赖练习",
            "questions": [
                {
                    "knowledge_point": "BCNF",
                    "content": "数据库关系模式 R(A,B,C,D) 上有 F={AB→C,C→D,D→B}，哪项说法正确？",
                    "options": {
                        "A": "D 不是超键",
                        "B": "C 不是超键",
                        "C": "AB 不是超键",
                        "D": "C 是超键",
                    },
                    "answer": "A",
                    "analysis": "D 的闭包不包含全部属性。",
                }
            ],
        },
        {
            "title": "事务练习",
            "questions": [
                {
                    "knowledge_point": "事务",
                    "content": "数据库事务原子性表示什么？",
                    "options": {"A": "整体成功或回滚", "B": "允许部分提交"},
                    "answer": "A",
                    "analysis": "原子性要求事务整体成功或整体回滚。",
                }
            ],
        },
    ]
    review_payloads = [
        {
            "reviewed_question_count": 1,
            "questions": [
                {
                    "question_index": 1,
                    "verdict": "block",
                    "correct_option_keys": ["A", "B"],
                    "issues": [
                        {
                            "severity": "blocking",
                            "category": "multiple_correct",
                            "reason": "D+ 与 C+ 都不含 A，A、B 两项同时成立",
                        }
                    ],
                }
            ],
            "issues": [],
        },
        {
            "reviewed_question_count": 1,
            "questions": [
                {
                    "question_index": 1,
                    "verdict": "pass",
                    "correct_option_keys": ["A"],
                    "issues": [],
                }
            ],
            "issues": [],
        },
    ]
    generation_prompts: list[str] = []
    review_calls = 0

    class GenerationModel:
        def invoke(self, messages):
            generation_prompts.append(messages[0].content)
            return SimpleNamespace(
                content=json.dumps(generated_payloads[len(generation_prompts) - 1], ensure_ascii=False)
            )

    class ReviewModel:
        def invoke(self, _messages):
            nonlocal review_calls
            payload = review_payloads[review_calls]
            review_calls += 1
            return SimpleNamespace(content=json.dumps(payload, ensure_ascii=False))

    generation_model = GenerationModel()
    review_model = ReviewModel()
    monkeypatch.setattr(
        ChatModelFactory,
        "create",
        lambda **kwargs: review_model if kwargs.get("temperature") == 0.0 else generation_model,
    )

    draft = quiz_service._generate_with_llm(
        course="数据库",
        knowledge_point="函数依赖",
        count=1,
        difficulty="challenge",
    )

    assert draft.questions[0].knowledge_point == "事务"
    assert review_calls == 2
    assert len(generation_prompts) == 2
    assert "D+ 与 C+ 都不含 A，A、B 两项同时成立" in generation_prompts[1]


def test_independent_reviewer_accepts_valid_single_answer(monkeypatch) -> None:
    draft = QuizDraft.model_validate(
        {
            "title": "事务练习",
            "questions": [
                {
                    "knowledge_point": "事务",
                    "content": "数据库事务原子性表示什么？",
                    "options": [
                        {"key": "A", "text": "整体成功或回滚"},
                        {"key": "B", "text": "允许部分提交"},
                    ],
                    "answer": "A",
                    "analysis": "原子性要求事务整体成功或整体回滚。",
                }
            ],
        }
    )
    create_kwargs: list[dict] = []

    class ReviewModel:
        def invoke(self, messages):
            assert "不要假定 answer 正确" in messages[0].content
            assert "不输出 Markdown、代码围栏、思维链" in messages[0].content
            return SimpleNamespace(
                content=json.dumps(
                    {
                        "reviewed_question_count": 1,
                        "questions": [
                            {
                                "question_index": 1,
                                "verdict": "pass",
                                "correct_option_keys": ["A"],
                                "issues": [],
                            }
                        ],
                        "issues": [],
                    },
                    ensure_ascii=False,
                )
            )

    def create_model(**kwargs):
        create_kwargs.append(kwargs)
        return ReviewModel()

    monkeypatch.setattr(ChatModelFactory, "create", create_model)

    quiz_service._review_quiz_with_llm(draft, course="数据库", knowledge_point="事务")

    assert create_kwargs[0]["temperature"] == 0.0
    assert create_kwargs[0]["timeout_seconds"] == 45


def test_reviewer_failure_is_fail_closed_before_resource_persistence(monkeypatch) -> None:
    db = _session()
    valid_generation = {
        "title": "事务练习",
        "questions": [
            {
                "knowledge_point": "事务",
                "content": "数据库事务原子性表示什么？",
                "options": {"A": "整体成功或回滚", "B": "允许部分提交"},
                "answer": "A",
                "analysis": "原子性要求事务整体成功或整体回滚。",
            }
        ],
    }

    class GenerationModel:
        def invoke(self, _messages):
            return SimpleNamespace(content=json.dumps(valid_generation, ensure_ascii=False))

    class BrokenReviewModel:
        def invoke(self, _messages):
            return SimpleNamespace(content="review unavailable")

    generation_model = GenerationModel()
    broken_reviewer = BrokenReviewModel()
    monkeypatch.setattr(
        ChatModelFactory,
        "create",
        lambda **kwargs: broken_reviewer if kwargs.get("temperature") == 0.0 else generation_model,
    )

    with pytest.raises(QuizGenerationError, match="独立质量审查失败"):
        quiz_service.generate(
            db,
            owner_id=uuid4(),
            course="数据库",
            knowledge_point="事务",
            count=1,
        )

    assert db.exec(select(Resource)).all() == []


def test_generate_rechecks_quality_before_persisting(monkeypatch) -> None:
    db = _session()
    invalid_draft = QuizDraft.model_validate(
        {
            "title": "事务练习",
            "questions": [
                {
                    "knowledge_point": "事务",
                    "content": "事务原子性表示什么？",
                    "options": [
                        {"key": "A", "text": "整体成功或回滚"},
                        {"key": "B", "text": "允许部分提交"},
                    ],
                    "answer": "A",
                    "analysis": "解析末尾却说正确答案是 B。",
                }
            ],
        }
    )
    monkeypatch.setattr(quiz_service, "_generate_with_llm", lambda **_: invalid_draft)

    with pytest.raises(QuizGenerationError, match="题目质量校验失败"):
        quiz_service.generate(
            db,
            owner_id=uuid4(),
            course="数据库",
            knowledge_point="事务",
            count=1,
        )

    assert db.exec(select(Resource)).all() == []


def test_structured_quiz_submit_updates_learning_loop(monkeypatch, tmp_path: Path) -> None:
    db = _session()
    owner_id = uuid4()
    draft = QuizDraft.model_validate(
        {
            "title": "数据库事务专项练习",
            "questions": [
                {
                    "knowledge_point": "ACID",
                    "content": "事务原子性表示什么？",
                    "options": [
                        {"key": "A", "text": "全部成功或全部失败"},
                        {"key": "B", "text": "允许部分提交"},
                        {"key": "C", "text": "只保证并发"},
                        {"key": "D", "text": "只保证持久"},
                    ],
                    "answer": "A",
                    "analysis": "原子性要求事务作为不可分割的工作单元。",
                },
                {
                    "knowledge_point": "隔离级别",
                    "content": "哪个隔离级别可以避免脏读？",
                    "options": [
                        {"key": "A", "text": "读未提交"},
                        {"key": "B", "text": "读已提交"},
                        {"key": "C", "text": "无事务"},
                        {"key": "D", "text": "自动提交"},
                    ],
                    "answer": "B",
                    "analysis": "读已提交不会读取其他事务尚未提交的数据。",
                },
            ],
        }
    )
    monkeypatch.setattr(quiz_service, "_generate_with_llm", lambda **_: draft)
    def write_word_file(**_) -> Path:
        target = tmp_path / "数据库事务专项练习.docx"
        target.write_bytes(b"docx-test")
        return target

    monkeypatch.setattr(quiz_service, "_write_word_file", write_word_file)

    quiz = quiz_service.generate(
        db,
        owner_id=owner_id,
        course="数据库",
        knowledge_point="事务",
        count=2,
    )
    assert quiz.title == "数据库事务专项练习"
    assert len(quiz.questions) == 2
    assert not hasattr(quiz.questions[0], "answer")
    assert quiz.file_name.endswith(".docx")
    assert quiz.download_url.endswith(f"/{quiz.resource_id}/download")
    assert db.exec(select(Resource)).one().type == "question"
    assert len(db.exec(select(Question)).all()) == 2

    result = quiz_service.submit(
        db,
        resource_id=quiz.resource_id,
        user_id=owner_id,
        answers={str(quiz.questions[0].id): "A", str(quiz.questions[1].id): "A"},
    )

    assert result.correct_count == 1
    assert result.score == 0.5
    assert result.wrong_knowledge_points == ["隔离级别"]
    assert db.exec(select(QuizAttempt)).one().score == 0.5
    assert db.exec(select(PracticeRecord)).one().correct_count == 1
    evidence = db.exec(select(LearningEvidence)).all()
    assert len(evidence) == 2
    # A free-form topic without a trusted curriculum node remains durable
    # behavioral evidence. The raw score is retained for audit, but it is not
    # promoted into the learner's mastery map.
    assert all(item.score is None for item in evidence)
    assert sorted(item.payload["observed_score"] for item in evidence) == [0.0, 1.0]
    assert all(item.payload["knowledge_identity"]["trusted"] is False for item in evidence)
    profile = db.exec(select(UserMemoryProfile)).one().memory_profile
    assert profile.get("mastery_map", {}) == {}
    assert profile["activity_summary"]["source_counts"]["quiz"] == 2
    assert db.exec(select(LearningPath)).one().nodes[0]["topic"] == "隔离级别"

    attempts = quiz_service.list_attempts(db, resource_id=quiz.resource_id, user_id=owner_id)
    assert len(attempts) == 1
    history = quiz_service.get_attempt(db, attempt_id=attempts[0].attempt_id, user_id=owner_id)
    assert history.results[1].selected_answer == "A"
    assert history.results[1].correct_answer == "B"

    wrong_question = db.exec(select(WrongQuestion)).one()
    assert wrong_question.wrong_count == 1
    assert wrong_question.is_favorite
    assert quiz_service.list_wrong_book(db, user_id=owner_id).count == 1
    quiz_service.set_wrong_question_favorite(
        db,
        question_id=quiz.questions[1].id,
        user_id=owner_id,
        favorite=False,
    )
    assert quiz_service.list_wrong_book(db, user_id=owner_id).count == 0
    quiz_service.set_wrong_question_favorite(
        db,
        question_id=quiz.questions[1].id,
        user_id=owner_id,
        favorite=True,
    )
    wrong_book = quiz_service.list_wrong_book(db, user_id=owner_id)
    assert wrong_book.count == 1
    assert wrong_book.items[0].question.id == quiz.questions[1].id

    redo = quiz_service.submit_wrong_book(
        db,
        user_id=owner_id,
        answers={str(quiz.questions[1].id): "B"},
    )
    assert redo.total_questions == 1
    assert redo.correct_count == 1
    assert db.exec(select(WrongQuestion)).one().mastered
    assert len(quiz_service.list_attempts(db, resource_id=quiz.resource_id, user_id=owner_id)) == 2


def test_quiz_score_updates_mastery_only_for_verified_course_node() -> None:
    db = _session()
    owner_id = uuid4()
    course_id = uuid4()
    node = CourseKnowledgeNode(
        course_id=course_id,
        normalized_key="concept:transaction:acid",
        label="ACID",
        node_type="concept",
        attributes={"source": "course_plan"},
    )
    resource = Resource(
        title="ACID 可信评测",
        type="question",
        subject="数据库",
        content_type="application/json",
        content={"course": "数据库"},
        course_id=course_id,
        knowledge_point="ACID",
        difficulty="standard",
        source="agent",
        uploader_id=owner_id,
    )
    db.add(node)
    db.add(resource)
    db.flush([resource])
    question = Question(
        resource_id=resource.id,
        knowledge_point="ACID",
        question_type="single_choice",
        content="事务原子性表示什么？",
        options=[
            {"key": "A", "text": "全部成功或全部失败"},
            {"key": "B", "text": "允许部分提交"},
        ],
        answer="A",
        analysis="原子性把事务视为不可分割的工作单元。",
        difficulty="standard",
        order=0,
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    result = quiz_service.submit(
        db,
        resource_id=resource.id,
        user_id=owner_id,
        answers={str(question.id): "A"},
    )

    assert result.score == 1.0
    evidence = db.exec(select(LearningEvidence)).one()
    assert evidence.score == 1.0
    assert evidence.knowledge_point_id == str(node.id)
    assert evidence.payload["knowledge_identity"] == {
        "trusted": True,
        "reason": "verified_course_graph_node",
    }
    profile = db.exec(select(UserMemoryProfile)).one().memory_profile
    assert profile["mastery_map"]["ACID"] > 0.5
    assert profile["profile_dimensions"]["knowledge_mastery"]["source_type"] == "learning_evidence"


def test_quiz_records_verified_resource_scope_when_question_labels_are_subtopics() -> None:
    db = _session()
    owner_id = uuid4()
    course_id = uuid4()
    node = CourseKnowledgeNode(
        course_id=course_id,
        normalized_key="concept:normalization:bcnf",
        label="范式与 BCNF",
        node_type="concept",
        attributes={"source": "course_plan"},
    )
    resource = Resource(
        title="数据库范式专项练习",
        type="question",
        subject="数据库",
        content_type="application/json",
        content={"course": "数据库"},
        course_id=course_id,
        knowledge_point="范式与 BCNF",
        difficulty="standard",
        source="agent",
        uploader_id=owner_id,
    )
    db.add(node)
    db.add(resource)
    db.flush([resource])
    questions = [
        Question(
            resource_id=resource.id,
            knowledge_point=topic,
            question_type="single_choice",
            content=content,
            options=[
                {"key": "A", "text": "正确"},
                {"key": "B", "text": "错误"},
            ],
            answer="A",
            analysis="用于验证课程节点聚合证据。",
            difficulty="standard",
            order=order,
        )
        for order, (topic, content) in enumerate(
            [("2NF 定义", "2NF 的核心约束是什么？"), ("BCNF 分解", "BCNF 分解保证什么？")]
        )
    ]
    db.add_all(questions)
    db.commit()
    for question in questions:
        db.refresh(question)

    result = quiz_service.submit(
        db,
        resource_id=resource.id,
        user_id=owner_id,
        answers={str(question.id): "A" for question in questions},
    )

    assert result.score == 1.0
    evidence = db.exec(select(LearningEvidence)).all()
    assert len(evidence) == 3
    trusted = [item for item in evidence if item.score is not None]
    assert len(trusted) == 1
    assert trusted[0].score == 1.0
    assert trusted[0].knowledge_point_id == str(node.id)
    assert trusted[0].payload["scope"] == "verified_resource_knowledge_point"
    assert trusted[0].payload["question_count"] == 2
    untrusted = [item for item in evidence if item.score is None]
    assert len(untrusted) == 2
    assert all(item.payload["knowledge_identity"]["trusted"] is False for item in untrusted)
    profile = db.exec(select(UserMemoryProfile)).one().memory_profile
    assert profile["mastery_map"]["范式与 BCNF"] > 0.5
