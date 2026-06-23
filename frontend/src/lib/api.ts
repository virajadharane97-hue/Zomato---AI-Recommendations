import type {
  CuisinesResponse,
  HealthResponse,
  LocationsResponse,
  RecommendRequest,
  RecommendResponse,
} from '@/types/api';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw { status: res.status, ...body };
  }

  return res.json() as Promise<T>;
}

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/api/v1/health');
}

export async function getLocations(): Promise<LocationsResponse> {
  return request<LocationsResponse>('/api/v1/locations');
}

export async function getCuisines(): Promise<CuisinesResponse> {
  return request<CuisinesResponse>('/api/v1/cuisines');
}

export async function postRecommend(req: RecommendRequest): Promise<RecommendResponse> {
  return request<RecommendResponse>('/api/v1/recommend', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}
