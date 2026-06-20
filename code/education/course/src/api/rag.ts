import axios from 'axios';
import { getToken } from '@/utils/auth';
import { normalizeCitationScope } from '@/utils/citationDisplay';
import { normalizeDisplayText, normalizeSuggestionList, normalizeTextList } from '@/utils/llmDisplay';

/** 会话列表/设置/知识库列表等：尽快失败，避免 AI 页长时间白屏等待 */
const READ_TIMEOUT_MS = 8000;

/** LangGraph 多轮 + 多专员 + 工具，整体可能远长于普通对话；fetch 无默认超时，此处显式放宽 */
const CHAT_STREAM_TIMEOUT_MS = 600000;

export type ReferenceScope = 'system' | 'personal';
export type ReferenceScopeFilter = 'all' | ReferenceScope;

export interface ReferenceFile {
  file_id: string;
  name: string;
  size: number;
  created: string;
  scope?: ReferenceScope;
  owner_id?: string | null;
  can_manage?: boolean;
}

export interface ChatRecord {
  id: number;
  thread_id: string;
  user_input: string;
  system_prompt?: string;
  response: string;
  created_at: string;
  citations?: CitationItem[];
  confidence?: 'high' | 'medium' | 'low' | string;
  grounding_mode?: 'rag' | 'general' | 'tool' | 'mixed' | string;
  suggestions?: string[];
  metrics?: ChatMetrics;
}

export interface ChatThread {
  id: number;
  thread_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface PromptOption {
  key: string;
  label: string;
  description: string;
}

export interface AssistantSettings {
  provider: string;
  model: string;
  rag_k_options: number[];
  rag_k_default: number;
  strict_mode_default: boolean;
  default_prompt_key: string;
  prompt_options: PromptOption[];
  tool_options?: Array<{
    key: string;
    label: string;
    description: string;
  }>;
  default_active_tools?: string[];
  developer_panel_enabled?: boolean;
  demo_mode?: boolean;
}

export interface CitationItem {
  citation_id: number;
  source: string;
  file_id?: string;
  file_name?: string;
  chunk_id?: number | string;
  context_scope?: 'uploaded_document' | 'knowledge_base' | string;
  locator?: string;
  score?: number;
  snippet: string;
  reason?: string;
  relevance_score?: number;
}

const firstText = (...values: unknown[]) => {
  for (const value of values) {
    if (value === undefined || value === null) continue;
    const text = String(value).trim();
    if (text) return text;
  }
  return '';
};

const normalizeCitationText = (value: unknown) => {
  const raw = firstText(value);
  if (!raw) return '';
  const withoutBlockSeparators = raw
    .replace(/<hr\s*\/?>/gi, '\n')
    .split(/\r?\n/)
    .filter((line) => {
      const trimmed = line.trim();
      if (!trimmed) return true;
      if (/^([-*_=])\1{2,}$/.test(trimmed)) return false;
      if (/^[＿_—─━―－﹘﹣]{3,}$/.test(trimmed)) return false;
      if (/^(?:\|\s*:?-{3,}:?\s*)+\|?$/.test(trimmed)) return false;
      return true;
    })
    .join('\n');
  return normalizeDisplayText(withoutBlockSeparators)
    .replace(/(?:^|\s)(?:[-*_=\u2014\u2015\u2500\u2501\uFF3F]){3,}(?=\s|$)/g, ' ')
    .replace(/\|\s*:?-{3,}:?\s*(?=\|)/g, '| ')
    .replace(/\s{2,}/g, ' ')
    .trim();
};

export function normalizeCitationItems(raw: unknown): CitationItem[] {
  const list = Array.isArray(raw) ? raw : [];
  const seen = new Set<string>();

  return list
    .map((entry, index) => {
      const item = (entry || {}) as Record<string, any>;
      const fileId = firstText(
        item.file_id,
        item.fileId,
        item.document_id,
        item.documentId,
        item.doc_id,
        item.docId
      );
      const fileName = firstText(
        item.file_name,
        item.fileName,
        item.filename,
        item.name,
        item.title
      );
      const source = firstText(
        fileName,
        item.source,
        item.path,
        item.document,
        fileId,
        `来源 ${index + 1}`
      );
      const chunkId =
        item.chunk_id ??
        item.chunkId ??
        item.segment_id ??
        item.segmentId ??
        item.chunk ??
        '';
      const locator = firstText(
        item.locator,
        item.location,
        item.page ? `第 ${item.page} 页` : '',
        item.section,
        chunkId ? `片段 ${chunkId}` : ''
      );
      const snippet = normalizeCitationText(
        firstText(item.snippet, item.text, item.content, item.quote, item.excerpt)
      );
      const reason = normalizeCitationText(
        firstText(item.reason, item.match_reason, item.rationale, item.why)
      );
      const citationId = Number(item.citation_id ?? item.citationId ?? index + 1);
      const score = Number(item.relevance_score ?? item.score ?? 0);
      const normalized: CitationItem = {
        citation_id: Number.isFinite(citationId) && citationId > 0 ? citationId : index + 1,
        source,
        file_id: fileId || undefined,
        file_name: fileName || source,
        chunk_id: chunkId || undefined,
        context_scope: normalizeCitationScope(item.context_scope ?? item.scope),
        locator: locator || undefined,
        snippet: snippet || '该证据片段未返回可展示文本，请结合文件定位继续核验。',
        reason: reason || undefined,
        relevance_score: Number.isFinite(score) && score > 0 ? score : undefined,
        score: Number.isFinite(score) && score > 0 ? score : undefined,
      };
      return normalized;
    })
    .filter((item) => {
      const key = [
        item.file_id || item.source,
        item.chunk_id || item.locator || '',
        item.snippet.slice(0, 80),
      ].join('|');
      if (seen.has(key)) return false;
      seen.add(key);
      return Boolean(item.source || item.snippet);
    });
}

export interface ChatMetrics {
  ttft_ms?: number;
  latency_ms?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  estimated_tokens?: boolean;
  agent_hops?: number;
  cache_hit?: boolean;
  rag_hit_count?: number;
  tool_calls_count?: number;
  route_trace?: string[];
}

export function uploadReferenceFile(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('scope', 'personal');
  return axios
    .post('/rag/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 0,
    })
    .then((res: any) => res.data);
}

