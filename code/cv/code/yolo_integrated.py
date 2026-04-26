"""
课堂行为检测服务 - 完整集成版（检测+行为识别）
运行: uvicorn yolo_integrated:app --host 0.0.0.0 --port 8000

功能:
1. 阶段1: YOLO检测器检测教室中所有人
2. 阶段2: 对每个人做姿态估计
3. 阶段3: 对每个人做行为识别（规则/LSTM）
4. 返回每个人的位置+行为+学习状态评分

支持两种模式:
- 快速模式: 直接使用YOLOv8-Pose（无需额外检测模型）
- 双模型模式: YOLO检测 + YOLO-Pose姿态（如果队友有训练好的检测器）
"""
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from ultralytics import YOLO
from PIL import Image
import io
import os
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple
import tempfile
from collections import deque
from datetime import datetime
import torch

app = FastAPI(title="课堂行为检测服务 - 完整集成版")

# ==================== 配置 ====================
# 模式选择
MODE = os.getenv("DETECTION_MODE", "fast")  # "fast" 或 "dual"

# 模型路径：检测器支持 yolov8n / yolo11n / yolo11m / yolo11l 等
# 推荐教室场景：yolo11m（平衡）或 yolo11l（高精度）
POSE_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "../model/yolov8n-pose.pt")
DETECTOR_MODEL_PATH = os.getenv("DETECTOR_MODEL_PATH", "../model/yolov8n.pt")
LSTM_WEIGHTS_PATH = os.getenv("LSTM_WEIGHTS_PATH", "../behavior_lstm.pth")

# 参数
SEQUENCE_LENGTH = int(os.getenv("SEQUENCE_LENGTH", "16"))
DETECTOR_CONF = float(os.getenv("DETECTOR_CONF", "0.5"))   # 检测器置信度阈值
POSE_CONF = float(os.getenv("POSE_CONF", "0.5"))           # 姿态估计置信度阈值
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"🖥️  使用设备: {DEVICE}")
print(f"🔧 运行模式: {MODE}")
print(f"📊 序列长度: {SEQUENCE_LENGTH}")

# ==================== 加载模型 ====================

# 1. 姿态估计模型（必须）
pose_model = None
try:
    pose_model = YOLO(POSE_MODEL_PATH)
    print(f"✅ 姿态估计模型加载成功: {POSE_MODEL_PATH}")
except Exception as e:
    print(f"⚠️ 姿态模型加载失败: {e}")
    pose_model = None

# 2. 人体检测模型（可选，双模型模式使用）
# 支持 yolov8n / yolo11n / yolo11m / yolo11l 等，教室场景推荐 yolo11m 或 yolo11l
detector_model = None
if MODE == "dual":
    try:
        if os.path.exists(DETECTOR_MODEL_PATH):
            detector_model = YOLO(DETECTOR_MODEL_PATH)
            print(f"✅ 检测模型加载成功: {DETECTOR_MODEL_PATH}")
            if "yolo11" in DETECTOR_MODEL_PATH.lower():
                print("🚀 已启用 YOLO11 检测器，教室场景检测能力更强")
        else:
            print(f"⚠️ 检测模型不存在: {DETECTOR_MODEL_PATH}，使用姿态模型检测")
            print("   推荐下载并放到 code/cv/model/ 目录:")
            print("   • yolo11m.pt (平衡): https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11m.pt")
            print("   • yolo11l.pt (高精度): https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11l.pt")
            detector_model = pose_model
    except Exception as e:
        print(f"⚠️ 检测模型加载失败: {e}，使用姿态模型检测")
        detector_model = pose_model
else:
    # 快速模式：直接使用姿态模型检测人
    detector_model = pose_model
    print(f"✅ 快速模式: 使用姿态模型同时检测和估计")

# 3. LSTM行为识别模型（可选）
lstm_model = None
use_lstm = False
if os.path.exists(LSTM_WEIGHTS_PATH):
    try:
        import torch
        import torch.nn as nn
        
        class BehaviorLSTM(nn.Module):
            def __init__(self, input_size=34, hidden_size=128, num_layers=2, num_classes=5):
                super().__init__()
                self.lstm = nn.LSTM(input_size, hidden_size, num_layers, 
                                   batch_first=True, bidirectional=True)
                self.fc = nn.Sequential(
                    nn.Linear(hidden_size * 2, hidden_size),
                    nn.ReLU(),
                    nn.Dropout(0.3),
                    nn.Linear(hidden_size, num_classes)
                )
            
            def forward(self, x):
                lstm_out, (hidden, cell) = self.lstm(x)
                hidden_forward = hidden[-2]
                hidden_backward = hidden[-1]
                hidden_concat = torch.cat((hidden_forward, hidden_backward), dim=1)
                return self.fc(hidden_concat)
        
        lstm_model = BehaviorLSTM()
        lstm_model.load_state_dict(torch.load(LSTM_WEIGHTS_PATH, map_location=DEVICE))
        lstm_model.eval()
        use_lstm = True
        print(f"✅ LSTM模型加载成功: {LSTM_WEIGHTS_PATH}")
    except Exception as e:
        print(f"⚠️ LSTM模型加载失败: {e}，使用规则分类")
        use_lstm = False
