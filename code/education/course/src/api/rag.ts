import axios from 'axios';
import { getToken } from '@/utils/auth';

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
}

export function uploadReferenceFile(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('scope', 'personal');
  return axios
    .post('/rag/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((res: any) => res.data);
}

export function fetchReferenceFiles(scope: ReferenceScopeFilter = 'all') {
  return axios
    .get('/rag/files', {
      params: { scope },
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
      } = ''
) {
  const normalized =
    typeof options === 'string' ? { systemPrompt: options } : options || {};

  return axios
    .post(
      '/chat/',
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
      },
      {
        timeout: 0,
      }
    )
    .then((res: any) => res.data as ChatRecord);
}

export interface ChatStreamEvent {
  type: 'thought' | 'token' | 'final' | 'error';
  content?: string;
  agent?: string;
  intent?: string;
  routing_reason?: string;
  tool_calls?: any[];
  requires_confirmation?: boolean;
  pending_action_id?: string;
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
}

export function createAssistantChatStream(
  userInput: string,
  threadId: string,
  options: ChatAdvancedOptions,
  onEvent: (event: ChatStreamEvent) => void
) {
  const normalized = options || {};
  return new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const base = axios.defaults.baseURL || import.meta.env.VITE_API_BASE_URL || '';
    const url = base ? `${base.replace(/\/+$/, '')}/chat/stream` : '/chat/stream';

    xhr.open('POST', url, true);
    const token = getToken();
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    }
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.setRequestHeader('Accept', 'text/event-stream');

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
    };

    let lastProcessedLength = 0;
    xhr.onprogress = () => {
      const text = xhr.responseText || '';
      const newText = text.substring(lastProcessedLength);
      lastProcessedLength = text.length;
      const lines = newText.split('\n');
      lines.forEach((line) => {
        if (!line.startsWith('data: ')) return;
        try {
          const event = JSON.parse(line.substring(6)) as ChatStreamEvent;
          onEvent(event);
          if (event.type === 'error') {
            reject(new Error(event.content || 'Stream error'));
          }
        } catch {
          // ignore incomplete line
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

    xhr.onerror = () => reject(new Error('Network error'));
    xhr.send(JSON.stringify(payload));
  });
}

export function askSelectionQuery(
  selectedText: string,
  surroundingContext: string,
  threadId: string,
  options: ChatAdvancedOptions
) {
  const normalized = options || {};
  return axios
    .post('/chat/selection-query', {
      user_input: selectedText,
      selected_text: selectedText,
      surrounding_context: surroundingContext,
      video_time: normalized.videoTime,
      course_module: normalized.courseModule,
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
    })
    .then((res: any) => res.data as ChatRecord);
}

export function resumeChatAction(pendingActionId: string, approve = true) {
  return axios
    .post('/chat/resume', {
      pending_action_id: pendingActionId,
      approve,
    })
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
    const base = axios.defaults.baseURL || import.meta.env.VITE_API_BASE_URL || '';
    const url = base
      ? `${base.replace(/\/+$/, '')}/chat/events/stream`
      : '/chat/events/stream';
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
    .get('/chat/settings')
    .then((res: any) => res.data as AssistantSettings);
}

export function fetchChatHistory(threadId = 'default') {
  return axios
    .get(`/chat/history/${threadId}`)
    .then((res: any) => res.data as ChatRecord[]);
}

export function createChatThread(title = '', threadId = '') {
  return axios
    .post('/chat/threads', { title, thread_id: threadId || undefined })
    .then((res: any) => res.data as ChatThread);
}

export function fetchChatThreads() {
  return axios
    .get('/chat/threads')
    .then((res: any) => res.data as ChatThread[]);
}

export function updateChatThreadTitle(threadId: string, title: string) {
  return axios
    .put(`/chat/threads/${threadId}`, { title })
    .then((res: any) => res.data as ChatThread);
}

export function deleteChatThread(threadId: string) {
  return axios
    .delete(`/chat/threads/${threadId}`)
    .then((res: any) => res.data as ChatThread);
}

export function submitChatFeedback(data: {
  record_id: number;
  rating: 'up' | 'down';
  prompt_key: string;
}) {
  return axios.post('/chat/feedback', data).then((res: any) => res.data);
}