export function fetchReferenceFiles(scope: ReferenceScopeFilter = 'all') {
  return axios
    .get('/rag/files', {
      params: { scope },
      timeout: READ_TIMEOUT_MS,
    })
    .then((res: any) => (res.data?.files || []) as ReferenceFile[]);
}

export function deleteReferenceFile(fileId: string) {
  return axios.delete(`/rag/files/${fileId}`).then((res: any) => res.data);
}

export function commitReferenceFile(fileId: string) {
  return axios
    .post('/rag/upload/commit', { file_id: fileId })
    .then((res: any) => res.data);
}

export function cancelReferenceFile(fileId: string) {
  return axios
    .post('/rag/upload/cancel', { file_id: fileId })
    .then((res: any) => res.data);
}

export interface StreamPreviewEvent {
  stage:
    | 'saving'
    | 'saved'
    | 'parsing'
    | 'parsed'
    | 'splitting'
    | 'ready'
    | 'committing'
    | 'completed'
    | 'error';
  message: string;
  file_id?: string;
  file_size?: number;
  created_at?: string;
  text_preview?: string;
  chunks_total?: number;
  chunks_preview?: Array<{
    chunk_id: number;
    text_preview: string;
    length: number;
  }>;
  error?: string;
}

export function uploadReferenceFileWithPreview(
  file: File,
  onEvent: (event: StreamPreviewEvent) => void,
  previewChars = 800,
  previewChunks = 5,
  chunkPreviewChars = 300,
  scope: ReferenceScope = 'personal'
) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('preview_chars', String(previewChars));
  formData.append('preview_chunks', String(previewChunks));
  formData.append('chunk_preview_chars', String(chunkPreviewChars));
  formData.append('scope', scope);

  return new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    // use the same baseURL configured for axios so requests hit the backend instead of the dev server
    const base =
      axios.defaults.baseURL || import.meta.env.VITE_API_BASE_URL || '';
    // axios.getUri can also build the URL but we'll just prepend base
    const url = base
      ? `${base.replace(/\/+$/, '')}/rag/upload/preview`
      : '/rag/upload/preview';

    xhr.open('POST', url, true);
    const token = getToken();
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    }

    let lastProcessedLength = 0;

    xhr.onprogress = () => {
      const text = xhr.responseText;
      const newText = text.substring(lastProcessedLength);
      lastProcessedLength = text.length;

      const lines = newText.split('\n');
      lines.forEach((line) => {
        if (line.startsWith('data: ')) {
          try {
            const json = JSON.parse(line.substring(6));
            onEvent(json);

            if (json.stage === 'error') {
              reject(new Error(json.message || 'Upload error'));
            }
          } catch (e) {
            // Ignore JSON parse errors for incomplete lines
          }
        }
      });
    };

    xhr.onload = () => {
      if (xhr.status === 200) {
        resolve();
      } else {
        reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
      }
    };

    xhr.onerror = () => {
      reject(new Error('Network error'));
    };

    xhr.setRequestHeader('Accept', 'text/event-stream');

    xhr.send(formData);
  });
}

