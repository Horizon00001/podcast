import type { GenerationCapabilities, TTSProviderCapability } from '../../services/api'
import type { UserPreferences } from '../../types/podcast'

export const SCRIPT_API_KEY_STORAGE_KEY = 'podcast.script_llm_api_key'

export const defaultPreferences: UserPreferences = {
  subscription: {
    categories: [],
    rss_sources: [],
    custom_rss: [],
    frequency: 'manual',
  },
  generation: {
    topic: 'daily-news',
    max_items: 4,
    use_subscriptions: true,
    script_provider: 'pydantic_ai',
    script_llm_model: 'openai:deepseek-v4-flash',
    script_llm_base_url: '',
  },
  settings: {
    voice: 'female',
    language: 'zh',
    auto_cover: false,
    console_mode: 'compact',
    tts_provider: 'dashscope',
    tts_model: 'cosyvoice-v2',
    tts_male_provider: 'dashscope',
    tts_male_model: 'cosyvoice-v2',
    tts_male_voice: 'loongdavid_v2',
    tts_female_provider: 'dashscope',
    tts_female_model: 'cosyvoice-v2',
    tts_female_voice: 'longanwen',
  },
}

export const defaultTtsCapabilities: Record<'dashscope' | 'edge', TTSProviderCapability> = {
  dashscope: { provider: 'dashscope', available: true },
  edge: { provider: 'edge', available: true },
}

export const defaultGenerationCapabilities: GenerationCapabilities = {
  script: [{ provider: 'pydantic_ai', available: true, models: [defaultPreferences.generation.script_llm_model] }],
  tts: [
    {
      provider: 'dashscope',
      available: true,
      models: [defaultPreferences.settings.tts_model],
      voices: {
        male: [defaultPreferences.settings.tts_male_voice],
        female: [defaultPreferences.settings.tts_female_voice],
      },
    },
    {
      provider: 'edge',
      available: true,
      models: ['edge-tts'],
      voices: { male: ['zh-CN-YunxiNeural'], female: ['zh-CN-XiaoxiaoNeural'] },
    },
  ],
}
