import axios from 'axios';

const READ_TIMEOUT_MS = 8000;

export interface ResourceRecord {
  id: string;
  title: string;
  type: string;
  subject: string;
  file_name: string;
  file_path: string;
  file_size: number;
  content_type: string;
  course_id?: string | null;
  package_id?: string | null;
  content?: Record<string, any> | null;
  url?: string | null;
  knowledge_point?: string | null;
  difficulty?: string | null;
  source?: string | null;
  favorite: boolean;
  top: boolean;
  upload_time: string;
  uploader_id: string;
}

export interface ResourcesResponse {
  data: ResourceRecord[];
  count: number;
}

export function queryResources(params?: {
  course_id?: string;
  title?: string;
  type?: string;
  skip?: number;
  limit?: number;
  owned_only?: boolean;
}) {
  return axios.get<ResourcesResponse>('/api/education/resources/', {
    params,
    timeout: READ_TIMEOUT_MS,
  });
}

export function getResource(resourceId: string) {
  return axios.get<ResourceRecord>(`/api/education/resources/${resourceId}`, {
    timeout: READ_TIMEOUT_MS,
  });
}

export function createResource(formData: FormData) {
  return axios.post<ResourceRecord>('/api/education/resources', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: READ_TIMEOUT_MS,
  });
}

export function updateResource(resourceId: string, data: { title?: string; type?: string }) {
  return axios.put<ResourceRecord>(
    `/api/education/resources/${resourceId}`,
    data,
    {
      timeout: READ_TIMEOUT_MS,
    }
  );
}

export function deleteResource(resourceId: string) {
  return axios.delete(`/api/education/resources/${resourceId}`, {
    timeout: READ_TIMEOUT_MS,
  });
}

export function downloadResource(resourceId: string) {
  return axios.get(`/api/education/resources/${resourceId}/download`, {
    responseType: 'blob',
    timeout: READ_TIMEOUT_MS,
  });
}

export function setResourceFavorite(resourceId: string, favorite: boolean) {
  return axios.put<{ resource_id: string; favorite: boolean }>(
    `/api/education/resources/${resourceId}/favorite`,
    { favorite },
    { timeout: READ_TIMEOUT_MS }
  );
}

export function setResourceTop(resourceId: string, isTop: boolean) {
  return axios.put<{ resource_id: string; top: boolean }>(
    `/api/education/resources/${resourceId}/config`,
    { is_top: isTop },
    { timeout: READ_TIMEOUT_MS }
  );
}

export function removeResourceFromLibrary(resourceId: string) {
  return axios.delete<{ resource_id: string; removed: boolean; physical_deleted: boolean }>(
    `/api/education/resources/${resourceId}/library`,
    { timeout: READ_TIMEOUT_MS }
  );
}
