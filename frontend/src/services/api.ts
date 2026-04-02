import type { Podcast, RecommendationResponse } from '../types/podcast'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`)
  }
  return response.json() as Promise<T>
}

export const api = {
  listPodcasts: () => request<Podcast[]>('/podcasts'),
  getPodcast: (id: number) => request<Podcast>(`/podcasts/${id}`),
  getRecommendations: (userId: number) =>
    request<RecommendationResponse>(`/recommendations/${userId}`),
  triggerGeneration: (payload: { rss_source: string; topic: string }) =>
    request<{ task_id: string; status: string; message: string }>('/generation/trigger', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
}
