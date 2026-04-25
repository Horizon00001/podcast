import type { CustomRSSSource, Podcast, RecommendationResponse, ScriptLine, UserPreferences } from '../types/podcast'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'
export const MEDIA_BASE_URL = BASE_URL.replace('/api/v1', '')
const REQUEST_TIMEOUT_MS = 8000

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
  recommendation_request_id?: string
}

class RequestError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  try {
    const response = await fetch(`${BASE_URL}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
      signal: controller.signal,
    })
    if (!response.ok) {
      throw new RequestError(response.status, `请求失败: ${response.status}`)
    }
    return response.json() as Promise<T>
  } catch (error) {
    if (error instanceof RequestError) {
      throw error
    }
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error(`请求超时，请确认后端服务已启动: ${BASE_URL}`)
    }
    throw new Error(`无法连接后端服务: ${BASE_URL}`)
  } finally {
    window.clearTimeout(timeoutId)
  }
}

export const api = {
  listPodcasts: () => request<Podcast[]>('/podcasts'),
  getPodcast: (id: number) => request<Podcast>(`/podcasts/${id}`),
  getRecommendations: (userId: number) =>
    request<RecommendationResponse>(`/recommendations/${userId}`),
  setPreferences: (userId: number, categories: string[]) =>
    request<{ ok: boolean; preferences: string[] }>(`/recommendations/${userId}/preferences`, {
      method: 'POST',
      body: JSON.stringify({ categories }),
    }),
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
  getUserPreferences: (userId: number) =>
    request<UserPreferences>(`/users/${userId}/preferences`),
  updateUserPreferences: (userId: number, payload: UserPreferences) =>
    request<UserPreferences>(`/users/${userId}/preferences`, {
      method: 'PUT',
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
  triggerGeneration: (payload: { rss_source: string; user_id?: number; use_subscriptions?: boolean; custom_rss?: CustomRSSSource[] }) =>
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
  cancelGeneration: (taskId: string) =>
    request<{ task_id: string; status: string; message: string }>(`/generation/${taskId}`, {
      method: 'DELETE',
    }),
  getPodcastScript: (id: number) =>
    request<ScriptLine[]>(`/podcasts/${id}/script`),
  getFavorites: (userId: number) =>
    request<Array<{ id: number; user_id: number; podcast_id: number; created_at: string }>>(
      `/favorites?user_id=${userId}`
    ),
  addFavorite: (userId: number, podcastId: number) =>
    request<{ id: number; user_id: number; podcast_id: number; created_at: string }>('/favorites', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, podcast_id: podcastId }),
    }),
  removeFavorite: (userId: number, podcastId: number) =>
    request<{ ok: boolean }>(`/favorites/${userId}/${podcastId}`, {
      method: 'DELETE',
    }),
}
