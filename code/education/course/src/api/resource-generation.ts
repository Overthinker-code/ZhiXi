import axios from 'axios';
import { getToken } from '@/utils/auth';
import { resolveTrustedResourceRunStreamUrl } from './resource-run-url';

export { resolveTrustedResourceRunStreamUrl } from './resource-run-url';

export type ResourceKind =
  | 'lecture_markdown'
  | 'lecture_docx'
  | 'lecture_pdf'
  | 'practice_markdown'
  | 'practice_docx'
  | 'practice_pdf'
  | 'mind_map'
  | 'reading_list'
  | 'case_project'
  | 'video_script'
  | 'quality_checklist';

export type ResourcePersistenceStatus =
  | 'file_only'
  | 'package_persisted'
  | 'resources_persisted';

export type ResourceRunStatus =
  | 'requested'
  | 'created'
  | 'running'
  | 'partial_success'
  | 'completed'
  | 'cancelled'
  | 'failed';

export type ResourceRunStageKey =
  | 'generation'
  | 'review'
  | 'persistence'
  | 'graph_link'
  | 'path_update'
  | 'profile_update';

export type ResourceRunStageStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'unsupported';

export interface ResourceRunStage {
  key: ResourceRunStageKey;
  status: ResourceRunStageStatus;
  message?: string;
  retryable?: boolean;
  error_code?: string;
}

export interface ResourceRunEvidence {
  run_id?: string;
  status: ResourceRunStatus;
  cancel_requested?: boolean;
  transport: 'resource_run_sse' | 'resource_run_polling' | 'legacy_sync';
  stages: ResourceRunStage[];
  requested?: Partial<ResourceGenerationRequest>;
}

export interface ResourceGenerationRequest {
  course_id?: string;
  resource_id?: string;
  node_id?: string;
  node_label?: string;
  map_type?: string;
  source?: string;
  subject: string;
  topic: string;
  learning_goal?: string;
  difficulty: 'foundation' | 'standard' | 'challenge';
  target_minutes: number;
  resource_types: ResourceKind[];
  use_web_search?: boolean;
}

export interface GeneratedResourceArtifact {
  kind: ResourceKind;
  title: string;
  file_name: string;
  download_url: string;
  content_type: string;
  file_size: number;
  preview: string;
}

export interface ResourceGenerationResponse {
  package_id: string;
  course_id?: string;
  resource_id?: string;
  node_id?: string;
  node_label?: string;
  map_type?: string;
  source?: string;
  subject: string;
  topic: string;
  generated_at: string;
  local_model_profile: Record<string, any>;
  agent_trace: string[];
  quality_notes: string[];
  persistence_status: ResourcePersistenceStatus;
  persisted_resource_ids: string[];
  artifacts: GeneratedResourceArtifact[];
  run?: ResourceRunEvidence;
}

interface ResourceRunStartResponse {
  run_id: string;
  status?: ResourceRunStatus;
  stream_url?: string;
  result_url?: string;
  package_id?: string;
  shared_state?: { stage_status?: Record<string, string> };
  cancel_requested?: boolean;
  steps?: ResourceRunStepResponse[];
  error_code?: string;
  error_message?: string;
  requested?: Partial<ResourceGenerationRequest>;
  result?: unknown;
}

export interface ResourceRunStepResponse {
  step_key: string;
  status: string;
  input_summary?: string;
  output_summary?: string;
  error_message?: string;
}

export interface ResourceRunCallbacks {
  onEvidence?: (evidence: ResourceRunEvidence) => void;
  onArtifact?: (artifact: GeneratedResourceArtifact) => void;
  signal?: AbortSignal;
  idempotencyKey?: string;
}