export function createAssistantChat(
  userInput: string,
  threadId = 'default',
  options:
    | string
    | {
        systemPrompt?: string;
        ragK?: 3 | 4 | 5;
        promptKey?: string;
        strictMode?: boolean;
        activeTools?: string[];
        maxTokens?: number;
        temperature?: number;
        topP?: number;
        topK?: number;
        currentFileId?: string;
        fileName?: string;
        routeContext?: Record<string, any>;
        imageBase64List?: string[];
        toolMode?:
          | 'chat'
          | 'exercise_grading'
          | 'image_tutoring'
          | 'digital_human_explain';
        forceAgent?: string;
        forceCache?: boolean;
        debugMode?: boolean;
        reasoningEnabled?: boolean;
      } = ''
) {
  const normalized =
    typeof options === 'string' ? { systemPrompt: options } : options || {};

  return axios
    .post(
      '/api/chat/',
      {
        thread_id: threadId,
        user_input: userInput,
        system_prompt: normalized.systemPrompt || '',
        rag_k: normalized.ragK,
        prompt_key: normalized.promptKey,
        strict_mode: normalized.strictMode,
        active_tools: normalized.activeTools,
        max_tokens: normalized.maxTokens,
        temperature: normalized.temperature,
        top_p: normalized.topP,
        top_k: normalized.topK,
        current_file_id: normalized.currentFileId,
        file_id: normalized.currentFileId,
        file_name: normalized.fileName,
        filename: normalized.fileName,
        route_context: normalized.routeContext,
        context_refs: normalized.routeContext,
        image_base64_list: normalized.imageBase64List,
        tool_mode: normalized.toolMode || 'chat',
        force_agent: normalized.forceAgent,
        force_cache: normalized.forceCache,
        debug_mode: normalized.debugMode,
        reasoning_enabled: normalized.reasoningEnabled,
      },
      {
        timeout: 0,
      }
    )
    .then((res: any) => normalizeChatRecord(res.data));
}

export interface ReasoningActionItem {
  action?: 'retrieve' | 'web_search' | 'code' | 'vision' | string;
  title?: string;
  detail?: string;
  items?: string[];
}

export interface ChatStreamEvent {
  type:
    | 'thought'
    | 'phase'
    | 'reasoning_token'
    | 'reasoning_action'
    | 'token'
    | 'citations'
    | 'final'
    | 'error'
    | 'suggestions';
  content?: string;
  action?: string;
  title?: string;
  detail?: string;
  items?: string[];
  phase?: string;
  agent?: string;
  summary?: string;
  status?: string;
  /** 后端可选：pipeline_start | kb_inject | tool_run | … */
  stage?: string;
  data?: unknown[];
  intent?: string;
  routing_reason?: string;
  tool_calls?: any[];
  requires_confirmation?: boolean;
  pending_action_id?: string;
  citations?: CitationItem[];
  confidence?: 'high' | 'medium' | 'low' | string;
  grounding_mode?: 'rag' | 'general' | 'tool' | 'mixed' | string;
  suggestions?: unknown[];
  metrics?: ChatMetrics;
}

