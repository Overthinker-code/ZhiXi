import base64
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

import cv2
import httpx
import numpy as np

from app.core.config import settings
from app.services.behavior_ws import (
    AnalysisMessage,
    PersonResult,
    SummaryResult,
    behavior_ws_service,
)


class BehaviorAnalysisService:
    """
    课堂行为分析服务。

    优先调用独立 YOLO 服务；当 YOLO 服务不可用时，自动回退到本地轻量级人脸检测，
    确保上传图片/视频分析在单机部署下仍然可用。
    
    教育学参数联动：分析结果自动缓存，供预警引擎和LLM服务消费
    """

    def __init__(
        self,
        yolo_host: Optional[str] = None,
        yolo_port: Optional[int] = None,
    ) -> None:
        host = yolo_host or getattr(settings, "YOLO_SERVICE_HOST", "http://127.0.0.1")
        port = yolo_port or getattr(settings, "YOLO_SERVICE_PORT", 8002)
        self.base_url = f"{host}:{port}"
        
        # 教育学参数联动：内存缓存最新分析结果（供alerts.py消费）
        self._last_educational_report: Optional[Dict[str, Any]] = None
        self._last_person_profiles: Dict[str, Any] = {}

        self.behavior_mapping = {
            0: "专注学习",
            1: "查看手机",
            2: "与他人交谈",
            3: "睡觉",
            4: "离开座位",
        }
        self.behavior_rules = {
            "专注学习": {
                "score": 1.0,
                "description": "学习状态良好",
                "color": "#52c41a",
            },
            "查看手机": {
                "score": -0.5,
                "description": "注意力分散",
                "color": "#faad14",
            },
            "与他人交谈": {
                "score": -0.3,
                "description": "可能影响他人学习",
                "color": "#fa8c16",
            },
            "睡觉": {
                "score": -1.0,
                "description": "未在学习",
                "color": "#f5222d",
            },
            "离开座位": {
                "score": -0.8,
                "description": "未在学习区域",
                "color": "#eb2f96",
            },
        }
        self.sequence_length = 16
        self.local_behavior_rules = {
            "专注学习": {
                "score": 0.9,
                "description": "检测到正常朝向，状态较稳定",
                "color": "#52c41a",
            },
            "注意力分散": {
                "score": 0.45,
                "description": "检测到低头、侧转或人脸过小",
                "color": "#faad14",
            },
            "缺席/未检测到": {
                "score": 0.1,
                "description": "当前画面未检测到有效人脸",
                "color": "#f5222d",
            },
        }

    def _status_to_behavior_name(self, status: str) -> str:
        return {
            "focused": "专注学习",
            "unfocused": "注意力分散",
            "absent": "缺席/未检测到",
        }.get(status, "注意力分散")

    def _score_to_learning_status(self, score: float) -> str:
        if score >= 0.8:
            return "学习状态优秀"
        if score >= 0.6:
            return "学习状态良好"
        if score >= 0.35:
            return "学习状态一般"
        if score >= 0.15:
            return "学习状态较差"
        return "学习状态极差"

    def _decode_base64_image(self, image_base64: str) -> Optional[bytes]:
        try:
            if "," in image_base64:
                image_base64 = image_base64.split(",", 1)[1]
            return base64.b64decode(image_base64)
        except Exception:
            return None

    def _yolo_behavior_to_status(self, behavior: str) -> str:
        if behavior == "专注学习":
            return "focused"
        if behavior in {"离开座位", "缺席/未检测到", "未检测到人体"}:
            return "absent"
        return "unfocused"

    def _match_bbox_face_detail(
        self,
        yolo_bbox: List[int],
        local_faces: List[Dict[str, Any]],
        img_w: int,
        img_h: int,
    ) -> Optional[Dict[str, Any]]:
        """
        通过 bbox 中心点距离匹配 YOLO 人脸与本地 FaceLandmarker 人脸，
        返回匹配到的人脸详情（eye_closed, is_reading 等）。
        """
        if not local_faces:
            return None
        yolo_cx = (yolo_bbox[0] + yolo_bbox[2]) / 2
        yolo_cy = (yolo_bbox[1] + yolo_bbox[3]) / 2
        max_dist = max(img_w, img_h) * 0.15

        best_match = None
        best_dist = float("inf")
        for face in local_faces:
            lb = face.get("bbox", [0, 0, 0, 0])
            if len(lb) != 4:
                continue
            lc_x = (lb[0] + lb[2]) / 2
            lc_y = (lb[1] + lb[3]) / 2
            dist = ((yolo_cx - lc_x) ** 2 + (yolo_cy - lc_y) ** 2) ** 0.5
            if dist < best_dist and dist < max_dist:
                best_dist = dist
                best_match = face

        return best_match

    def _clamp_score(self, value: Any, default: float = 0.5) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            score = default
        return round(max(0.0, min(1.0, score)), 2)

    async def analyze_realtime_frame(
        self,
        image_base64: str,
        frame_id: int,
    ) -> Optional[AnalysisMessage]:
        """
        实时课堂帧优先走独立 YOLO 服务。

        返回 None 表示 YOLO 服务不可用，由 WebSocket 原有本地检测链路兜底。
        """
        image_data = self._decode_base64_image(image_base64)
        if image_data is None:
            return AnalysisMessage(
                frame_id=frame_id,
                timestamp=int(datetime.now().timestamp()),
                error="Failed to decode image",
            )

        try:
            files = {"file": ("frame.jpg", image_data, "image/jpeg")}
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/analyze/frame",
                    files=files,
                    timeout=15.0,
                )
                response.raise_for_status()
                result = response.json()
        except (httpx.RequestError, httpx.HTTPStatusError):
            return None
        except Exception:
            return None

        if result.get("status") != "success":
            return None

        # 教育学参数联动：缓存实时帧的教育学数据（供预警引擎消费）
        self._cache_educational_data(result)

        # 叠加本地 FaceLandmarker 细节检测，增强 YOLO 结果
        local_face_results: List[Dict[str, Any]] = []
        img_h, img_w = 0, 0
        try:
            decoded = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
            if decoded is not None:
                img_h, img_w = decoded.shape[:2]
                local_face_results = behavior_ws_service.detect_face_detail(image_data)
        except Exception:
            pass

        persons: List[PersonResult] = []
        focused_count = 0
        unfocused_count = 0
        absent_count = 0

        for index, person in enumerate(result.get("persons", [])):
            behavior = person.get("behavior", "未知")
            status = self._yolo_behavior_to_status(behavior)
            bbox = person.get("bbox") or [0, 0, 0, 0]
            if len(bbox) != 4:
                bbox = [0, 0, 0, 0]

            # 用 FaceLandmarker 辅助验证：匹配本地人脸详情
            local_detail = None
            if img_w > 0 and img_h > 0:
                local_detail = self._match_bbox_face_detail(bbox, local_face_results, img_w, img_h)

            eye_closed = local_detail.get("eye_closed") if local_detail else None
            is_reading = local_detail.get("is_reading") if local_detail else False

            # 1. 闭眼修正：专注学习 → 注意力分散
            if behavior == "专注学习" and eye_closed:
                status = "unfocused"
                behavior = "注意力分散"
                person["behavior"] = behavior
                person["color"] = "#faad14"
                original_reason = person.get("reason") or ""
                suffix = "（FaceLandmarker 辅助检测到闭眼）"
                person["reason"] = f"{original_reason}{suffix}" if original_reason else suffix

            # 2. 睡觉过滤：低头看书/写字被 YOLO 误判为睡觉 → 修正回专注学习
            if behavior == "睡觉" and is_reading:
                status = "focused"
                behavior = "专注学习"
                person["behavior"] = behavior
                person["color"] = "#52c41a"
                original_reason = person.get("reason") or ""
                suffix = "（FaceLandmarker 辅助：低头看书/写字，非睡觉）"
                person["reason"] = f"{original_reason}{suffix}" if original_reason else suffix

            if status == "focused":
                focused_count += 1
            elif status == "absent":
                absent_count += 1
            else:
                unfocused_count += 1

            score = self._clamp_score(person.get("score"), 0.5)
            confidence = self._clamp_score(person.get("confidence"), score)
            try:
                person_index = int(person.get("id", index)) + 1
            except (TypeError, ValueError):
                person_index = index + 1
            persons.append(
                PersonResult(
                    track_id=f"person_{person_index}",
                    bbox=[int(float(v)) for v in bbox],
                    status=status,
                    score=score,
                    behavior=behavior,
                    confidence=confidence,
                    color=person.get("color"),
                    reason=person.get("reason"),
                    method="yolo",
                    eye_closed=eye_closed,
                )
            )

        if not persons:
            absent_count = 1
        classroom_metrics = result.get("classroom_metrics") or {}

        return AnalysisMessage(
            frame_id=frame_id,
            timestamp=int(datetime.now().timestamp()),
            persons=persons,
            summary=SummaryResult(
                focused_count=focused_count,
                unfocused_count=unfocused_count,
                absent_count=absent_count,
                overall_score=self._clamp_score(result.get("overall_score"), 0.0),
                attention_score=self._clamp_score(
                    classroom_metrics.get("attention_score", result.get("overall_score")),
                    0.0,
                ),
                focus_rate=self._clamp_score(classroom_metrics.get("focus_rate"), 0.0),
                stability_index=self._clamp_score(
                    classroom_metrics.get("stability_index"),
                    0.0,
                ),
            ),
        )

    def _stabilize_local_confidence(
        self,
        status: str,
        raw_score: float,
        bbox: List[int],
        image_width: int,
        image_height: int,
    ) -> float:
        x1, y1, x2, y2 = bbox
        bbox_area = max(0, x2 - x1) * max(0, y2 - y1)
        image_area = max(1, image_width * image_height)
        area_ratio = bbox_area / image_area
        size_bonus = min(0.12, area_ratio * 4.5)

        if status == "focused":
            return round(min(0.98, max(raw_score, 0.68) + size_bonus), 2)
        if status == "unfocused":
            return round(min(0.9, max(raw_score, 0.36) + size_bonus / 2), 2)
        return round(max(raw_score, 0.2), 2)

    def _build_local_behavior_definitions(self) -> Dict[str, Any]:
        return {
            "behaviors": [
                {
                    "id": idx,
                    "name": name,
                    "score": meta["score"],
                    "description": meta["description"],
                    "color": meta["color"],
                }
                for idx, (name, meta) in enumerate(self.local_behavior_rules.items())
            ],
            "score_ranges": [
                {"min": 0.8, "max": 1.0, "status": "学习状态优秀", "color": "#52c41a"},
                {"min": 0.6, "max": 0.8, "status": "学习状态良好", "color": "#1890ff"},
                {"min": 0.35, "max": 0.6, "status": "学习状态一般", "color": "#faad14"},
                {"min": 0.15, "max": 0.35, "status": "学习状态较差", "color": "#fa541c"},
                {"min": 0.0, "max": 0.15, "status": "学习状态极差", "color": "#f5222d"},
            ],
            "method": "local_face_fallback",
        }

    def _build_local_image_result(
        self,
        image_data: bytes,
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        analysis = behavior_ws_service.analyze_image_bytes(image_data)
        decoded = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
        image_height = int(decoded.shape[0]) if decoded is not None else 0
        image_width = int(decoded.shape[1]) if decoded is not None else 0

        persons: List[Dict[str, Any]] = []
        behaviors: List[Dict[str, Any]] = []
        score_values: List[float] = []

        for idx, person in enumerate(analysis.persons):
            behavior_name = self._status_to_behavior_name(person.status)
            meta = self.local_behavior_rules[behavior_name]
            confidence = self._stabilize_local_confidence(
                person.status,
                float(person.score),
                person.bbox,
                image_width,
                image_height,
            )
            persons.append(
                {
                    "id": idx + 1,
                    "bbox": person.bbox,
                    "behavior": behavior_name,
                    "confidence": confidence,
                    "score": meta["score"],
                    "color": meta["color"],
                    "reason": meta["description"],
                }
            )
            behaviors.append(
                {
                    "behavior": behavior_name,
                    "confidence": confidence,
                    "description": meta["description"],
                    "score_contribution": meta["score"],
                }
            )
            score_values.append(meta["score"])

        if not persons:
            meta = self.local_behavior_rules["缺席/未检测到"]
            behaviors.append(
                {
                    "behavior": "缺席/未检测到",
                    "confidence": 1.0,
                    "description": analysis.error or meta["description"],
                    "score_contribution": meta["score"],
                }
            )
            score_values.append(meta["score"])

        overall_score = round(sum(score_values) / len(score_values), 2) if score_values else 0.0
        return {
            "status": "success",
            "behaviors": behaviors,
            "persons": persons,
            "overall_score": overall_score,
            "learning_status": self._score_to_learning_status(overall_score),
            "classroom_metrics": {
                "attention_score": overall_score,
                "learning_status": self._score_to_learning_status(overall_score),
                "focus_rate": round(
                    sum(1 for person in persons if person["behavior"] == "专注学习")
                    / max(1, len(persons)),
                    4,
                ),
                "average_confidence": round(
                    sum(float(person["confidence"]) for person in persons)
                    / max(1, len(persons)),
                    4,
                ),
                "stability_index": 0.65,
                "formula": "本地降级：平均行为得分 + 人脸尺寸置信度校正",
            },
            "timestamp": timestamp or datetime.now().isoformat(),
            "image_width": image_width,
            "image_height": image_height,
        }

    async def _analyze_video_locally(
        self,
        video_data: bytes,
        sample_interval: int = 1,
    ) -> Dict[str, Any]:
        temp_path: Optional[str] = None
        cap: Optional[cv2.VideoCapture] = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
                temp_file.write(video_data)
                temp_path = temp_file.name

            cap = cv2.VideoCapture(temp_path)
            if not cap.isOpened():
                return {"status": "error", "error": "无法读取视频文件", "summary": None}

            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            duration = round(total_frames / fps, 2) if fps else 0.0

            frame_number = 0
            analyzed_count = 0
            frame_analyses: List[Dict[str, Any]] = []
            first_persons: List[Dict[str, Any]] = []
            behavior_counts: Dict[str, int] = {}
            score_values: List[float] = []
            previous_behavior: Optional[str] = None
            key_moments: List[Dict[str, Any]] = []
            effective_interval = max(1, sample_interval)

            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                frame_number += 1
                if (frame_number - 1) % effective_interval != 0:
                    continue

                ok_encode, encoded = cv2.imencode(".jpg", frame)
                if not ok_encode:
                    continue

                result = self._build_local_image_result(
                    encoded.tobytes(),
                    timestamp=datetime.now().isoformat(),
                )
                analyzed_count += 1

                persons = result.get("persons", [])
                if not first_persons and persons:
                    first_persons = persons

                frame_behavior = (
                    persons[0]["behavior"] if persons else result["behaviors"][0]["behavior"]
                )
                frame_score = float(result["overall_score"])
                behavior_counts[frame_behavior] = behavior_counts.get(frame_behavior, 0) + 1
                score_values.append(frame_score)

                frame_analyses.append(
                    {
                        "timestamp": round(frame_number / fps, 2) if fps else float(frame_number),
                        "frame_number": frame_number,
                        "behaviors": result["behaviors"],
                        "score": frame_score,
                    }
                )

                if frame_behavior != previous_behavior:
                    key_moments.append(
                        {
                            "timestamp": round(frame_number / fps, 2) if fps else float(frame_number),
                            "behaviors": [frame_behavior],
                            "score": frame_score,
                        }
                    )
                previous_behavior = frame_behavior

            average_score = round(sum(score_values) / len(score_values), 2) if score_values else 0.0
            total_predictions = max(1, len(frame_analyses))
            summary = {
                "average_score": average_score,
                "overall_status": self._score_to_learning_status(average_score),
                "behavior_statistics": {
                    behavior: {
                        "count": count,
                        "duration": round((count * effective_interval) / fps, 2) if fps else 0.0,
                        "percentage": round(count / total_predictions * 100, 1),
                    }
                    for behavior, count in behavior_counts.items()
                },
                "key_moments": key_moments[:10],
            }

            return {
                "status": "success",
                "frame_analyses": frame_analyses,
                "summary": summary,
                "video_info": {
                    "total_frames": total_frames,
                    "fps": fps,
                    "duration": duration,
                    "frames_analyzed": analyzed_count,
                    "image_width": width,
                    "image_height": height,
                },
                "persons": first_persons,
            }
        except Exception as exc:
            return {"status": "error", "error": f"视频分析失败: {exc}", "summary": None}
        finally:
            if cap is not None:
                cap.release()
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    def _cache_educational_data(self, result: Dict[str, Any]) -> None:
        """缓存教育学数据，供预警引擎消费（联动3）"""
        edu_report = result.get("educational_report")
        if edu_report:
            self._last_educational_report = edu_report
        # 从persons中提取时序画像（engagement_profile包含is_abnormal_decline等预警所需字段）
        persons = result.get("persons", [])
        for p in persons:
            track_id = p.get("track_id") or p.get("id")
            if track_id:
                # 优先使用时序画像（供Rule 4个体预警），回退到单帧教育学位段
                profile = p.get("engagement_profile")
                if profile:
                    self._last_person_profiles[str(track_id)] = profile
                elif "educational" in p:
                    self._last_person_profiles[str(track_id)] = p.get("educational", {})

    def _persist_behavior_summary_sync(
        self,
        result: Dict[str, Any],
        course_id: Optional[str] = None,
        tc_id: Optional[str] = None,
    ) -> None:
        """
        同步方法：将分析结果持久化到数据库（联动1/2/4/6/7的基础）
        写入两张表：
        - CourseEngagementRecord: 课程级指标（联动6）
        - BehaviorSummaryRecord: 课堂行为摘要（联动1/2/4/7）
        此方法应在后台线程中调用，避免阻塞async事件循环
        """
        try:
            from app.core.db import engine
            from app.models import CourseEngagementRecord, BehaviorSummaryRecord
            from sqlmodel import Session
            import json
            from uuid import uuid4, UUID
            
            edu_report = result.get("educational_report", {})
            if not edu_report:
                return
            
            # 解析UUID
            actual_course_id = None
            actual_tc_id = None
            try:
                if course_id:
                    actual_course_id = UUID(course_id)
                if tc_id:
                    actual_tc_id = UUID(tc_id)
            except (ValueError, TypeError):
                pass
            
            with Session(engine) as session:
                # 1) 课程级记录（联动6：LEI趋势→课程质量）
                # 仅在有 course_id 时保存，避免 NOT NULL 约束冲突
                if actual_course_id is not None:
                    cer = CourseEngagementRecord(
                        id=uuid4(),
                        course_id=actual_course_id,
                        tc_id=actual_tc_id,
                        avg_lei=float(edu_report.get("class_learning_engagement_index", 0.0) or 0.0),
                        avg_cognitive_depth=float(edu_report.get("class_cognitive_depth", 0.0) or 0.0),
                        mind_wandering_rate=float(edu_report.get("class_mind_wandering_rate", 0.0) or 0.0),
                        contagion_index=float(edu_report.get("contagion_index", 0.0) or 0.0),
                        bloom_distribution=json.dumps(edu_report.get("bloom_distribution") or {}),
                        cognitive_state_distribution=json.dumps(edu_report.get("cognitive_state_distribution") or {}),
                        pedagogical_suggestions=json.dumps(edu_report.get("pedagogical_suggestions") or []),
                        attention_cycle_phase=edu_report.get("attention_cycle_phase"),
                        class_attention_trend=edu_report.get("class_attention_trend"),
                        student_count=int(edu_report.get("student_count", 0) or 0),
                    )
                    session.add(cer)
                
                # 2) 课堂行为摘要记录（联动1/2/4/7：学情诊断/复习计划/学习画像/错题归因）
                # 当前YOLO无学生身份识别，student_id留NULL，存储课堂整体数据作为参考
                # 提取BEI/CEI/EEI等三维投入指标存入快照，供学情档案展示
                engagement_snapshot = {
                    "class_behavioral_engagement": edu_report.get("class_behavioral_engagement", 0),
                    "class_cognitive_engagement": edu_report.get("class_cognitive_engagement", 0),
                    "class_emotional_engagement": getattr(edu_report, "class_emotional_engagement", 0) or edu_report.get("class_emotional_engagement", 0),
                    "attention_cycle_phase": edu_report.get("attention_cycle_phase"),
                    "class_attention_trend": edu_report.get("class_attention_trend"),
                    "student_count": edu_report.get("student_count", 0),
                }
                bsr = BehaviorSummaryRecord(
                    id=uuid4(),
                    student_id=None,
                    course_id=actual_course_id,
                    tc_id=actual_tc_id,
                    avg_lei=float(edu_report.get("class_learning_engagement_index", 0.0) or 0.0),
                    avg_cognitive_depth=float(edu_report.get("class_cognitive_depth", 0.0) or 0.0),
                    mind_wandering_rate=float(edu_report.get("class_mind_wandering_rate", 0.0) or 0.0),
                    contagion_index=float(edu_report.get("contagion_index", 0.0) or 0.0),
                    on_task_rate=float(edu_report.get("class_on_task_rate", 0.0) or 0.0),
                    bloom_distribution=json.dumps(edu_report.get("bloom_distribution") or {}),
                    cognitive_state_distribution=json.dumps(edu_report.get("cognitive_state_distribution") or {}),
                    pedagogical_suggestions=json.dumps(edu_report.get("pedagogical_suggestions") or []),
                    student_profiles_snapshot=json.dumps(engagement_snapshot),
                    source_type="image_analysis" if result.get("image_width") else "video_analysis",
                )
                session.add(bsr)
                session.commit()
        except Exception as _exc:
            # 持久化失败不应阻塞主流程
            import traceback
            print(f"[BehaviorAnalysis] _persist_behavior_summary_sync failed: {_exc}")
            traceback.print_exc()

    async def _persist_behavior_summary(
        self,
        result: Dict[str, Any],
        course_id: Optional[str] = None,
        tc_id: Optional[str] = None,
    ) -> None:
        """异步包装：在后台线程执行持久化，避免阻塞事件循环"""
        import asyncio
        try:
            await asyncio.to_thread(
                self._persist_behavior_summary_sync,
                result,
                course_id,
                tc_id,
            )
        except Exception:
            # to_thread需要Python 3.9+，如果失败则静默跳过
            pass

    async def analyze_video(
        self,
        video_data: bytes,
        sample_interval: int = 1,
        course_id: Optional[str] = None,
        tc_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        分析视频中的行为。

        `course_id` / `tc_id` 用于课后数据持久化（教育学参数联动）
        """
        try:
            files = {"file": ("video.mp4", video_data, "video/mp4")}
            data = {"sample_interval": sample_interval}

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/analyze/video",
                    files=files,
                    data=data,
                    timeout=300.0,
                )
                response.raise_for_status()
                result = response.json()

            if result.get("status") != "success":
                fallback = await self._analyze_video_locally(video_data, sample_interval)
                if fallback.get("status") == "success":
                    return fallback
                return {
                    "status": "error",
                    "error": result.get("error", "视频分析失败"),
                    "summary": None,
                }

            summary = self._build_video_summary(result)
            
            # 教育学参数联动：缓存+持久化
            self._cache_educational_data(result)
            await self._persist_behavior_summary(result, course_id=course_id, tc_id=tc_id)
            
            # 防御YOLO返回的summary可能为None的情况
            raw_summary = result.get("summary") or {}
            return {
                "status": "success",
                "frame_analyses": result.get("frame_analyses", []),
                "summary": result.get("summary") or summary,
                "video_info": result.get("video_info", {}),
                "persons": result.get("persons", []),
                "classroom_metrics": raw_summary.get("classroom_metrics", {}),
                "educational_report": result.get("educational_report"),
            }
        except httpx.RequestError as exc:
            fallback = await self._analyze_video_locally(video_data, sample_interval)
            if fallback.get("status") == "success":
                return fallback
            return {
                "status": "error",
                "error": f"YOLO服务连接失败: {exc}；本地回退也失败：{fallback.get('error', '未知错误')}",
                "summary": None,
            }
        except Exception as exc:
            fallback = await self._analyze_video_locally(video_data, sample_interval)
            if fallback.get("status") == "success":
                return fallback
            return {
                "status": "error",
                "error": f"视频分析失败: {exc}",
                "summary": None,
            }

    async def analyze_frame_sequence(self, frames_data: List[List[float]]) -> Dict[str, Any]:
        """分析连续帧序列（用于实时流分析）。"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/analyze/stream",
                    json=frames_data,
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as exc:
            return {"status": "error", "error": f"YOLO服务连接失败: {exc}"}
        except Exception as exc:
            return {"status": "error", "error": f"分析失败: {exc}"}

    async def extract_pose_from_image(self, image_data: bytes) -> Dict[str, Any]:
        """从图像中提取姿态关键点。"""
        try:
            files = {"file": ("image.jpg", image_data, "image/jpeg")}
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/analyze/frame",
                    files=files,
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as exc:
            return {"status": "error", "error": f"YOLO服务连接失败: {exc}"}
        except Exception as exc:
            return {"status": "error", "error": f"姿态提取失败: {exc}"}

    async def get_behavior_definitions(self) -> Dict[str, Any]:
        """获取行为定义。"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/behaviors", timeout=5.0)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError:
            return self._build_local_behavior_definitions()
        except Exception as exc:
            return {"status": "error", "error": f"获取行为定义失败: {exc}"}

    def _build_video_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """构建 YOLO 视频分析结果的汇总视图。"""
        predictions = result.get("frame_analyses", [])
        if not predictions:
            return {
                "average_score": 0,
                "overall_status": "无法评估",
                "behavior_statistics": {},
                "time_distribution": {},
                "key_moments": [],
            }

        behavior_counts: Dict[str, int] = {}
        behavior_durations: Dict[str, float] = {}
        for pred in predictions:
            behavior = pred.get("behavior", "未知")
            if behavior not in behavior_counts:
                behavior_counts[behavior] = 0
                behavior_durations[behavior] = 0
            behavior_counts[behavior] += 1

        total_windows = len(predictions)
        video_duration = result.get("video_info", {}).get("duration", 0)
        window_duration = video_duration / total_windows if total_windows > 0 else 0
        for behavior in behavior_counts:
            behavior_durations[behavior] = behavior_counts[behavior] * window_duration

        key_moments = []
        prev_behavior = None
        for pred in predictions:
            if pred.get("behavior", "未知") != prev_behavior:
                key_moments.append(
                    {
                        "timestamp": pred.get("timestamp", 0),
                        "behavior": pred.get("behavior", "未知"),
                        "confidence": pred.get("confidence", 0.0),
                        "score": pred.get("score", 0.0),
                    }
                )
            prev_behavior = pred.get("behavior", "未知")

        return {
            "average_score": result.get("overall_score", 0),
            "overall_status": result.get("learning_status", "无法评估"),
            "dominant_behavior": result.get("overall_behavior", "未知"),
            "behavior_statistics": {
                behavior: {
                    "count": count,
                    "duration": round(behavior_durations[behavior], 2),
                    "percentage": round(count / total_windows * 100, 1),
                }
                for behavior, count in behavior_counts.items()
            },
            "key_moments": key_moments[:10],
            "total_predictions": total_windows,
        }

    async def analyze_image(self, image_data: bytes) -> Dict[str, Any]:
        """
        分析单张图片中的行为。

        优先调用 YOLO 服务；当 YOLO 不可用或返回异常时，自动回退到本地轻量检测。
        """
        try:
            result = await self.extract_pose_from_image(image_data)
            if result.get("status") == "error":
                fallback = self._build_local_image_result(image_data)
                if fallback.get("persons") or fallback.get("behaviors"):
                    return fallback
                return {
                    "status": "error",
                    "error": result.get("error", "姿态提取失败"),
                    "behaviors": [],
                    "persons": [],
                    "overall_score": 0,
                    "learning_status": "无法评估",
                }

            persons = result.get("persons", [])
            behaviors = [
                {
                    "behavior": person.get("behavior", "未知"),
                    "confidence": person.get("confidence", 0),
                    "score_contribution": person.get("score", 0),
                }
                for person in persons
            ]
            return {
                "status": "success",
                "behaviors": behaviors,
                "persons": persons,
                "overall_score": result.get("overall_score", 0),
                "learning_status": result.get("learning_status", "无法评估"),
                "classroom_metrics": result.get("classroom_metrics", {}),
                "educational_report": result.get("educational_report"),
                "image_width": result.get("image_width", 0),
                "image_height": result.get("image_height", 0),
            }
        except Exception as exc:
            fallback = self._build_local_image_result(image_data)
            if fallback.get("persons") or fallback.get("behaviors"):
                return fallback
            return {
                "status": "error",
                "error": f"图片分析失败: {exc}",
                "behaviors": [],
                "persons": [],
                "overall_score": 0,
                "learning_status": "无法评估",
            }


behavior_service = BehaviorAnalysisService()
