from typing import Literal

from app.core.config import settings

DEFAULT_PROMPT_KEY = "tutor"
PROMPT_PRESETS: dict[str, dict[str, str]] = {
    "tutor": {
        "label": "学习辅导",
        "description": "分步骤讲解，强调理解与迁移。",
        "prompt": (
            "你是一名学习辅导助手。"
            "请优先依据给定知识片段回答，禁止编造。"
            "若信息不足，明确说明并给出最小补充建议。"
        ),
    },
    "exam": {
        "label": "考试作答",
        "description": "按考试得分点组织答案。",
        "prompt": (
            "你是一名考试辅导助手。请按“得分点”结构化回答。"
            "先给【结论】，再列要点，每点简短清晰。结论部分限制在50字内。回答总字数在200字内。"
            "仅依据知识片段作答，禁止编造。"
        ),
    },
    "concise": {
        "label": "简洁速答",
        "description": "更短更直接，适合快速确认。",
        "prompt": (
            "请用简洁风格回答：先一句话结论，再给 3-5 条关键点。"
            "不展开无关背景，保持可执行。"
        ),
    },
    "socratic": {
        "label": "苏格拉底引导",
        "description": "先用问题引导思考，再给提示。",
        "prompt": (
            "请采用苏格拉底式引导：先提出 1-2 个关键问题，"
            "再给方向性提示，最后给参考答案。"
            "内容必须基于知识片段。"
        ),
    },
}

AgentName = Literal[
    "code_tutor", "knowledge_mentor", "planner", "analyst", "supervisor"
]

AGENT_CONFIG: dict[AgentName, dict[str, str]] = {
    "code_tutor": {
        "label": "代码导师",
        "prompt": (
            "你是 Code_Tutor_Agent，专注代码报错、调试、原理讲解与最小修复建议。"
            "优先给出可执行步骤与验证方式。"
        ),
    },
    "knowledge_mentor": {
        "label": "学科知识讲师",
        "prompt": (
            "你是 Knowledge_Mentor_Agent，面向多学科（经管、数理、文史、自然科学等）做知识点讲解、概念辨析与例题思路。"
            "用分步说明帮助理解，避免与纯代码排错混淆；需要代码时再建议用户也可咨询代码导师。"
        ),
    },
    "planner": {
        "label": "学习规划师",
        "prompt": (
            "你是 Planner_Agent，专注学习目标拆解、计划重排、进度追踪与里程碑设计。"
            "回答应包含阶段目标与下一步行动。"
        ),
    },
    "analyst": {
        "label": "学习分析师",
        "prompt": (
            "你是 Analyst_Agent，专注行为分析、风险识别和数据解释。"
            "结论应清晰并附带可执行改进建议。"
        ),
    },
    "supervisor": {
        "label": "协作主管",
        "prompt": "主管节点仅负责编排与最终汇总，不直接承担单科答疑。",
    },
}

def get_active_model_name() -> str:
    if settings.CHAT_PROVIDER.lower() == "ollama":
        return settings.OLLAMA_MODEL
    return settings.CHAT_MODEL


def list_prompt_presets() -> list[dict[str, str]]:
    return [
        {
            "key": key,
            "label": value["label"],
            "description": value["description"],
        }
        for key, value in PROMPT_PRESETS.items()
    ]


def get_chat_runtime_settings() -> dict:
    return {
        "provider": settings.CHAT_PROVIDER.lower(),
        "model": get_active_model_name(),
        "rag_k_options": [3, 4, 5],
        "rag_k_default": 4,
        "strict_mode_default": False,
        "default_prompt_key": DEFAULT_PROMPT_KEY,
        "prompt_options": list_prompt_presets(),
        "agent_options": [
            {
                "key": key,
                "label": value["label"],
                "description": value["prompt"],
            }
            for key, value in AGENT_CONFIG.items()
            if key != "supervisor"
        ],
        "tool_options": [
            {
                "key": "knowledge_base",
                "label": "知识库检索",
                "description": "检索课程与文档知识片段。",
            },
            {
                "key": "web_search",
                "label": "联网搜索",
                "description": "从外部网络检索公开信息。",
            },
            {
                "key": "code_sandbox",
                "label": "代码沙盒",
                "description": "在安全沙盒中运行代码并返回结果。",
            },
            {
                "key": "behavior_analysis",
                "label": "行为分析",
                "description": "对课堂行为图片进行分析。",
            },
        ],
        "default_active_tools": ["knowledge_base", "web_search", "code_sandbox"],
    }


def resolve_system_prompt(prompt_key: str, custom_prompt: str) -> str:
    preset = PROMPT_PRESETS.get(prompt_key) or PROMPT_PRESETS[DEFAULT_PROMPT_KEY]
    preset_prompt = preset["prompt"].strip()
    custom = (custom_prompt or "").strip()
    if not custom:
        return preset_prompt
    return f"{preset_prompt}\n\n补充要求：\n{custom}"