function normalizeChatRecord(raw: any): ChatRecord {
  return {
    ...raw,
    citations: normalizeCitationItems(raw?.citations),
    suggestions: normalizeSuggestionList(raw?.suggestions || []),
  } as ChatRecord;
}

function normalizeLearningReport(raw: any): LearningReport {
  return {
    ...raw,
    summary: normalizeDisplayText(raw?.summary),
    overall_summary: normalizeDisplayText(raw?.overall_summary),
    current_goal: normalizeDisplayText(raw?.current_goal),
    learning_style: normalizeDisplayText(raw?.learning_style),
    risk_level: normalizeDisplayText(raw?.risk_level),
    weak_points: normalizeTextList(raw?.weak_points),
    mastery_insights: normalizeTextList(raw?.mastery_insights),
    strengths: normalizeTextList(raw?.strengths),
    recommended_actions: normalizeTextList(raw?.recommended_actions),
    recommended_resources: normalizeTextList(raw?.recommended_resources),
    follow_up_questions: normalizeSuggestionList(raw?.follow_up_questions, 12),
    sections: Array.isArray(raw?.sections)
      ? raw.sections.map((section: any) => ({
          ...section,
          title: normalizeDisplayText(section?.title),
          content: normalizeDisplayText(section?.content),
        }))
      : [],
    process_steps: Array.isArray(raw?.process_steps) ? raw.process_steps : [],
  } as LearningReport;
}

function normalizeReviewPlan(raw: any): ReviewPlan {
  return {
    ...raw,
    summary: normalizeDisplayText(raw?.summary),
    overview: normalizeDisplayText(raw?.overview),
    focus_topics: normalizeTextList(raw?.focus_topics),
    daily_plan: Array.isArray(raw?.daily_plan)
      ? raw.daily_plan.map((day: any) => ({
          ...day,
          day_label: normalizeDisplayText(day?.day_label),
          focus: normalizeDisplayText(day?.focus),
          tasks: normalizeTextList(day?.tasks),
        }))
      : [],
    checkpoints: normalizeTextList(raw?.checkpoints),
  } as ReviewPlan;
}

function normalizeMistakeDigest(raw: any): MistakeDigest {
  return {
    ...raw,
    summary: normalizeDisplayText(raw?.summary),
    mistakes: Array.isArray(raw?.mistakes)
      ? raw.mistakes.map((item: any) => ({
          ...item,
          title: normalizeDisplayText(item?.title),
          symptom: normalizeDisplayText(item?.symptom),
          evidence: normalizeDisplayText(item?.evidence),
          fix_strategy: normalizeDisplayText(item?.fix_strategy),
        }))
      : [],
    flashcards: normalizeTextList(raw?.flashcards),
  } as MistakeDigest;
}

export interface ChatAdvancedOptions {
  systemPrompt?: string;
  ragK?: 3 | 4 | 5;
  promptKey?: string;
  strictMode?: boolean;
  activeTools?: string[];
  maxTokens?: number;
  temperature?: number;
  topP?: number;
  topK?: number;
  selectedText?: string;
  surroundingContext?: string;
  videoTime?: string;
  courseModule?: string;
  currentFileId?: string;
  fileName?: string;
  routeContext?: Record<string, any>;
  imageBase64List?: string[];
  toolMode?:
    | 'chat'
    | 'exercise_grading'
    | 'image_tutoring'
    | 'digital_human_explain';
  forceAgent?: string;
  forceCache?: boolean;
  debugMode?: boolean;
  reasoningEnabled?: boolean;
  signal?: AbortSignal;
}

