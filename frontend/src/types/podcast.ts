export interface Podcast {
  id: number
  title: string
  summary: string
  audio_url: string
  script_path: string
  published_at: string
}

export interface RecommendationItem {
  podcast_id: number
  score: number
  reason: string
}

export interface RecommendationResponse {
  user_id: number
  strategy: string
  items: RecommendationItem[]
}
