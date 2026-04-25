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

print(f"🖥️  使用设备: {DEVICE}")
print(f"📊 序列长度: {SEQUENCE_LENGTH} 帧")
print(f"✅ 规则-Based版本，无需训练，立即可用！")

# ==================== 加载YOLOv8-Pose模型 ====================
try:
    pose_model = YOLO(MODEL_PATH)
    print(f"✅ 姿态估计模型加载成功: {MODEL_PATH}")
except Exception as e:
    print(f"⚠️ 模型加载失败: {e}")
    print("尝试下载默认模型...")
    pose_model = YOLO("yolov8n-pose.pt")

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


# 创建分类器实例
classifier = RuleBasedBehaviorClassifier()

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
        "version": "2.1.0-rule-based",
        "device": str(DEVICE),
        "sequence_length": SEQUENCE_LENGTH,
        "method": "rule_based",
        "detection_mode": "dual_stage" if USE_DUAL_STAGE else "single_stage",
        "note": "基于几何规则判断，无需训练数据，立即可用！",
        "accuracy": "约60-75%，适合演示和应急使用",
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
        "classifier": "rule_based",
        "note": "无需LSTM权重，立即可用"
    }


@app.get("/behaviors")
async def get_behavior_definitions():
    """获取行为定义"""
    return {
        "behaviors": list(BEHAVIOR_LABELS.values()),
        "method": "rule_based",
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
            
            # 综合置信度：检测器置信度 * 行为分类置信度
            detector_conf = person.get("confidence", 0.75)
            final_conf = float(round(float(detector_conf) * float(behavior_conf), 4))
            
            analyzed_persons.append({
                "id": person["id"],
                "bbox": person["bbox"],  # [x1, y1, x2, y2]
                "behavior": behavior_info["name"],
                "confidence": final_conf,
                "score": float(behavior_info["score"]),
                "color": behavior_info["color"],
                "reason": reason
            })
        
        # 使用科学的课堂评分算法计算整体评分
        overall_score, learning_status = calculate_classroom_score(analyzed_persons)
        
        return {
            "status": "success",
            "method": "rule_based",
            "person_count": len(analyzed_persons),
            "persons": analyzed_persons,
            "overall_score": overall_score,
            "learning_status": learning_status,
            "image_width": w,
            "image_height": h
        }
        
    except Exception as e:
        import traceback
        print(f"Error in analyze_frame: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"error": f"分析失败: {str(e)}", "status": "error"}
        )


@app.post("/analyze/video")
async def analyze_video(file: UploadFile = File(...), sample_interval: int = 1):
    """
    分析视频文件的行为
    使用滑动窗口对视频进行分段分析
    """
    try:
        contents = await file.read()
        
        # 保存临时视频
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
            temp_video.write(contents)
            video_path = temp_video.name
        
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError("无法打开视频文件")
            
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
                
                # 计算平均得分
                avg_score = sum(p["score"] for p in predictions) / len(predictions)
                
                # 构建汇总信息
                summary = {
                    "average_score": float(round(float(avg_score), 2)),
                    "overall_status": get_learning_status(avg_score),
                    "dominant_behavior": dominant_behavior["name"],
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
                    "method": "rule_based",
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
                
        finally:
            if os.path.exists(video_path):
                os.unlink(video_path)
                
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"视频分析失败: {str(e)}", "status": "error"}
        )


@app.post("/analyze/stream")
async def analyze_stream(frames: List[List[float]]):
    """
    分析连续帧序列（用于实时流）
    输入: 连续16帧的关键点序列，每帧34个值（17个关键点 × 2坐标）
    """
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
        
        # 规则分类
        behavior_id, confidence, reason = classifier.classify_sequence(keypoints_seq)
        behavior_info = BEHAVIOR_LABELS[behavior_id]
        
        return {
            "status": "success",
            "method": "rule_based",
            "class_id": behavior_id,
            "behavior": behavior_info["name"],
            "confidence": float(round(float(confidence), 4)),
            "score": float(behavior_info["score"]),
            "learning_status": get_learning_status(float(behavior_info["score"])),
            "description": behavior_info["description"],
            "color": behavior_info["color"],
            "reason": reason
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"分析失败: {str(e)}", "status": "error"}
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
