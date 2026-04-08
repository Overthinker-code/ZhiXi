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

export interface ToolCallEvent {
  tool: string;
  step: string;
  progress: number;
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
        stream?: boolean;
        activeTools?: string[];
        onToolCall?: (event: ToolCallEvent) => void;
      } = ''
) {
  const normalized =
    typeof options === 'string' ? { systemPrompt: options } : options || {};

  // onToolCall is a frontend-only callback — strip before serializing
  const { onToolCall: _onToolCall, ...restOptions } = normalized as any;

  return axios
    .post(
      '/chat/',
      {
        thread_id: threadId,
        user_input: userInput,
        system_prompt: restOptions.systemPrompt || '',
        rag_k: restOptions.ragK,
        prompt_key: restOptions.promptKey,
        strict_mode: restOptions.strictMode,
        stream: restOptions.stream !== false,
        active_tools: restOptions.activeTools || [],
      },
      {
        timeout: 0,
      }
    )
    .then((res: any) => res.data as ChatRecord);
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