async function consumeAssistantChatStream(
  url: string,
  payload: Record<string, unknown>,
  onEvent: (event: ChatStreamEvent) => void,
  externalSignal?: AbortSignal
): Promise<void> {
  const token = getToken();
  const controller = new AbortController();
  if (externalSignal) {
    if (externalSignal.aborted) {
      controller.abort();
    } else {
      externalSignal.addEventListener('abort', () => controller.abort(), {
        once: true,
      });
    }
  }
  const timer = window.setTimeout(() => {
    controller.abort();
  }, CHAT_STREAM_TIMEOUT_MS);
  try {
    let res: Response;
    try {
      res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
    } catch (e: unknown) {
      if (e instanceof Error && e.name === 'AbortError') {
        throw new Error(
          `对话生成超时（>${Math.round(
            CHAT_STREAM_TIMEOUT_MS / 1000
          )}s），请稍后重试或缩短问题`
        );
      }
      throw e;
    }
    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      throw new Error(errText || `HTTP ${res.status}`);
    }
    if (!res.body) {
      throw new Error('响应无正文（流不可用）');
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';

    const handleLine = (line: string) => {
      const trimmed = line.replace(/\r$/, '').trim();
      if (!trimmed.startsWith('data: ')) return;
      try {
        const event = JSON.parse(trimmed.slice(6)) as ChatStreamEvent;
        if (event.type === 'suggestions') {
          event.data = normalizeSuggestionList(event.data || []);
        }
        if (event.type === 'final') {
          (event as any).suggestions = normalizeSuggestionList((event as any).suggestions || []);
        }
        onEvent(event);
        if (event.type === 'error') {
          throw new Error(event.content || 'Stream error');
        }
      } catch (e) {
        if (e instanceof SyntaxError) return;
        throw e;
      }
    };

    /* SSE 只能顺序 read；此处 await 不可避免 */
    /* eslint-disable no-await-in-loop */
    for (;;) {
      const { value, done } = await reader.read();
      if (value?.length) {
        buf += decoder.decode(value, { stream: true });
      }
      for (;;) {
        const nl = buf.indexOf('\n');
        if (nl < 0) break;
        const line = buf.slice(0, nl);
        buf = buf.slice(nl + 1);
        handleLine(line);
      }
      if (done) break;
    }
    /* eslint-enable no-await-in-loop */

    if (buf.trim()) {
      handleLine(buf);
    }
  } finally {
    window.clearTimeout(timer);
  }
}

// AI辅助生成：Trae IDE, 2026-04-22
export function createAssistantChatStream(
  userInput: string,
  threadId: string,
  options: ChatAdvancedOptions,
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal
) {
  const normalized = options || {};
  const base =
    axios.defaults.baseURL || import.meta.env.VITE_API_BASE_URL || '';
  const url = base ? `${base.replace(/\/+$/, '')}/api/chat/stream` : '/api/chat/stream';
  const payload = {
    user_input: userInput,
    thread_id: threadId,
    system_prompt: normalized.systemPrompt || '',
    rag_k: normalized.ragK,
    prompt_key: normalized.promptKey,
    strict_mode: normalized.strictMode,
    active_tools: normalized.activeTools,
    max_tokens: normalized.maxTokens,
    temperature: normalized.temperature,
    top_p: normalized.topP,
    top_k: normalized.topK,
    selected_text: normalized.selectedText,
    surrounding_context: normalized.surroundingContext,
    video_time: normalized.videoTime,
    course_module: normalized.courseModule,
    current_file_id: normalized.currentFileId,
    file_id: normalized.currentFileId,
    file_name: normalized.fileName,
    filename: normalized.fileName,
    route_context: normalized.routeContext,
    context_refs: normalized.routeContext,
    image_base64_list: normalized.imageBase64List,
    tool_mode: normalized.toolMode || 'chat',
    force_agent: normalized.forceAgent,
    force_cache: normalized.forceCache,
    debug_mode: normalized.debugMode,
    reasoning_enabled: normalized.reasoningEnabled,
  };

  /** fetch + ReadableStream：避免 XHR 在隧道/跨端口下长时间缓冲无输出 */
  return consumeAssistantChatStream(url, payload, onEvent, signal);
}