export interface RecentGeneratedPackage {
  package_id: string;
  course_id?: string;
  resource_id?: string;
  node_id?: string;
  node_label?: string;
  map_type?: string;
  source?: string;
  subject: string;
  topic: string;
  generated_at: string;
  status?: string;
  run_id?: string;
  run_status?: ResourceRunStatus;
  stage_status?: Record<string, string>;
  cancel_requested?: boolean;
  steps?: ResourceRunStepResponse[];
  persistence_status: ResourcePersistenceStatus;
  persisted_resource_ids: string[];
  local_model_profile: Record<string, any>;
  agent_trace: string[];
  quality_notes: string[];
  artifacts: Array<{
    kind?: ResourceKind;
    title?: string;
    file_name: string;
    file_size: number;
    download_url?: string;
    content_type?: string;
    preview?: string;
  }>;
}

const resourceKinds = new Set<ResourceKind>([
  'lecture_markdown',
  'lecture_docx',
  'lecture_pdf',
  'practice_markdown',
  'practice_docx',
  'practice_pdf',
  'mind_map',
  'reading_list',
  'case_project',
  'video_script',
  'quality_checklist',
]);

function inferResourceKind(fileName: string): ResourceKind {
  const name = fileName.toLowerCase();
  if (name.includes('practice')) {
    if (name.endsWith('.pdf')) return 'practice_pdf';
    if (name.endsWith('.docx')) return 'practice_docx';
    return 'practice_markdown';
  }
  if (name.includes('mind')) return 'mind_map';
  if (name.includes('reading')) return 'reading_list';
  if (name.includes('case')) return 'case_project';
  if (name.includes('video') || name.includes('script')) return 'video_script';
  if (name.includes('quality') || name.includes('check')) {
    return 'quality_checklist';
  }
  if (name.endsWith('.pdf')) return 'lecture_pdf';
  if (name.endsWith('.docx')) return 'lecture_docx';
  return 'lecture_markdown';
}

function inferContentType(fileName: string) {
  if (fileName.toLowerCase().endsWith('.pdf')) return 'application/pdf';
  if (fileName.toLowerCase().endsWith('.docx')) {
    return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
  }
  if (fileName.toLowerCase().endsWith('.md')) return 'text/markdown';
  return 'text/plain';
}

function normalizePackageList(value: unknown): RecentGeneratedPackage[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item: any) => ({
      package_id: String(item?.package_id || '').trim(),
      course_id: item?.course_id ? String(item.course_id) : undefined,
      resource_id: item?.resource_id ? String(item.resource_id) : undefined,
      node_id: item?.node_id ? String(item.node_id) : undefined,
      node_label: item?.node_label ? String(item.node_label) : undefined,
      map_type: item?.map_type ? String(item.map_type) : undefined,
      source: item?.source ? String(item.source) : undefined,
      subject: String(item?.subject || '').trim(),
      topic: String(item?.topic || '').trim(),
      generated_at: String(item?.generated_at || '').trim(),
      status: item?.status ? String(item.status) : undefined,
      run_id: item?.run_id ? String(item.run_id) : undefined,
      run_status: item?.run_status as ResourceRunStatus | undefined,
      stage_status:
        item?.stage_status && typeof item.stage_status === 'object'
          ? item.stage_status
          : {},
      cancel_requested: Boolean(item?.cancel_requested),
      steps: Array.isArray(item?.steps) ? item.steps : [],
      persistence_status: ['package_persisted', 'resources_persisted'].includes(
        item?.persistence_status
      )
        ? item.persistence_status
        : 'file_only',
      persisted_resource_ids: Array.isArray(item?.persisted_resource_ids)
        ? item.persisted_resource_ids.map(String)
        : [],
      local_model_profile:
        item?.local_model_profile && typeof item.local_model_profile === 'object'
          ? item.local_model_profile
          : {},
      agent_trace: Array.isArray(item?.agent_trace)
        ? item.agent_trace.map(String)
        : [],
      quality_notes: Array.isArray(item?.quality_notes)
        ? item.quality_notes.map(String)
        : [],
      artifacts: Array.isArray(item?.artifacts)
        ? item.artifacts
            .map((artifact: any) => ({
              kind: artifact?.kind,
              title: artifact?.title ? String(artifact.title) : undefined,
              file_name: String(artifact?.file_name || '').trim(),
              file_size: Number(artifact?.file_size) || 0,
              download_url: artifact?.download_url
                ? String(artifact.download_url)
                : undefined,
              content_type: artifact?.content_type
                ? String(artifact.content_type)
                : undefined,
              preview: artifact?.preview ? String(artifact.preview) : undefined,
            }))
            .filter((artifact: any) => artifact.file_name)
        : [],
    }))
    .filter((item) => item.package_id && item.topic);
}

