import { request } from './client';
import type {
  BatchDeleteResponse,
  CancelResearchResponse,
  ResearchCreateRequest,
  ResearchReviseRequest,
  ResearchSessionResponse,
  ResearchStatus,
  ResearchTaskResponse,
  StartResearchResponse,
} from './types';

const BASE_URL = '/api/v1/researches';

export async function listResearches(params?: {
  status?: ResearchStatus;
  limit?: number;
  offset?: number;
}): Promise<ResearchSessionResponse[]> {
  const queryParams = new URLSearchParams();
  if (params?.status) queryParams.set('status', params.status);
  if (params?.limit !== undefined) queryParams.set('limit', params.limit.toString());
  if (params?.offset !== undefined) queryParams.set('offset', params.offset.toString());

  const queryString = queryParams.toString();
  const url = queryString ? `${BASE_URL}?${queryString}` : BASE_URL;
  return request<ResearchSessionResponse[]>(url);
}

export async function getResearch(id: string): Promise<ResearchSessionResponse> {
  return request<ResearchSessionResponse>(`${BASE_URL}/${id}`);
}

export async function createResearch(
  data: ResearchCreateRequest
): Promise<ResearchSessionResponse> {
  return request<ResearchSessionResponse>(BASE_URL, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function reviseResearch(
  id: string,
  data: ResearchReviseRequest
): Promise<ResearchSessionResponse> {
  return request<ResearchSessionResponse>(`${BASE_URL}/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function startResearch(id: string): Promise<StartResearchResponse> {
  return request<StartResearchResponse>(`${BASE_URL}/${id}/start`, {
    method: 'POST',
  });
}

export async function cancelResearch(id: string): Promise<CancelResearchResponse> {
  return request<CancelResearchResponse>(`${BASE_URL}/${id}/cancel`, {
    method: 'POST',
  });
}

export async function deleteResearch(id: string): Promise<void> {
  return request<void>(`${BASE_URL}/${id}`, {
    method: 'DELETE',
  });
}

export async function batchDeleteResearches(ids: string[]): Promise<BatchDeleteResponse> {
  return request<BatchDeleteResponse>(`${BASE_URL}/batch-delete`, {
    method: 'POST',
    body: JSON.stringify({ ids }),
  });
}

export async function listResearchTasks(id: string): Promise<ResearchTaskResponse[]> {
  return request<ResearchTaskResponse[]>(`${BASE_URL}/${id}/tasks`);
}

export async function getResearchTask(
  id: string,
  taskId: string
): Promise<ResearchTaskResponse> {
  return request<ResearchTaskResponse>(`${BASE_URL}/${id}/tasks/${taskId}`);
}
