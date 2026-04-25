import axios from 'axios';

const READ_TIMEOUT_MS = 8000;

export interface ResourceRecord {
  id: string;
  title: string;
  type: string;
  file_name: string;
  file_path: string;
  file_size: number;
  content_type: string;
  course_id: string;
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
}) {
  return axios.get<ResourcesResponse>('/api/education/resources', {
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
