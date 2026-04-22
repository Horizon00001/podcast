import type { Podcast, RecommendationResponse } from '../types/podcast'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'
export const MEDIA_BASE_URL = BASE_URL.replace('/api/v1', '')

export type InteractionAction = 'play' | 'pause' | 'resume' | 'like' | 'favorite' | 'skip' | 'complete'

export type InteractionPayload = {
  user_id: number
  podcast_id: number
  action: InteractionAction
  listen_duration_ms?: number
  progress_pct?: number
  session_id?: string
  context_hour?: number
  context_weekday?: number
  context_bucket?: string
}

class RequestError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    throw new RequestError(response.status, `请求失败: ${response.status}`)
  }
  return response.json() as Promise<T>
}

export const api = {
  listPodcasts: () => request<Podcast[]>('/podcasts'),
  getPodcast: (id: number) => request<Podcast>(`/podcasts/${id}`),
  getRecommendations: (userId: number) =>
    request<RecommendationResponse>(`/recommendations/${userId}`),
  reportInteraction: (payload: InteractionPayload) =>
    request<{ id: number; user_id: number; podcast_id: number; action: string; created_at: string }>('/interactions', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getUserByUsername: (username: string) =>
    request<{ id: number; username: string; email: string; created_at: string }>(`/users/by-username/${encodeURIComponent(username)}`),
  createUser: (payload: { username: string; email: string }) =>
    request<{ id: number; username: string; email: string; created_at: string }>('/users', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  ensureUser: async (username: string) => {
    const normalized = username.trim()
    if (!normalized) {
      throw new Error('用户名不能为空')
    }
    try {
      return await api.getUserByUsername(normalized)
    } catch (error) {
      if (error instanceof RequestError && error.status === 404) {
        const safeName = normalized.toLowerCase().replace(/[^a-z0-9_-]/g, '-')
        const emailName = safeName || `user-${Date.now()}`
        return api.createUser({ username: normalized, email: `${emailName}@podcast.local` })
      }
      throw error
    }
  },
  getRSSSources: () =>
    request<{ sources: Array<{ id: string; name: string; url: string; category: string }> }>(
      '/generation/sources'
    ),
  getTopics: () =>
    request<{ topics: Array<{ id: string; name: string; description: string }> }>(
      '/generation/topics'
    ),
  triggerGeneration: (payload: { rss_source: string; topic: string }) =>
    request<{ task_id: string; status: string; message: string }>('/generation/trigger', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getGenerationStatus: (taskId: string) =>
    request<{ task_id: string; status: string; message: string }>(`/generation/${taskId}`),
  createEventSource: (taskId: string) => {
    const url = `${BASE_URL}/generation/${taskId}/stream`
    return new EventSource(url)
  },
}