export function askSelectionQuery(
  selectedText: string,
  surroundingContext: string,
  threadId: string,
  options: ChatAdvancedOptions
) {
  const normalized = options || {};
  return axios
    .post(
      '/api/chat/selection-query',
      {
        user_input: selectedText,
        selected_text: selectedText,
        surrounding_context: surroundingContext,
        video_time: normalized.videoTime,
        course_module: normalized.courseModule,
        current_file_id: normalized.currentFileId,
        file_id: normalized.currentFileId,
        file_name: normalized.fileName,
        filename: normalized.fileName,
        route_context: normalized.routeContext,
        context_refs: normalized.routeContext,
        image_base64_list: normalized.imageBase64List,
        tool_mode: normalized.toolMode || 'chat',
        force_agent: normalized.forceAgent,
        force_cache: normalized.forceCache,
        debug_mode: normalized.debugMode,
        thread_id: threadId,
        system_prompt: normalized.systemPrompt || '',
        rag_k: normalized.ragK,
        prompt_key: normalized.promptKey,
        strict_mode: normalized.strictMode,
        active_tools: normalized.activeTools,
        max_tokens: normalized.maxTokens,
        temperature: normalized.temperature,
        top_p: normalized.topP,
        top_k: normalized.topK,
      },
      {
        signal: normalized.signal,
        timeout: 120000,
      }
    )
    .then((res: any) => normalizeChatRecord(res.data));
}

export function resumeChatAction(pendingActionId: string, approve = true) {
  return axios
    .post(
      '/api/chat/resume',
      {
        pending_action_id: pendingActionId,
        approve,
      },
      { timeout: 0 }
    )
    .then((res: any) => res.data);
}

export interface InterventionEvent {
  type: 'intervention';
  event_type: string;
  content: string;
  payload?: Record<string, any>;
  created_at: string;
}

export function streamInterventionEvents(
  onEvent: (event: InterventionEvent) => void
) {
  return new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const base =
      axios.defaults.baseURL || import.meta.env.VITE_API_BASE_URL || '';
    const url = base
      ? `${base.replace(/\/+$/, '')}/api/chat/events/stream`
      : '/api/chat/events/stream';
    xhr.open('GET', url, true);
    const token = getToken();
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    }
    xhr.setRequestHeader('Accept', 'text/event-stream');

    let lastProcessedLength = 0;
    xhr.onprogress = () => {
      const text = xhr.responseText || '';
      const newText = text.substring(lastProcessedLength);
      lastProcessedLength = text.length;
      const lines = newText.split('\n');
      lines.forEach((line) => {
        if (!line.startsWith('data: ')) return;
        try {
          const event = JSON.parse(line.substring(6)) as InterventionEvent;
          onEvent(event);
        } catch {
          // ignore incomplete chunks
        }
      });
    };
    xhr.onload = () => resolve();
    xhr.onerror = () => reject(new Error('Event stream failed'));
    xhr.send();
  });
}

export function fetchAssistantSettings() {
  return axios
    .get('/api/chat/settings', { timeout: READ_TIMEOUT_MS })
    .then((res: any) => res.data as AssistantSettings);
}

export interface LearningReportSection {
  title: string;
  content: string;
}

export interface ClassroomBehaviorSummary {
  recent_avg_lei: number;
  dominant_cognitive_state: string;
  mind_wandering_rate: number;
  bloom_distribution: Record<string, number>;
  teacher_note: string;
  behavioral_engagement?: number;
  cognitive_engagement?: number;
  emotional_engagement?: number;
  avg_cognitive_depth?: number;
  contagion_index?: number;
  on_task_rate?: number;
  attention_cycle_phase?: string;
  class_attention_trend?: string;
  student_count?: number;
}

export interface ProcessStep {
  key: string;
  label: string;
  message?: string;
  status?: 'idle' | 'running' | 'done' | 'error';
}

export interface LearningReport {
  learner_id: string;
  generated_at: string;
  summary: string;
  overall_summary?: string;
  current_goal: string;
  learning_style: string;
  risk_level: string;
  weak_points: string[];
  mastery_map?: Record<string, number>;
  mastery_insights?: string[];
  mastery_formula?: string;
  strengths: string[];
  recommended_actions: string[];
  recommended_resources: string[];
  follow_up_questions: string[];
  sections: LearningReportSection[];
  classroom_behavior_summary?: ClassroomBehaviorSummary;
  process_steps?: ProcessStep[];
}

