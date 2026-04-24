import base64
import io
import os
import time
import urllib.request
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image
from pydantic import BaseModel, Field

try:
    from mediapipe import Image as MPImage, ImageFormat
    from mediapipe.tasks.python.vision import FaceDetector, FaceDetectorOptions
    from mediapipe.tasks.python.core.base_options import BaseOptions

    MEDIAPIPE_AVAILABLE = True
    MEDIAPIPE_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - import guard for optional dependency
    MPImage = None  # type: ignore[assignment]
    ImageFormat = None  # type: ignore[assignment]
    FaceDetector = None  # type: ignore[assignment]
    FaceDetectorOptions = None  # type: ignore[assignment]
    BaseOptions = None  # type: ignore[assignment]
    MEDIAPIPE_AVAILABLE = False
    MEDIAPIPE_IMPORT_ERROR = exc


class FrameMessage(BaseModel):
    """前端 -> 后端的帧消息"""
    type: str = Field(..., description="消息类型，固定为 'frame'")
    frame_id: int = Field(..., description="帧序号")
    timestamp: Optional[int] = Field(None, description="前端时间戳（毫秒或秒）")
    image_base64: str = Field(..., description="base64 编码的图像数据，支持 data URI")


class PersonResult(BaseModel):
    """单个人员检测结果"""
    track_id: str = Field(..., description="人员追踪 ID，如 person_1")
    bbox: List[int] = Field(..., description="人脸边界框 [x1, y1, x2, y2]")
    status: str = Field(..., description="状态：focused / unfocused / absent")
    score: float = Field(..., ge=0.0, le=1.0, description="专注度分数")