const RUN_STAGE_KEYS = new Set<ResourceRunStageKey>([
  'generation',
  'review',
  'persistence',
  'graph_link',
  'path_update',
  'profile_update',
]);

function normalizeRunEvidence(value: any): ResourceRunEvidence | undefined {
  if (!value || typeof value !== 'object') return undefined;
  const rawStages = Array.isArray(value.stages) ? value.stages : [];
  const stages = rawStages
    .map((stage: any) => ({
      key: String(stage?.key || stage?.stage || '') as ResourceRunStageKey,
      status: String(stage?.status || 'pending') as ResourceRunStageStatus,
      message: stage?.message ? String(stage.message) : undefined,
      retryable: Boolean(stage?.retryable),
      error_code: stage?.error_code ? String(stage.error_code) : undefined,
    }))
    .filter((stage: ResourceRunStage) => RUN_STAGE_KEYS.has(stage.key));
  if (!stages.length) return undefined;
  const status = ['requested', 'created', 'running', 'partial_success', 'completed', 'cancelled', 'failed'].includes(
    value.status
  )
    ? value.status
    : 'running';
  return {
    run_id: value.run_id ? String(value.run_id) : undefined,
    status,
    cancel_requested: Boolean(value.cancel_requested),
    transport: 'resource_run_sse',
    stages,
    requested:
      value.requested && typeof value.requested === 'object'
        ? value.requested
        : undefined,
  };
}

const BACKEND_STAGE_MAP: Record<string, ResourceRunStageKey | undefined> = {
  generating: 'generation',
  reviewing: 'review',
  persisting: 'persistence',
  linking_graph: 'graph_link',
  updating_path: 'path_update',
  updating_profile: 'profile_update',
};

function normalizeTopLevelRunEvidence(value: any): ResourceRunEvidence | undefined {
  if (!value?.run_id || !value?.stage_status || typeof value.stage_status !== 'object') {
    return undefined;
  }
  const status = ['requested', 'running', 'partial_success', 'completed', 'cancelled', 'failed'].includes(
    value.run_status
  )
    ? value.run_status
    : 'running';
  const stages = Object.entries(BACKEND_STAGE_MAP).map(([backendKey, key]) => {
    const rawStatus = String(value.stage_status[backendKey] || 'pending');
    const stageStatus: ResourceRunStageStatus =
      rawStatus === 'completed'
        ? 'completed'
        : rawStatus === 'failed'
        ? 'failed'
        : rawStatus === 'running'
        ? 'running'
        : rawStatus === 'skipped'
        ? 'unsupported'
        : 'pending';
    const step = Array.isArray(value.steps)
      ? (value.steps as ResourceRunStepResponse[]).find(
          (item) => item.step_key === backendKey
        )
      : undefined;
    const stepSummary = String(
      stageStatus === 'running'
        ? step?.input_summary || ''
        : stageStatus === 'completed' || stageStatus === 'unsupported'
        ? step?.output_summary || ''
        : ''
    )
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 160);
    return {
      key: key as ResourceRunStageKey,
      status: stageStatus,
      retryable: stageStatus === 'failed',
      message:
        stepSummary || (stageStatus === 'completed'
          ? '本阶段已完成'
          : stageStatus === 'failed'
          ? '本阶段失败，可以重试'
          : stageStatus === 'unsupported'
          ? '本次不需要执行该阶段'
          : '等待处理'),
    };
  });
  return {
    run_id: String(value.run_id),
    status,
    cancel_requested: Boolean(value.cancel_requested),
    transport: 'resource_run_polling',
    stages,
    requested:
      value.requested && typeof value.requested === 'object'
        ? value.requested
        : undefined,
  };
}

