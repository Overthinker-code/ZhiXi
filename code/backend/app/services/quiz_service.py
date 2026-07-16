from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from docx import Document
from langchain_core.messages import HumanMessage
from sqlmodel import Session, select

from app.models import LearningPath, PracticeRecord, Question, QuizAttempt, Resource, WrongQuestion
from app.core.config import settings
from app.schemas.quiz import (
    QuizDraft,
    QuizQuestionPublic,
    QuizResourcePublic,
    QuizSubmitResponse,
    QuizQuestionResult,
    QuizAttemptSummary,
    QuizAttemptDetail,
    WrongQuestionBookResponse,
    WrongQuestionPublic,
    WrongBookSubmitResponse,
)
from app.services.chat_model_factory import ChatModelFactory
from app.services.profile_update_service import profile_update_service
from app.services.resource_subject_service import resolve_resource_subject


class QuizGenerationError(RuntimeError):
    pass


class QuizService:
    def generate(
        self,
        session: Session,
        *,
        owner_id: UUID,
        course: str,
        knowledge_point: str,
        count: int,
        difficulty: str = "standard",
        course_id: UUID | None = None,
    ) -> QuizResourcePublic:
        count = max(1, min(30, count))
        draft = self._generate_with_llm(
            course=course,
            knowledge_point=knowledge_point,
            count=count,
            difficulty=difficulty,
        )
        questions = draft.questions[:count]
        resource = Resource(
            title=draft.title,
            type="question",
            subject=resolve_resource_subject(course, knowledge_point, draft.title),
            content_type="application/json",
            course_id=course_id,
            content={"question_count": len(questions), "course": course},
            knowledge_point=knowledge_point,
            difficulty=difficulty,
            source="agent",
            uploader_id=owner_id,
        )
        session.add(resource)
        session.flush([resource])
        records: list[Question] = []
        for index, item in enumerate(questions):
            option_keys = {option.key.strip().upper() for option in item.options}
            answer = item.answer.strip().upper()
            if answer not in option_keys:
                continue
            record = Question(
                resource_id=resource.id,
                knowledge_point=item.knowledge_point.strip(),
                question_type=item.question_type,
                content=item.content.strip(),
                options=[option.model_dump() for option in item.options],
                answer=answer,
                analysis=item.analysis.strip(),
                difficulty=item.difficulty,
                order=index,
            )
            session.add(record)
            records.append(record)
        if not records:
            session.rollback()
            raise QuizGenerationError("题目结构校验失败，未生成有效题目")
        word_path: Path | None = None
        try:
            word_path = self._write_word_file(resource=resource, questions=records)
            resource.file_name = word_path.name
            resource.file_path = f"resources/{word_path.name}"
            resource.file_size = word_path.stat().st_size
            resource.content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            resource.content = {
                **(resource.content or {}),
                "formats": ["interactive_quiz", "docx"],
            }
            session.add(resource)
            session.commit()
        except Exception as exc:
            session.rollback()
            if word_path:
                word_path.unlink(missing_ok=True)
            raise QuizGenerationError("题目已生成，但 Word 文件保存失败") from exc
        for record in records:
            session.refresh(record)
        return self._public(resource, records)

    def get(self, session: Session, *, resource_id: UUID, user_id: UUID) -> QuizResourcePublic:
        resource = session.get(Resource, resource_id)
        if not resource or resource.type != "question" or resource.uploader_id != user_id:
            raise QuizGenerationError("未找到指定题目资源")
        questions = session.exec(
            select(Question)
            .where(Question.resource_id == resource_id)
            .order_by(Question.order)
        ).all()
        return self._public(resource, questions)

    def submit(
        self,
        session: Session,
        *,
        resource_id: UUID,
        user_id: UUID,
        answers: dict[str, str],
    ) -> QuizSubmitResponse:
        resource = session.get(Resource, resource_id)
        if not resource or resource.type != "question" or resource.uploader_id != user_id:
            raise QuizGenerationError("未找到指定题目资源")
        questions = list(session.exec(
            select(Question).where(Question.resource_id == resource_id).order_by(Question.order)
        ).all())
        if not questions:
            raise QuizGenerationError("题目资源中没有可作答题目")
        return self._submit_questions(
            session,
            resource=resource,
            user_id=user_id,
            answers=answers,
            questions=questions,
        )

    def list_attempts(
        self, session: Session, *, resource_id: UUID, user_id: UUID
    ) -> list[QuizAttemptSummary]:
        self._owned_resource(session, resource_id=resource_id, user_id=user_id)
        attempts = session.exec(
            select(QuizAttempt)
            .where(QuizAttempt.resource_id == resource_id, QuizAttempt.user_id == user_id)
            .order_by(QuizAttempt.created_time.desc())
        ).all()
        return [
            QuizAttemptSummary(
                attempt_id=item.id,
                resource_id=item.resource_id,
                total_questions=item.total_questions,
                correct_count=item.correct_count,
                score=item.score,
                wrong_knowledge_points=item.wrong_knowledge_points,
                created_time=item.created_time,
            )
            for item in attempts
        ]

    def get_attempt(
        self, session: Session, *, attempt_id: UUID, user_id: UUID
    ) -> QuizAttemptDetail:
        attempt = session.get(QuizAttempt, attempt_id)
        if not attempt or attempt.user_id != user_id:
            raise QuizGenerationError("未找到指定答题记录")
        self._owned_resource(session, resource_id=attempt.resource_id, user_id=user_id)
        question_ids = [UUID(value) for value in attempt.answers if self._is_uuid(value)]
        questions = list(session.exec(
            select(Question).where(Question.id.in_(question_ids)).order_by(Question.order)
        ).all()) if question_ids else []
        results = self._question_results(
            session,
            user_id=user_id,
            questions=questions,
            answers=attempt.answers,
        )
        return QuizAttemptDetail(
            attempt_id=attempt.id,
            resource_id=attempt.resource_id,
            total_questions=attempt.total_questions,
            correct_count=attempt.correct_count,
            score=attempt.score,
            wrong_knowledge_points=attempt.wrong_knowledge_points,
            results=results,
            created_time=attempt.created_time,
        )

    def set_wrong_question_favorite(
        self,
        session: Session,
        *,
        question_id: UUID,
        user_id: UUID,
        favorite: bool,
    ) -> dict[str, object]:
        question = session.get(Question, question_id)
        if not question:
            raise QuizGenerationError("未找到指定题目")
        self._owned_resource(session, resource_id=question.resource_id, user_id=user_id)
        record = session.exec(
            select(WrongQuestion).where(
                WrongQuestion.user_id == user_id,
                WrongQuestion.question_id == question_id,
            )
        ).first()
        if not record:
            record = WrongQuestion(
                user_id=user_id,
                question_id=question_id,
                wrong_count=1,
            )
        record.is_favorite = favorite
        record.updated_time = datetime.now(timezone.utc)
        session.add(record)
        session.commit()
        session.refresh(record)
        return {"question_id": str(question_id), "favorite": favorite, "wrong_count": record.wrong_count}

    def list_wrong_book(self, session: Session, *, user_id: UUID) -> WrongQuestionBookResponse:
        rows = session.exec(
            select(WrongQuestion, Question, Resource)
            .join(Question, Question.id == WrongQuestion.question_id)
            .join(Resource, Resource.id == Question.resource_id)
            .where(WrongQuestion.user_id == user_id, WrongQuestion.is_favorite.is_(True))
            .order_by(WrongQuestion.updated_time.desc())
        ).all()
        items = [
            WrongQuestionPublic(
                id=wrong.id,
                question=self._public_question(question),
                resource_id=resource.id,
                resource_title=resource.title,
                subject=resource.subject,
                wrong_count=wrong.wrong_count,
                mastered=wrong.mastered,
                created_time=wrong.created_time,
                updated_time=wrong.updated_time,
            )
            for wrong, question, resource in rows
        ]
        return WrongQuestionBookResponse(items=items, count=len(items))

    def submit_wrong_book(
        self, session: Session, *, user_id: UUID, answers: dict[str, str]
    ) -> WrongBookSubmitResponse:
        question_ids = [UUID(value) for value in answers if self._is_uuid(value)]
        if not question_ids:
            raise QuizGenerationError("请先完成错题本中的题目")
        allowed = session.exec(
            select(WrongQuestion).where(
                WrongQuestion.user_id == user_id,
                WrongQuestion.is_favorite.is_(True),
                WrongQuestion.question_id.in_(question_ids),
            )
        ).all()
        allowed_ids = {item.question_id for item in allowed}
        questions = list(session.exec(
            select(Question).where(Question.id.in_(allowed_ids)).order_by(Question.resource_id, Question.order)
        ).all())
        if not questions:
            raise QuizGenerationError("错题本中没有可重做题目")
        grouped: dict[UUID, list[Question]] = {}
        for question in questions:
            grouped.setdefault(question.resource_id, []).append(question)
        submissions: list[QuizSubmitResponse] = []
        for resource_id, group in grouped.items():
            resource = self._owned_resource(session, resource_id=resource_id, user_id=user_id)
            submissions.append(
                self._submit_questions(
                    session,
                    resource=resource,
                    user_id=user_id,
                    answers=answers,
                    questions=group,
                )
            )
        results = [result for submission in submissions for result in submission.results]
        total = sum(item.total_questions for item in submissions)
        correct = sum(item.correct_count for item in submissions)
        wrong_points = list(dict.fromkeys(
            point for submission in submissions for point in submission.wrong_knowledge_points
        ))
        return WrongBookSubmitResponse(
            total_questions=total,
            correct_count=correct,
            score=round(correct / total, 4) if total else 0,
            wrong_knowledge_points=wrong_points,
            results=results,
            attempt_ids=[item.attempt_id for item in submissions],
        )

    def _submit_questions(
        self,
        session: Session,
        *,
        resource: Resource,
        user_id: UUID,
        answers: dict[str, str],
        questions: list[Question],
    ) -> QuizSubmitResponse:
        results: list[QuizQuestionResult] = []
        wrong_points: list[str] = []
        correct_count = 0
        for question in questions:
            selected = str(answers.get(str(question.id), "")).strip().upper()
            is_correct = selected == question.answer.strip().upper()
            correct_count += int(is_correct)
            if not is_correct and question.knowledge_point not in wrong_points:
                wrong_points.append(question.knowledge_point)
            results.append(
                QuizQuestionResult(
                    question_id=question.id,
                    selected_answer=selected,
                    correct_answer=question.answer,
                    is_correct=is_correct,
                    analysis=question.analysis,
                    knowledge_point=question.knowledge_point,
                )
            )
        total = len(questions)
        accuracy = round(correct_count / total, 4)
        stored_answers = {str(question.id): str(answers.get(str(question.id), "")) for question in questions}
        attempt = QuizAttempt(
            user_id=user_id,
            resource_id=resource.id,
            answers=stored_answers,
            total_questions=total,
            correct_count=correct_count,
            score=accuracy,
            wrong_knowledge_points=wrong_points,
        )
        session.add(attempt)
        session.add(
            PracticeRecord(
                user_id=user_id,
                subject=str((resource.content or {}).get("course") or "AI专项练习"),
                topic=resource.knowledge_point or resource.title,
                total_questions=total,
                correct_count=correct_count,
                score=accuracy,
            )
        )
        session.commit()
        session.refresh(attempt)
        self._sync_wrong_questions(
            session,
            user_id=user_id,
            attempt_id=attempt.id,
            results=results,
        )
        favorite_ids = set(session.exec(
            select(WrongQuestion.question_id).where(
                WrongQuestion.user_id == user_id,
                WrongQuestion.is_favorite.is_(True),
            )
        ).all())
        results = [
            item.model_copy(update={"saved_to_wrong_book": item.question_id in favorite_ids})
            for item in results
        ]

        update_topics = wrong_points or [resource.knowledge_point or resource.title]
        for topic in update_topics[:6]:
            profile_update_service.apply_incremental_update(
                session,
                user_id=user_id,
                analysis={
                    "knowledge_point": topic,
                    "observed_mastery": accuracy if topic == resource.knowledge_point else 0.25,
                    "difficulty": "high" if accuracy < 0.6 else "medium" if accuracy < 0.8 else "low",
                    "weakness": "quiz_error" if topic in wrong_points else "",
                    "behavior_signals": {"quiz_attempts": 1, "quiz_questions": total},
                },
                source_type="quiz_evaluation",
                alpha=0.3,
                evidence={"resource_id": str(resource.id), "accuracy": accuracy, "wrong_points": wrong_points},
            )
        self._update_learning_path(session, user_id=user_id, resource=resource, wrong_points=wrong_points)
        return QuizSubmitResponse(
            attempt_id=attempt.id,
            total_questions=total,
            correct_count=correct_count,
            score=accuracy,
            wrong_knowledge_points=wrong_points,
            results=results,
        )

    def _sync_wrong_questions(
        self,
        session: Session,
        *,
        user_id: UUID,
        attempt_id: UUID,
        results: list[QuizQuestionResult],
    ) -> None:
        question_ids = [item.question_id for item in results]
        existing = session.exec(
            select(WrongQuestion).where(
                WrongQuestion.user_id == user_id,
                WrongQuestion.question_id.in_(question_ids),
            )
        ).all()
        by_question = {item.question_id: item for item in existing}
        now = datetime.now(timezone.utc)
        for result in results:
            record = by_question.get(result.question_id)
            if result.is_correct:
                if record:
                    record.mastered = True
                    record.updated_time = now
                    session.add(record)
                continue
            if not record:
                record = WrongQuestion(
                    user_id=user_id,
                    question_id=result.question_id,
                    wrong_count=0,
                )
            record.wrong_count += 1
            record.is_favorite = True
            record.mastered = False
            record.source_attempt_id = attempt_id
            record.updated_time = now
            session.add(record)
        session.commit()

    def _question_results(
        self,
        session: Session,
        *,
        user_id: UUID,
        questions: list[Question],
        answers: dict[str, str],
    ) -> list[QuizQuestionResult]:
        favorites = set(session.exec(
            select(WrongQuestion.question_id).where(
                WrongQuestion.user_id == user_id,
                WrongQuestion.is_favorite.is_(True),
            )
        ).all())
        return [
            QuizQuestionResult(
                question_id=question.id,
                selected_answer=str(answers.get(str(question.id), "")).strip().upper(),
                correct_answer=question.answer,
                is_correct=str(answers.get(str(question.id), "")).strip().upper() == question.answer.strip().upper(),
                analysis=question.analysis,
                knowledge_point=question.knowledge_point,
                saved_to_wrong_book=question.id in favorites,
            )
            for question in questions
        ]

    def _owned_resource(self, session: Session, *, resource_id: UUID, user_id: UUID) -> Resource:
        resource = session.get(Resource, resource_id)
        if not resource or resource.type != "question" or resource.uploader_id != user_id:
            raise QuizGenerationError("未找到指定题目资源")
        return resource

    @staticmethod
    def _is_uuid(value: str) -> bool:
        try:
            UUID(str(value))
            return True
        except (TypeError, ValueError):
            return False

    def _generate_with_llm(
        self, *, course: str, knowledge_point: str, count: int, difficulty: str
    ) -> QuizDraft:
        prompt = f"""你是 Quiz Agent。只为课程“{course}”的范围“{knowledge_point}”生成恰好 {count} 道单选题，难度为 {difficulty}。
只输出一个 JSON 对象，不输出 Markdown、代码围栏或额外说明。严格使用下面的字段结构：
{{
  "title": "{course}{knowledge_point}专项练习",
  "questions": [
    {{
      "knowledge_point": "具体考点",
      "question_type": "single_choice",
      "content": "题干",
      "options": [
        {{"key": "A", "text": "选项A"}},
        {{"key": "B", "text": "选项B"}},
        {{"key": "C", "text": "选项C"}},
        {{"key": "D", "text": "选项D"}}
      ],
      "answer": "A",
      "analysis": "答案解析",
      "difficulty": "{difficulty}"
    }}
  ]
}}
不得生成其他课程的题目；题目不得重复，并覆盖概念、机制、计算、应用和易错边界。"""
        model = ChatModelFactory.create(temperature=0.25, max_tokens=6000, reasoning=False)
        errors: list[str] = []
        for attempt in range(2):
            try:
                correction = (
                    "\n上一次输出未通过结构或课程主题校验。请重新生成完整 JSON，并逐项遵守字段名称与课程范围。"
                    if attempt
                    else ""
                )
                raw_result = model.invoke([HumanMessage(content=prompt + correction)])
                raw = str(getattr(raw_result, "content", raw_result) or "")
                match = re.search(r"\{[\s\S]*\}", raw)
                payload = json.loads(match.group(0) if match else raw)
                draft = self._normalize_draft_payload(
                    payload,
                    course=course,
                    knowledge_point=knowledge_point,
                    difficulty=difficulty,
                    count=count,
                )
                self._validate_topic_alignment(draft, course=course)
                return draft
            except Exception as exc:
                errors.append(str(exc))
        detail = errors[-1][:160] if errors else "模型未返回有效 JSON"
        raise QuizGenerationError(f"结构化题目生成失败：{detail}")

    @staticmethod
    def _normalize_draft_payload(
        payload: object,
        *,
        course: str,
        knowledge_point: str,
        difficulty: str,
        count: int,
    ) -> QuizDraft:
        if isinstance(payload, list):
            root: dict = {"questions": payload}
        elif isinstance(payload, dict):
            root = payload
        else:
            raise ValueError("JSON 根节点必须是对象")
        raw_questions = root.get("questions") or root.get("items") or root.get("problems")
        if not isinstance(raw_questions, list):
            raise ValueError("JSON 中缺少 questions 数组")
        normalized: list[dict] = []
        for item in raw_questions[:count]:
            if not isinstance(item, dict):
                continue
            raw_options = item.get("options") or item.get("choices") or []
            options: list[dict[str, str]] = []
            if isinstance(raw_options, dict):
                options = [
                    {"key": str(key).strip().upper(), "text": str(value).strip()}
                    for key, value in raw_options.items()
                ]
            elif isinstance(raw_options, list):
                for index, option in enumerate(raw_options):
                    if isinstance(option, dict):
                        key = option.get("key") or option.get("label") or option.get("id") or chr(65 + index)
                        text = option.get("text") or option.get("content") or option.get("value") or ""
                    else:
                        key, text = chr(65 + index), option
                    options.append({"key": str(key).strip().upper(), "text": str(text).strip()})
            options = [option for option in options if option["key"] and option["text"]][:6]
            answer = str(item.get("answer") or item.get("correct_answer") or "").strip()
            answer_key = answer[:1].upper()
            if answer_key not in {option["key"] for option in options}:
                answer_key = next(
                    (option["key"] for option in options if option["text"] == answer),
                    "",
                )
            item_difficulty = str(item.get("difficulty") or difficulty).lower()
            if item_difficulty not in {"foundation", "standard", "challenge"}:
                item_difficulty = difficulty
            normalized.append(
                {
                    "knowledge_point": str(
                        item.get("knowledge_point") or item.get("topic") or knowledge_point
                    ).strip(),
                    "question_type": "single_choice",
                    "content": str(
                        item.get("content") or item.get("question") or item.get("stem") or ""
                    ).strip(),
                    "options": options,
                    "answer": answer_key,
                    "analysis": str(
                        item.get("analysis")
                        or item.get("explanation")
                        or item.get("rationale")
                        or "根据题目所考查的概念与条件可得该答案。"
                    ).strip(),
                    "difficulty": item_difficulty,
                }
            )
        valid = [item for item in normalized if item["content"] and len(item["options"]) >= 2 and item["answer"]]
        minimum = min(count, 3)
        if len(valid) < minimum:
            raise ValueError(f"有效题目不足：期望至少 {minimum} 道，实际 {len(valid)} 道")
        return QuizDraft.model_validate(
            {
                "title": str(root.get("title") or f"{course}{knowledge_point}专项练习").strip(),
                "questions": valid,
            }
        )

    @staticmethod
    def _validate_topic_alignment(draft: QuizDraft, *, course: str) -> None:
        keyword_groups = {
            "计算机组成原理": (
                "CPU", "处理器", "指令", "存储", "缓存", "Cache", "总线", "运算器",
                "控制器", "寻址", "流水线", "中断", "I/O", "主存", "字长",
            ),
            "数据库": ("数据库", "事务", "SQL", "索引", "锁", "关系", "范式", "查询"),
            "计算机网络": ("TCP", "网络", "协议", "拥塞", "路由", "报文", "窗口", "IP"),
        }
        keywords = next((items for name, items in keyword_groups.items() if name in course), None)
        if not keywords:
            return
        matched = sum(
            any(keyword.lower() in f"{question.content} {question.knowledge_point}".lower() for keyword in keywords)
            for question in draft.questions
        )
        if matched < max(1, len(draft.questions) // 3):
            raise ValueError(f"模型返回内容与课程“{course}”不匹配")

    def _update_learning_path(
        self, session: Session, *, user_id: UUID, resource: Resource, wrong_points: list[str]
    ) -> None:
        path = session.exec(select(LearningPath).where(LearningPath.user_id == user_id)).first()
        existing_nodes = list(path.nodes or []) if path else []
        remaining = [node for node in existing_nodes if node.get("topic") not in wrong_points]
        new_nodes = [
            {
                "title": f"巩固 {topic}",
                "status": "in_progress" if index == 0 else "pending",
                "order": index,
                "topic": topic,
                "action": f"复盘错题并重新完成《{resource.title}》",
            }
            for index, topic in enumerate(wrong_points)
        ]
        nodes = new_nodes + remaining
        for index, node in enumerate(nodes):
            node["order"] = index
        if path:
            path.subject = str((resource.content or {}).get("course") or path.subject)
            path.summary = "已根据最近答题结果调整学习路径"
            path.nodes = nodes[:12]
            path.updated_at = datetime.utcnow()
        else:
            path = LearningPath(
                user_id=user_id,
                subject=str((resource.content or {}).get("course") or "专项练习"),
                summary="已根据最近答题结果生成学习路径",
                nodes=nodes[:12],
            )
        session.add(path)
        session.commit()

    @staticmethod
    def _write_word_file(*, resource: Resource, questions: list[Question]) -> Path:
        output_dir = Path(settings.BASE_PATH) / "files" / "resources"
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_title = re.sub(r'[\\/:*?"<>|]+', "_", resource.title).strip(" ._") or "AI专项练习"
        target = output_dir / f"{safe_title}-{resource.id}.docx"
        document = Document()
        document.add_heading(resource.title, level=0)
        document.add_paragraph(f"知识点：{resource.knowledge_point or '综合'}")
        document.add_paragraph(f"题量：{len(questions)} 题")
        document.add_heading("试题", level=1)
        for index, question in enumerate(questions, start=1):
            document.add_paragraph(f"{index}. {question.content}")
            for option in question.options:
                document.add_paragraph(
                    f"{option.get('key', '')}. {option.get('text', '')}",
                    style="List Bullet",
                )
        document.add_page_break()
        document.add_heading("参考答案与解析", level=1)
        for index, question in enumerate(questions, start=1):
            document.add_paragraph(f"{index}. 答案：{question.answer}")
            document.add_paragraph(question.analysis)
        document.save(target)
        return target

    @staticmethod
    def _public_question(item: Question) -> QuizQuestionPublic:
        return QuizQuestionPublic(
            id=item.id,
            knowledge_point=item.knowledge_point,
            question_type=item.question_type,
            content=item.content,
            options=item.options,
            difficulty=item.difficulty,
            order=item.order,
        )

    @staticmethod
    def _public(resource: Resource, questions: list[Question]) -> QuizResourcePublic:
        return QuizResourcePublic(
            resource_id=resource.id,
            title=resource.title,
            subject=resource.subject,
            knowledge_point=resource.knowledge_point or "",
            difficulty=resource.difficulty or "standard",
            file_name=resource.file_name,
            download_url=f"/api/education/resources/{resource.id}/download",
            questions=[QuizService._public_question(item) for item in questions],
        )


quiz_service = QuizService()