class SummaryResult(BaseModel):
    """当前帧统计摘要"""
    focused_count: int = Field(0, description="专注人数")
    unfocused_count: int = Field(0, description="不专注人数")
    absent_count: int = Field(0, description="缺席人数")


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

    # MediaPipe 模型下载地址
    MODEL_URL = (
        "https://storage.googleapis.com/mediapipe-models/"
        "face_detector/blaze_face_short_range/float16/1/"
        "blaze_face_short_range.tflite"
    )
    MODEL_PATH = "models/blaze_face_short_range.tflite"

    def __init__(self) -> None:
        self._detector = None
        self._haar_detector = None
        self._detector_mode = "unavailable"
        self._mediapipe_error = str(MEDIAPIPE_IMPORT_ERROR) if MEDIAPIPE_IMPORT_ERROR else ""
        if not MEDIAPIPE_AVAILABLE:
            print(
                "[BehaviorWebSocketService] MediaPipe 未安装，实时行为分析 WebSocket 将以降级模式运行。"
            )
            self._init_haar_detector()
            return
        self._ensure_model()
        self._init_detector()
        if self._detector is None:
            self._init_haar_detector()

    def _ensure_model(self) -> None:
        """确保 MediaPipe 模型文件已下载到本地"""
        if os.path.exists(self.MODEL_PATH):
            return
        try:
            os.makedirs(os.path.dirname(self.MODEL_PATH), exist_ok=True)
            urllib.request.urlretrieve(self.MODEL_URL, self.MODEL_PATH)
        except Exception as e:
            print(f"[BehaviorWebSocketService] 模型下载失败: {e}")

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
    ) -> List[Tuple[int, int, int, int, List[Tuple[float, float]]]]:
        """
        使用 MediaPipe FaceDetector 检测图像中的人脸。

        Returns:
            [(x, y, w, h, keypoints), ...]
            keypoints 顺序: [(left_eye_x, left_eye_y), (right_eye_x, right_eye_y),
                           (nose_x, nose_y), (mouth_x, mouth_y),
                           (left_ear_x, left_ear_y), (right_ear_x, right_ear_y)]
        """
        if self._detector is None:
            if self._haar_detector is None:
                return []
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            boxes = self._haar_detector.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(36, 36),
            )
            return [(int(x), int(y), int(w), int(h), []) for x, y, w, h in boxes]

        mp_image = MPImage(
            image_format=ImageFormat.SRGB,
            data=cv2.cvtColor(image, cv2.COLOR_BGR2RGB),
        )
        result = self._detector.detect(mp_image)

        faces = []
        for detection in result.detections:
            bbox = detection.bounding_box
            x, y, w, h = bbox.origin_x, bbox.origin_y, bbox.width, bbox.height
            # keypoints 是归一化坐标 (0~1)
            keypoints = [(kp.x, kp.y) for kp in detection.keypoints]
            faces.append((x, y, w, h, keypoints))

        return faces

    def _estimate_pose(
        self,
        face: Tuple[int, int, int, int, List[Tuple[float, float]]],
        img_h: int,
        img_w: int,
    ) -> Tuple[str, float]:
        """
        基于 MediaPipe FaceDetector 返回的 6 个关键点，估算头部姿态状态。

        关键点顺序（MediaPipe 官方定义）：
        0: left_eye, 1: right_eye, 2: nose, 3: mouth, 4: left_ear, 5: right_ear

        判断逻辑：
        - 低头：鼻尖 y 坐标明显低于眼睛中心（鼻尖下沉）
        - 转头：左右眼 y 坐标差异大（头部侧倾）
        - 远离/转头离开：人脸占比过小
        - 正常 → focused
        """
        x, y, w, h, keypoints = face

        if len(keypoints) < 4:
            # Haar 降级模式下没有关键点，只能基于人脸尺寸做保守判断
            face_area_ratio = (w * h) / (img_w * img_h)
            if face_area_ratio < 0.01:
                return self.STATUS_UNFOCUSED, 0.45
            return self.STATUS_FOCUSED, 0.82

        left_eye = keypoints[0]
        right_eye = keypoints[1]
        nose = keypoints[2]
        mouth = keypoints[3]

        # 眼睛中心 y 坐标（归一化）
        eye_center_y = (left_eye[1] + right_eye[1]) / 2

        # 鼻尖相对于眼睛中心的垂直偏移（归一化）
        # 正常抬头时，鼻尖在眼睛下方约 0.15~0.25；低头时会更大
        nose_offset_y = nose[1] - eye_center_y

        # 左右眼高度差（转头侧倾判断）
        eye_height_diff = abs(left_eye[1] - right_eye[1])

        # 人脸占比
        face_area_ratio = (w * h) / (img_w * img_h)

        # 判断规则
        is_head_down = nose_offset_y > 0.30  # 鼻尖明显下沉
        is_turning = eye_height_diff > 0.06  # 头部侧倾
        is_small = face_area_ratio < 0.005  # 人脸占比过小

        if is_head_down or is_turning or is_small:
            # 综合计算不专注分数
            score = max(
                0.0,
                1.0
                - (nose_offset_y * 2.0 + eye_height_diff * 3.0 + (0.02 if is_small else 0)),
            )
            return self.STATUS_UNFOCUSED, round(score, 2)

        # 正常专注状态
        score = min(1.0, 0.90 + (0.25 - nose_offset_y) * 0.5)
        return self.STATUS_FOCUSED, round(score, 2)

    def analyze_frame(
        self, image_base64: str, frame_id: int
    ) -> AnalysisMessage:
        """
        分析单帧图像，返回符合文档规范的 AnalysisMessage 模型。
        """
        timestamp = int(time.time())
        persons: List[PersonResult] = []

        if self._detector is None and self._haar_detector is None:
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

        if faces:
            for idx, (x, y, w, h, keypoints) in enumerate(faces):
                status, score = self._estimate_pose((x, y, w, h, keypoints), img_h, img_w)
                person_id = f"person_{idx + 1}"
                persons.append(
                    PersonResult(
                        track_id=person_id,
                        bbox=[int(x), int(y), int(x + w), int(y + h)],
                        status=status,
                        score=score,
                    )
                )

                if status == self.STATUS_FOCUSED:
                    focused_count += 1
                elif status == self.STATUS_UNFOCUSED:
                    unfocused_count += 1
        else:
            # 画面中没有检测到人脸，视为缺席
            absent_count = 1

        return AnalysisMessage(
            frame_id=frame_id,
            timestamp=timestamp,
            persons=persons,
            summary=SummaryResult(
                focused_count=focused_count,
                unfocused_count=unfocused_count,
                absent_count=absent_count,
            ),
        )

    def analyze_image_bytes(self, image_data: bytes, frame_id: int = 1) -> AnalysisMessage:
        """供 HTTP 上传分析复用的字节入口。"""
        data_uri = f"data:image/jpeg;base64,{base64.b64encode(image_data).decode('utf-8')}"
        return self.analyze_frame(data_uri, frame_id)


# 全局单例（避免每次请求都重新加载模型）
behavior_ws_service = BehaviorWebSocketService()
