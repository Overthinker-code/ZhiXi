from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session, select

from app.api.v1.endpoints.ai_chat import _is_quiz_generation_intent, _quiz_context
from app.db.base_class import Base
from app.models import LearningPath, PracticeRecord, Question, QuizAttempt, Resource, WrongQuestion
from app.models.user import User  # noqa: F401
from app.models.user_memory_profile import UserMemoryProfile
from app.schemas.quiz import QuizDraft
from app.services.quiz_service import quiz_service


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
    profile = db.exec(select(UserMemoryProfile)).one().memory_profile
    assert profile["knowledge_state"]["隔离级别"] < 0.5
    assert "隔离级别" in profile["weak_points"]
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
