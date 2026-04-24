// src/types/podcast.ts
export interface Podcast {
  id: number
  title: string
  summary: string
  audio_url: string
  script_path: string
  published_at: string
  category: string      // 领域：technology, finance, sports, entertainment, health
}

export interface RecommendationItem {
  podcast_id: number
  score: number
  reason: string
}

export interface RecommendationResponse {
  user_id: number
  strategy: string
  request_id: string
  items: RecommendationItem[]
}

// 脚本行（带时间戳）
export interface ScriptLine {
  id: number
  speaker: 'host' | 'guest'
  text: string
  startTime: number   // 毫秒
  endTime: number
}

// 订阅设置
export interface SubscriptionSettings {
  categories: string[]
  frequency: 'daily' | 'weekly'
  customRSS: string[]
}

// 用户设置
export interface UserSettings {
  voice: 'male' | 'female' | 'style1' | 'style2'
  language: 'zh' | 'en'
  autoCover: boolean
}
