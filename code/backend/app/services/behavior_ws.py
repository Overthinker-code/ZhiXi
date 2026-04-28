import base64
import io
import os
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image
from pydantic import BaseModel, Field

try:
    from mediapipe import Image as MPImage, ImageFormat
    from mediapipe.tasks.python.vision import FaceDetector, FaceDetectorOptions
    from mediapipe.tasks.python.core.base_options import BaseOptions
    from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions, RunningMode

    MEDIAPIPE_AVAILABLE = True
    MEDIAPIPE_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - import guard for optional dependency
    MPImage = None  # type: ignore[assignment]
    ImageFormat = None  # type: ignore[assignment]
    FaceDetector = None  # type: ignore[assignment]
    FaceDetectorOptions = None  # type: ignore[assignment]
    BaseOptions = None  # type: ignore[assignment]
    FaceLandmarker = None  # type: ignore[assignment]
    FaceLandmarkerOptions = None  # type: ignore[assignment]
    RunningMode = None  # type: ignore[assignment]
    MEDIAPIPE_AVAILABLE = False
    MEDIAPIPE_IMPORT_ERROR = exc


class FrameMessage(BaseModel):
    """前端 -> 后端的帧消息"""
    type: str = Field(..., description="消息类型，固定为 'frame'")
    frame_id: int = Field(..., description="帧序号")
    timestamp: Optional[int] = Field(None, description="前端时间戳（毫秒或秒）")
    image_base64: str = Field(..., description="base64 编码的图像数据，支持 data URI")


class EducationalMetrics(BaseModel):
    """单个人员的教育学参数（基于头部姿态推导）"""
    lei: float = Field(0.0, ge=0.0, le=1.0, description="学习投入指数 Learning Engagement Index")
    bloom_level: str = Field("understand", description="布鲁姆认知层次: remember/understand/apply/analyze/evaluate/create")
    cognitive_state: str = Field("专注", description="认知状态: 深度专注/阅读书写/轻度走神/明显走神/疲劳/困惑")
    bei: float = Field(0.0, ge=0.0, le=1.0, description="身体投入指数 Body Engagement Index")
    cei: float = Field(0.0, ge=0.0, le=1.0, description="认知投入指数 Cognitive Engagement Index")
    eei: float = Field(0.0, ge=0.0, le=1.0, description="情感投入指数 Emotional Engagement Index")
    attention_deviation: float = Field(0.0, description="注意力偏离度(负值=低于基线)")
    mind_wandering: bool = Field(False, description="是否判定为走神")


class PersonResult(BaseModel):
    """单个人员检测结果"""
    track_id: str = Field(..., description="人员追踪 ID，如 person_1")
    bbox: List[int] = Field(..., description="人脸边界框 [x1, y1, x2, y2]")
    status: str = Field(..., description="状态：focused / unfocused / absent")
    score: float = Field(..., ge=0.0, le=1.0, description="专注度分数")
    behavior: Optional[str] = Field(None, description="YOLO 行为标签，如专注学习/查看手机")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="行为识别置信度")
    color: Optional[str] = Field(None, description="行为标签颜色")
    reason: Optional[str] = Field(None, description="行为判断原因")
    method: Optional[str] = Field(None, description="检测方法：yolo / fallback")
    eye_closed: Optional[bool] = Field(None, description="是否检测到闭眼（仅 FaceLandmarker 模式有效）")
    educational: Optional[EducationalMetrics] = Field(None, description="教育学参数（LEI/布鲁姆/认知状态等）")


class SummaryResult(BaseModel):
    """当前帧统计摘要"""
    focused_count: int = Field(0, description="专注人数")
    unfocused_count: int = Field(0, description="不专注人数")
    absent_count: int = Field(0, description="缺席人数")
    overall_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="综合课堂状态得分")
    attention_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="专注度指标公式得分")
    focus_rate: Optional[float] = Field(None, ge=0.0, le=1.0, description="专注率")
    stability_index: Optional[float] = Field(None, ge=0.0, le=1.0, description="时序稳定度")
    avg_lei: Optional[float] = Field(None, ge=0.0, le=1.0, description="全班平均 LEI")
    bloom_distribution: Optional[Dict[str, float]] = Field(None, description="布鲁姆层次分布")
    on_task_rate: Optional[float] = Field(None, ge=0.0, le=1.0, description="on-task 比例")
    mind_wandering_rate: Optional[float] = Field(None, ge=0.0, le=1.0, description="走神率")


class AnalysisMessage(BaseModel):
    """后端 -> 前端的分析结果消息"""
    type: str = Field("analysis", description="消息类型，固定为 'analysis'")
    frame_id: int = Field(..., description="对应帧序号")
    timestamp: int = Field(..., description="后端处理时间戳（秒）")
    persons: List[PersonResult] = Field(default_factory=list, description="检测到的人员列表")
    summary: SummaryResult = Field(default_factory=SummaryResult, description="统计摘要")
    error: Optional[str] = Field(None, description="若处理出错，返回错误描述")


