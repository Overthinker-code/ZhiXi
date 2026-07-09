import { streamAIChat, type AIChatStreamPayload, type AIStreamEvent } from '@/api/ai-chat';

const FLUSH_INTERVAL_MS = 50;

function appendDelta(queue: AIStreamEvent[], event: AIStreamEvent) {
  const previous = queue[queue.length - 1];
  if (previous && previous.event === event.event && event.event === 'answer_delta') {
    previous.data = {
      ...previous.data,
      ...event.data,
      text: `${previous.data.text || ''}${event.data.text || ''}`,
    };
    return;
  }
  queue.push(event);
}

export function streamTutorChat(
  payload: AIChatStreamPayload,
  onEvent: (event: AIStreamEvent) => void,
  signal?: AbortSignal
) {
  const queue: AIStreamEvent[] = [];
  let timer: ReturnType<typeof window.setTimeout> | null = null;
  let raf = 0;

  const drain = () => {
    if (timer) {
      window.clearTimeout(timer);
      timer = null;
    }
    if (raf) {
      window.cancelAnimationFrame(raf);
      raf = 0;
    }
    const next = queue.splice(0, queue.length);
    next.forEach(onEvent);
  };

  const flush = () => {
    if (timer) {
      window.clearTimeout(timer);
      timer = null;
    }
    if (raf) return;
    raf = window.requestAnimationFrame(() => {
      raf = 0;
      const next = queue.splice(0, queue.length);
      next.forEach(onEvent);
    });
  };

  const schedule = () => {
    if (timer) return;
    timer = window.setTimeout(flush, FLUSH_INTERVAL_MS);
  };

  return streamAIChat(
    payload,
    (event) => {
      appendDelta(queue, event);
      if (['run_started', 'phase_started', 'tool_started', 'error', 'run_finished', 'done'].includes(event.event)) {
        flush();
      } else {
        schedule();
      }
    },
    signal
  ).finally(drain);
}
