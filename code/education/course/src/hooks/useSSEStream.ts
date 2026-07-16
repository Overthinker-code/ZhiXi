import { ref, type Ref } from 'vue';
import axios from 'axios';
import { getToken } from '@/utils/auth';

export interface SSEStreamOptions {
  /** Headers to merge into the request. Authorization is added automatically. */
  headers?: Record<string, string>;
}

/**
 * Composable for consuming Server-Sent Events (SSE) from a POST endpoint.
 *
 * Uses XHR (not EventSource) so we can send a POST body and custom headers.
 * Parses lines prefixed with "data: " as JSON events.
 *
 * Usage:
 * ```ts
 * const { events, isDone, error, start, abort } = useSSEStream<MyEvent>(
 *   '/rag/upload/preview', formData, { headers: { 'Accept': 'text/event-stream' } }
 * )
 * start()
 * watch(events, (list) => console.log('Latest event:', list[list.length - 1]))
 * ```
 */
export function useSSEStream<T = unknown>(
  url: string,
  body: FormData | object,
  options?: SSEStreamOptions
) {
  const events: Ref<T[]> = ref([]);
  const isDone = ref(false);
  const error: Ref<Error | null> = ref(null);

  let xhr: XMLHttpRequest | null = null;

  function start() {
    isDone.value = false;
    error.value = null;
    events.value = [];

    xhr = new XMLHttpRequest();

    // Resolve full URL using axios baseURL
    const base =
      axios.defaults.baseURL || import.meta.env.VITE_API_BASE_URL || '';
    const fullUrl = base ? `${base.replace(/\/+$/, '')}${url}` : url;

    xhr.open('POST', fullUrl, true);

    // Auth
    const token = getToken();
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    }

    // Merge custom headers
    if (options?.headers) {
      Object.entries(options.headers).forEach(([key, value]) => {
        xhr!.setRequestHeader(key, value);
      });
    }

    xhr.setRequestHeader('Accept', 'text/event-stream');

    let lastProcessedLength = 0;

    xhr.onprogress = () => {
      const text = xhr!.responseText;
      const newText = text.substring(lastProcessedLength);
      lastProcessedLength = text.length;

      const lines = newText.split('\n');
      lines.forEach((line) => {
        if (line.startsWith('data: ')) {
          try {
            const json = JSON.parse(line.substring(6)) as T;
            events.value.push(json);

            // Check for error stage (RAG upload convention)
            if ((json as any).stage === 'error') {
              error.value = new Error(
                (json as any).message || 'Stream error'
              );
            }
          } catch {
            // Ignore incomplete JSON lines
          }
        }
      });
    };

    xhr.onload = () => {
      isDone.value = true;
      if (xhr!.status !== 200) {
        error.value = new Error(`HTTP ${xhr!.status}: ${xhr!.statusText}`);
      }
    };

    xhr.onerror = () => {
      isDone.value = true;
      error.value = new Error('Network error');
    };

    // Send body
    if (body instanceof FormData) {
      xhr.send(body);
    } else {
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.send(JSON.stringify(body));
    }
  }

  function abort() {
    if (xhr) {
      xhr.abort();
      isDone.value = true;
    }
  }

  return { events, isDone, error, start, abort };
}
