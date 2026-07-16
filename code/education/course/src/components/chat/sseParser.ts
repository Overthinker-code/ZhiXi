export interface ParsedSSEEvent {
  event: string;
  data: Record<string, any>;
}

export function parseSSEBlock(block: string): ParsedSSEEvent | null {
  const lines = block.split(/\r?\n/);
  let event = 'message';
  const dataLines: string[] = [];

  lines.forEach((line) => {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trimStart());
    }
  });

  if (!dataLines.length) return null;

  try {
    return {
      event,
      data: JSON.parse(dataLines.join('\n')) as Record<string, any>,
    };
  } catch {
    return {
      event: 'error',
      data: {
        code: 'INVALID_SSE_PAYLOAD',
        message: '流式响应格式异常，请重试',
        sourceEvent: event,
      },
    };
  }
}