else:
    print(f"ℹ️ 未找到LSTM模型，使用规则分类")

# ==================== 行为标签定义 ====================
BEHAVIOR_LABELS = {
    0: {"name": "专注学习", "score": 1.0, "description": "学习状态良好", "color": "#52c41a"},
    1: {"name": "查看手机", "score": -0.5, "description": "注意力分散", "color": "#faad14"},
    2: {"name": "与他人交谈", "score": -0.3, "description": "可能影响他人学习", "color": "#fa8c16"},
    3: {"name": "睡觉", "score": -1.0, "description": "未在学习", "color": "#f5222d"},
    4: {"name": "离开座位", "score": -0.8, "description": "未在学习区域", "color": "#eb2f96"},
}

# COCO关键点索引
KEYPOINT_DICT = {
    'nose': 0, 'left_eye': 1, 'right_eye': 2, 'left_ear': 3, 'right_ear': 4,
    'left_shoulder': 5, 'right_shoulder': 6, 'left_elbow': 7, 'right_elbow': 8,
    'left_wrist': 9, 'right_wrist': 10, 'left_hip': 11, 'right_hip': 12,
    'left_knee': 13, 'right_knee': 14, 'left_ankle': 15, 'right_ankle': 16,
}

# ==================== 工具函数 ====================

def detect_all_persons(image: np.ndarray) -> List[Dict]:
    """
    检测图片中所有人
    返回: [{bbox: [x1,y1,x2,y2], confidence: float, person_id: int}, ...]
    """
    persons = []
    
    if detector_model is None:
        return persons
    
    # 使用检测模型检测人
    results = detector_model(image, verbose=False)
    
    if MODE == "dual" and detector_model != pose_model:
        # 双模型模式：使用专用检测器
        boxes = results[0].boxes
        for i, box in enumerate(boxes):
            conf = float(box.conf[0])
            if conf < DETECTOR_CONF:
                continue
            
            xyxy = box.xyxy[0].cpu().numpy().astype(int)
            persons.append({
                "bbox": xyxy.tolist(),  # [x1, y1, x2, y2]
                "confidence": conf,
                "person_id": i
            })
    else:
        # 快速模式：使用姿态模型的检测结果
        if results[0].boxes is not None:
            boxes = results[0].boxes
            for i, box in enumerate(boxes):
                conf = float(box.conf[0])
                if conf < DETECTOR_CONF:
                    continue
                
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                persons.append({
                    "bbox": xyxy.tolist(),
                    "confidence": conf,
                    "person_id": i
                })
    
    return persons


def extract_pose_from_crop(image: np.ndarray, bbox: List[int]) -> Tuple[np.ndarray, bool]:
    """
    从裁剪区域提取姿态关键点
    返回: (keypoints_normalized, success)
    """
    x1, y1, x2, y2 = bbox
    h, w = image.shape[:2]
    
    # 边界检查
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    
    if x2 <= x1 or y2 <= y1:
        return None, False
    
    # 裁剪
    crop = image[y1:y2, x1:x2]
    if crop.size == 0:
        return None, False
    
    # 姿态估计
    results = pose_model(crop, verbose=False)
    
    if results[0].keypoints is None or len(results[0].keypoints) == 0:
        return None, False
    
    # 获取关键点
    keypoints = results[0].keypoints.xy[0].cpu().numpy()  # (17, 2)
    
    # 转换回原始图像坐标
    keypoints_orig = keypoints.copy()
    keypoints_orig[:, 0] += x1
    keypoints_orig[:, 1] += y1
    
    # 归一化到0-1
    keypoints_norm = keypoints_orig.copy()
    keypoints_norm[:, 0] /= w
    keypoints_norm[:, 1] /= h
    
    return keypoints_norm, True


