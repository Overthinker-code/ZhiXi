from typing import List, Dict, Any, Optional
import httpx
import cv2
import numpy as np
import tempfile
import os
from datetime import datetime
from pydantic import BaseModel
from app.core.config import settings


class BehaviorAnalysisService:
    """
    课堂行为分析服务
    基于 YOLOv8-Pose + LSTM 方案
    """
    
    def __init__(self, yolo_host: Optional[str] = None, yolo_port: Optional[int] = None):
        """初始化行为分析服务"""
        host = yolo_host or getattr(settings, "YOLO_SERVICE_HOST", "http://127.0.0.1")
        port = yolo_port or getattr(settings, "YOLO_SERVICE_PORT", 8002)
        self.base_url = f"{host}:{port}"
        
        # 行为映射（与 yolo.py 中一致）
        self.behavior_mapping = {
            0: "专注学习",
            1: "查看手机",
            2: "与他人交谈",
            3: "睡觉",
            4: "离开座位",
        }
        
        self.behavior_rules = {
            "专注学习": {"score": 1.0, "description": "学习状态良好", "color": "#52c41a"},
            "查看手机": {"score": -0.5, "description": "注意力分散", "color": "#faad14"},
            "与他人交谈": {"score": -0.3, "description": "可能影响他人学习", "color": "#fa8c16"},
            "睡觉": {"score": -1.0, "description": "未在学习", "color": "#f5222d"},
            "离开座位": {"score": -0.8, "description": "未在学习区域", "color": "#eb2f96"},
        }
        
        # LSTM 序列长度（与 yolo.py 中一致）
        self.sequence_length = 16

    async def analyze_video(self, video_data: bytes, sample_interval: int = 1, course_id: Optional[str] = None) -> Dict[str, Any]:
        """
        分析视频中的行为（使用 YOLOv8-Pose + LSTM）
        
        Args:
            video_data: 视频数据
            sample_interval: 采样间隔（帧数），默认每1帧采样
            course_id: 可选，关联的课程ID
        """
        try:
            # 直接转发到 YOLO 服务进行视频分析
            files = {'file': ('video.mp4', video_data, 'video/mp4')}
            data = {'sample_interval': sample_interval}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/analyze/video",
                    files=files,
                    data=data,
                    timeout=300.0  # 视频分析可能需要较长时间
                )
                response.raise_for_status()
                result = response.json()
            
            if result.get("status") != "success":
                return {
                    "status": "error",
                    "error": result.get("error", "视频分析失败"),
                    "summary": None
                }
            
            # 构建汇总结果
            summary = self._build_video_summary(result)
            
            return {
                "status": "success",
                "frame_analyses": result.get("frame_analyses", []),
                "summary": result.get("summary", summary),
                "video_info": result.get("video_info", {}),
                "persons": result.get("persons", []),  # 转发人员检测数据
            }

        except httpx.RequestError as e:
            return {
                "status": "error",
                "error": f"YOLO服务连接失败: {str(e)}",
                "summary": None
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"视频分析失败: {str(e)}",
                "summary": None
            }

    async def analyze_frame_sequence(self, frames_data: List[List[float]]) -> Dict[str, Any]:
        """
        分析连续帧序列（用于实时流分析）
        
        Args:
            frames_data: 连续16帧的姿态关键点序列，每帧34个值（17*2）
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/analyze/stream",
                    json=frames_data,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.RequestError as e:
            return {
                "status": "error",
                "error": f"YOLO服务连接失败: {str(e)}"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"分析失败: {str(e)}"
            }

    async def extract_pose_from_image(self, image_data: bytes) -> Dict[str, Any]:
        """
        从图像中提取姿态关键点
        """
        try:
            files = {'file': ('image.jpg', image_data, 'image/jpeg')}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/analyze/frame",
                    files=files,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.RequestError as e:
            return {
                "status": "error",
                "error": f"YOLO服务连接失败: {str(e)}"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"姿态提取失败: {str(e)}"
            }

    async def get_behavior_definitions(self) -> Dict[str, Any]:
        """
        获取行为定义
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/behaviors",
                    timeout=5.0
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.RequestError as e:
            # 如果服务不可用，返回本地定义
            return {
                "behaviors": list(self.behavior_rules.values()),
                "score_ranges": [
                    {"min": 0.7, "max": 1.0, "status": "学习状态优秀", "color": "#52c41a"},
                    {"min": 0.3, "max": 0.7, "status": "学习状态良好", "color": "#1890ff"},
                    {"min": -0.3, "max": 0.3, "status": "学习状态一般", "color": "#faad14"},
                    {"min": -0.7, "max": -0.3, "status": "学习状态较差", "color": "#fa541c"},
                    {"min": -1.0, "max": -0.7, "status": "学习状态极差", "color": "#f5222d"},
                ],
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"获取行为定义失败: {str(e)}"
            }

    def _build_video_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """构建视频分析汇总"""
        predictions = result.get("frame_analyses", [])
        
        if not predictions:
            return {
                "average_score": 0,
                "overall_status": "无法评估",
                "behavior_statistics": {},
                "time_distribution": {},
                "key_moments": []
            }
        
        # 统计各行为出现次数
        behavior_counts = {}
        behavior_durations = {}
        
        for pred in predictions:
            behavior = pred["behavior"]
            if behavior not in behavior_counts:
                behavior_counts[behavior] = 0
                behavior_durations[behavior] = 0
            behavior_counts[behavior] += 1
        
        # 计算每个行为的持续时间（基于窗口数）
        total_windows = len(predictions)
        video_duration = result.get("video_info", {}).get("duration", 0)
        window_duration = video_duration / total_windows if total_windows > 0 else 0
        
        for behavior in behavior_counts:
            behavior_durations[behavior] = behavior_counts[behavior] * window_duration
        
        # 识别关键时刻（行为切换的时刻）
        key_moments = []
        prev_behavior = None
        for pred in predictions:
            if pred["behavior"] != prev_behavior:
                key_moments.append({
                    "timestamp": pred["timestamp"],
                    "behavior": pred["behavior"],
                    "confidence": pred["confidence"],
                    "score": pred["score"]
                })
            prev_behavior = pred["behavior"]
        
        return {
            "average_score": result.get("overall_score", 0),
            "overall_status": result.get("learning_status", "无法评估"),
            "dominant_behavior": result.get("overall_behavior", "未知"),
            "behavior_statistics": {
                behavior: {
                    "count": count,
                    "duration": round(behavior_durations[behavior], 2),
                    "percentage": round(count / total_windows * 100, 1)
                }
                for behavior, count in behavior_counts.items()
            },
            "key_moments": key_moments[:10],  # 最多保留10个关键时刻
            "total_predictions": total_windows
        }

    async def analyze_image(self, image_data: bytes) -> Dict[str, Any]:
        """
        分析单张图片中的行为
        
        Args:
            image_data: 图片二进制数据
            
        Returns:
            行为分析结果，包含每个人的检测框和行为
        """
        try:
            # 调用YOLO服务分析单帧
            result = await self.extract_pose_from_image(image_data)
            
            if result.get("status") == "error":
                return {
                    "status": "error",
                    "error": result.get("error", "姿态提取失败"),
                    "behaviors": [],
                    "persons": [],
                    "overall_score": 0,
                    "learning_status": "无法评估"
                }
            
            # 新的YOLO返回格式包含多人检测框
            persons = result.get("persons", [])
            
            # 构建行为列表
            behaviors = []
            for person in persons:
                behaviors.append({
                    "behavior": person.get("behavior", "未知"),
                    "confidence": person.get("confidence", 0),
                    "score_contribution": person.get("score", 0)
                })
            
            return {
                "status": "success",
                "behaviors": behaviors,
                "persons": persons,  # 包含检测框信息
                "overall_score": result.get("overall_score", 0),
                "learning_status": result.get("learning_status", "无法评估"),
                "image_width": result.get("image_width", 0),
                "image_height": result.get("image_height", 0),
            }
            
        except Exception as e:
            import traceback
            print(f"analyze_image error: {traceback.format_exc()}")
            return {
                "status": "error",
                "error": f"图片分析失败: {str(e)}",
                "behaviors": [],
                "persons": [],
                "overall_score": 0,
                "learning_status": "无法评估"
            }


# 创建服务实例
behavior_service = BehaviorAnalysisService()
