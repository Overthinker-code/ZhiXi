import axios from 'axios';

export type ResourceKind =
  | 'lecture_markdown'
  | 'lecture_pdf'
  | 'practice_markdown'
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
  'lecture_pdf',
  'practice_markdown',
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
    return name.endsWith('.pdf') ? 'practice_pdf' : 'practice_markdown';
  }
  if (name.includes('mind')) return 'mind_map';
  if (name.includes('reading')) return 'reading_list';
  if (name.includes('case')) return 'case_project';
  if (name.includes('video') || name.includes('script')) return 'video_script';
  if (name.includes('quality') || name.includes('check')) {
    return 'quality_checklist';
  }
  return name.endsWith('.pdf') ? 'lecture_pdf' : 'lecture_markdown';
}

function inferContentType(fileName: string) {
  if (fileName.toLowerCase().endsWith('.pdf')) return 'application/pdf';
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
  };
}

export function generateResourcePackage(payload: ResourceGenerationRequest) {
  return axios
    .post<ResourceGenerationResponse>('/api/resource-generation/packages', payload, {
      timeout: 0,
    })
    .then((res: any) => res.data);
}

export function fetchRecentGeneratedPackages(courseId?: string) {
  return axios
    .get('/api/resource-generation/packages/recent', {
      params: courseId ? { course_id: courseId } : undefined,
    })
    .then((res: any) => normalizePackageList(res.data?.packages || []));
}