class RuleBasedClassifier:
    """规则分类器（备用）"""
    
    def classify(self, keypoints: np.ndarray) -> Tuple[int, float, str]:
        """返回: (behavior_id, confidence, reason)"""
        nose = keypoints[0]
        left_wrist = keypoints[9]
        right_wrist = keypoints[10]
        left_shoulder = keypoints[5]
        right_shoulder = keypoints[6]
        
        shoulder_center = (left_shoulder + right_shoulder) / 2
        
        # 检查手机
        left_dist = np.linalg.norm(left_wrist - nose)
        right_dist = np.linalg.norm(right_wrist - nose)
        min_dist = min(left_dist, right_dist)
        head_low = nose[1] > shoulder_center[1] + 0.05
        
        if min_dist < 0.15 and head_low:
            return 1, 0.9, f"手腕靠近面部(距离{min_dist:.3f})"
        
        # 检查睡觉
        if nose[1] > shoulder_center[1] + 0.12:
            return 3, 0.85, "头部低下"
        
        # 检查交谈
        left_ear = keypoints[3]
        right_ear = keypoints[4]
        ear_height_diff = abs(left_ear[1] - right_ear[1])
        if ear_height_diff > 0.06:
            return 2, 0.7, "头部转向"
        
        # 默认专注
        return 0, 0.75, "正常姿态"


def recognize_behavior(keypoints: np.ndarray) -> Dict[str, Any]:
    """
    识别行为
    返回: {class_id, behavior, confidence, score, description, color, reason}
    """
    if use_lstm and lstm_model is not None:
        # 使用LSTM模型（如果有）
        try:
            import torch
            # 单帧输入，复制成序列
            flat = keypoints.flatten()
            # 维度校验：必须是 17×2=34 维
            if flat.shape[0] != 34:
                raise ValueError(f"关键点维度异常: {flat.shape[0]}，期望34")
            seq = np.tile(flat, (SEQUENCE_LENGTH, 1))
            input_tensor = torch.FloatTensor(seq).unsqueeze(0).to(DEVICE)
            
            with torch.no_grad():
                output = lstm_model(input_tensor)
                probs = torch.softmax(output, dim=1)
                pred_class = torch.argmax(probs, dim=1).item()
                confidence = float(probs[0][pred_class])
            
            behavior_info = BEHAVIOR_LABELS[pred_class]
            return {
                "class_id": pred_class,
                "behavior": behavior_info["name"],
                "confidence": round(confidence, 4),
                "score": behavior_info["score"],
                "description": behavior_info["description"],
                "color": behavior_info["color"],
                "reason": "LSTM预测",
                "method": "lstm"
            }
        except Exception as e:
            # LSTM失败，回退到规则
            pass
    
    # 使用规则分类
    classifier = RuleBasedClassifier()
    behavior_id, confidence, reason = classifier.classify(keypoints)
    behavior_info = BEHAVIOR_LABELS[behavior_id]
    
    return {
        "class_id": behavior_id,
        "behavior": behavior_info["name"],
        "confidence": round(confidence, 4),
        "score": behavior_info["score"],
        "description": behavior_info["description"],
        "color": behavior_info["color"],
        "reason": reason,
        "method": "rule_based"
    }


def calculate_classroom_stats(person_results: List[Dict]) -> Dict:
    """计算教室整体统计"""
    if not person_results:
        return {
            "total_students": 0,
            "average_score": 0,
            "learning_status": "无数据"
        }
    
    total = len(person_results)
    scores = [p["behavior_result"]["score"] for p in person_results]
    avg_score = sum(scores) / total
    
    # 统计各类行为人数
    behavior_counts = {}
    for p in person_results:
        behavior = p["behavior_result"]["behavior"]
        behavior_counts[behavior] = behavior_counts.get(behavior, 0) + 1
    
    # 评估整体学习状态
    if avg_score >= 0.7:
        status = "整体学习状态优秀"
    elif avg_score >= 0.3:
        status = "整体学习状态良好"
    elif avg_score >= -0.3:
        status = "整体学习状态一般"
    elif avg_score >= -0.7:
        status = "整体学习状态较差"
    else:
        status = "整体学习状态极差"
    
    return {
        "total_students": total,
        "average_score": round(avg_score, 2),
        "learning_status": status,
        "behavior_distribution": behavior_counts,
        "focused_count": behavior_counts.get("专注学习", 0),
        "phone_count": behavior_counts.get("查看手机", 0),
        "talking_count": behavior_counts.get("与他人交谈", 0),
        "sleeping_count": behavior_counts.get("睡觉", 0),
        "away_count": behavior_counts.get("离开座位", 0)
    }


# ==================== API接口 ====================

@app.get("/")
async def root():
    return {
        "service": "课堂行为检测服务 - 完整集成版（检测+行为识别）",
        "version": "3.0.0",
        "mode": MODE,
        "device": DEVICE,
        "features": {
            "person_detection": detector_model is not None,
            "pose_estimation": pose_model is not None,
            "behavior_recognition": "lstm" if use_lstm else "rule_based"
        },
        "endpoints": [
            "/analyze/classroom - POST 分析整个教室",
            "/analyze/person - POST 分析单个人",
            "/health - GET 健康检查"
        ]
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "mode": MODE,
        "detector_loaded": detector_model is not None,
        "pose_model_loaded": pose_model is not None,
        "lstm_loaded": use_lstm,
        "device": DEVICE
    }


