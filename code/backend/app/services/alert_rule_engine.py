"""
课堂行为预警规则引擎
基于教育学参数生成真实预警，替代alerts.py中的mock数据

联动方案：联动3 - 注意力异常 + 社会传染 -> 实时预警
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import uuid4


@dataclass
class AlertEvent:
    id: str
    student_id: Optional[str]           # None表示群体预警
    student_name: Optional[str]
    alert_time: str
    reason: str
    severity: str                       # low / medium / high
    alert_type: str                     # individual_overload / group_contagion / attention_trough / cognitive_shallow
    trigger_metrics: Dict[str, Any] = field(default_factory=dict)


class AlertRuleEngine:
    """
    预警规则引擎
    
    规则设计原则：
    1. 个体规则：基于学生自身画像的异常偏离
    2. 群体规则：基于课堂整体指标的异常
    3. 周期规则：基于注意力动态模型的阶段提示
    4. 控制推送频率，避免信息过载
    """
    
    def __init__(self):
        # 用于去重和频率控制的内存缓存（生产环境建议用Redis）
        self._last_alert_time: Dict[str, datetime] = {}
        self._cooldown_seconds = 30       # 同类型预警冷却时间
    
    def evaluate(
        self,
        educational_report: Dict[str, Any],
        person_profiles: Dict[str, Any],
        student_name_map: Optional[Dict[str, str]] = None,
    ) -> List[AlertEvent]:
        """
        评估当前课堂状态，生成预警列表
        
        Args:
            educational_report: 课堂整体报告（来自educational_behavior.get_report_summary）
            person_profiles: {track_id: StudentEngagementProfile} 学生画像字典
            student_name_map: {track_id: student_name} 学生姓名映射
            
        Returns:
            List[AlertEvent]: 预警事件列表（最多3条，避免信息过载）
        """
        alerts: List[AlertEvent] = []
        now = datetime.utcnow()
        name_map = student_name_map or {}
        
        # ==================== 规则1: 群体传染预警 ====================
        contagion = educational_report.get("contagion_index", 0.0)
        if contagion > 0.5:
            alert_key = "group_contagion"
            if self._can_trigger(alert_key, now):
                alerts.append(AlertEvent(
                    id=str(uuid4()),
                    student_id=None,
                    student_name=None,
                    alert_time=now.isoformat(),
                    reason=f"分心行为呈群体聚集(传染指数{contagion:.2f})，提示可能存在教学节奏或知识点难度问题",
                    severity="high" if contagion > 0.7 else "medium",
                    alert_type="group_contagion",
                    trigger_metrics={"contagion_index": contagion},
                ))
        
        # ==================== 规则2: 注意力周期低谷预警 ====================
        phase = educational_report.get("attention_cycle_phase", "")
        trend = educational_report.get("class_attention_trend", "")
        if phase == "trough" and trend in ("declining", "crisis"):
            alert_key = "attention_trough"
            if self._can_trigger(alert_key, now):
                alerts.append(AlertEvent(
                    id=str(uuid4()),
                    student_id=None,
                    student_name=None,
                    alert_time=now.isoformat(),
                    reason="课堂处于注意力周期低谷，建议进行2-3分钟认知唤醒活动（快速问答/肢体活动）",
                    severity="medium",
                    alert_type="attention_trough",
                    trigger_metrics={"phase": phase, "trend": trend},
                ))
        
        # ==================== 规则3: 认知深度不足预警 ====================
        cognitive_depth = educational_report.get("class_cognitive_depth", 0.0)
        if cognitive_depth < 0.45:
            alert_key = "cognitive_shallow"
            if self._can_trigger(alert_key, now):
                alerts.append(AlertEvent(
                    id=str(uuid4()),
                    student_id=None,
                    student_name=None,
                    alert_time=now.isoformat(),
                    reason=f"学生认知活动多停留在低阶思维(认知深度{cognitive_depth:.2f})，建议设计应用/分析类任务",
                    severity="medium",
                    alert_type="cognitive_shallow",
                    trigger_metrics={"cognitive_depth": cognitive_depth},
                ))
        
        # ==================== 规则4: 个体认知过载预警 ====================
        for track_id, profile in person_profiles.items():
            # profile是dict（来自behavior_analysis._cache_educational_data）
            if isinstance(profile, dict):
                if not profile.get("is_abnormal_decline", False):
                    continue
                deviation = profile.get("attention_deviation", 0.0)
                lei = profile.get("learning_engagement_index", 1.0)
            else:
                # 兼容dataclass对象
                if not getattr(profile, "is_abnormal_decline", False):
                    continue
                deviation = getattr(profile, "attention_deviation", 0.0)
                lei = getattr(profile, "learning_engagement_index", 1.0)
            
            # 严重偏离且LEI低
            if deviation < -0.35 and lei < 0.5:
                alert_key = f"individual_{track_id}"
                if self._can_trigger(alert_key, now):
                    student_name = name_map.get(track_id, track_id)
                    if isinstance(profile, dict):
                        baseline = profile.get("attention_baseline", 0.7)
                    else:
                        baseline = getattr(profile, "attention_baseline", 0.7)
                    alerts.append(AlertEvent(
                        id=str(uuid4()),
                        student_id=track_id,
                        student_name=student_name,
                        alert_time=now.isoformat(),
                        reason=f"学生{student_name}注意力异常下降(偏离基线{deviation:+.2f})，疑似认知过载",
                        severity="high" if lei < 0.3 else "medium",
                        alert_type="individual_overload",
                        trigger_metrics={
                            "attention_deviation": deviation,
                            "lei": lei,
                            "attention_baseline": baseline,
                        },
                    ))
        
        # ==================== 规则5: 持续走神预警 ====================
        mind_wandering_rate = educational_report.get("class_mind_wandering_rate", 0.0)
        if mind_wandering_rate > 0.3:
            alert_key = "class_mind_wandering"
            if self._can_trigger(alert_key, now):
                alerts.append(AlertEvent(
                    id=str(uuid4()),
                    student_id=None,
                    student_name=None,
                    alert_time=now.isoformat(),
                    reason=f"课堂走神率达{mind_wandering_rate:.0%}，可能与认知过载有关，建议分解复杂概念",
                    severity="high" if mind_wandering_rate > 0.5 else "medium",
                    alert_type="class_mind_wandering",
                    trigger_metrics={"mind_wandering_rate": mind_wandering_rate},
                ))
        
        # 按严重程度排序，最多返回3条
        severity_order = {"high": 0, "medium": 1, "low": 2}
        alerts.sort(key=lambda a: severity_order.get(a.severity, 3))
        return alerts[:3]
    
    def _can_trigger(self, alert_key: str, now: datetime) -> bool:
        """检查是否超过冷却时间"""
        last_time = self._last_alert_time.get(alert_key)
        if last_time is None:
            self._last_alert_time[alert_key] = now
            return True
        elapsed = (now - last_time).total_seconds()
        if elapsed >= self._cooldown_seconds:
            self._last_alert_time[alert_key] = now
            return True
        return False
    
    def reset_cooldown(self):
        """重置冷却（新课程开始时调用）"""
        self._last_alert_time.clear()


# 全局实例
alert_rule_engine = AlertRuleEngine()