class BehaviorWebSocketService:
    """
    实时行为检测服务（WebSocket 专用）
    基于 MediaPipe FaceDetector（blaze_face_short_range）
    """

    # 状态枚举（与文档统一）
    STATUS_FOCUSED = "focused"
    STATUS_UNFOCUSED = "unfocused"
    STATUS_ABSENT = "absent"

    # 帧间状态平滑阈值（避免单帧抖动）
    UNFOCUSED_THRESHOLD = 2   # 连续低头/转头 N 帧才判定为 unfocused
    FOCUSED_THRESHOLD = 2     # 连续正常 N 帧才恢复为 focused
    MAX_TRACK_DISTANCE_RATIO = 0.15  # 关联上一帧人脸的最大距离（相对于图像宽高）
    LOST_TRACK_THRESHOLD = 3  # 人脸追踪丢失 N 帧后才真正移除（低头/转头导致暂时检测不到）

    # MediaPipe 模型下载地址
    MODEL_URL = (
        "https://storage.googleapis.com/mediapipe-models/"
        "face_detector/blaze_face_short_range/float16/1/"
        "blaze_face_short_range.tflite"
    )
    LANDMARKER_MODEL_URL = (
        "https://storage.googleapis.com/mediapipe-models/"
        "face_landmarker/face_landmarker/float16/1/"
        "face_landmarker.task"
    )
    YUNET_MODEL_URL = (
        "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/"
        "face_detection_yunet/face_detection_yunet_2023mar.onnx"
    )
    MODEL_DIR = Path(__file__).resolve().parents[2] / "models"
    MODEL_PATH = str(MODEL_DIR / "blaze_face_short_range.tflite")
    MODEL_PATH_LANDMARKER = str(MODEL_DIR / "face_landmarker.task")
    MODEL_PATH_YUNET = str(MODEL_DIR / "face_detection_yunet_2023mar.onnx")

    def __init__(self) -> None:
        self._detector = None
        self._landmarker = None
        self._yunet_detector = None
        self._haar_detector = None
        self._detector_mode = "unavailable"
        self._mediapipe_error = str(MEDIAPIPE_IMPORT_ERROR) if MEDIAPIPE_IMPORT_ERROR else ""
        # 帧间追踪与状态平滑
        self._last_persons: List[Dict[str, Any]] = []
        self._next_track_seq = 1
        self._person_states: Dict[str, Dict[str, Any]] = {}
        if not MEDIAPIPE_AVAILABLE:
            print(
                "[BehaviorWebSocketService] MediaPipe 未安装，实时行为分析 WebSocket 将以降级模式运行。"
            )
            self._init_haar_detector()
            return
        self._ensure_models()
        self._init_landmarker()
        if self._landmarker is None:
            self._init_detector()
        if self._landmarker is None and self._detector is None:
            self._init_yunet_detector()
        if self._landmarker is None and self._detector is None and self._yunet_detector is None:
            self._init_haar_detector()

    def _ensure_models(self) -> None:
        """确保 MediaPipe 模型文件已下载到本地。"""
        assets = [
            (self.MODEL_PATH, self.MODEL_URL, "FaceDetector"),
            (self.MODEL_PATH_LANDMARKER, self.LANDMARKER_MODEL_URL, "FaceLandmarker"),
            (self.MODEL_PATH_YUNET, self.YUNET_MODEL_URL, "YuNet"),
        ]
        for path, url, asset_name in assets:
            if os.path.exists(path):
                continue
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                urllib.request.urlretrieve(url, path)
            except Exception as e:
                print(f"[BehaviorWebSocketService] {asset_name} 模型下载失败: {e}")

    def _init_landmarker(self) -> None:
        """初始化 MediaPipe FaceLandmarker（精细面部检测，支持闭眼/头部姿态）"""
        if not MEDIAPIPE_AVAILABLE:
            return
        if not os.path.exists(self.MODEL_PATH_LANDMARKER):

            return
        try:
            options = FaceLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=self.MODEL_PATH_LANDMARKER),
                num_faces=10,
                min_face_detection_confidence=0.3,
                min_face_presence_confidence=0.3,
                min_tracking_confidence=0.3,
                output_face_blendshapes=True,
                running_mode=RunningMode.IMAGE,
            )
            self._landmarker = FaceLandmarker.create_from_options(options)
            self._detector_mode = "landmarker"
            print("[BehaviorWebSocketService] FaceLandmarker initialized")
        except Exception as e:
            print(f"[BehaviorWebSocketService] FaceLandmarker init failed: {e}")

    def _init_detector(self) -> None:
        """初始化 MediaPipe FaceDetector"""
        if not MEDIAPIPE_AVAILABLE:
            return
        if not os.path.exists(self.MODEL_PATH):
            return
        try:
            options = FaceDetectorOptions(
                base_options=BaseOptions(model_asset_path=self.MODEL_PATH),
                min_detection_confidence=0.5,
            )
            self._detector = FaceDetector.create_from_options(options)
            self._detector_mode = "mediapipe"
        except Exception as e:
            print(f"[BehaviorWebSocketService] FaceDetector 初始化失败: {e}")

    def _init_haar_detector(self) -> None:
        """初始化 OpenCV Haar 级联分类器，作为无额外系统依赖的降级路径"""
        try:
            cascade_path = os.path.join(
                cv2.data.haarcascades,
                "haarcascade_frontalface_default.xml",
            )
            detector = cv2.CascadeClassifier(cascade_path)
            if detector.empty():
                raise RuntimeError(f"failed to load cascade from {cascade_path}")
            self._haar_detector = detector
            self._detector_mode = "haar"
            print("[BehaviorWebSocketService] 已启用 OpenCV Haar 级联降级检测。")
        except Exception as e:
            print(f"[BehaviorWebSocketService] Haar 检测器初始化失败: {e}")

    def _init_yunet_detector(self) -> None:
        """初始化 OpenCV YuNet 人脸检测器（纯 CPU 路径）。"""
        if not os.path.exists(self.MODEL_PATH_YUNET):
            return
        try:
            self._yunet_detector = cv2.FaceDetectorYN.create(
                self.MODEL_PATH_YUNET,
                "",
                (320, 320),
                0.65,
                0.3,
                20,
            )
            self._detector_mode = "yunet"
            print("[BehaviorWebSocketService] OpenCV YuNet detector initialized")
        except Exception as e:
            print(f"[BehaviorWebSocketService] YuNet 初始化失败: {e}")

    def _decode_frame(self, image_base64: str) -> Optional[np.ndarray]:
        """将 base64 字符串解码为 OpenCV BGR 图像"""
        try:
            if "," in image_base64:
                image_base64 = image_base64.split(",")[1]
            img_bytes = base64.b64decode(image_base64)
            pil_image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        except Exception:
            return None

    def _detect_faces(
        self, image: np.ndarray
    ) -> List[Tuple[int, int, int, int, List[Any], Optional[Dict[str, float]]]]:
        """主分发器：优先使用 FaceLandmarker，降级到 FaceDetector / Haar。"""
        if self._landmarker is not None:
            return self._detect_faces_landmarker(image)
        if self._detector is not None:
            return self._detect_faces_detector(image)
        if self._yunet_detector is not None:
            return self._detect_faces_yunet(image)
        if self._haar_detector is not None:
            return self._detect_faces_haar(image)
        return []

    def _detect_faces_landmarker(
        self, image: np.ndarray
    ) -> List[Tuple[int, int, int, int, List[Any], Optional[Dict[str, float]]]]:
        """FaceLandmarker：468 个关键点 + blendshapes（支持闭眼检测）。"""
        mp_image = MPImage(
            image_format=ImageFormat.SRGB,
            data=cv2.cvtColor(image, cv2.COLOR_BGR2RGB),
        )
        result = self._landmarker.detect(mp_image)

        faces = []
        for i, face_landmarks in enumerate(result.face_landmarks):
            xs = [lm.x for lm in face_landmarks]
            ys = [lm.y for lm in face_landmarks]
            x = int(min(xs) * image.shape[1])
            y = int(min(ys) * image.shape[0])
            w = int((max(xs) - min(xs)) * image.shape[1])
            h = int((max(ys) - min(ys)) * image.shape[0])

            blendshapes: Dict[str, float] = {}
            if result.face_blendshapes and i < len(result.face_blendshapes):
                for category in result.face_blendshapes[i]:
                    blendshapes[category.category_name] = category.score

            faces.append((x, y, w, h, face_landmarks, blendshapes))

        return faces

    def _detect_faces_detector(
        self, image: np.ndarray
    ) -> List[Tuple[int, int, int, int, List[Any], Optional[Dict[str, float]]]]:
        """FaceDetector：6 个关键点（降级方案）。"""
        mp_image = MPImage(
            image_format=ImageFormat.SRGB,
            data=cv2.cvtColor(image, cv2.COLOR_BGR2RGB),
        )
        result = self._detector.detect(mp_image)

        faces = []
        for detection in result.detections:
            bbox = detection.bounding_box
            x, y, w, h = bbox.origin_x, bbox.origin_y, bbox.width, bbox.height
            keypoints = [(kp.x, kp.y) for kp in detection.keypoints]
            faces.append((x, y, w, h, keypoints, {}))

        return faces

    def _detect_faces_haar(
        self, image: np.ndarray
    ) -> List[Tuple[int, int, int, int, List[Any], Optional[Dict[str, float]]]]:
        """OpenCV Haar 级联降级检测。"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        boxes = self._haar_detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(36, 36),
        )
        return [(int(x), int(y), int(w), int(h), [], {}) for x, y, w, h in boxes]

    def _detect_faces_yunet(
        self, image: np.ndarray
    ) -> List[Tuple[int, int, int, int, List[Any], Optional[Dict[str, float]]]]:
        """OpenCV YuNet：CPU 可用的人脸检测与关键点定位。"""
        if self._yunet_detector is None:
            return []

        img_h, img_w = image.shape[:2]
        self._yunet_detector.setInputSize((img_w, img_h))
        _, detections = self._yunet_detector.detect(image)
        if detections is None:
            return []

        faces = []
        for det in detections:
            x, y, w, h = det[:4]
            pts = det[4:14].reshape(5, 2)
            eye_points = sorted(pts[:2], key=lambda p: p[0])
            left_eye = (float(eye_points[0][0] / img_w), float(eye_points[0][1] / img_h))
            right_eye = (float(eye_points[1][0] / img_w), float(eye_points[1][1] / img_h))
            nose = (float(pts[2][0] / img_w), float(pts[2][1] / img_h))
            mouth_right = pts[3]
            mouth_left = pts[4]
            mouth = (
                float((mouth_left[0] + mouth_right[0]) / 2 / img_w),
                float((mouth_left[1] + mouth_right[1]) / 2 / img_h),
            )
            faces.append(
                (
                    int(x),
                    int(y),
                    int(w),
                    int(h),
                    [left_eye, right_eye, nose, mouth],
                    {},
                )
            )

        return faces

    def _estimate_pose(
        self,
        face: Tuple[int, int, int, int, List[Any], Optional[Dict[str, float]]],
        img_h: int,
        img_w: int,
    ) -> Tuple[str, float, Optional[bool]]:
        """
        估算头部姿态状态。
        - FaceLandmarker 模式：468 个关键点 + blendshapes，支持闭眼检测
        - FaceDetector 模式：6 个关键点
        - Haar 降级模式：无关键点
        """
        if len(face) == 6:
            x, y, w, h, keypoints, blendshapes = face
        else:
            x, y, w, h, keypoints = face
            blendshapes = {}

        face_area_ratio = (w * h) / (img_w * img_h)

        def _lm_xy(kp):
            if hasattr(kp, 'x'):
                return kp.x, kp.y
            return kp[0], kp[1]

        # ============= FaceLandmarker 精细模式 (468+ 点) =============
        if keypoints and hasattr(keypoints[0], 'x') and len(keypoints) > 100:
            lm = keypoints

            # 1. 闭眼检测（blendshapes 优先，EAR 兜底）
            is_eye_closed = False
            if blendshapes:
                left_blink = blendshapes.get('eyeBlinkLeft', 0)
                right_blink = blendshapes.get('eyeBlinkRight', 0)
                if left_blink > 0.5 or right_blink > 0.5:
                    is_eye_closed = True

            if not is_eye_closed:
                # EAR (Eye Aspect Ratio) 兜底
                def _ear(indices):
                    p = [lm[i] for i in indices]
                    v1 = ((p[1].x - p[5].x)**2 + (p[1].y - p[5].y)**2)**0.5
                    v2 = ((p[2].x - p[4].x)**2 + (p[2].y - p[4].y)**2)**0.5
                    h = ((p[0].x - p[3].x)**2 + (p[0].y - p[3].y)**2)**0.5
                    return (v1 + v2) / (2.0 * h) if h > 0 else 1.0

                left_ear = _ear([33, 160, 158, 133, 153, 144])
                right_ear = _ear([362, 385, 387, 263, 373, 380])
                if left_ear < 0.18 or right_ear < 0.18:
                    is_eye_closed = True

            # 2. 头部姿态（低头 / 侧倾 / 左右转头）
            nose = lm[1]
            left_eye = lm[33]
            right_eye = lm[263]

            eye_center_y = (left_eye.y + right_eye.y) / 2
            nose_offset_y = nose.y - eye_center_y
            eye_height_diff = abs(left_eye.y - right_eye.y)

            eye_center_x = (left_eye.x + right_eye.x) / 2
            eye_span = abs(right_eye.x - left_eye.x)
            nose_offset_x = abs(nose.x - eye_center_x)
            is_turning_yaw = (nose_offset_x / eye_span) > 0.18 if eye_span > 0 else False

            is_head_down = nose_offset_y > 0.20
            is_turning = eye_height_diff > 0.030
            is_small = face_area_ratio < 0.0035

            # 3. 区分"低头看书"与"低头走神"：
            # 利用 blendshapes 的眼睛注视方向 —— 低头时眼睛明显向下看 + 睁开，大概率在看书/写字
            is_reading = False
            if blendshapes and is_head_down and not is_eye_closed:
                eye_look_down = (blendshapes.get('eyeLookDownLeft', 0) + blendshapes.get('eyeLookDownRight', 0)) / 2
                if eye_look_down > 0.25:
                    is_reading = True
                    is_head_down = False  # 不判定为低头走神

            if is_eye_closed or is_head_down or is_turning or is_turning_yaw or is_small:
                score = max(
                    0.0,
                    1.0 - (nose_offset_y * 2.0 + eye_height_diff * 3.0 + (0.3 if is_eye_closed else 0)),
                )
                return self.STATUS_UNFOCUSED, round(score, 2), is_eye_closed

            score = min(1.0, 0.90 + (0.25 - nose_offset_y) * 0.5)
            return self.STATUS_FOCUSED, round(score, 2), is_eye_closed

        # ============= FaceDetector 模式 (6 点) =============
        if len(keypoints) >= 4:
            left_eye = keypoints[0]
            right_eye = keypoints[1]
            nose = keypoints[2]
            mouth = keypoints[3]

            eye_center_y = (left_eye[1] + right_eye[1]) / 2
            nose_offset_y = nose[1] - eye_center_y
            eye_height_diff = abs(left_eye[1] - right_eye[1])

            is_turning_horizontal = False
            if len(keypoints) >= 6:
                left_ear = keypoints[4]
                right_ear = keypoints[5]
                ear_span = abs(right_ear[0] - left_ear[0])
                eye_span = abs(right_eye[0] - left_eye[0])
                if eye_span > 0 and (ear_span / eye_span) < 1.7:
                    is_turning_horizontal = True

            is_head_down = nose_offset_y > 0.22
            is_turning = eye_height_diff > 0.035
            is_small = face_area_ratio < 0.0035

            if is_head_down or is_turning or is_turning_horizontal or is_small:
                score = max(
                    0.0,
                    1.0 - (nose_offset_y * 2.0 + eye_height_diff * 3.0 + (0.02 if is_small else 0)),
                )
                return self.STATUS_UNFOCUSED, round(score, 2), None

            score = min(1.0, 0.90 + (0.25 - nose_offset_y) * 0.5)
            return self.STATUS_FOCUSED, round(score, 2), None

        # ============= Haar 降级模式 =============
        def _clamp(value: float, minimum: float, maximum: float) -> float:
            return max(minimum, min(maximum, value))

        center_x = (x + w / 2) / img_w if img_w else 0.5
        center_y = (y + h / 2) / img_h if img_h else 0.5
        edge_penalty = 0.08 if (
            center_x < 0.12 or center_x > 0.88 or center_y < 0.1 or center_y > 0.9
        ) else 0.0
        if face_area_ratio < 0.004:
            score = _clamp(0.34 + face_area_ratio * 34 - edge_penalty, 0.28, 0.58)
            return self.STATUS_UNFOCUSED, round(score, 2), None

        score = _clamp(0.64 + face_area_ratio * 10 - edge_penalty, 0.46, 0.93)
        if score < 0.63:
            return self.STATUS_UNFOCUSED, round(score, 2), None
        return self.STATUS_FOCUSED, round(score, 2), None

    def _derive_educational_metrics(
        self,
        face: Tuple[int, int, int, int, List[Any], Optional[Dict[str, float]]],
        img_h: int,
        img_w: int,
        final_status: str,
        final_score: float,
        eye_closed: Optional[bool],
    ) -> EducationalMetrics:
        """
        基于头部姿态特征推导教育学参数（LEI / 布鲁姆层次 / 认知状态）。
        与 _estimate_pose 共用相同的特征提取逻辑，避免重复计算时直接复用中间值。
        """
        if len(face) == 6:
            x, y, w, h, keypoints, blendshapes = face
        else:
            x, y, w, h, keypoints = face
            blendshapes = {}
        blendshapes = blendshapes or {}

        face_area_ratio = (w * h) / (img_w * img_h) if img_w > 0 and img_h > 0 else 0.01

        # ---------- 特征提取 ----------
        is_head_down = False
        is_turning = False
        is_turning_yaw = False
        is_reading = False
        is_eye_closed = eye_closed or False
        nose_offset_y = 0.0
        eye_height_diff = 0.0
        has_fine_lm = keypoints and hasattr(keypoints[0], 'x') and len(keypoints) > 100
        has_6pt = len(keypoints) >= 4 if keypoints else False

        if has_fine_lm:
            lm = keypoints
            nose = lm[1]
            left_eye = lm[33]
            right_eye = lm[263]
            eye_center_y = (left_eye.y + right_eye.y) / 2
            nose_offset_y = nose.y - eye_center_y
            eye_height_diff = abs(left_eye.y - right_eye.y)
            eye_center_x = (left_eye.x + right_eye.x) / 2
            eye_span = abs(right_eye.x - left_eye.x)
            nose_offset_x = abs(nose.x - eye_center_x)
            is_turning_yaw = (nose_offset_x / eye_span) > 0.18 if eye_span > 0 else False
            is_head_down = nose_offset_y > 0.20
            is_turning = eye_height_diff > 0.030
            if blendshapes and is_head_down and not is_eye_closed:
                eye_look_down = (blendshapes.get('eyeLookDownLeft', 0) + blendshapes.get('eyeLookDownRight', 0)) / 2
                if eye_look_down > 0.25:
                    is_reading = True
                    is_head_down = False
        elif has_6pt:
            left_eye = keypoints[0]
            right_eye = keypoints[1]
            nose = keypoints[2]
            eye_center_y = (left_eye[1] + right_eye[1]) / 2
            nose_offset_y = nose[1] - eye_center_y
            eye_height_diff = abs(left_eye[1] - right_eye[1])
            is_head_down = nose_offset_y > 0.22
            is_turning = eye_height_diff > 0.035
            if len(keypoints) >= 6:
                left_ear = keypoints[4]
                right_ear = keypoints[5]
                ear_span = abs(right_ear[0] - left_ear[0])
                eye_span = abs(right_eye[0] - left_eye[0])
                if eye_span > 0 and (ear_span / eye_span) < 1.7:
                    is_turning_yaw = True
        else:
            # Haar 降级：用 face_area_ratio 和 final_score 推断
            is_head_down = face_area_ratio < 0.004
            is_turning = final_score < 0.55

        # ---------- 认知状态 ----------
        if final_status == self.STATUS_FOCUSED:
            if is_reading:
                cognitive_state = "阅读书写"
            elif not is_head_down and not is_turning and not is_eye_closed:
                cognitive_state = "深度专注"
            else:
                cognitive_state = "专注"
        else:  # unfocused
            if is_eye_closed:
                cognitive_state = "疲劳"
            elif is_turning or is_turning_yaw:
                cognitive_state = "明显走神"
            elif is_head_down and not is_reading:
                cognitive_state = "轻度走神"
            else:
                cognitive_state = "困惑"

        # ---------- 布鲁姆层次 ----------
        if cognitive_state == "深度专注":
            if 0.05 < nose_offset_y <= 0.15:
                bloom_level = "analyze"
            else:
                bloom_level = "understand"
        elif cognitive_state == "阅读书写":
            bloom_level = "apply"
        elif cognitive_state in ("疲劳", "轻度走神"):
            bloom_level = "remember"
        elif cognitive_state == "明显走神":
            bloom_level = "remember"
        elif final_status == self.STATUS_FOCUSED:
            bloom_level = "understand"
        else:
            bloom_level = "remember"

        # ---------- LEI 三维度 ----------
        # BEI: 身体投入（头部姿态正直度）
        if has_fine_lm or has_6pt:
            bei = max(0.0, min(1.0, 1.0 - nose_offset_y * 2.5 - eye_height_diff * 2.0))
        else:
            bei = max(0.3, min(0.9, final_score))

        # CEI: 认知投入（布鲁姆层次映射）
        BLOOM_CEI = {
            "remember": 0.35,
            "understand": 0.55,
            "apply": 0.70,
            "analyze": 0.82,
            "evaluate": 0.90,
            "create": 0.95,
        }
        cei = BLOOM_CEI.get(bloom_level, 0.5)

        # EEI: 情感投入（面部活跃度，blendshapes 嘴部/眉毛变化）
        if blendshapes and has_fine_lm:
            expressiveness = (
                blendshapes.get('jawOpen', 0)
                + blendshapes.get('mouthSmileLeft', 0)
                + blendshapes.get('mouthSmileRight', 0)
                + blendshapes.get('browDownLeft', 0)
                + blendshapes.get('browDownRight', 0)
                + blendshapes.get('browInnerUp', 0)
            ) / 6.0
            eei = max(0.2, min(0.95, 0.5 + expressiveness * 0.8))
        else:
            eei = max(0.25, min(0.85, final_score * 0.9 + 0.1))

        # LEI = 0.35*BEI + 0.40*CEI + 0.25*EEI
        lei = round(0.35 * bei + 0.40 * cei + 0.25 * eei, 3)

        # 注意力偏离度（以 0.7 为课堂基线）
        attention_deviation = round(final_score - 0.7, 3)

        # 走神判定
        mind_wandering = (
            final_status == self.STATUS_UNFOCUSED
            and (is_turning or is_turning_yaw or (is_head_down and not is_reading))
        )

        return EducationalMetrics(
            lei=lei,
            bloom_level=bloom_level,
            cognitive_state=cognitive_state,
            bei=round(bei, 3),
            cei=round(cei, 3),
            eei=round(eei, 3),
            attention_deviation=attention_deviation,
            mind_wandering=mind_wandering,
        )

    def analyze_frame(
        self, image_base64: str, frame_id: int
    ) -> AnalysisMessage:
        """
        分析单帧图像，返回符合文档规范的 AnalysisMessage 模型。
        包含帧间状态平滑：连续低头/转头 >= UNFOCUSED_THRESHOLD 帧才标记为 unfocused，
        连续正常 >= FOCUSED_THRESHOLD 帧才恢复为 focused，避免单帧抖动。
        """
        timestamp = int(time.time())
        persons: List[PersonResult] = []

        if (
            self._landmarker is None
            and self._detector is None
            and self._yunet_detector is None
            and self._haar_detector is None
        ):
            return AnalysisMessage(
                frame_id=frame_id,
                timestamp=timestamp,
                error=(
                    "MediaPipe FaceDetector not available"
                    if not self._mediapipe_error
                    else f"MediaPipe unavailable: {self._mediapipe_error}"
                ),
            )

        image = self._decode_frame(image_base64)
        if image is None:
            return AnalysisMessage(
                frame_id=frame_id,
                timestamp=timestamp,
                error="Failed to decode image",
            )

        img_h, img_w = image.shape[:2]
        faces = self._detect_faces(image)

        focused_count = 0
        unfocused_count = 0
        absent_count = 0

        # 1. 计算当前帧检测到的人脸
        current_raw: List[Dict[str, Any]] = []
        for (x, y, w, h, keypoints, blendshapes) in faces:
            raw_status, raw_score, eye_closed = self._estimate_pose((x, y, w, h, keypoints, blendshapes), img_h, img_w)
            current_raw.append({
                "bbox": (x, y, w, h),
                "center": (x + w / 2, y + h / 2),
                "raw_status": raw_status,
                "raw_score": raw_score,
                "eye_closed": eye_closed,
                "keypoints": keypoints,
                "blendshapes": blendshapes,
            })

        # 2. 与上一帧按人脸中心点距离做最近邻匹配
        max_track_dist = max(img_w, img_h) * self.MAX_TRACK_DISTANCE_RATIO
        current_persons: List[Dict[str, Any]] = []
        used_last_indices: set[int] = set()

        for curr in current_raw:
            best_idx = -1
            best_dist = float("inf")
            for idx, last in enumerate(self._last_persons):
                if idx in used_last_indices:
                    continue
                dx = curr["center"][0] - last["center"][0]
                dy = curr["center"][1] - last["center"][1]
                dist = (dx * dx + dy * dy) ** 0.5
                if dist < best_dist and dist < max_track_dist:
                    best_dist = dist
                    best_idx = idx

            if best_idx != -1:
                track_id = self._last_persons[best_idx]["track_id"]
                used_last_indices.add(best_idx)
            else:
                track_id = f"person_{self._next_track_seq}"
                self._next_track_seq += 1

            current_persons.append({**curr, "track_id": track_id})

        # 3. 处理上一帧中未匹配到的人脸（可能是低头/转头导致暂时检测不到）
        # 在丢失追踪的宽限期内保留这些人，避免低头被误判为缺席
        for idx, last in enumerate(self._last_persons):
            if idx in used_last_indices:
                continue
            tid = last["track_id"]
            state = self._person_states.get(tid)
            if state is None:
                continue

            state["lost_frames"] = state.get("lost_frames", 0) + 1
            if state["lost_frames"] <= self.LOST_TRACK_THRESHOLD:
                # 宽限期内：保留追踪，状态降级为 unfocused（低头/转头通常是不专注的表现）
                current_persons.append({
                    "track_id": tid,
                    "bbox": last["bbox"],
                    "center": last["center"],
                    "raw_status": self.STATUS_UNFOCUSED,
                    "raw_score": 0.5,
                    "final_status": self.STATUS_UNFOCUSED,
                    "final_score": 0.5,
                    "_is_lost_track": True,
                })

        # 4. 更新帧间状态缓冲区并做阈值平滑
        active_track_ids: set[str] = set()
        for person in current_persons:
            tid = person["track_id"]
            active_track_ids.add(tid)
            raw_status = person.get("raw_status", self.STATUS_UNFOCUSED)

            if tid not in self._person_states:
                self._person_states[tid] = {
                    "consecutive_unfocused": 0,
                    "consecutive_focused": 0,
                    "final_status": raw_status,
                    "lost_frames": 0,
                }

            state = self._person_states[tid]
            if not person.get("_is_lost_track"):
                state["lost_frames"] = 0  # 当前帧真正检测到了，才重置丢失计数

            if raw_status == self.STATUS_UNFOCUSED:
                state["consecutive_unfocused"] += 1
                state["consecutive_focused"] = 0
            else:  # focused
                state["consecutive_focused"] += 1
                state["consecutive_unfocused"] = 0

            # 应用阈值切换最终状态
            if state["consecutive_unfocused"] >= self.UNFOCUSED_THRESHOLD:
                state["final_status"] = self.STATUS_UNFOCUSED
            elif state["consecutive_focused"] >= self.FOCUSED_THRESHOLD:
                state["final_status"] = self.STATUS_FOCUSED

            if "final_status" not in person:
                person["final_status"] = state["final_status"]
                person["final_score"] = person.get("raw_score", 0.5)

        # 5. 清理已消失人员的状态（超过宽限期才真正移除）
        for tid in list(self._person_states.keys()):
            if tid not in active_track_ids:
                del self._person_states[tid]

        self._last_persons = [
            {"track_id": p["track_id"], "bbox": p["bbox"], "center": p["center"],
             "raw_status": p.get("raw_status"), "raw_score": p.get("raw_score")}
            for p in current_persons
        ]

        # 6. 构建返回结果（填充教育学参数）
        status_colors = {
            self.STATUS_FOCUSED: "#52c41a",
            self.STATUS_UNFOCUSED: "#faad14",
            self.STATUS_ABSENT: "#f5222d",
        }
        lei_values: List[float] = []
        bloom_counts: Dict[str, int] = {}
        on_task = 0
        mind_wandering = 0

        for person in current_persons:
            x, y, w, h = person["bbox"]
            final_status = person["final_status"]
            final_score = person["final_score"]

            # 推导教育学参数
            edu = self._derive_educational_metrics(
                (x, y, w, h, person.get("keypoints"), person.get("blendshapes")),
                img_h,
                img_w,
                final_status,
                final_score,
                person.get("eye_closed"),
            )

            persons.append(
                PersonResult(
                    track_id=person["track_id"],
                    bbox=[int(x), int(y), int(x + w), int(y + h)],
                    status=final_status,
                    score=final_score,
                    color=status_colors.get(final_status),
                    eye_closed=person.get("eye_closed"),
                    educational=edu,
                )
            )

            if final_status == self.STATUS_FOCUSED:
                focused_count += 1
            elif final_status == self.STATUS_UNFOCUSED:
                unfocused_count += 1

            # 汇总教育学统计
            if edu:
                lei_values.append(edu.lei)
                bloom_counts[edu.bloom_level] = bloom_counts.get(edu.bloom_level, 0) + 1
                if edu.cognitive_state in ("深度专注", "阅读书写", "专注"):
                    on_task += 1
                if edu.mind_wandering:
                    mind_wandering += 1

        # 7. 如果当前帧一个人都没有（包括追踪中的），才判定为缺席
        if not persons:
            absent_count = 1

        total_persons = len(persons) or 1
        avg_lei = round(sum(lei_values) / total_persons, 3) if lei_values else None
        bloom_distribution = {
            k: round(v / total_persons, 3) for k, v in bloom_counts.items()
        } if bloom_counts else None
        on_task_rate = round(on_task / total_persons, 3) if persons else None
        mind_wandering_rate = round(mind_wandering / total_persons, 3) if persons else None
        overall_score = avg_lei if avg_lei is not None else (focused_count / total_persons if persons else 0.0)

        return AnalysisMessage(
            frame_id=frame_id,
            timestamp=timestamp,
            persons=persons,
            summary=SummaryResult(
                focused_count=focused_count,
                unfocused_count=unfocused_count,
                absent_count=absent_count,
                overall_score=round(overall_score, 3),
                focus_rate=round(focused_count / total_persons, 3) if persons else 0.0,
                avg_lei=avg_lei,
                bloom_distribution=bloom_distribution,
                on_task_rate=on_task_rate,
                mind_wandering_rate=mind_wandering_rate,
            ),
        )

    def analyze_image_bytes(self, image_data: bytes, frame_id: int = 1) -> AnalysisMessage:
        """供 HTTP 上传分析复用的字节入口。"""
        data_uri = f"data:image/jpeg;base64,{base64.b64encode(image_data).decode('utf-8')}"
        return self.analyze_frame(data_uri, frame_id)

    def detect_face_detail(self, image_data: bytes) -> List[Dict[str, Any]]:
        """
        对单张图片做人脸检测，返回每个人脸的 bbox、闭眼状态、是否在看书/写字。
        不维护帧间追踪状态，适合作为 YOLO 结果的辅助增强。
        """
        image = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            return []
        img_h, img_w = image.shape[:2]
        faces = self._detect_faces(image)
        results = []
        for face in faces:
            if len(face) == 6:
                x, y, w, h, keypoints, blendshapes = face
            else:
                x, y, w, h, keypoints = face
                blendshapes = {}
            _, _, is_eye_closed = self._estimate_pose((x, y, w, h, keypoints, blendshapes), img_h, img_w)

            # 提取"看书/写字"特征：低头 + 眼睛向下看 + 眼睛睁开
            is_reading = False
            if blendshapes and keypoints and hasattr(keypoints[0], 'x') and len(keypoints) > 100:
                lm = keypoints
                nose = lm[1]
                left_eye = lm[33]
                right_eye = lm[263]
                eye_center_y = (left_eye.y + right_eye.y) / 2
                nose_offset_y = nose.y - eye_center_y
                is_head_down = nose_offset_y > 0.20
                if is_head_down and not is_eye_closed:
                    eye_look_down = (blendshapes.get('eyeLookDownLeft', 0) + blendshapes.get('eyeLookDownRight', 0)) / 2
                    if eye_look_down > 0.25:
                        is_reading = True

            results.append({
                "bbox": [int(x), int(y), int(x + w), int(y + h)],
                "eye_closed": is_eye_closed,
                "is_reading": is_reading,
            })
        return results


# 全局单例（避免每次请求都重新加载模型）
behavior_ws_service = BehaviorWebSocketService()