@app.post("/analyze/classroom")
async def analyze_classroom(file: UploadFile = File(...)):
    """
    分析整个教室场景
    返回: 每个人的位置 + 行为 + 整体统计
    """
    if pose_model is None:
        return JSONResponse(
            status_code=503,
            content={"error": "姿态估计模型未加载，服务不可用", "status": "error"}
        )
    try:
        # 读取图片
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        img_array = np.array(image)
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        h, w = img_array.shape[:2]
        
        # 阶段1: 检测所有人
        persons = detect_all_persons(img_array)
        
        if not persons:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "warning",
                    "message": "未检测到任何人",
                    "total_students": 0
                }
            )
        
        # 阶段2&3: 对每个人提取姿态并识别行为
        person_results = []
        
        for person in persons:
            bbox = person["bbox"]
            
            # 提取姿态
            keypoints, success = extract_pose_from_crop(img_array, bbox)
            
            if not success:
                person_results.append({
                    "person_id": person["person_id"],
                    "bbox": bbox,
                    "detection_confidence": person["confidence"],
                    "status": "pose_extraction_failed",
                    "behavior_result": None
                })
                continue
            
            # 行为识别
            behavior_result = recognize_behavior(keypoints)
            
            person_results.append({
                "person_id": person["person_id"],
                "bbox": {
                    "x1": bbox[0], "y1": bbox[1], "x2": bbox[2], "y2": bbox[3],
                    "width": bbox[2] - bbox[0],
                    "height": bbox[3] - bbox[1]
                },
                "bbox_normalized": {
                    "x1": bbox[0]/w, "y1": bbox[1]/h, 
                    "x2": bbox[2]/w, "y2": bbox[3]/h
                },
                "detection_confidence": round(person["confidence"], 4),
                "keypoints": keypoints.tolist(),
                "behavior_result": behavior_result,
                "status": "success"
            })
        
        # 计算整体统计
        stats = calculate_classroom_stats([p for p in person_results if p["behavior_result"]])
        
        return {
            "status": "success",
            "mode": MODE,
            "image_info": {"width": w, "height": h},
            "total_detected": len(persons),
            "successfully_analyzed": len([p for p in person_results if p["behavior_result"]]),
            "classroom_stats": stats,
            "persons": person_results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        import traceback
        print(f"Error in analyze_classroom: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": "教室分析失败，请检查图像格式或稍后重试"
            }
        )


@app.post("/analyze/person")
async def analyze_person(file: UploadFile = File(...)):
    """
    分析单个人（已裁剪的图片）
    """
    if pose_model is None:
        return JSONResponse(
            status_code=503,
            content={"error": "姿态估计模型未加载，服务不可用", "status": "error"}
        )
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        img_array = np.array(image)
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        h, w = img_array.shape[:2]
        
        # 直接做姿态估计
        results = pose_model(img_array, verbose=False)
        
        if results[0].keypoints is None or len(results[0].keypoints) == 0:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "未检测到人体"}
            )
        
        # 获取关键点
        keypoints = results[0].keypoints.xy[0].cpu().numpy()
        keypoints_norm = keypoints.copy()
        keypoints_norm[:, 0] /= w
        keypoints_norm[:, 1] /= h
        
        # 行为识别
        behavior_result = recognize_behavior(keypoints_norm)
        
        return {
            "status": "success",
            "image_size": {"width": w, "height": h},
            "keypoints": keypoints_norm.tolist(),
            "behavior": behavior_result
        }
        
    except Exception as e:
        import traceback
        print(f"Error in analyze_person: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": "分析失败，请检查图像格式或稍后重试"}
        )


# ==================== 主程序 ====================
if __name__ == "__main__":
    import uvicorn
    
    print("=" * 70)
    print("🚀 启动课堂行为检测服务 - 完整集成版")
    print("=" * 70)
    print(f"模式: {MODE}")
    print(f"检测模型: {DETECTOR_MODEL_PATH if detector_model else 'None'}")
    print(f"姿态模型: {POSE_MODEL_PATH if pose_model else 'None'}")
    print(f"行为识别: {'LSTM' if use_lstm else '规则分类'}")
    print("=" * 70)
    print("API端点:")
    print("  POST /analyze/classroom - 分析整个教室")
    print("  POST /analyze/person    - 分析单个人")
    print("  GET  /health            - 健康检查")
    print("=" * 70)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
