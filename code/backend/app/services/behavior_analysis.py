import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

import cv2
import httpx
import numpy as np

from app.core.config import settings
from app.services.behavior_ws import behavior_ws_service


class BehaviorAnalysisService:
    """
    课堂行为分析服务。

    优先调用独立 YOLO 服务；当 YOLO 服务不可用时，自动回退到本地轻量级人脸检测，
    确保上传图片/视频分析在单机部署下仍然可用。
    """

    def __init__(
        self,
        yolo_host: Optional[str] = None,
        yolo_port: Optional[int] = None,
    ) -> None:
        host = yolo_host or getattr(settings, "YOLO_SERVICE_HOST", "http://127.0.0.1")
        port = yolo_port or getattr(settings, "YOLO_SERVICE_PORT", 8002)
        self.base_url = f"{host}:{port}"

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

    async def analyze_video(
        self,
        video_data: bytes,
        sample_interval: int = 1,
        course_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        分析视频中的行为。

        `course_id` 目前保留给上层路由记录使用，服务内部不依赖。
        """
        del course_id
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
            return {
                "status": "success",
                "frame_analyses": result.get("frame_analyses", []),
                "summary": result.get("summary", summary),
                "video_info": result.get("video_info", {}),
                "persons": result.get("persons", []),
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
            behavior = pred["behavior"]
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
            if pred["behavior"] != prev_behavior:
                key_moments.append(
                    {
                        "timestamp": pred["timestamp"],
                        "behavior": pred["behavior"],
                        "confidence": pred["confidence"],
                        "score": pred["score"],
                    }
                )
            prev_behavior = pred["behavior"]

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