function normalizePolledRunEvidence(value: ResourceRunStartResponse) {
  return normalizeTopLevelRunEvidence({
    run_id: value.run_id,
    run_status: value.status,
    stage_status: value.shared_state?.stage_status || {},
    cancel_requested: value.cancel_requested,
    steps: value.steps || [],
    requested: value.requested,
  });
}

function legacyRunEvidence(pkg: ResourceGenerationResponse): ResourceRunEvidence {
  const generated = pkg.artifacts.length > 0;
  const reviewed =
    pkg.quality_notes.length > 0 ||
    pkg.artifacts.some((item) => item.kind === 'quality_checklist');
  const persisted = pkg.persistence_status !== 'file_only';
  const courseResourcesPersisted = pkg.persistence_status === 'resources_persisted';
  return {
    status: generated && persisted ? 'partial_success' : generated ? 'partial_success' : 'failed',
    transport: 'legacy_sync',
    stages: [
      {
        key: 'generation',
        status: generated ? 'completed' : 'failed',
        message: generated ? `${pkg.artifacts.length} 个文件已生成` : '没有生成可用文件',
      },
      {
        key: 'review',
        status: reviewed ? 'completed' : 'unsupported',
        message: reviewed ? '质量说明与检查清单已生成' : '本次没有独立质量说明',
      },
      {
        key: 'persistence',
        status: persisted ? 'completed' : 'failed',
        message: courseResourcesPersisted
          ? `${pkg.persisted_resource_ids.length} 条课程资源记录已入库`
          : persisted
          ? '资源包已保存为个人记录'
          : '资源尚未保存',
      },
      {
        key: 'graph_link',
        status: 'unsupported',
        message: '本次资源尚未关联课程图谱',
      },
      {
        key: 'path_update',
        status: 'unsupported',
        message: '学习路径未更新',
      },
      {
        key: 'profile_update',
        status: 'unsupported',
        message: '学习画像未更新',
      },
    ],
  };
}

function normalizeGenerationResponse(value: any): ResourceGenerationResponse {
  const response = value as ResourceGenerationResponse;
  response.artifacts = Array.isArray(response.artifacts) ? response.artifacts : [];
  response.agent_trace = Array.isArray(response.agent_trace) ? response.agent_trace : [];
  response.quality_notes = Array.isArray(response.quality_notes) ? response.quality_notes : [];
  response.persisted_resource_ids = Array.isArray(response.persisted_resource_ids)
    ? response.persisted_resource_ids.map(String)
    : [];
  response.run =
    normalizeRunEvidence(value?.run) ||
    normalizeTopLevelRunEvidence(value) ||
    legacyRunEvidence(response);
  return response;
}

