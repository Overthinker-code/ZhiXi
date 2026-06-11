/**
 * 将后端流水线 thought / phase 转为 DeepSeek 式第一人称思考独白（纯文字，无阶段标签重复）。
 */

function stripTag(raw: string): { tag: string; body: string } {
  const m = String(raw).trim().match(/^【([^】]+)】([\s\S]*)$/);
  if (m) return { tag: m[1].trim(), body: m[2].trim() };
  return { tag: '', body: String(raw).trim() };
}

const STAGE_NARRATIVE: Record<string, string> = {
  pipeline_start:
    '用户刚发来一个问题。我先快速判断它属于哪类学习场景，再决定要不要走检索、联网或多步推理。',
  kb_inject:
    '课程知识库里应该有相关段落，我先去检索并核对，确保后面的解释有依据、不凭空编造。',
  tool_policy:
    '根据问题类型，我会按需启用检索、联网或代码沙盒等工具，用不上的能力先关掉，避免干扰回答。',
  web_policy:
    '这道题可能需要较新的外部信息，我准备补充一次联网检索，和知识库内容交叉验证。',
  tool_run: '正在调用后端工具获取中间结果，拿到数据后再组织语言。',
  vision_status: '用户附带了图片，我先理解画面里的关键信息，再结合文字问题一起分析。',
  demo_mode: '当前处于演示模式，我会用稳定的示例回答保证展示效果。',
  cache: '这个问题和之前的很相似，可以直接复用已验证过的回答要点。',
};

function tagNarrative(tag: string, body: string): string | null {
  const t = tag.toLowerCase();
  if (/流水线|主管|协作|策略|拆解/.test(tag)) {
    return body
      ? `我先梳理一下整体思路：${body}`
      : '我先梳理一下整体思路，把任务拆成几步来完成。';
  }
  if (/知识检索|RAG|检索|文档|知识库/.test(tag)) {
    return body
      ? `我去知识库里找相关内容：${body}`
      : '我去知识库里找与问题相关的知识点和教材片段。';
  }
  if (/联网|web/i.test(tag)) {
    return body
      ? `需要补充外部信息：${body}`
      : '可能需要联网查一下最新资料，和已有知识对照一下。';
  }
  if (/学情|行为|画像/.test(tag)) {
    return body
      ? `结合学习行为数据看：${body}`
      : '我会参考这位同学的学习行为和掌握情况来定制回答。';
  }
  if (/测验|出题|练习/.test(tag)) {
    return body
      ? `关于练习与测验：${body}`
      : '用户可能想练手，我先准备合适的题目和讲解思路。';
  }
  if (/代码|沙盒|debug/i.test(tag)) {
    return body
      ? `代码相关：${body}`
      : '这像是编程题，我需要在沙盒里验证逻辑再给出解释。';
  }
  if (/汇总|审查|安全|合成/.test(tag)) {
    return body
      ? `整理最终答复前：${body}`
      : '各模块的结果都齐了，我来做最后一遍核对和润色。';
  }
  if (/视觉|图像|图片/.test(tag)) {
    return body ? `看图理解：${body}` : '先理解图片内容，再回答文字问题。';
  }
  if (/工具执行/.test(tag)) {
    return body || '工具正在跑，等结果回来再继续。';
  }
  if (body && body.length > 4 && !/^[a-z_]+$/i.test(body)) {
    return body;
  }
  return null;
}

/** 单条 thought 转为可追加的自然语言段落 */
export function thoughtToNarrative(
  raw: string,
  stage?: string
): string | null {
  const trimmed = String(raw || '').trim();
  if (!trimmed) return null;

  const stageKey = String(stage || '').trim();
  if (stageKey && STAGE_NARRATIVE[stageKey]) {
    const base = STAGE_NARRATIVE[stageKey];
    const { body } = stripTag(trimmed);
    if (body && body.length > 8 && !base.includes(body.slice(0, 20))) {
      return `${base} ${body}`;
    }
    return base;
  }

  const { tag, body } = stripTag(trimmed);
  if (tag) {
    const fromTag = tagNarrative(tag, body);
    if (fromTag) return fromTag;
  }

  if (/^(agent|planner|router|tool|worker)_/i.test(trimmed)) return null;
  if (/^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$/i.test(trimmed) && trimmed.length < 48) {
    return null;
  }

  return body || trimmed;
}

/** 追加段落，避免重复相同句子 */
export function appendThoughtToReasoning(
  existing: string,
  raw: string,
  stage?: string
): string {
  const line = thoughtToNarrative(raw, stage);
  if (!line) return existing;
  const prev = (existing || '').trim();
  if (!prev) return line;
  if (prev.includes(line) || prev.endsWith(line.slice(0, 40))) return prev;
  return `${prev}\n\n${line}`;
}

export function phaseSummaryToNarrative(event: {
  phase?: string;
  summary?: string;
  agent?: string;
}): string | null {
  const summary = String(event.summary || '').trim();
  if (!summary) return null;
  if (/^理解/.test(summary) && summary.length < 12) return null;
  if (/协作处理中|理解问题/.test(summary) && summary.length < 20) {
    return thoughtToNarrative(`【协作】${summary}`);
  }
  return summary;
}

export default thoughtToNarrative;
