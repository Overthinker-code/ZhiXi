export type TraceItemKind = 'phase' | 'tool';

type TraceRecord = Record<string, any>;

const TERMINAL_STATES = new Set([
  'done',
  'error',
  'failed',
  'cancelled',
  'skipped',
]);

function finiteSequence(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function traceKey(item: TraceRecord, kind: TraceItemKind) {
  if (kind === 'phase') return String(item.stepId || item.id || item.phaseId || 'phase');
  return String(item.callId || item.stepId || item.tool || item.id || 'tool');
}

function findTraceIndex(list: TraceRecord[], next: TraceRecord, kind: TraceItemKind) {
  const key = traceKey(next, kind);
  return list.findIndex((item) => {
    if (String(item.traceKey || '') === key) return true;
    if (kind === 'phase') {
      return Boolean(next.phaseId) && String(item.phaseId || item.id || '') === String(next.phaseId);
    }
    if (next.callId) return String(item.callId || '') === String(next.callId);
    if (next.stepId) return String(item.stepId || '') === String(next.stepId);
    return !item.callId && !item.stepId && String(item.tool || '') === String(next.tool || '');
  });
}

export function mergeTraceItem(
  source: TraceRecord[],
  incoming: TraceRecord,
  kind: TraceItemKind
) {
  const list = [...source];
  const key = traceKey(incoming, kind);
  const index = findTraceIndex(list, incoming, kind);
  const current = index >= 0 ? list[index] : {};
  const incomingSequence = finiteSequence(incoming.sequence);
  const currentSequence = finiteSequence(current.lastSequence ?? current.sequence);

  if (
    index >= 0 &&
    incomingSequence !== undefined &&
    currentSequence !== undefined &&
    incomingSequence < currentSequence
  ) {
    return list;
  }

  const terminal = TERMINAL_STATES.has(String(current.status || ''));
  const attemptsRollback = ['pending', 'running'].includes(String(incoming.status || ''));
  const definedIncoming = Object.fromEntries(
    Object.entries(incoming).filter(([, value]) => value !== undefined && value !== null)
  );
  const next: TraceRecord = {
    ...current,
    ...definedIncoming,
    traceKey: key,
    status: terminal && attemptsRollback ? current.status : incoming.status || current.status || 'running',
    text: incoming.text || current.text || '',
    summary: incoming.summary || current.summary,
    resultSummary: incoming.resultSummary || incoming.summary || current.resultSummary,
    items: Array.isArray(incoming.items) ? incoming.items : current.items || [],
    startedAt: current.startedAt || incoming.startedAt || incoming.timestamp || Date.now(),
    finishedAt: incoming.finishedAt || current.finishedAt,
    durationMs: incoming.durationMs ?? current.durationMs,
    sequence: current.sequence ?? incomingSequence,
    lastSequence: incomingSequence ?? currentSequence,
  };

  if (kind === 'phase') {
    next.id = String(incoming.stepId || current.id || incoming.id || incoming.phaseId || key);
    next.phaseId = incoming.phaseId || current.phaseId || incoming.id;
  } else {
    next.tool = incoming.tool || current.tool || key;
    next.callId = incoming.callId || current.callId;
    next.stepId = incoming.stepId || current.stepId;
  }

  if (index >= 0) list[index] = next;
  else list.push(next);
  return list;
}
