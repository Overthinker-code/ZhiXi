import axios from 'axios';
import { getToken } from '@/utils/auth';
import { parseSSEBlock } from '@/components/chat/sseParser';

const AI_STREAM_TIMEOUT_MS = 600000;

export type TutorMode =
  | 'tutor'
  | 'homework_review'
  | 'resource_generation'
  | 'deep_research';

export type ReasoningLevel = 'fast' | 'balanced' | 'deep';

export type AttachmentKind = 'image' | 'pdf' | 'doc' | 'ppt' | 'code' | 'other';

export interface CourseContextPayload {
  courseId?: string;
  chapterId?: string;
  knowledgePointIds: string[];
  useCourseRag: boolean;
}

export interface ChatToolPayload {
  webSearch: boolean;
  courseRag?: boolean;
  deepResearch: boolean;
  homeworkReview: boolean;
  resourceGeneration: boolean;
  citationRequired: boolean;
}

export interface ChatReasoningPayload {
  level: ReasoningLevel;
  showSummary: boolean;
  showProcess?: boolean;
}

export interface ChatAttachmentPayload {
  fileId: string;
  type: AttachmentKind;
  name?: string;
}

export interface ResourceRequestPayload {
  types: string[];
  difficulty: 'basic' | 'normal' | 'advanced';
  target: string;
}

export interface AIChatStreamPayload {
  sessionId?: string;
  message: string;
  mode: TutorMode;
  actionId?: string;
  courseContext: CourseContextPayload;
  tools: ChatToolPayload;
  reasoning: ChatReasoningPayload;
  attachments: ChatAttachmentPayload[];
  resourceRequest: ResourceRequestPayload;
}

export interface AIAttachmentUploadResponse {
  fileId: string;
  name: string;
  type: AttachmentKind;
  chunks?: number;
  preview?: string;
}

export interface AIStreamEvent {
  event: string;
  data: Record<string, any>;
}

export interface AIContextCourse {
  courseId: string;
  title: string;
  chapters: Array<{
    chapterId: string;
    title: string;
    knowledgePointIds: string[];
  }>;
}

function apiBase() {
  return (axios.defaults.baseURL || import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');
}

function streamUrl() {
  const base = apiBase();
  return base ? `${base}/api/ai/chat/stream` : '/api/ai/chat/stream';
}

export async function streamAIChat(
  payload: AIChatStreamPayload,
  onEvent: (event: AIStreamEvent) => void,
  signal?: AbortSignal
) {
  const token = getToken();
  const controller = new AbortController();
  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener('abort', () => controller.abort(), { once: true });
  }
  const timeout = window.setTimeout(() => controller.abort(), AI_STREAM_TIMEOUT_MS);
  try {
    const response = await fetch(streamUrl(), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    if (!response.ok) {
      const text = await response.text().catch(() => '');
      throw new Error(text || `HTTP ${response.status}`);
    }
    if (!response.body) throw new Error('流式响应不可用');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    /* eslint-disable no-await-in-loop */
    for (;;) {
      const { value, done } = await reader.read();
      if (value?.length) {
        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split(/\n\n/);
        buffer = blocks.pop() || '';
        blocks.forEach((block) => {
          const parsed = parseSSEBlock(block);
          if (parsed) onEvent(parsed);
        });
      }
      if (done) break;
    }
    /* eslint-enable no-await-in-loop */
    const tail = buffer.trim();
    if (tail) {
      const parsed = parseSSEBlock(tail);
      if (parsed) onEvent(parsed);
    }
  } finally {
    window.clearTimeout(timeout);
  }
}

export function uploadAIAttachment(file: File, sessionId: string) {
  const body = new FormData();
  body.append('file', file);
  body.append('session_id', sessionId);
  return axios
    .post('/api/ai/attachments', body, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 0,
    })
    .then((res: any) => res.data as AIAttachmentUploadResponse);
}

export function fetchAIContextCourses() {
  return axios
    .get('/api/ai/context/courses')
    .then((res: any) => res.data as AIContextCourse[]);
}
