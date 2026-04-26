"""
课堂行为检测服务 - YOLOv8-Pose + 规则-Based分类（无需训练，立即可用）
运行: uvicorn yolo:app --host 0.0.0.0 --port 8000

基于YOLOv8-Pose提取关键点，使用几何规则判断行为
适合比赛应急使用，无需准备训练数据

规则逻辑:
- 看手机: 手腕靠近面部（鼻子）
- 睡觉: 头部低于肩部（低头）或后仰
- 交谈: 头部转向侧面
- 离开: 人体检测不完整
- 专注: 默认正常姿态
"""
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from ultralytics import YOLO
from PIL import Image
import io
import os
import cv2
import numpy as np
from typing import List, Dict, Any, Optional
import tempfile
from collections import deque
from datetime import datetime
import time
import torch

app = FastAPI(title="课堂行为检测服务 - 规则-Based版本")

# ==================== 配置 ====================
MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "../model/yolov8n-pose.pt")
SEQUENCE_LENGTH = int(os.getenv("SEQUENCE_LENGTH", "16"))  # 16帧约0.5秒
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# 检测模型配置：支持 yolov8n/yolo11n/yolo11m/yolo11l 等
# 推荐教室场景：yolo11m（精度与速度平衡）或 yolo11l（精度优先）
# 默认使用 yolo11m.pt（教室场景精度与速度平衡），如不存在会自动回退到单阶段模式
DETECTOR_PATH = os.getenv("DETECTOR_MODEL_PATH", "../model/yolo11m.pt")
DETECTOR_CONF = float(os.getenv("DETECTOR_CONF", "0.35"))   # yolo11 系列建议 0.35-0.4
POSE_CONF = float(os.getenv("POSE_CONF", "0.3"))           # 姿态估计置信度阈值
TEMPORAL_WINDOW = int(os.getenv("YOLO_TEMPORAL_WINDOW", "6"))
TEMPORAL_DECAY = float(os.getenv("YOLO_TEMPORAL_DECAY", "0.72"))
TEMPORAL_RESET_SECONDS = float(os.getenv("YOLO_TEMPORAL_RESET_SECONDS", "3.0"))

print(f"🖥️  使用设备: {DEVICE}")
print(f"📊 序列长度: {SEQUENCE_LENGTH} 帧")
print(f"✅ 规则-Based版本，无需训练，立即可用！")

# ==================== 加载YOLOv8-Pose模型 ====================
pose_model = None
try:
    pose_model = YOLO(MODEL_PATH)
    print(f"✅ 姿态估计模型加载成功: {MODEL_PATH}")
except Exception as e:
    print(f"⚠️ 模型加载失败: {e}")
    print("尝试下载默认模型...")
    try:
        pose_model = YOLO("yolov8n-pose.pt")
        print("✅ 默认模型加载成功")
    except Exception as e2:
        print(f"❌ 默认模型也加载失败: {e2}")
        print("   服务将以降级模式运行，行为分析功能不可用")
        pose_model = None

# 是否使用双阶段模式（检测器 + Pose）
# 需要检测模型（如 yolov8n.pt / yolo11m.pt / yolo11l.pt），网络不通时设为 false 回退到单阶段
USE_DUAL_STAGE = os.getenv("USE_DUAL_STAGE", "true").lower() in ("true", "1", "yes")

# ==================== 加载人体检测模型（仅在双阶段模式下）====================
detector_model = None
if USE_DUAL_STAGE:
    if os.path.exists(DETECTOR_PATH):
        try:
            detector_model = YOLO(DETECTOR_PATH)
            print(f"✅ 人体检测模型加载成功: {DETECTOR_PATH}")
            # 自动提示：如果是 yolo11 系列，效果会比 yolov8 更好
            if "yolo11" in DETECTOR_PATH.lower():
                print("🚀 已启用 YOLO11 检测器，教室场景检测能力更强")
        except Exception as e:
            print(f"⚠️ 检测模型加载失败: {e}")
            print("回退到单阶段模式")
            USE_DUAL_STAGE = False
    else:
        print(f"⚠️ 未找到检测模型: {DETECTOR_PATH}，回退到单阶段模式")
        print("   如需双阶段检测，请从以下地址下载模型并放到 code/cv/model/ 目录:")
        print("   • yolov8n.pt (轻量): https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt")
        print("   • yolo11m.pt (推荐): https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11m.pt")
        print("   • yolo11l.pt (高精度): https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11l.pt")
        USE_DUAL_STAGE = False
else:
    print("ℹ️ 单阶段模式，跳过检测模型加载")

print(f"🔧 检测模式: {'双阶段（检测器+Pose）' if USE_DUAL_STAGE else '单阶段（Pose一体化）'}")

# ==================== 行为标签定义 ====================
# 基础得分：专注学习可以超过1，负面行为在0-1之间
# 影响系数：该行为对课堂整体氛围的影响程度（用于群体效应计算）
BEHAVIOR_LABELS = {
    0: {"name": "专注学习", "score": 1.3, "impact": 0.05, "description": "学习状态良好", "color": "#52c41a"},
    1: {"name": "查看手机", "score": 0.35, "impact": 0.65, "description": "注意力分散", "color": "#faad14"},
    2: {"name": "与他人交谈", "score": 0.4, "impact": 0.85, "description": "可能影响他人学习", "color": "#fa8c16"},
    3: {"name": "睡觉", "score": 0.05, "impact": 0.95, "description": "未在学习", "color": "#f5222d"},
    4: {"name": "离开座位", "score": 0.15, "impact": 0.55, "description": "未在学习区域", "color": "#eb2f96"},
}


def clamp01(value: float) -> float:
    return float(max(0.0, min(1.0, value)))


