type TraceRecord = Record<string, any>;

function stopRunningItems(items: unknown) {
  if (!Array.isArray(items)) return [];
  return items.map((item) =>
    item?.status === 'running'
      ? { ...item, status: 'cancelled', finishedAt: Date.now() }
      : item
  );
}

export function markTraceStopping(source: TraceRecord | null | undefined) {
  const process = source || {};
  return {
    ...process,
    status: 'stopping',
    currentSummary: '正在停止本轮生成…',
  };
}

export function markTraceStopped(
  source: TraceRecord | null | undefined,
  finishedAt = Date.now()
) {
  const process = source || {};
  return {
    ...process,
    status: 'stopped',
    currentSummary: '已按你的要求停止生成',
    finishedAt,
    phases: stopRunningItems(process.phases),
    tools: stopRunningItems(process.tools),
  };
}

export function isAbortFailure(error: unknown) {
  if (!(error instanceof Error)) return false;
  return error.name === 'AbortError' || /abort|aborted|中止/i.test(error.message);
}
