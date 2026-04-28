"""
课堂行为检测 —— 教育学理论增强模块
基于学习投入理论(Learning Engagement Theory)与布鲁姆认知分类法(Bloom's Taxonomy)
对纯CV几何检测输出进行教育学语义重构与认知状态推断。

核心理论支撑:
1. Fredricks et al. (2004) 三维学习投入模型:
   - 行为投入(Behavioral Engagement): 可观测的身体参与
   - 认知投入(Cognitive Engagement): 学习策略与心理努力(从行为模式推断)
   - 情感投入(Emotional Engagement): 兴趣与态度(预留面部表情接口)

2. Bloom's Taxonomy 修订版 (Anderson & Krathwohl, 2001):
   将可观测行为映射到认知层次: 记忆→理解→应用→分析→评价→创造

3. 注意力动态模型 (Sustained Attention Literature):
   - 正常课堂注意力呈周期性波动(~15-20min周期)
   - 区分"正常波动"与"异常脱离"
   - 引入"认知负荷窗口"概念

4. 社会传染理论 (Social Contagion Theory):
   课堂中的分心行为具有传染性，群体氛围影响个体投入
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from enum import Enum
import numpy as np
import time


# ==================== 教育学常量与配置 ====================

# 课堂注意力周期参数 (单位: 秒)
# 文献支持: 青少年持续性注意力的自然波动周期约为15-20分钟
ATTENTION_CYCLE_SECONDS = 900  # 15分钟一个周期
ATTENTION_CYCLE_VARIANCE = 300  # 允许±5分钟个体差异

# 认知投入推断的时间窗口
COGNITIVE_WINDOW_FRAMES = 48  # 约1.6秒@30fps，用于判断认知模式

# 行为投入权重 (三维投入模型)
BEHAVIORAL_WEIGHT = 0.35
COGNITIVE_WEIGHT = 0.40
EMOTIONAL_WEIGHT = 0.25  # 预留，当前主要靠姿态推断

# 布鲁姆认知层次评分映射
BLOOM_LEVEL_SCORES = {
    "remembering": 0.35,    # 记忆: 最低层次认知活动
    "understanding": 0.55,  # 理解: 能跟随讲解
    "applying": 0.70,       # 应用: 主动记录、练习
    "analyzing": 0.82,      # 分析: 深度思考、质疑
    "evaluating": 0.90,     # 评价: 批判性思考
    "creating": 1.00,       # 创造: 最高层次，课堂中极少出现，作为上限
}


# ==================== 数据类定义 ====================

class EngagementDimension(Enum):
    """学习投入维度"""
    BEHAVIORAL = "behavioral"   # 行为投入
    COGNITIVE = "cognitive"     # 认知投入
    EMOTIONAL = "emotional"     # 情感投入


class BloomLevel(Enum):
    """布鲁姆认知层次"""
    REMEMBERING = "remembering"
    UNDERSTANDING = "understanding"
    APPLYING = "applying"
    ANALYZING = "analyzing"
    EVALUATING = "evaluating"
    CREATING = "creating"
    UNKNOWN = "unknown"


class CognitiveState(Enum):
    """认知状态推断结果"""
    DEEP_PROCESSING = "deep_processing"      # 深度加工: 稳定注视+笔记/思考迹象
    SHALLOW_ATTENTION = "shallow_attention"  # 浅层注意: 目光稳定但无认知迹象
    MIND_WANDERING = "mind_wandering"        # 走神: 目光游离，频繁小动作
    TASK_SWITCHING = "task_switching"        # 任务切换: 频繁切换行为
    PASSIVE_LISTENING = "passive_listening"  # 被动听讲: 单纯注视，无互动
    COGNITIVE_OVERLOAD = "cognitive_overload"  # 认知过载: 长时间皱眉/停顿


@dataclass
class BehavioralEvent:
    """单帧行为事件的教育学封装"""
    timestamp: float
    raw_behavior: str           # CV原始输出: 专注/手机/睡觉/交谈/离开
    keypoints: Optional[np.ndarray] = None
    confidence: float = 0.75
    
    # 教育学推断字段
    engagement_dimension: EngagementDimension = EngagementDimension.BEHAVIORAL
    bloom_level: BloomLevel = BloomLevel.UNKNOWN
    cognitive_state: CognitiveState = CognitiveState.SHALLOW_ATTENTION
    
    # 姿态特征 (用于认知推断)
    head_pose: str = "neutral"       # forward / down / up / turned_left / turned_right
    gaze_direction: str = "unknown"  # front / down / up / left / right / wandering
    body_lean: float = 0.0           # 身体前倾角度归一化 [-1, 1]
    hand_position: str = "unknown"   # writing / resting / raised / near_face


@dataclass
class StudentEngagementProfile:
    """单个学生的学习投入画像"""
    track_id: str
    
    # 行为投入指标 (可直接观测)
    attendance_rate: float = 1.0           # 在席率
    on_task_rate: float = 1.0              # 目标行为占比
    active_participation_rate: float = 0.0  # 主动参与率(笔记、点头等)
    disruptive_rate: float = 0.0           # 破坏性行为占比
    
    # 认知投入指标 (从行为模式推断)
    sustained_attention_score: float = 0.0   # 持续注意得分
    cognitive_depth_score: float = 0.0       # 认知深度得分
    attention_stability: float = 0.0         # 注意稳定性
    task_switching_freq: float = 0.0         # 任务切换频率
    bloom_distribution: Dict[str, float] = field(default_factory=dict)  # 布鲁姆层次分布
    
    # 情感投入指标 (预留)
    emotional_valence: float = 0.5           # 情感效价 0-1
    
    # 综合指标
    behavioral_engagement_index: float = 0.0   # BEI
    cognitive_engagement_index: float = 0.0    # CEI
    emotional_engagement_index: float = 0.5    # EEI (默认中性)
    learning_engagement_index: float = 0.0     # LEI (综合学习投入指数)
    
    # 注意力动态
    attention_baseline: float = 0.7            # 个体注意力基线
    attention_deviation: float = 0.0           # 偏离基线的程度
    is_abnormal_decline: bool = False          # 是否异常下降
    
    # 时序数据
    behavior_history: deque = field(default_factory=lambda: deque(maxlen=128))
    cognitive_state_history: deque = field(default_factory=lambda: deque(maxlen=64))


@dataclass
class ClassroomEngagementReport:
    """课堂整体学习投入报告"""
    timestamp: float
    student_count: int = 0
    
    # 群体行为投入
    class_behavioral_engagement: float = 0.0
    class_on_task_rate: float = 0.0
    class_disruptive_rate: float = 0.0
    
    # 群体认知投入
    class_cognitive_engagement: float = 0.0
    class_cognitive_depth: float = 0.0
    class_mind_wandering_rate: float = 0.0
    
    # 群体学习投入指数
    class_learning_engagement_index: float = 0.0
    
    # 布鲁姆认知层次分布
    bloom_distribution: Dict[str, float] = field(default_factory=dict)
    
    # 认知状态分布
    cognitive_state_distribution: Dict[str, int] = field(default_factory=dict)
    
    # 注意力动态
    class_attention_trend: str = "stable"      # rising / stable / declining / crisis
    attention_cycle_phase: str = "unknown"     # peak / decline / trough / recovery
    
    # 教学建议
    pedagogical_suggestions: List[str] = field(default_factory=list)
    
    # 社会传染指标
    contagion_index: float = 0.0               # 分心行为传染指数


# ==================== 核心分析器 ====================

class EducationalBehaviorAnalyzer:
    """
    教育学行为分析器
    将CV几何检测结果转换为教育学语义
    """
    
    def __init__(self, attention_cycle_sec: float = ATTENTION_CYCLE_SECONDS):
        self.attention_cycle = attention_cycle_sec
        self.student_profiles: Dict[str, StudentEngagementProfile] = {}
        self.class_start_time: Optional[float] = None
        self.frame_history: deque = deque(maxlen=256)
        
    def reset_class(self):
        """新课开始时重置"""
        self.student_profiles.clear()
        self.class_start_time = time.monotonic()
        self.frame_history.clear()
    
    # -------------------- 姿态教育学解码 --------------------
    
    def decode_posture_education(
        self,
        keypoints: np.ndarray,
        raw_behavior: str,
        confidence: float,
    ) -> BehavioralEvent:
        """
        将几何关键点解码为教育学姿态语义
        
        Args:
            keypoints: 归一化后的17个关键点 (17, 2)
            raw_behavior: CV原始行为标签
            confidence: 检测置信度
            
        Returns:
            BehavioralEvent: 包含教育学推断的事件
        """
        event = BehavioralEvent(
            timestamp=time.monotonic(),
            raw_behavior=raw_behavior,
            keypoints=keypoints,
            confidence=confidence,
        )
        
        if keypoints is None or not hasattr(keypoints, 'shape') or keypoints.ndim != 2 or keypoints.shape[0] < 17 or keypoints.shape[1] < 2:
            return event
        
        # 提取关键点
        nose = keypoints[0]
        left_eye = keypoints[1]
        right_eye = keypoints[2]
        left_ear = keypoints[3]
        right_ear = keypoints[4]
        left_shoulder = keypoints[5]
        right_shoulder = keypoints[6]
        left_elbow = keypoints[7]
        right_elbow = keypoints[8]
        left_wrist = keypoints[9]
        right_wrist = keypoints[10]
        
        shoulder_center = (left_shoulder + right_shoulder) / 2
        
        # 1. 头部姿态解码
        head_vertical = nose[1] - shoulder_center[1]  # 正值为低头
        head_turn = (left_ear[0] - right_ear[0])       # 头部转向
        
        if head_vertical > 0.18:
            event.head_pose = "down"
        elif head_vertical < -0.10:
            event.head_pose = "up"
        elif head_turn > 0.06:
            event.head_pose = "turned_left"
        elif head_turn < -0.06:
            event.head_pose = "turned_right"
        else:
            event.head_pose = "forward"
        
        # 2. 视线方向推断 (简化版，基于头部姿态)
        if event.head_pose == "forward":
            event.gaze_direction = "front"
        elif event.head_pose == "down":
            # 如果眼睛可见且在低头的合理范围内，可能是阅读/书写
            eyes_visible = (
                np.linalg.norm(left_eye) > 0.001 
                and np.linalg.norm(right_eye) > 0.001
            )
            if eyes_visible and head_vertical < 0.30:
                event.gaze_direction = "down_reading"
            else:
                event.gaze_direction = "down_sleeping"
        elif event.head_pose in ("turned_left", "turned_right"):
            event.gaze_direction = "sideways"
        else:
            event.gaze_direction = "unknown"
        
        # 3. 身体前倾度 (教育心理学中，身体前倾通常表示投入)
        hip_center = (keypoints[11] + keypoints[12]) / 2
        torso_vector = shoulder_center - hip_center
        # 前倾时肩部x相对髋部前移 (假设图像坐标x向右)
        # 使用肩-髋连线与垂直线的夹角近似
        if np.linalg.norm(torso_vector) > 0.001:
            lean_angle = np.arctan2(torso_vector[0], -torso_vector[1])
            event.body_lean = np.clip(lean_angle / 0.5, -1.0, 1.0)  # 归一化
        
        # 4. 手部位置
        left_wrist_y = left_wrist[1]
        right_wrist_y = right_wrist[1]
        shoulder_y = shoulder_center[1]
        
        # 判断是否有手在桌面高度 (书写区域)
        hand_on_desk = (left_wrist_y > shoulder_y + 0.05) or (right_wrist_y > shoulder_y + 0.05)
        hand_near_face = raw_behavior == "查看手机"  # CV已检测
        
        if hand_near_face:
            event.hand_position = "near_face"
        elif hand_on_desk and event.head_pose == "down":
            event.hand_position = "writing"
        elif hand_on_desk:
            event.hand_position = "resting"
        else:
            event.hand_position = "unknown"
        
        # 5. 布鲁姆认知层次映射
        event.bloom_level = self._map_to_bloom_level(event)
        
        # 6. 认知状态推断 (单帧)
        event.cognitive_state = self._infer_cognitive_state(event, raw_behavior)
        
        return event
    
    def _map_to_bloom_level(self, event: BehavioralEvent) -> BloomLevel:
        """
        将姿态语义映射到布鲁姆认知层次
        
        映射逻辑 (基于课堂可观测行为):
        - 单纯注视前方 → Remembering (被动接收)
        - 注视+身体前倾 → Understanding (主动跟随)
        - 低头书写/记录 → Applying (主动加工)
        - 注视+停顿+身体前倾 → Analyzing (深度思考)
        - 看手机/交谈/睡觉 → Unknown (非学习行为)
        """
        if event.raw_behavior in ("睡觉", "查看手机", "离开座位"):
            return BloomLevel.UNKNOWN
        
        if event.raw_behavior == "与他人交谈":
            # 课堂讨论可能涉及高阶思维，但当前无法区分
            return BloomLevel.UNDERSTANDING
        
        # 专注学习状态下的细分
        if event.hand_position == "writing":
            # 记录笔记 → Applying (主动加工信息)
            return BloomLevel.APPLYING
        
        if event.gaze_direction == "front":
            if event.body_lean > 0.3:
                # 身体前倾注视 → Understanding到Analyzing
                return BloomLevel.ANALYZING
            elif event.body_lean > 0.1:
                return BloomLevel.UNDERSTANDING
            else:
                # 单纯注视，无明显前倾 → Remembering
                return BloomLevel.REMEMBERING
        
        if event.gaze_direction == "down_reading":
            # 阅读/查看材料 → Applying
            return BloomLevel.APPLYING
        
        return BloomLevel.UNDERSTANDING
    
    def _infer_cognitive_state(self, event: BehavioralEvent, raw_behavior: str) -> CognitiveState:
        """
        基于单帧姿态推断认知状态
        
        注意: 单帧推断不确定性高，需要结合时序数据验证
        """
        if raw_behavior == "睡觉":
            return CognitiveState.MIND_WANDERING
        
        if raw_behavior == "查看手机":
            return CognitiveState.TASK_SWITCHING
        
        if raw_behavior == "离开座位":
            return CognitiveState.MIND_WANDERING
        
        if raw_behavior == "与他人交谈":
            return CognitiveState.TASK_SWITCHING
        
        # 专注学习状态下的细分
        if event.hand_position == "writing":
            return CognitiveState.DEEP_PROCESSING
        
        if event.gaze_direction == "front":
            if event.body_lean > 0.2:
                return CognitiveState.DEEP_PROCESSING
            else:
                return CognitiveState.PASSIVE_LISTENING
        
        if event.gaze_direction == "down_reading":
            return CognitiveState.DEEP_PROCESSING
        
        return CognitiveState.SHALLOW_ATTENTION
    
    # -------------------- 时序认知分析 --------------------
    
    def update_student_profile(
        self,
        track_id: str,
        event: BehavioralEvent,
    ) -> StudentEngagementProfile:
        """
        更新单个学生的学习投入画像
        
        基于时序行为数据计算认知投入指标
        """
        if track_id not in self.student_profiles:
            self.student_profiles[track_id] = StudentEngagementProfile(track_id=track_id)
        
        profile = self.student_profiles[track_id]
        profile.behavior_history.append(event)
        
        history = list(profile.behavior_history)
        total = len(history)
        
        # 1. 计算行为投入指标（单帧也计算）
        on_task_count = sum(1 for e in history if e.raw_behavior == "专注学习")
        active_count = sum(1 for e in history if e.hand_position == "writing")
        disruptive_count = sum(1 for e in history if e.raw_behavior in ("查看手机", "睡觉", "离开座位"))
        
        profile.on_task_rate = on_task_count / total
        profile.active_participation_rate = active_count / total
        profile.disruptive_rate = disruptive_count / total
        
        # 2. 计算认知投入指标（单帧使用当前帧推断，多帧使用时序统计）
        if len(history) >= 10:
            # 多帧：使用时序统计
            consecutive_focus = self._max_consecutive_focus(history)
            profile.sustained_attention_score = min(1.0, consecutive_focus / 30)
            
            valid_bloom = [e for e in history if e.bloom_level != BloomLevel.UNKNOWN]
            if valid_bloom:
                depth_scores = [BLOOM_LEVEL_SCORES.get(e.bloom_level.value, 0.5) for e in valid_bloom]
                profile.cognitive_depth_score = float(np.mean(depth_scores)) if depth_scores else 0.0
            
            switches = sum(
                1 for i in range(1, len(history))
                if history[i].raw_behavior != history[i-1].raw_behavior
            )
            profile.attention_stability = max(0.0, 1.0 - switches / total)
            profile.task_switching_freq = switches / max(1, total)
            
            bloom_counts = {}
            for e in valid_bloom:
                level = e.bloom_level.value
                bloom_counts[level] = bloom_counts.get(level, 0) + 1
            profile.bloom_distribution = {
                k: v / len(valid_bloom) for k, v in bloom_counts.items()
            } if valid_bloom else {}
        else:
            # 单帧/少帧：基于当前帧直接推断
            profile.sustained_attention_score = 1.0 if event.raw_behavior == "专注学习" else 0.3
            profile.cognitive_depth_score = BLOOM_LEVEL_SCORES.get(event.bloom_level.value, 0.5)
            profile.attention_stability = 1.0  # 单帧默认稳定
            profile.task_switching_freq = 0.0
            profile.bloom_distribution = {event.bloom_level.value: 1.0} if event.bloom_level != BloomLevel.UNKNOWN else {}
        
        # 3. 计算注意力动态
        profile.attention_baseline = self._estimate_attention_baseline(profile)
        recent_focus = sum(
            1 for e in history[-20:]
            if e.raw_behavior == "专注学习"
        ) / min(20, len(history))
        profile.attention_deviation = recent_focus - profile.attention_baseline
        
        profile.is_abnormal_decline = (
            profile.attention_baseline > 0.5 
            and profile.attention_deviation < -0.35
        )
        
        # 4. 认知状态时序验证
        cognitive_states = [e.cognitive_state for e in history[-COGNITIVE_WINDOW_FRAMES:]]
        if cognitive_states:
            state_counts = {}
            for s in cognitive_states:
                state_counts[s] = state_counts.get(s, 0) + 1
            dominant_state = max(state_counts, key=state_counts.get)
            profile.cognitive_state_history.append(dominant_state)
        
        # 5. 综合学习投入指数 (LEI) —— 无论单帧多帧都计算
        self._calculate_engagement_indices(profile)
        
        return profile
    
    def _max_consecutive_focus(self, history: List[BehavioralEvent]) -> int:
        """计算最长连续专注帧数"""
        max_streak = 0
        current = 0
        for e in history:
            if e.raw_behavior == "专注学习":
                current += 1
                max_streak = max(max_streak, current)
            else:
                current = 0
        return max_streak
    
    def _estimate_attention_baseline(self, profile: StudentEngagementProfile) -> float:
        """
        估计个体注意力基线
        
        使用历史数据中前1/3的专注率作为基线
        (假设课堂开始时学生注意力通常较高)
        """
        history = list(profile.behavior_history)
        if len(history) < 15:
            return 0.7  # 默认基线
        
        early_third = history[:max(1, len(history) // 3)]
        early_focus = sum(1 for e in early_third if e.raw_behavior == "专注学习")
        baseline = early_focus / len(early_third)
        
        # 基线不应低于0.4或高于0.95
        return float(np.clip(baseline, 0.4, 0.95))
    
    def _calculate_engagement_indices(self, profile: StudentEngagementProfile):
        """计算三维学习投入指数"""
        # BEI: 行为投入指数
        profile.behavioral_engagement_index = (
            0.30 * profile.attendance_rate
            + 0.35 * profile.on_task_rate
            + 0.20 * profile.active_participation_rate
            + 0.15 * max(0.0, 1.0 - profile.disruptive_rate * 2)
        )
        
        # CEI: 认知投入指数
        profile.cognitive_engagement_index = (
            0.30 * profile.sustained_attention_score
            + 0.25 * profile.cognitive_depth_score
            + 0.25 * profile.attention_stability
            + 0.20 * max(0.0, 1.0 - profile.task_switching_freq * 3)
        )
        
        # EEI: 情感投入指数 (当前主要基于行为 proxies)
        # 高行为投入+高认知投入通常伴随正向情感
        profile.emotional_engagement_index = (
            0.6 * profile.behavioral_engagement_index
            + 0.4 * profile.cognitive_engagement_index
        )
        
        # LEI: 综合学习投入指数
        profile.learning_engagement_index = (
            BEHAVIORAL_WEIGHT * profile.behavioral_engagement_index
            + COGNITIVE_WEIGHT * profile.cognitive_engagement_index
            + EMOTIONAL_WEIGHT * profile.emotional_engagement_index
        )
    
    # -------------------- 课堂群体分析 --------------------
    
    def generate_classroom_report(
        self,
        student_profiles: Dict[str, StudentEngagementProfile],
    ) -> ClassroomEngagementReport:
        """
        生成课堂整体学习投入报告
        
        结合社会传染理论与注意力动态模型
        """
        report = ClassroomEngagementReport(
            timestamp=time.monotonic(),
            student_count=len(student_profiles),
        )
        
        if not student_profiles:
            return report
        
        profiles = list(student_profiles.values())
        n = len(profiles)
        
        # 1. 群体行为投入
        report.class_behavioral_engagement = float(np.mean([
            p.behavioral_engagement_index for p in profiles
        ]))
        report.class_on_task_rate = float(np.mean([
            p.on_task_rate for p in profiles
        ]))
        report.class_disruptive_rate = float(np.mean([
            p.disruptive_rate for p in profiles
        ]))
        
        # 2. 群体认知投入
        report.class_cognitive_engagement = float(np.mean([
            p.cognitive_engagement_index for p in profiles
        ]))
        report.class_cognitive_depth = float(np.mean([
            p.cognitive_depth_score for p in profiles if p.cognitive_depth_score > 0
        ])) if any(p.cognitive_depth_score > 0 for p in profiles) else 0.0
        report.class_mind_wandering_rate = float(np.mean([
            1.0 if p.is_abnormal_decline else 0.0 for p in profiles
        ]))
        
        # 3. 综合学习投入指数
        report.class_learning_engagement_index = float(np.mean([
            p.learning_engagement_index for p in profiles
        ]))
        
        # 4. 布鲁姆认知层次分布 (群体聚合)
        all_bloom = {}
        total_bloom_count = 0
        for p in profiles:
            for level, ratio in p.bloom_distribution.items():
                all_bloom[level] = all_bloom.get(level, 0.0) + ratio
                total_bloom_count += ratio
        if total_bloom_count > 0:
            report.bloom_distribution = {
                k: round(v / total_bloom_count, 4) for k, v in all_bloom.items()
            }
        
        # 5. 认知状态分布
        state_counts = {}
        for p in profiles:
            if p.cognitive_state_history:
                recent_state = p.cognitive_state_history[-1]
                state_name = recent_state.value
                state_counts[state_name] = state_counts.get(state_name, 0) + 1
        report.cognitive_state_distribution = state_counts
        
        # 6. 注意力动态分析
        # 课堂注意力周期相位判断
        if self.class_start_time:
            elapsed = time.monotonic() - self.class_start_time
            cycle_phase = (elapsed % self.attention_cycle) / self.attention_cycle
            if cycle_phase < 0.25:
                report.attention_cycle_phase = "peak"
            elif cycle_phase < 0.50:
                report.attention_cycle_phase = "decline"
            elif cycle_phase < 0.75:
                report.attention_cycle_phase = "trough"
            else:
                report.attention_cycle_phase = "recovery"
        
        # 注意力趋势判断
        recent_lei = [p.learning_engagement_index for p in profiles]
        avg_lei = float(np.mean(recent_lei))
        if report.class_mind_wandering_rate > 0.4:
            report.class_attention_trend = "crisis"
        elif report.class_mind_wandering_rate > 0.25:
            report.class_attention_trend = "declining"
        elif avg_lei > 0.75:
            report.class_attention_trend = "rising"
        else:
            report.class_attention_trend = "stable"
        
        # 7. 社会传染指数 (Social Contagion Index)
        # 基于空间邻域内分心行为的聚集程度
        report.contagion_index = self._calculate_contagion_index(profiles)
        
        # 8. 生成教学建议
        report.pedagogical_suggestions = self._generate_pedagogical_suggestions(report)
        
        return report
    
    def _calculate_contagion_index(
        self,
        profiles: List[StudentEngagementProfile],
    ) -> float:
        """
        计算分心行为的社会传染指数
        
        原理: 如果分心学生在空间中聚集(相邻座位同时分心)，
        说明可能存在社会传染而非个体因素
        
        简化实现: 使用注意力偏离的方差作为 proxy
        - 方差低: 大家同步分心 → 高传染 (可能是教学因素)
        - 方差高: 随机分心 → 低传染 (个体因素)
        """
        deviations = [p.attention_deviation for p in profiles]
        if len(deviations) < 3:
            return 0.0
        
        std_dev = float(np.std(deviations))
        # 低方差+普遍偏离基线 = 高传染
        mean_dev = float(np.mean(deviations))
        
        if mean_dev < -0.2 and std_dev < 0.25:
            return 0.8  # 群体同步分心，高传染
        elif mean_dev < -0.2:
            return 0.5  # 普遍分心但不同步
        elif std_dev < 0.2:
            return 0.3  # 状态趋同但不算差
        else:
            return 0.1  # 个体差异大，低传染
    
    def _generate_pedagogical_suggestions(
        self,
        report: ClassroomEngagementReport,
    ) -> List[str]:
        """基于数据生成教学建议"""
        suggestions = []
        
        if report.class_learning_engagement_index >= 0.80:
            suggestions.append("课堂整体投入度优秀，可维持当前教学节奏，适当增加高阶思维任务。")
        elif report.class_learning_engagement_index >= 0.60:
            suggestions.append("课堂投入度良好，建议穿插互动环节以维持认知活跃。")
        elif report.class_learning_engagement_index >= 0.40:
            suggestions.append("课堂投入度一般，建议调整教学策略: 缩短连续讲授时长，增加小组讨论或即时测验。")
        else:
            suggestions.append("课堂投入度较低，建议立即调整: 暂停讲授，进行课堂互动或认知唤醒活动。")
        
        if report.class_mind_wandering_rate > 0.30:
            suggestions.append(
                f"检测到{report.class_mind_wandering_rate*100:.0f}%学生出现注意力异常下降，"
                "可能与认知过载有关，建议分解复杂概念或提供可视化辅助。"
            )
        
        if report.contagion_index > 0.5:
            suggestions.append(
                "分心行为呈现群体聚集特征，提示可能存在课堂氛围问题或教学内容难度不适配，"
                "建议检查当前知识点是否过难或过易。"
            )
        
        if report.class_cognitive_depth < 0.55:
            suggestions.append(
                "学生认知活动多停留在记忆/理解层面，建议设计应用/分析类任务以促进深度学习。"
            )
        elif report.class_cognitive_depth > 0.80:
            suggestions.append(
                "学生处于高认知投入状态，注意控制认知负荷，避免过度消耗导致后续疲劳。"
            )
        
        # 注意力周期建议
        if report.attention_cycle_phase == "trough":
            suggestions.append(
                "当前处于课堂注意力周期低谷，建议进行2-3分钟的认知唤醒活动(如快速问答、肢体活动)。"
            )
        elif report.attention_cycle_phase == "decline":
            suggestions.append(
                "课堂注意力进入下降阶段，建议通过案例引入或问题驱动重新聚焦。"
            )
        
        return suggestions
    
    # -------------------- 辅助函数 --------------------
    
    def get_profile_summary(self, track_id: str) -> Dict[str, Any]:
        """获取单个学生的学习投入摘要"""
        p = self.student_profiles.get(track_id)
        if p is None:
            return {}
        
        recent_states = list(p.cognitive_state_history)[-5:]
        
        return {
            "track_id": p.track_id,
            "behavioral_engagement_index": round(p.behavioral_engagement_index, 3),
            "cognitive_engagement_index": round(p.cognitive_engagement_index, 3),
            "emotional_engagement_index": round(p.emotional_engagement_index, 3),
            "learning_engagement_index": round(p.learning_engagement_index, 3),
            "attention_baseline": round(p.attention_baseline, 3),
            "attention_deviation": round(p.attention_deviation, 3),
            "is_abnormal_decline": p.is_abnormal_decline,
            "on_task_rate": round(p.on_task_rate, 3),
            "active_participation_rate": round(p.active_participation_rate, 3),
            "cognitive_depth_score": round(p.cognitive_depth_score, 3),
            "attention_stability": round(p.attention_stability, 3),
            "bloom_distribution": p.bloom_distribution,
            "recent_cognitive_states": [s.value for s in recent_states],
        }
    
    def get_report_summary(self) -> Dict[str, Any]:
        """获取课堂报告摘要"""
        report = self.generate_classroom_report(self.student_profiles)
        return {
            "timestamp": report.timestamp,
            "student_count": report.student_count,
            "class_learning_engagement_index": round(report.class_learning_engagement_index, 3),
            "class_behavioral_engagement": round(report.class_behavioral_engagement, 3),
            "class_cognitive_engagement": round(report.class_cognitive_engagement, 3),
            "class_on_task_rate": round(report.class_on_task_rate, 3),
            "class_disruptive_rate": round(report.class_disruptive_rate, 3),
            "class_mind_wandering_rate": round(report.class_mind_wandering_rate, 3),
            "class_cognitive_depth": round(report.class_cognitive_depth, 3),
            "attention_cycle_phase": report.attention_cycle_phase,
            "class_attention_trend": report.class_attention_trend,
            "contagion_index": round(report.contagion_index, 3),
            "bloom_distribution": report.bloom_distribution,
            "cognitive_state_distribution": report.cognitive_state_distribution,
            "pedagogical_suggestions": report.pedagogical_suggestions,
            "theoretical_framework": [
                "Fredricks三维学习投入模型 (Behavioral/Cognitive/Emotional Engagement)",
                "Bloom认知分类法修订版 (Anderson & Krathwohl, 2001)",
                "持续性注意力动态模型 (Attention Cycle Theory)",
                "社会传染理论 (Social Contagion in Classroom)",
            ],
        }