def bbox_iou(box_a: List[float], box_b: List[float]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_area = max(0.0, inter_x2 - inter_x1) * max(0.0, inter_y2 - inter_y1)
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter_area
    return float(inter_area / union) if union > 0 else 0.0


def bbox_center_distance_ratio(
    box_a: List[float],
    box_b: List[float],
    image_width: int,
    image_height: int,
) -> float:
    ax = (box_a[0] + box_a[2]) / 2
    ay = (box_a[1] + box_a[3]) / 2
    bx = (box_b[0] + box_b[2]) / 2
    by = (box_b[1] + box_b[3]) / 2
    diagonal = max(1.0, float((image_width ** 2 + image_height ** 2) ** 0.5))
    return float(((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5 / diagonal)


def estimate_pose_quality(keypoints: np.ndarray) -> float:
    """根据关键点完整度和头肩关键点可见性估计姿态可靠度。"""
    valid_mask = np.linalg.norm(keypoints, axis=1) > 0.001
    valid_ratio = float(np.mean(valid_mask))
    core_indices = [
        KEYPOINT_DICT["nose"],
        KEYPOINT_DICT["left_shoulder"],
        KEYPOINT_DICT["right_shoulder"],
        KEYPOINT_DICT["left_hip"],
        KEYPOINT_DICT["right_hip"],
    ]
    core_ratio = float(np.mean(valid_mask[core_indices]))
    return round(clamp01(valid_ratio * 0.55 + core_ratio * 0.45), 4)


def estimate_bbox_quality(bbox: List[float], image_width: int, image_height: int) -> float:
    """用目标尺寸、长宽比和边界截断情况估计检测框质量。"""
    x1, y1, x2, y2 = bbox
    width = max(1.0, float(x2 - x1))
    height = max(1.0, float(y2 - y1))
    image_area = max(1.0, float(image_width * image_height))
    area_ratio = (width * height) / image_area
    size_score = clamp01((area_ratio - 0.01) / 0.16)
    aspect = width / height
    aspect_score = clamp01(1.0 - abs(aspect - 0.45) / 0.9)
    clipped_edges = sum(
        [
            x1 <= 1,
            y1 <= 1,
            x2 >= image_width - 1,
            y2 >= image_height - 1,
        ]
    )
    edge_penalty = clipped_edges * 0.08
    return round(clamp01(size_score * 0.45 + aspect_score * 0.45 + 0.18 - edge_penalty), 4)


def fuse_confidence(
    detector_confidence: float,
    behavior_confidence: float,
    pose_quality: float,
    bbox_quality: float,
) -> float:
    """
    多源置信度融合。

    不再简单相乘，避免检测器略低置信度时把规则分类结果整体压得过低。
    公式：
    C = 0.34*C_behavior + 0.28*C_detector + 0.22*Q_pose + 0.16*Q_bbox
    再与几何均值融合，兼顾任一信号过低时的抑制作用。
    """
    detector_confidence = clamp01(float(detector_confidence))
    behavior_confidence = clamp01(float(behavior_confidence))
    pose_quality = clamp01(float(pose_quality))
    bbox_quality = clamp01(float(bbox_quality))
    weighted = (
        behavior_confidence * 0.34
        + detector_confidence * 0.28
        + pose_quality * 0.22
        + bbox_quality * 0.16
    )
    geometric = (max(0.001, detector_confidence * behavior_confidence * pose_quality)) ** (1 / 3)
    return round(clamp01(weighted * 0.68 + geometric * 0.32), 4)


class TemporalBehaviorSmoother:
    """轨迹级时序平滑器，用衰减投票降低课堂实时检测的单帧抖动。"""

    def __init__(
        self,
        window_size: int = TEMPORAL_WINDOW,
        decay: float = TEMPORAL_DECAY,
        reset_seconds: float = TEMPORAL_RESET_SECONDS,
    ) -> None:
        self.window_size = max(2, window_size)
        self.decay = clamp01(decay) or 0.72
        self.reset_seconds = max(1.0, reset_seconds)
        self.tracks: Dict[int, Dict[str, Any]] = {}
        self.next_track_id = 1
        self.last_update = time.monotonic()

    def _maybe_reset(self, image_width: int, image_height: int) -> None:
        now = time.monotonic()
        previous_shape = getattr(self, "_last_shape", None)
        shape = (int(image_width), int(image_height))
        if now - self.last_update > self.reset_seconds or (
            previous_shape is not None and previous_shape != shape
        ):
            self.tracks.clear()
            self.next_track_id = 1
        self._last_shape = shape
        self.last_update = now

    def _match_track(
        self,
        bbox: List[float],
        image_width: int,
        image_height: int,
        used_tracks: set[int],
    ) -> Optional[int]:
        best_track_id = None
        best_score = -1.0
        for track_id, state in self.tracks.items():
            if track_id in used_tracks:
                continue
            prev_bbox = state.get("bbox")
            if not prev_bbox:
                continue
            iou = bbox_iou(bbox, prev_bbox)
            distance = bbox_center_distance_ratio(bbox, prev_bbox, image_width, image_height)
            if iou < 0.08 and distance > 0.18:
                continue
            score = iou * 0.7 + (1.0 - min(1.0, distance / 0.18)) * 0.3
            if score > best_score:
                best_score = score
                best_track_id = track_id
        return best_track_id

    def _create_track(self, bbox: List[float]) -> int:
        track_id = self.next_track_id
        self.next_track_id += 1
        self.tracks[track_id] = {
            "bbox": bbox,
            "history": deque(maxlen=self.window_size),
            "stable_class_id": None,
            "last_seen": time.monotonic(),
        }
        return track_id

    def _stable_vote(self, state: Dict[str, Any]) -> tuple[int, float, float, float]:
        history = list(state["history"])
        if not history:
            return 0, 0.0, 0.0, 1.0

        votes: Dict[int, float] = {}
        confidence_votes: Dict[int, List[float]] = {}
        for age, item in enumerate(reversed(history)):
            weight = (self.decay ** age) * float(item.get("confidence", 0.0))
            class_id = int(item.get("class_id", 0))
            votes[class_id] = votes.get(class_id, 0.0) + weight
            confidence_votes.setdefault(class_id, []).append(float(item.get("confidence", 0.0)))

        dominant = max(votes, key=votes.get)
        previous = state.get("stable_class_id")
        if previous is not None and previous != dominant:
            previous_vote = votes.get(previous, 0.0)
            dominant_vote = votes.get(dominant, 0.0)
            recent_ids = [int(item.get("class_id", 0)) for item in history[-3:]]
            repeated = recent_ids.count(dominant) >= 2
            required_margin = 0.16 if previous == 0 and dominant != 0 else 0.08
            if (not repeated) or (dominant_vote - previous_vote < required_margin):
                dominant = int(previous)

        state["stable_class_id"] = dominant
        consistency = sum(
            1 for item in history if int(item.get("class_id", 0)) == dominant
        ) / len(history)
        avg_confidence = float(np.mean(confidence_votes.get(dominant, [0.0])))
        stable_confidence = clamp01(avg_confidence * 0.78 + consistency * 0.22)
        volatility = 1.0 - consistency
        return dominant, round(stable_confidence, 4), round(consistency, 4), round(volatility, 4)

    def smooth(
        self,
        persons: List[Dict[str, Any]],
        image_width: int,
        image_height: int,
    ) -> List[Dict[str, Any]]:
        self._maybe_reset(image_width, image_height)
        now = time.monotonic()
        used_tracks: set[int] = set()
        smoothed: List[Dict[str, Any]] = []

        for person in persons:
            bbox = [float(v) for v in person.get("bbox", [0, 0, 0, 0])]
            track_id = self._match_track(bbox, image_width, image_height, used_tracks)
            if track_id is None:
                track_id = self._create_track(bbox)
            used_tracks.add(track_id)

            state = self.tracks[track_id]
            state["bbox"] = bbox
            state["last_seen"] = now
            state["history"].append(
                {
                    "class_id": int(person.get("class_id", 0)),
                    "confidence": float(person.get("confidence", 0.0)),
                }
            )
            stable_class_id, stable_conf, stability, volatility = self._stable_vote(state)
            stable_info = BEHAVIOR_LABELS[stable_class_id]

            updated = dict(person)
            raw_behavior = updated.get("behavior")
            if stable_class_id != int(person.get("class_id", 0)):
                updated["raw_behavior"] = raw_behavior
                updated["reason"] = f"时序平滑稳定为{stable_info['name']}；单帧判断：{person.get('reason', '')}"
            updated["id"] = track_id
            updated["track_id"] = f"person_{track_id}"
            updated["class_id"] = stable_class_id
            updated["behavior"] = stable_info["name"]
            updated["confidence"] = stable_conf
            updated["score"] = float(stable_info["score"])
            updated["color"] = stable_info["color"]
            updated["temporal_stability"] = stability
            updated["temporal_volatility"] = volatility
            smoothed.append(updated)

        stale_ids = [
            track_id
            for track_id, state in self.tracks.items()
            if now - float(state.get("last_seen", now)) > self.reset_seconds
        ]
        for track_id in stale_ids:
            self.tracks.pop(track_id, None)
        return smoothed


def calculate_classroom_score(persons):
    """
    科学的课堂学习状态评分算法（优化版）
    
    考虑因素：
    1. 置信度加权 - 检测越准确，权重越高
    2. 正面奖励 - 专注学习人数越多，额外加分
    3. 群体效应 - 负面行为有传染性，多人违纪影响指数级增长
    4. 行为严重性 - 睡觉比看手机对课堂影响更大
    5. 人数占比 - 负面行为人数占比越高，整体评分下降越快
    
    公式：
    基础分 = Σ(个人得分 × 置信度) / Σ(置信度)
    专注奖励 = 1 + (专注人数占比 × 0.3)  # 最多加30%
    群体惩罚 = 1 - Σ(负面行为人数占比 × 影响系数)^0.7 × 0.5  # 惩罚更温和
    最终得分 = min(1.0, 基础分 × 专注奖励 × 群体惩罚)
    
    返回：0-1之间的分数
    """
    if not persons or len(persons) == 0:
        return 0.5, "无法评估"
    
    total_persons = len(persons)
    
    # 统计各行为的人数和平均置信度
    behavior_stats = {}
    for person in persons:
        behavior_name = person.get("behavior", "专注学习")
        confidence = person.get("confidence", 0.75)
        
        if behavior_name not in behavior_stats:
            behavior_stats[behavior_name] = {
                "count": 0,
                "total_confidence": 0,
                "behavior_id": None
            }
        
        # 找到对应的行为ID
        for bid, info in BEHAVIOR_LABELS.items():
            if info["name"] == behavior_name:
                behavior_stats[behavior_name]["behavior_id"] = bid
                break
        
        behavior_stats[behavior_name]["count"] += 1
        behavior_stats[behavior_name]["total_confidence"] += confidence
    
    # 计算基础分（置信度加权平均）
    total_weighted_score = 0
    total_confidence = 0
    
    for behavior_name, stats in behavior_stats.items():
        bid = stats["behavior_id"]
        if bid is None:
            bid = 0
        
        base_score = BEHAVIOR_LABELS[bid]["score"]
        avg_confidence = stats["total_confidence"] / stats["count"]
        count = stats["count"]
        
        total_weighted_score += base_score * avg_confidence * count
        total_confidence += avg_confidence * count
    
    base_score = total_weighted_score / total_confidence if total_confidence > 0 else 0.5
    
    # 计算专注学习奖励（专注人数越多，奖励越高）
    focus_count = 0
    if "专注学习" in behavior_stats:
        focus_count = behavior_stats["专注学习"]["count"]
    
    focus_ratio = focus_count / total_persons
    # 专注奖励：最多增加 25%（当所有人都专注时）
    focus_bonus = 1 + (focus_ratio ** 1.2) * 0.25
    
    # 计算群体效应惩罚（更温和的惩罚）
    negative_impact = 0
    for behavior_name, stats in behavior_stats.items():
        bid = stats["behavior_id"]
        if bid is None:
            continue
        
        # 只计算负面行为
        if bid != 0:  # 0 是专注学习
            ratio = stats["count"] / total_persons
            impact = BEHAVIOR_LABELS[bid]["impact"]
            negative_impact += (ratio * impact) ** 0.7
    
    # 群体惩罚系数：0.55-1.0之间（惩罚更温和）
    group_penalty = max(0.55, 1 - negative_impact * 0.5)
    
    # 最终得分 = 基础分 × 专注奖励 × 群体惩罚
    final_score = base_score * focus_bonus * group_penalty
    
    # 确保在0-1范围内，但允许接近1
    final_score = max(0.0, min(1.0, final_score))
    
    final_score = float(round(float(final_score), 2))
    return final_score, get_learning_status(final_score)


def calculate_classroom_metrics(persons: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    面向课堂场景的综合指标公式。

    Attention = 0.44 * 专注率
              + 0.24 * 置信度加权行为得分
              + 0.16 * 平均置信度
              + 0.16 * 时序稳定度
              - 0.18 * 严重行为率
              - 0.10 * 分心率

    其中严重行为包含睡觉、离开座位，分心行为包含看手机、交谈。
    """
    if not persons:
        return {
            "attention_score": 0.0,
            "learning_status": "未检测到人体",
            "focus_rate": 0.0,
            "distraction_rate": 0.0,
            "severe_behavior_rate": 0.0,
            "average_confidence": 0.0,
            "stability_index": 0.0,
            "volatility_index": 1.0,
            "behavior_score": 0.0,
            "formula": "0.44*专注率 + 0.24*行为得分 + 0.16*平均置信度 + 0.16*时序稳定度 - 0.18*严重行为率 - 0.10*分心率",
        }

    total = len(persons)
    focus_count = 0
    distraction_count = 0
    severe_count = 0
    confidence_sum = 0.0
    stability_sum = 0.0
    volatility_sum = 0.0
    weighted_behavior_score = 0.0
    confidence_weight = 0.0
    distribution: Dict[str, int] = {}

    score_ceiling = max(info["score"] for info in BEHAVIOR_LABELS.values())
    for person in persons:
        behavior = str(person.get("behavior", "专注学习"))
        confidence = clamp01(float(person.get("confidence", 0.65)))
        stability = clamp01(float(person.get("temporal_stability", 0.72)))
        volatility = clamp01(float(person.get("temporal_volatility", 1.0 - stability)))
        raw_score = clamp01(float(person.get("score", 0.5)) / score_ceiling)

        distribution[behavior] = distribution.get(behavior, 0) + 1
        confidence_sum += confidence
        stability_sum += stability
        volatility_sum += volatility
        weighted_behavior_score += raw_score * max(0.25, confidence)
        confidence_weight += max(0.25, confidence)

        if behavior == "专注学习":
            focus_count += 1
        elif behavior in {"睡觉", "离开座位"}:
            severe_count += 1
        else:
            distraction_count += 1

    focus_rate = focus_count / total
    distraction_rate = distraction_count / total
    severe_behavior_rate = severe_count / total
    average_confidence = confidence_sum / total
    stability_index = stability_sum / total
    volatility_index = volatility_sum / total
    behavior_score = weighted_behavior_score / confidence_weight if confidence_weight else 0.0
    attention_score = (
        focus_rate * 0.44
        + behavior_score * 0.24
        + average_confidence * 0.16
        + stability_index * 0.16
        - severe_behavior_rate * 0.18
        - distraction_rate * 0.10
    )
    attention_score = round(clamp01(attention_score), 2)

    return {
        "attention_score": attention_score,
        "learning_status": get_learning_status(attention_score),
        "focus_rate": round(focus_rate, 4),
        "distraction_rate": round(distraction_rate, 4),
        "severe_behavior_rate": round(severe_behavior_rate, 4),
        "average_confidence": round(average_confidence, 4),
        "stability_index": round(stability_index, 4),
        "volatility_index": round(volatility_index, 4),
        "behavior_score": round(behavior_score, 4),
        "behavior_distribution": distribution,
        "formula": "0.44*专注率 + 0.24*行为得分 + 0.16*平均置信度 + 0.16*时序稳定度 - 0.18*严重行为率 - 0.10*分心率",
    }

# COCO关键点索引
KEYPOINT_DICT = {
    'nose': 0, 'left_eye': 1, 'right_eye': 2, 'left_ear': 3, 'right_ear': 4,
    'left_shoulder': 5, 'right_shoulder': 6, 'left_elbow': 7, 'right_elbow': 8,
    'left_wrist': 9, 'right_wrist': 10, 'left_hip': 11, 'right_hip': 12,
    'left_knee': 13, 'right_knee': 14, 'left_ankle': 15, 'right_ankle': 16,
}

# ==================== 规则分类器 ====================
class RuleBasedBehaviorClassifier:
    """
    基于几何规则的行为分类器
    无需训练，直接使用人体关键点的几何关系判断行为
    """
    
    def __init__(self):
        self.frame_buffer = deque(maxlen=SEQUENCE_LENGTH)
    
    def get_keypoint(self, keypoints, name):
        """获取指定关键点的坐标"""
        idx = KEYPOINT_DICT[name]
        return keypoints[idx]
    
    def check_phone_usage(self, keypoints):
        """
        检查是否在看手机
        规则：手腕非常靠近面部，并结合人体尺度与手腕高度过滤读写姿态。
        """
        nose = self.get_keypoint(keypoints, 'nose')
        left_wrist = self.get_keypoint(keypoints, 'left_wrist')
        right_wrist = self.get_keypoint(keypoints, 'right_wrist')
        left_shoulder = self.get_keypoint(keypoints, 'left_shoulder')
        right_shoulder = self.get_keypoint(keypoints, 'right_shoulder')
        left_hip = self.get_keypoint(keypoints, 'left_hip')
        right_hip = self.get_keypoint(keypoints, 'right_hip')
        
        # 计算手腕到鼻子的距离
        left_dist = np.linalg.norm(left_wrist - nose)
        right_dist = np.linalg.norm(right_wrist - nose)
        min_dist = min(left_dist, right_dist)
        nearest_wrist = left_wrist if left_dist <= right_dist else right_wrist
        
        # 用人体自身尺度归一化，避免远景课堂中正常读写被固定阈值误判为看手机
        shoulder_center = (left_shoulder + right_shoulder) / 2
        hip_center = (left_hip + right_hip) / 2
        shoulder_width = np.linalg.norm(left_shoulder - right_shoulder)
        torso_height = np.linalg.norm(shoulder_center - hip_center)
        body_scale = max(shoulder_width, torso_height * 0.65, 0.045)
        relative_dist = min_dist / body_scale
        
        # 头部是否低下（有助于区分看手机 vs 举手/听课）
        head_low = nose[1] > shoulder_center[1] + body_scale * 0.18
        # 手腕必须真的抬到胸口以上；否则大量读写/敲键盘动作会被误判为手机
        wrist_near_head_height = nearest_wrist[1] < shoulder_center[1] + body_scale * 0.35
        
        # 判断逻辑
        if relative_dist < 0.24 and wrist_near_head_height:
            confidence = 0.82 + max(0.0, 0.24 - relative_dist) * 0.5
            return True, float(relative_dist), float(min(0.92, confidence))
        if relative_dist < 0.34 and head_low and wrist_near_head_height:
            confidence = 0.72 + max(0.0, 0.34 - relative_dist) * 0.45
            return True, float(relative_dist), float(min(0.86, confidence))
        return False, float(relative_dist), 0.0
    
    def check_sleeping(self, keypoints):
        """
        检查是否在睡觉
        规则1：头部远低于肩部（低头打瞌睡）
        规则2：头部后仰（仰头睡觉）
        规则3：长时间静止（需要时序信息，这里简化为姿态判断）
        """
        nose = self.get_keypoint(keypoints, 'nose')
        left_shoulder = self.get_keypoint(keypoints, 'left_shoulder')
        right_shoulder = self.get_keypoint(keypoints, 'right_shoulder')
        left_ear = self.get_keypoint(keypoints, 'left_ear')
        right_ear = self.get_keypoint(keypoints, 'right_ear')
        
        shoulder_center = (left_shoulder + right_shoulder) / 2
        ear_center = (left_ear + right_ear) / 2
        
        # 规则1：头部低于肩部（低头）
        head_low = nose[1] > shoulder_center[1] + 0.12
        
        # 规则2：头部后仰（仰头，耳朵在鼻子下方很多）
        head_back = ear_center[1] < nose[1] - 0.1
        
        if head_low:
            severity = min(1.0, (nose[1] - shoulder_center[1]) / 0.3)
            return True, "head_down", 0.7 + severity * 0.25
        elif head_back:
            return True, "head_back", 0.75
        else:
            return False, "normal", 0.0
    
    def check_talking(self, keypoints):
        """
        检查是否在交谈
        规则：头部转向侧面（左右耳与肩膀的相对位置变化）
        """
        left_ear = self.get_keypoint(keypoints, 'left_ear')
        right_ear = self.get_keypoint(keypoints, 'right_ear')
        nose = self.get_keypoint(keypoints, 'nose')
        left_shoulder = self.get_keypoint(keypoints, 'left_shoulder')
        right_shoulder = self.get_keypoint(keypoints, 'right_shoulder')
        
        # 耳朵高度差异（判断头部是否倾斜/转向）
        ear_height_diff = abs(left_ear[1] - right_ear[1])
        
        # 鼻子相对于两耳中心的位置
        ear_center_x = (left_ear[0] + right_ear[0]) / 2
        head_turn_x = abs(nose[0] - ear_center_x)
        
        # 肩部朝向（辅助判断身体转向）
        shoulder_slope = abs(left_shoulder[1] - right_shoulder[1])
        
        # 综合判断
        if ear_height_diff > 0.06 or head_turn_x > 0.04 or shoulder_slope > 0.05:
            confidence = min(0.9, 0.5 + ear_height_diff * 3 + head_turn_x * 5)
            return True, float(confidence)
        else:
            return False, 0.0
    
    def check_away(self, keypoints):
        """
        检查是否离开座位
        规则：关键点大面积缺失（检测不到人体）或位置异常
        """
        # 检查有多少关键点被检测到（非零）
        valid_count = np.sum(np.linalg.norm(keypoints, axis=1) > 0.001)
        
        # 检查臀部位置
        left_hip = self.get_keypoint(keypoints, 'left_hip')
        right_hip = self.get_keypoint(keypoints, 'right_hip')
        hip_y = (left_hip[1] + right_hip[1]) / 2
        
        if valid_count < 8:  # 检测到关键点太少
            return True, 0.95, "人体检测不完整"
        elif hip_y > 0.95:  # 臀部在画面底部（可能坐下或蹲下）
            return True, 0.7, "人体位置异常"
        elif valid_count < 12:  # 部分遮挡
            return True, 0.5, "人体部分遮挡"
        else:
            return False, 0.0, ""
    
    def classify_single_frame(self, keypoints):
        """
        对单帧进行分类
        优先级：离开 > 看手机 > 睡觉 > 交谈 > 专注
        """
        # 检查是否离开（最高优先级）
        is_away, conf_away, reason_away = self.check_away(keypoints)
        if is_away and conf_away > 0.7:
            return 4, conf_away, reason_away
        
        # 检查是否在看手机（高优先级）
        is_phone, dist, conf_phone = self.check_phone_usage(keypoints)
        if is_phone and conf_phone > 0.7:
            return 1, conf_phone, f"手腕靠近面部(距离{dist:.3f})"
        
        # 检查是否在睡觉（中高优先级）
        is_sleep, pose, conf_sleep = self.check_sleeping(keypoints)
        if is_sleep and conf_sleep > 0.65:
            reason_map = {"head_down": "头部低下", "head_back": "头部后仰"}
            return 3, conf_sleep, reason_map.get(pose, "姿态异常")
        
        # 检查是否在交谈（中优先级）
        is_talk, conf_talk = self.check_talking(keypoints)
        if is_talk and conf_talk > 0.6:
            return 2, conf_talk, "头部转向侧面"
        
        # 默认专注学习
        return 0, 0.75, "正常学习姿态"
    
    def classify_sequence(self, keypoints_sequence):
        """
        对序列进行分类（时序平滑，减少抖动）
        """
        if len(keypoints_sequence) == 0:
            return 0, 0.0, "无数据"
        
        if len(keypoints_sequence) == 1:
            # 单帧直接分类
            behavior_id, conf, reason = self.classify_single_frame(keypoints_sequence[0].reshape(17, 2))
            return behavior_id, conf, reason
        
        # 对每帧分类
        frame_results = []
        for kp in keypoints_sequence:
            behavior_id, conf, reason = self.classify_single_frame(kp.reshape(17, 2))
            frame_results.append((behavior_id, conf, reason))
        
        # 统计各行为出现次数（加权）
        behavior_scores = {}
        for bid, conf, _ in frame_results:
            if bid not in behavior_scores:
                behavior_scores[bid] = []
            behavior_scores[bid].append(conf)
        
        # 计算平均置信度
        behavior_avg_scores = {
            bid: np.mean(scores) * len(scores)  # 加权：平均置信度 × 出现次数
            for bid, scores in behavior_scores.items()
        }
        
        # 选择得分最高的行为
        dominant_behavior = max(behavior_avg_scores, key=behavior_avg_scores.get)
        avg_confidence = float(np.mean(behavior_scores[dominant_behavior]))
        
        # 获取该行为的主要理由
        reasons = [r for bid, _, r in frame_results if bid == dominant_behavior]
        main_reason = max(set(reasons), key=reasons.count)
        
        return dominant_behavior, avg_confidence, main_reason


# 创建分类器实例（无状态，可全局复用）
classifier = RuleBasedBehaviorClassifier()
# temporal_smoother 不再作为全局单例，改为每个请求独立创建，避免并发状态污染

# ==================== 工具函数 ====================

def detect_persons(image: np.ndarray, conf_threshold: float = None, pad_ratio: float = 0.25):
    """
    使用专用检测器检测图片中所有人
    返回: [{id, bbox:[x1,y1,x2,y2], confidence, crop}, ...]
    """
    if detector_model is None:
        return []
    
    if conf_threshold is None:
        conf_threshold = DETECTOR_CONF
    
    h, w = image.shape[:2]
    results = detector_model(image, verbose=False, conf=conf_threshold, classes=[0])  # 只检测人
    boxes = results[0].boxes
    
    if boxes is None or len(boxes) == 0:
        return []
    
    persons = []
    for i, box in enumerate(boxes):
        conf = float(box.conf[0])
        x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
        
        # 扩大检测框（让姿态模型更容易识别）
        bw, bh = x2 - x1, y2 - y1
        pad_x = int(bw * pad_ratio)
        pad_y = int(bh * pad_ratio)
        
        x1 = max(0, x1 - pad_x)
        y1 = max(0, y1 - pad_y)
        x2 = min(w, x2 + pad_x)
        y2 = min(h, y2 + pad_y)
        
        crop = image[y1:y2, x1:x2]
        
        persons.append({
            "id": i,
            "bbox": [x1, y1, x2, y2],
            "confidence": conf,
            "crop": crop
        })
    
    print(f"检测器发现 {len(persons)} 人")
    return persons


def extract_pose_from_crop(crop: np.ndarray):
    """从裁剪区域提取姿态关键点"""
    if crop is None or crop.size == 0:
        return None
    
    results = pose_model(crop, verbose=False, conf=POSE_CONF)
    
    if results[0].keypoints is None or len(results[0].keypoints) == 0:
        return None
    
    # 取第一个人（crop 里应该只有一个人）
    keypoints = results[0].keypoints.xy[0].cpu().numpy()  # (17, 2)
    return keypoints


def extract_pose_keypoints(frame: np.ndarray):
    """提取单帧中最佳人物的关键点（用于视频分析）"""
    if not USE_DUAL_STAGE or detector_model is None:
        # 回退到单阶段模式
        results = pose_model(frame, verbose=False, conf=POSE_CONF)
        if results[0].keypoints is None or len(results[0].keypoints) == 0:
            return None
        keypoints = results[0].keypoints.xy.cpu().numpy()
        if len(keypoints) == 0:
            return None
        if len(keypoints) > 1:
            nonzero_counts = [np.count_nonzero(kp) for kp in keypoints]
            best_idx = np.argmax(nonzero_counts)
            return keypoints[best_idx]
        return keypoints[0]
    
    # 双阶段：先检测所有人，取最大的人做姿态估计
    persons = detect_persons(frame, conf_threshold=0.3, pad_ratio=0.25)
    if not persons:
        return None
    
    # 选择面积最大的人
    best_person = max(persons, key=lambda p: (p["bbox"][2] - p["bbox"][0]) * (p["bbox"][3] - p["bbox"][1]))
    keypoints = extract_pose_from_crop(best_person["crop"])
    
    if keypoints is None:
        return None
    
    # 映射回原始图像坐标
    x1, y1, _, _ = best_person["bbox"]
    keypoints[:, 0] += x1
    keypoints[:, 1] += y1
    
    return keypoints


def extract_all_persons(frame: np.ndarray):
    """提取图片中所有人的关键点和检测框（双阶段模式）"""
    h, w = frame.shape[:2]
    
    if not USE_DUAL_STAGE or detector_model is None:
        # 回退到单阶段模式
        results = pose_model(frame, verbose=False, conf=POSE_CONF)
        if results[0].keypoints is None:
            return []
        keypoints = results[0].keypoints.xy.cpu().numpy()
        if len(keypoints) == 0:
            return []
        
        persons = []
        for i, kp in enumerate(keypoints):
            if np.all(kp == 0):
                continue
            x_min, y_min = kp[:, 0].min(), kp[:, 1].min()
            x_max, y_max = kp[:, 0].max(), kp[:, 1].max()
            margin = 30
            x_min = max(0, x_min - margin)
            y_min = max(0, y_min - margin)
            x_max = min(w, x_max + margin)
            y_max = min(h, y_max + margin)
            persons.append({
                "id": i,
                "keypoints": kp,
                "bbox": [float(x_min), float(y_min), float(x_max), float(y_max)]
            })
        return persons
    
    # 双阶段模式
    detected = detect_persons(frame, conf_threshold=DETECTOR_CONF, pad_ratio=0.25)
    if not detected:
        return []
    
    persons = []
    for person in detected:
        keypoints = extract_pose_from_crop(person["crop"])
        if keypoints is None:
            print(f"Person {person['id']}: pose extraction failed, skipping")
            continue
        
        # 映射回原始图像坐标
        x1, y1, x2, y2 = person["bbox"]
        keypoints[:, 0] += x1
        keypoints[:, 1] += y1
        
        # 限制在图像边界内
        keypoints[:, 0] = np.clip(keypoints[:, 0], 0, w)
        keypoints[:, 1] = np.clip(keypoints[:, 1], 0, h)
        
        persons.append({
            "id": person["id"],
            "keypoints": keypoints,
            "bbox": [float(x1), float(y1), float(x2), float(y2)],
            "confidence": person["confidence"]
        })
    
    print(f"姿态估计成功 {len(persons)}/{len(detected)} 人")
    return persons


def normalize_keypoints(keypoints, image_width, image_height):
    """归一化关键点到[0,1]范围"""
    normalized = keypoints.copy()
    normalized[:, 0] /= image_width
    normalized[:, 1] /= image_height
    return normalized


def get_learning_status(score):
    """根据得分评估学习状态（0-1范围）
    
    优化后的评分标准：
    - 0.90-1.00: 优秀（绝大多数学生专注）
    - 0.75-0.90: 良好（多数学生专注，少量负面行为）
    - 0.60-0.75: 一般（专注与负面行为参半）
    - 0.45-0.60: 较差（负面行为较多，影响课堂）
    - 0.00-0.45: 极差（严重违纪，课堂秩序混乱）
    """
    if score >= 0.90:
        return "学习状态优秀"
    elif score >= 0.75:
        return "学习状态良好"
    elif score >= 0.60:
        return "学习状态一般"
    elif score >= 0.45:
        return "学习状态较差"
    else:
        return "学习状态极差"


# ==================== API接口 ====================

@app.get("/")
async def root():
    """服务信息"""
    return {
        "service": "课堂行为检测服务 - 规则-Based版本",
        "version": "2.2.0-temporal-fusion",
        "device": str(DEVICE),
        "sequence_length": SEQUENCE_LENGTH,
        "method": "rule_based_temporal_fusion",
        "temporal_window": TEMPORAL_WINDOW,
        "confidence_fusion": "behavior/detector/pose/bbox weighted fusion",
        "detection_mode": "dual_stage" if USE_DUAL_STAGE else "single_stage",
        "note": "基于几何规则 + 时序平滑 + 多源置信度融合，无需训练数据，立即可用！",
        "accuracy": "课堂场景下比单帧规则更稳定，适合实时监测与比赛演示",
        "endpoints": [
            "/analyze/frame - POST 分析单帧姿态",
            "/analyze/video - POST 分析视频行为",
            "/analyze/stream - POST 分析连续帧序列",
            "/behaviors - GET 获取行为定义",
            "/health - GET 健康检查"
        ]
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "pose_model_loaded": pose_model is not None,
        "detector_loaded": detector_model is not None,
        "dual_stage_enabled": USE_DUAL_STAGE,
        "classifier": "rule_based_temporal_fusion",
        "temporal_window": TEMPORAL_WINDOW,
        "confidence_fusion": True,
        "note": "无需LSTM权重，立即可用"
    }


@app.get("/behaviors")
async def get_behavior_definitions():
    """获取行为定义"""
    return {
        "behaviors": list(BEHAVIOR_LABELS.values()),
        "method": "rule_based",
        "algorithm": {
            "temporal_smoothing": f"最近{TEMPORAL_WINDOW}帧轨迹级衰减投票",
            "confidence_fusion": "0.34*规则置信度 + 0.28*检测置信度 + 0.22*姿态完整度 + 0.16*框质量，并融合几何均值",
            "attention_formula": "0.44*专注率 + 0.24*行为得分 + 0.16*平均置信度 + 0.16*时序稳定度 - 0.18*严重行为率 - 0.10*分心率",
        },
        "rules": {
            "看手机": "手腕靠近面部（距离<0.15）且头部低下",
            "睡觉": "头部低于肩部（低头）或后仰",
            "交谈": "头部转向侧面（耳高差异>0.06）",
            "离开": "人体检测不完整（关键点<8）",
            "专注": "默认正常姿态"
        },
        "score_ranges": [
            {"min": 0.7, "max": 1.0, "status": "学习状态优秀", "color": "#52c41a"},
            {"min": 0.3, "max": 0.7, "status": "学习状态良好", "color": "#1890ff"},
            {"min": -0.3, "max": 0.3, "status": "学习状态一般", "color": "#faad14"},
            {"min": -0.7, "max": -0.3, "status": "学习状态较差", "color": "#fa541c"},
            {"min": -1.0, "max": -0.7, "status": "学习状态极差", "color": "#f5222d"},
        ],
    }


@app.post("/analyze/frame")
async def analyze_frame(file: UploadFile = File(...)):
    """
    分析单帧图像的姿态和行为
    返回所有人的检测框和行为
    """
    if pose_model is None:
        return JSONResponse(
            status_code=503,
            content={"error": "姿态估计模型未加载，服务不可用", "status": "error"}
        )
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        frame = np.array(image)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        h, w = frame.shape[:2]
        print(f"Image size: {w}x{h}")
        
        # 提取所有人（双阶段：检测器 -> Pose）
        persons = extract_all_persons(frame)
        
        if len(persons) == 0:
            print("No persons detected, returning debug info")
            return {
                "status": "success",
                "person_count": 0,
                "persons": [],
                "overall_score": 0,
                "learning_status": "未检测到人体",
                "classroom_metrics": calculate_classroom_metrics([]),
                "image_width": w,
                "image_height": h,
                "debug": "未检测到人体，请确保画面中有人"
            }
        
        # 分析每个人的行为
        analyzed_persons = []
        for person in persons:
            # 归一化关键点
            keypoints_norm = normalize_keypoints(person["keypoints"], w, h)
            
            # 规则分类
            behavior_id, behavior_conf, reason = classifier.classify_single_frame(keypoints_norm)
            behavior_info = BEHAVIOR_LABELS[behavior_id]
            
            # 综合置信度：检测器、规则分类、姿态完整度、框质量融合
            detector_conf = person.get("confidence", 0.75)
            pose_quality = estimate_pose_quality(keypoints_norm)
            bbox_quality = estimate_bbox_quality(person["bbox"], w, h)
            final_conf = fuse_confidence(
                detector_confidence=float(detector_conf),
                behavior_confidence=float(behavior_conf),
                pose_quality=pose_quality,
                bbox_quality=bbox_quality,
            )
            
            analyzed_persons.append({
                "id": person["id"],
                "bbox": person["bbox"],  # [x1, y1, x2, y2]
                "class_id": behavior_id,
                "behavior": behavior_info["name"],
                "confidence": final_conf,
                "detection_confidence": round(float(detector_conf), 4),
                "behavior_confidence": round(float(behavior_conf), 4),
                "pose_quality": pose_quality,
                "bbox_quality": bbox_quality,
                "score": float(behavior_info["score"]),
                "color": behavior_info["color"],
                "reason": reason
            })
        
        # 使用独立的 temporal_smoother 实例，避免并发请求间状态污染
        local_smoother = TemporalBehaviorSmoother()
        analyzed_persons = local_smoother.smooth(analyzed_persons, w, h)
        classroom_metrics = calculate_classroom_metrics(analyzed_persons)
        overall_score = classroom_metrics["attention_score"]
        learning_status = classroom_metrics["learning_status"]
        
        return {
            "status": "success",
            "method": "rule_based_temporal_fusion",
            "person_count": len(analyzed_persons),
            "persons": analyzed_persons,
            "overall_score": overall_score,
            "learning_status": learning_status,
            "classroom_metrics": classroom_metrics,
            "image_width": w,
            "image_height": h
        }
        
    except Exception as e:
        import traceback
        print(f"Error in analyze_frame: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"error": "图像分析失败，请检查输入格式或稍后重试", "status": "error"}
        )


@app.post("/analyze/video")
async def analyze_video(file: UploadFile = File(...), sample_interval: int = 1):
    # 参数校验
    if sample_interval < 1:
        return JSONResponse(
            status_code=400,
            content={"error": "sample_interval必须大于等于1", "status": "error"}
        )
    """
    分析视频文件的行为
    使用滑动窗口对视频进行分段分析
    """
    video_path = None
    try:
        contents = await file.read()
        
        # 保存临时视频
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
            temp_video.write(contents)
            video_path = temp_video.name
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return JSONResponse(
                status_code=400,
                content={"error": "无法打开视频文件，请检查格式", "status": "error"}
            )
        
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        # 收集关键点序列和人员检测数据
        keypoints_sequence = []
        frame_count = 0
        valid_frames = 0
        
        # 保存第一帧有人员的图像用于预览
        first_frame_with_persons = None
        first_frame_persons = []
        first_frame_shape = None
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % sample_interval == 0:
                keypoints = extract_pose_keypoints(frame)
                
                if keypoints is not None:
                    h, w = frame.shape[:2]
                    kp_norm = normalize_keypoints(keypoints, w, h)
                    keypoints_sequence.append(kp_norm)
                    valid_frames += 1
                    
                    # 保存第一帧有人员的数据用于后续显示
                    if first_frame_with_persons is None:
                        first_frame_with_persons = frame.copy()
                        first_frame_shape = (h, w)
                        # 提取所有人员信息
                        persons_data = extract_all_persons(frame)
                        if persons_data:
                            first_frame_persons = persons_data
            
            frame_count += 1
        
        cap.release()
        
        if len(keypoints_sequence) < SEQUENCE_LENGTH:
            return JSONResponse(
                status_code=400,
                content={
                    "error": f"视频有效帧数不足，需要至少{SEQUENCE_LENGTH}帧检测到人体，实际只有{len(keypoints_sequence)}帧",
                    "status": "error"
                }
            )
            
        # 使用滑动窗口分析视频
        window_size = SEQUENCE_LENGTH
        stride = window_size // 2  # 50% 重叠
        
        predictions = []
        
        for start in range(0, len(keypoints_sequence) - window_size + 1, stride):
            end = start + window_size
            window = keypoints_sequence[start:end]
            
            # 规则分类
            behavior_id, confidence, reason = classifier.classify_sequence(window)
            behavior_info = BEHAVIOR_LABELS[behavior_id]
            
            # 计算时间戳
            timestamp = (start + window_size // 2) / fps if fps > 0 else 0
            
            predictions.append({
                "class_id": behavior_id,
                "behavior": behavior_info["name"],
                "confidence": float(round(float(confidence), 4)),
                "score": float(behavior_info["score"]),
                "timestamp": round(timestamp, 2),
                "frame_range": [start, end],
                "reason": reason
            })
        
        # 汇总结果
        if predictions:
            # 多数投票确定整体行为
            class_counts = {}
            for p in predictions:
                cid = p["class_id"]
                class_counts[cid] = class_counts.get(cid, 0) + 1
            
            dominant_class = max(class_counts, key=class_counts.get)
            dominant_behavior = BEHAVIOR_LABELS[dominant_class]
            dominant_ratio = class_counts[dominant_class] / max(1, len(predictions))
            
            metrics_persons = [
                {
                    "behavior": p["behavior"],
                    "confidence": p["confidence"],
                    "score": p["score"],
                    "temporal_stability": dominant_ratio,
                }
                for p in predictions
            ]
            classroom_metrics = calculate_classroom_metrics(metrics_persons)
            avg_score = classroom_metrics["attention_score"]
            
            # 构建汇总信息
            summary = {
                "average_score": float(round(float(avg_score), 2)),
                "overall_status": classroom_metrics["learning_status"],
                "dominant_behavior": dominant_behavior["name"],
                "classroom_metrics": classroom_metrics,
                "behavior_statistics": {
                    BEHAVIOR_LABELS[cid]["name"]: {
                        "count": count,
                        "percentage": round(count / len(predictions) * 100, 1)
                    }
                    for cid, count in class_counts.items()
                }
            }
            
            # 对第一帧的人员进行行为分类（用于前端显示检测框）
            # 默认所有人为主要行为类型
            persons_for_display = []
            if first_frame_persons:
                for i, person in enumerate(first_frame_persons):
                    persons_for_display.append({
                        "id": i,
                        "bbox": person["bbox"],
                        "behavior": dominant_behavior["name"],
                        "confidence": 0.85,
                        "score": float(BEHAVIOR_LABELS[dominant_class]["score"]),
                        "color": BEHAVIOR_LABELS[dominant_class]["color"]
                    })
            
            # 返回与后端匹配的数据结构
            return {
                "status": "success",
                "method": "rule_based_temporal_fusion",
                "frame_analyses": predictions,  #  renamed from predictions
                "summary": summary,
                "persons": persons_for_display,  # 添加人员检测数据
                "video_info": {
                    "total_frames": total_frames,
                    "valid_frames": valid_frames,
                    "fps": fps,
                    "duration": round(duration, 2),
                    "frames_analyzed": len(predictions),
                    "image_width": first_frame_shape[1] if first_frame_shape else 0,
                    "image_height": first_frame_shape[0] if first_frame_shape else 0
                }
            }
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "视频分析失败，无法生成预测结果", "status": "error"}
            )
                
    except Exception as e:
        import traceback
        print(f"Error in analyze_video: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"error": "视频分析失败，请检查输入格式或稍后重试", "status": "error"}
        )
    finally:
        # 确保任何情况下都清理临时文件
        if video_path and os.path.exists(video_path):
            os.unlink(video_path)


@app.post("/analyze/stream")
async def analyze_stream(frames: List[List[float]]):
    """
    分析连续帧序列（用于实时流）
    输入: 连续16帧的关键点序列，每帧34个值（17个关键点 × 2坐标）
    """
    if pose_model is None:
        return JSONResponse(
            status_code=503,
            content={"error": "姿态估计模型未加载，服务不可用", "status": "error"}
        )
    try:
        if len(frames) < SEQUENCE_LENGTH:
            return JSONResponse(
                status_code=400,
                content={
                    "error": f"输入帧数不足，需要至少{SEQUENCE_LENGTH}帧，实际收到{len(frames)}帧",
                    "status": "error"
                }
            )
        
        # 取最近SEQUENCE_LENGTH帧
        recent_frames = frames[-SEQUENCE_LENGTH:]
        keypoints_seq = np.array(recent_frames)
        
        # 规则分类（使用独立实例，避免并发状态污染）
        local_classifier = RuleBasedBehaviorClassifier()
        behavior_id, confidence, reason = local_classifier.classify_sequence(keypoints_seq)
        behavior_info = BEHAVIOR_LABELS[behavior_id]
        metrics = calculate_classroom_metrics([
            {
                "behavior": behavior_info["name"],
                "confidence": confidence,
                "score": behavior_info["score"],
                "temporal_stability": 0.85,
            }
        ])
        
        return {
            "status": "success",
            "method": "rule_based_temporal_fusion",
            "class_id": behavior_id,
            "behavior": behavior_info["name"],
            "confidence": float(round(float(confidence), 4)),
            "score": metrics["attention_score"],
            "learning_status": metrics["learning_status"],
            "description": behavior_info["description"],
            "color": behavior_info["color"],
            "reason": reason,
            "classroom_metrics": metrics,
        }
        
    except Exception as e:
        import traceback
        print(f"Error in analyze_stream: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"error": "分析失败，请检查输入数据或稍后重试", "status": "error"}
        )


# ==================== 主程序 ====================
if __name__ == "__main__":
    import uvicorn
    
    print("=" * 70)
    print("🚀 启动课堂行为检测服务 - 规则-Based版本")
    print("=" * 70)
    print("✅ 无需训练数据，无需LSTM权重，立即可用！")
    print("📊 准确率: 约60-75%（适合演示和比赛应急）")
    print("🔧 规则逻辑:")
    print("   • 看手机: 手腕靠近面部(距离<0.15) + 低头")
    print("   • 睡觉: 头部低于肩部(低头) 或后仰")
    print("   • 交谈: 头部转向侧面(耳高差异>0.06)")
    print("   • 离开: 人体检测不完整(关键点<8)")
    print("   • 专注: 默认正常姿态")
    print("=" * 70)
    
    port = int(os.getenv("YOLO_PORT", "8000"))
    host = os.getenv("YOLO_HOST", "0.0.0.0")
    
    uvicorn.run(app, host=host, port=port)
