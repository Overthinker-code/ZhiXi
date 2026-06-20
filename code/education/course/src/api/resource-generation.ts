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

const recentPackageStorageKey = 'zhixi-resource-generated-packages-v1';

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

export function readLocalGeneratedPackages() {
  if (typeof window === 'undefined') return [] as RecentGeneratedPackage[];
  try {
    return normalizePackageList(
      JSON.parse(window.localStorage.getItem(recentPackageStorageKey) || '[]')
    );
  } catch {
    return [];
  }
}

export function rememberGeneratedPackage(
  pkg: ResourceGenerationResponse,
  courseId?: string
) {
  if (typeof window === 'undefined' || !pkg?.package_id) return;
  const nextPackage: RecentGeneratedPackage = {
    package_id: pkg.package_id,
    course_id: courseId || pkg.course_id,
    resource_id: pkg.resource_id,
    node_id: pkg.node_id,
    node_label: pkg.node_label,
    map_type: pkg.map_type,
    source: pkg.source,
    subject: pkg.subject,
    topic: pkg.topic,
    generated_at: pkg.generated_at,
    artifacts: pkg.artifacts.map((artifact) => ({
      kind: artifact.kind,
      title: artifact.title,
      file_name: artifact.file_name,
      file_size: artifact.file_size,
      download_url: artifact.download_url,
      content_type: artifact.content_type,
      preview: artifact.preview,
    })),
  };
  const merged = [
    nextPackage,
    ...readLocalGeneratedPackages().filter(
      (item) => item.package_id !== nextPackage.package_id
    ),
  ].slice(0, 12);
  try {
    window.localStorage.setItem(recentPackageStorageKey, JSON.stringify(merged));
  } catch {
    // Local persistence is a convenience cache; generation itself has succeeded.
  }
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
    .then((res: any) => {
      const remotePackages = normalizePackageList(res.data?.packages || []);
      const localPackages = readLocalGeneratedPackages();
      const seen = new Set<string>();
      return [...localPackages, ...remotePackages].filter((item) => {
        if (seen.has(item.package_id)) return false;
        seen.add(item.package_id);
        return true;
      });
    })
    .catch(() => readLocalGeneratedPackages());
}