async function consumeRunStream(
  start: ResourceRunStartResponse,
  callbacks: ResourceRunCallbacks
): Promise<ResourceGenerationResponse> {
  if (start.result) return normalizeGenerationResponse(start.result);
  const streamUrl = start.stream_url || `/api/resource-generation/runs/${start.run_id}/events`;
  const resolvedUrl = resolveTrustedResourceRunStreamUrl(
    streamUrl,
    window.location.origin,
    axios.defaults.baseURL
  );
  const token = getToken();
  const response = await fetch(resolvedUrl, {
    headers: {
      Accept: 'text/event-stream',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    credentials: 'same-origin',
    signal: callbacks.signal,
  });
  if (!response.ok || !response.body) throw new Error(`ResourceRun stream failed: ${response.status}`);
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let finalResult: ResourceGenerationResponse | null = null;
  const processFrame = (frame: string) => {
    const event = frame.match(/^event:\s*(.+)$/m)?.[1]?.trim() || 'message';
    const dataText = frame
      .split(/\r?\n/)
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trim())
      .join('\n');
    if (!dataText) return;
    let data: any;
    try {
      data = JSON.parse(dataText);
    } catch {
      // A malformed frame is isolated; later valid progress and completion events remain usable.
      return;
    }
    const evidence = normalizeRunEvidence(data.run || data);
    if (evidence) callbacks.onEvidence?.(evidence);
    if (event === 'artifact_finished' && data.artifact) callbacks.onArtifact?.(data.artifact);
    if (event === 'completed' || event === 'partial_success' || data.result) {
      finalResult = normalizeGenerationResponse(data.result || data);
    }
  };
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const frames = buffer.split(/\r?\n\r?\n/);
    buffer = frames.pop() || '';
    frames.forEach(processFrame);
    if (done) {
      if (buffer.trim()) processFrame(buffer);
      break;
    }
  }
  if (!finalResult) throw new Error('ResourceRun stream ended without a final result');
  return finalResult;
}

const RESOURCE_RUN_POLL_MS = 2000;
const RESOURCE_RUN_TIMEOUT_MS = 20 * 60 * 1000;

function waitForNextPoll(signal: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException('Resource generation polling aborted', 'AbortError'));
      return;
    }
    const onAbort = () => {
      window.clearTimeout(timeoutId);
      reject(new DOMException('Resource generation polling aborted', 'AbortError'));
    };
    const timeoutId = window.setTimeout(() => {
      signal.removeEventListener('abort', onAbort);
      resolve();
    }, RESOURCE_RUN_POLL_MS);
    signal.addEventListener('abort', onAbort, { once: true });
  });
}

async function consumeRunPolling(
  start: ResourceRunStartResponse,
  callbacks: ResourceRunCallbacks
): Promise<ResourceGenerationResponse> {
  const controller = new AbortController();
  const abortOnPageHide = () => controller.abort();
  const abortFromCaller = () => controller.abort();
  window.addEventListener('pagehide', abortOnPageHide, { once: true });
  if (callbacks.signal?.aborted) controller.abort();
  else callbacks.signal?.addEventListener('abort', abortFromCaller, { once: true });
  const startedAt = Date.now();
  let run = start;
  try {
    while (true) {
      const evidence = normalizePolledRunEvidence(run);
      if (evidence) callbacks.onEvidence?.(evidence);
      if (run.status === 'completed' || run.status === 'partial_success') {
        if (run.result) return normalizeGenerationResponse(run.result);
        const resultUrl = run.result_url ||
          (run.package_id ? `/api/resource-generation/packages/${run.package_id}` : '');
        if (!resultUrl) throw new Error('Resource generation completed without a result URL');
        const trustedResultUrl = resolveTrustedResourceRunStreamUrl(
          resultUrl,
          window.location.origin,
          axios.defaults.baseURL
        );
        const response = await axios.get(trustedResultUrl, {
          signal: controller.signal,
        });
        return normalizeGenerationResponse(response.data);
      }
      if (run.status === 'failed' || run.status === 'cancelled') {
        throw new Error(run.error_message || `Resource generation ${run.status}`);
      }
      if (Date.now() - startedAt >= RESOURCE_RUN_TIMEOUT_MS) {
        throw new Error('Resource generation polling timed out');
      }
      await waitForNextPoll(controller.signal);
      const response = await axios.get<ResourceRunStartResponse>(
        `/api/resource-generation/runs/${start.run_id}`,
        { signal: controller.signal }
      );
      run = response.data;
    }
  } finally {
    controller.abort();
    window.removeEventListener('pagehide', abortOnPageHide);
    callbacks.signal?.removeEventListener('abort', abortFromCaller);
  }
}

export async function cancelResourceRun(runId: string) {
  const response = await axios.post<ResourceRunStartResponse>(
    `/api/resource-generation/runs/${runId}/cancel`
  );
  return normalizePolledRunEvidence(response.data);
}