export interface ReviewPlanDay {
  day_label: string;
  focus: string;
  tasks: string[];
}

export interface ReviewPlan {
  learner_id: string;
  generated_at: string;
  summary: string;
  overview?: string;
  focus_topics: string[];
  daily_plan: ReviewPlanDay[];
  checkpoints: string[];
}

export interface MistakeDigestItem {
  title: string;
  symptom: string;
  evidence: string;
  fix_strategy: string;
}

export interface MistakeDigest {
  learner_id: string;
  generated_at: string;
  summary: string;
  mistakes: MistakeDigestItem[];
  flashcards: string[];
}

export interface AiMetricsOverview {
  window_days: number;
  requests: number;
  avg_ttft_ms: number;
  avg_latency_ms: number;
  avg_agent_hops: number;
  cache_hit_rate: number;
  rag_grounded_rate: number;
  total_tokens: number;
  last_updated_at?: string;
}

export function fetchLearningReport(refresh = false) {
  return axios
    .get('/api/learning-report/me', {
      params: { refresh },
      timeout: 0,
    })
    .then((res: any) => normalizeLearningReport(res.data));
}

export function fetchAiMetricsOverview(days = 7) {
  return axios
    .get('/api/ai-metrics/overview', {
      params: { days },
      timeout: READ_TIMEOUT_MS,
    })
    .then((res: any) => res.data as AiMetricsOverview);
}

export function runLearningDiagnosis(refresh = true) {
  return axios
    .post('/api/learning-report/actions/diagnose', null, {
      params: { refresh },
      timeout: 0,
    })
    .then((res: any) => normalizeLearningReport(res.data));
}

export function generateReviewPlan(refresh = true) {
  return axios
    .post('/api/learning-report/actions/review-plan', null, {
      params: { refresh },
      timeout: 0,
    })
    .then((res: any) => normalizeReviewPlan(res.data));
}

export function generateMistakeDigest(refresh = true) {
  return axios
    .post('/api/learning-report/actions/mistake-digest', null, {
      params: { refresh },
      timeout: 0,
    })
    .then((res: any) => normalizeMistakeDigest(res.data));
}

export function fetchChatHistory(threadId = 'default') {
  return axios
    .get(`/chat/history/${threadId}`, { timeout: READ_TIMEOUT_MS })
    .then((res: any) =>
      Array.isArray(res.data) ? res.data.map(normalizeChatRecord) : []
    );
}

export function createChatThread(title = '', threadId = '') {
  return axios
    .post(
      '/api/chat/threads',
      { title, thread_id: threadId || undefined },
      { timeout: READ_TIMEOUT_MS }
    )
    .then((res: any) => res.data as ChatThread);
}

export function fetchChatThreads() {
  return axios
    .get('/api/chat/threads', { timeout: READ_TIMEOUT_MS })
    .then((res: any) => res.data as ChatThread[]);
}

export function updateChatThreadTitle(threadId: string, title: string) {
  return axios
    .put(`/api/chat/threads/${threadId}`, { title })
    .then((res: any) => res.data as ChatThread);
}

export function deleteChatThread(threadId: string) {
  return axios
    .delete(`/api/chat/threads/${threadId}`)
    .then((res: any) => res.data as ChatThread);
}

export function submitChatFeedback(data: {
  record_id: number;
  rating: 'up' | 'down';
  prompt_key: string;
}) {
  return axios.post('/api/chat/feedback', data).then((res: any) => res.data);
}

export function generateChatTitle(query: string, answer?: string) {
  return axios
    .post(
      '/api/chat/generate-title',
      { query, ...(answer ? { answer } : {}) },
      { timeout: READ_TIMEOUT_MS }
    )
    .then((res: any) => ({ title: String(res.data?.title || '').trim() }));
}

export function uploadThreadFile(file: File, threadId: string) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('thread_id', threadId);
  return axios
    .post('/file/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 0,
    })
    .then((res: any) => res.data);
}
