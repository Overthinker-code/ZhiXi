from typing import List, Dict, Any, Optional
import httpx
from PIL import Image
import io
import base64
import cv2
import numpy as np
import tempfile
import os
from datetime import datetime
from pydantic import BaseModel

class BehaviorAnalysisService:
    def __init__(self, yolo_host: str = "http://localhost", yolo_port: int = 8000):
        """初始化行为分析服务"""
        self.yolo_url = f"{yolo_host}:{yolo_port}/detect/"
        
        self.behavior_mapping = {
            0: "专注学习",
            1: "查看手机",
            2: "与他人交谈",
            3: "睡觉",
            4: "离开座位",
        }
        
        self.behavior_rules = {
            "专注学习": {"score": 1.0, "description": "学习状态良好"},
            "查看手机": {"score": -0.5, "description": "注意力分散"},
            "与他人交谈": {"score": -0.3, "description": "可能影响他人学习"},
            "睡觉": {"score": -1.0, "description": "未在学习"},
            "离开座位": {"score": -0.8, "description": "未在学习区域"},
        }

    async def analyze_video(self, video_data: bytes, sample_interval: int = 30) -> Dict[str, Any]:
        """分析视频中的行为
        Args:
            video_data: 视频数据
            sample_interval: 采样间隔（帧数），默认每30帧采样一次
        """
        try:
            # 保存视频数据到临时文件
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
                temp_video.write(video_data)
                video_path = temp_video.name

            try:
                # 读取视频
                cap = cv2.VideoCapture(video_path)
                if not cap.isOpened():
                    raise ValueError("无法打开视频文件")

                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = int(cap.get(cv2.CAP_PROP_FPS))
                duration = total_frames / fps  # 视频时长（秒）

                frame_analyses = []
                frame_count = 0
                timestamps = []

                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break

                    if frame_count % sample_interval == 0:
                        # 转换帧为JPEG格式
                        _, buffer = cv2.imencode('.jpg', frame)
                        image_data = buffer.tobytes()

                        # 分析当前帧
                        frame_result = await self.analyze_image(image_data)
                        
                        # 记录时间戳
                        timestamp = frame_count / fps
                        timestamps.append(timestamp)
                        
                        if frame_result["status"] == "success":
                            frame_analyses.append({
                                "timestamp": timestamp,
                                "frame_number": frame_count,
                                "behaviors": frame_result["behaviors"],
                                "score": frame_result["overall_score"]
                            })

                    frame_count += 1

                cap.release()

                # 汇总分析结果
                if not frame_analyses:
                    return {
                        "status": "error",
                        "error": "未能成功分析任何视频帧",
                        "summary": None
                    }

                summary = self._summarize_video_analysis(frame_analyses, duration)

                return {
                    "status": "success",
                    "frame_analyses": frame_analyses,
                    "summary": summary,
                    "video_info": {
                        "total_frames": total_frames,
                        "fps": fps,
                        "duration": duration,
                        "frames_analyzed": len(frame_analyses)
                    }
                }

            finally:
                # 清理临时文件
                if os.path.exists(video_path):
                    os.unlink(video_path)

        except Exception as e:
            return {
                "status": "error",
                "error": f"视频分析失败: {str(e)}",
                "summary": None
            }

    async def analyze_image(self, image_data: bytes) -> Dict[str, Any]:
        """分析图像中的行为"""
        try:
            files = {'file': ('image.jpg', image_data, 'image/jpeg')}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(self.yolo_url, files=files)
                response.raise_for_status()
                
            detection_results = response.json()
            
            behaviors = []
            overall_score = 0.0
            
            for detection in detection_results.get("results", []):
                class_id = detection["class_id"]
                confidence = detection["confidence"]
                behavior = self.behavior_mapping.get(class_id, "未知行为")
                
                # 计算行为得分
                behavior_info = self.behavior_rules.get(behavior, {"score": 0, "description": "未知行为影响"})
                score_contribution = behavior_info["score"] * confidence
                
                behaviors.append({
                    "behavior": behavior,
                    "confidence": confidence,
                    "description": behavior_info["description"],
                    "score_contribution": score_contribution
                })
                
                overall_score += score_contribution
            
            # 归一化
            if behaviors:
                overall_score = max(min(overall_score / len(behaviors), 1.0), -1.0)
            
            # 生成学习状态评估
            learning_status = self._evaluate_learning_status(overall_score)
            
            return {
                "status": "success",
                "behaviors": behaviors,
                "overall_score": overall_score,
                "learning_status": learning_status
            }
            
        except httpx.RequestError as e:
            return {
                "status": "error",
                "error": f"YOLO服务请求失败: {str(e)}",
                "behaviors": [],
                "overall_score": 0,
                "learning_status": "无法评估"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"行为分析失败: {str(e)}",
                "behaviors": [],
                "overall_score": 0,
                "learning_status": "无法评估"
            }
    
    def _evaluate_learning_status(self, score: float) -> str:
        """根据得分评估学习状态"""
        if score >= 0.7:
            return "学习状态优秀"
        elif score >= 0.3:
            return "学习状态良好"
        elif score >= -0.3:
            return "学习状态一般"
        elif score >= -0.7:
            return "学习状态较差"
        else:
            return "学习状态极差"

    def _summarize_video_analysis(self, frame_analyses: List[Dict], duration: float) -> Dict[str, Any]:
        """汇总视频分析结果"""
        if not frame_analyses:
            return {
                "average_score": 0,
                "overall_status": "无法评估",
                "behavior_statistics": {},
                "time_distribution": {},
                "key_moments": []
            }

        # 计算平均分数
        scores = [analysis["score"] for analysis in frame_analyses]
        average_score = sum(scores) / len(scores)

        # 统计行为出现次数和时长
        behavior_counts = {}
        behavior_durations = {}
        frame_interval = duration / len(frame_analyses)

        for analysis in frame_analyses:
            for behavior in analysis["behaviors"]:
                name = behavior["behavior"]
                if name not in behavior_counts:
                    behavior_counts[name] = 0
                    behavior_durations[name] = 0
                behavior_counts[name] += 1
                behavior_durations[name] += frame_interval

        # 识别关键时刻（行为变化或分数显著变化的时刻）
        key_moments = []
        prev_behaviors = set()
        for analysis in frame_analyses:
            current_behaviors = {b["behavior"] for b in analysis["behaviors"]}
            if current_behaviors != prev_behaviors:
                key_moments.append({
                    "timestamp": analysis["timestamp"],
                    "behaviors": list(current_behaviors),
                    "score": analysis["score"]
                })
            prev_behaviors = current_behaviors

        return {
            "average_score": average_score,
            "overall_status": self._evaluate_learning_status(average_score),
            "behavior_statistics": {
                behavior: {
                    "count": count,
                    "duration": round(behavior_durations[behavior], 2),
                    "percentage": round(behavior_durations[behavior] / duration * 100, 1)
                }
                for behavior, count in behavior_counts.items()
            },
            "key_moments": key_moments[:5]  
        }

# 创建服务实例
behavior_service = BehaviorAnalysisService(
    yolo_host="http://your-yolo-server",  # 部署后替换！
    yolo_port=8000                        # 部署后替换！
) 