export async function resumeResourceRun(
  runId: string,
  callbacks: ResourceRunCallbacks = {}
) {
  const response = await axios.post<ResourceRunStartResponse>(
    `/api/resource-generation/runs/${runId}/resume`,
    undefined,
    { signal: callbacks.signal }
  );
  if (response.data.result) return normalizeGenerationResponse(response.data.result);
  if (response.data.stream_url) return consumeRunStream(response.data, callbacks);
  return consumeRunPolling(response.data, callbacks);
}

export function restoreGeneratedPackage(
  pkg: RecentGeneratedPackage
): ResourceGenerationResponse | null {
  if (!pkg?.package_id || !pkg.topic) return null;
  const artifacts = pkg.artifacts
    .filter((artifact) => artifact.file_name)
    .map((artifact) => {
      const kind = resourceKinds.has(artifact.kind as ResourceKind)
        ? (artifact.kind as ResourceKind)
        : inferResourceKind(artifact.file_name);
      return {
        kind,
        title: artifact.title || artifact.file_name,
        file_name: artifact.file_name,
        download_url:
          artifact.download_url ||
          `/api/v1/resource-generation/artifacts/${pkg.package_id}/${artifact.file_name}`,
        content_type:
          artifact.content_type || inferContentType(artifact.file_name),
        file_size: artifact.file_size,
        preview: artifact.preview || '',
      };
    });

  return {
    package_id: pkg.package_id,
    course_id: pkg.course_id,
    resource_id: pkg.resource_id,
    node_id: pkg.node_id,
    node_label: pkg.node_label,
    map_type: pkg.map_type,
    source: pkg.source,
    subject: pkg.subject,
    topic: pkg.topic,
    generated_at: pkg.generated_at,
    local_model_profile: pkg.local_model_profile,
    agent_trace: pkg.agent_trace,
    quality_notes: pkg.quality_notes,
    persistence_status: pkg.persistence_status,
    persisted_resource_ids: pkg.persisted_resource_ids,
    artifacts,
    run:
      normalizeTopLevelRunEvidence({
        run_id: pkg.run_id,
        run_status: pkg.run_status,
        stage_status: pkg.stage_status,
        cancel_requested: pkg.cancel_requested,
        steps: pkg.steps,
      }) ||
      legacyRunEvidence({
        ...pkg,
        artifacts,
      } as ResourceGenerationResponse),
  };
}

export function generateResourcePackage(payload: ResourceGenerationRequest) {
  return axios
    .post<ResourceGenerationResponse>('/api/resource-generation/packages', payload, {
      timeout: 0,
    })
    .then((res: any) => normalizeGenerationResponse(res.data));
}

export async function generateResourcePackageCompatible(
  payload: ResourceGenerationRequest,
  callbacks: ResourceRunCallbacks = {}
) {
  if (import.meta.env.VITE_RESOURCE_RUN_API_ENABLED === 'false') {
    const result = await generateResourcePackage(payload);
    callbacks.onEvidence?.(result.run as ResourceRunEvidence);
    return result;
  }
  const idempotencyKey =
    callbacks.idempotencyKey ||
    (typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `resource-${Date.now()}-${Math.random().toString(16).slice(2)}`);
  const response = await axios.post<ResourceRunStartResponse>(
    '/api/resource-generation/runs',
    payload,
    {
      timeout: 0,
      signal: callbacks.signal,
      headers: { 'Idempotency-Key': idempotencyKey },
    }
  );
  if (response.data.result || response.data.stream_url) {
    return consumeRunStream(response.data, callbacks);
  }
  return consumeRunPolling(response.data, callbacks);
}

export function fetchRecentGeneratedPackages(courseId?: string) {
  return axios
    .get('/api/resource-generation/packages/recent', {
      params: courseId ? { course_id: courseId } : undefined,
    })
    .then((res: any) => normalizePackageList(res.data?.packages || []));
}
