import { useEffect, useState } from 'react'

import { api, type GenerationCapabilities, type ProviderHealthResponse, type TTSProviderCapability } from '../../services/api'
import type { UserPreferences } from '../../types/podcast'
import { canSelectTtsProvider, normalizeGeneratePagePreferences } from './capabilityUtils'
import { defaultGenerationCapabilities, defaultPreferences, defaultTtsCapabilities, SCRIPT_API_KEY_STORAGE_KEY } from './defaultPreferences'

export interface RSSSource {
  id: string
  name: string
  url: string
  category: string
}

interface UseGenerationOptionsParams {
  userId?: number
}

export function useGenerationOptions({ userId }: UseGenerationOptionsParams) {
  const [rssSources, setRssSources] = useState<RSSSource[]>([])
  const [rssSource, setRssSource] = useState('')
  const [preferences, setPreferences] = useState<UserPreferences>(defaultPreferences)
  const [ttsCapabilities, setTtsCapabilities] = useState<Record<'dashscope' | 'edge', TTSProviderCapability>>(defaultTtsCapabilities)
  const [generationCapabilities, setGenerationCapabilities] = useState<GenerationCapabilities>(defaultGenerationCapabilities)
  const [ttsCapabilityStatus, setTtsCapabilityStatus] = useState('')
  const [providerHealth, setProviderHealth] = useState<ProviderHealthResponse>({ script: [], tts: [] })
  const [useSubscriptions, setUseSubscriptions] = useState(true)
  const [scriptApiKey, setScriptApiKey] = useState('')

  useEffect(() => {
    async function loadOptions() {
      try {
        const [sourceResponse, capabilityResponse, generationCapabilityResponse, providerHealthResponse] = await Promise.all([
          api.getRSSSources(),
          api.getTTSProviderCapabilities(),
          api.getGenerationCapabilities(),
          api.getProviderHealth(),
        ])

        const capabilityMap = capabilityResponse.providers.reduce<Record<'dashscope' | 'edge', TTSProviderCapability>>((acc, item) => {
          acc[item.provider] = item
          return acc
        }, { ...defaultTtsCapabilities })

        setTtsCapabilities(capabilityMap)
        setGenerationCapabilities(generationCapabilityResponse)
        setProviderHealth(providerHealthResponse)
        const unavailableReasons = Object.values(capabilityMap)
          .filter((provider) => !provider.available && provider.reason)
          .map((provider) => `${provider.provider === 'edge' ? 'Edge TTS' : 'DashScope'}：${provider.reason}`)
        setTtsCapabilityStatus(unavailableReasons.join('；'))

        setRssSources(sourceResponse.sources)
        if (sourceResponse.sources.length > 0) {
          setRssSource((prev) => prev || sourceResponse.sources[0].id)
        }
      } catch (error) {
        console.error('加载生成选项失败:', error)
      }
    }

    void loadOptions()
  }, [])

  useEffect(() => {
    setScriptApiKey(window.localStorage.getItem(SCRIPT_API_KEY_STORAGE_KEY) ?? '')
  }, [])

  useEffect(() => {
    async function loadPreferences() {
      if (!userId) {
        return
      }

      try {
        const saved = normalizeGeneratePagePreferences(await api.getUserPreferences(userId), generationCapabilities)
        const fallbackProvider = canSelectTtsProvider('edge', ttsCapabilities) ? 'edge' : 'dashscope'
        const preferredProvider = saved.settings.tts_provider
        const preferredMaleProvider = saved.settings.tts_male_provider
        const preferredFemaleProvider = saved.settings.tts_female_provider
        const nextProvider = canSelectTtsProvider(preferredProvider, ttsCapabilities) ? preferredProvider : fallbackProvider
        const nextMaleProvider = canSelectTtsProvider(preferredMaleProvider, ttsCapabilities) ? preferredMaleProvider : fallbackProvider
        const nextFemaleProvider = canSelectTtsProvider(preferredFemaleProvider, ttsCapabilities) ? preferredFemaleProvider : fallbackProvider

        setPreferences({
          ...saved,
          settings: {
            ...saved.settings,
            tts_provider: nextProvider,
            tts_male_provider: nextMaleProvider,
            tts_male_model: saved.settings.tts_male_model,
            tts_female_provider: nextFemaleProvider,
            tts_female_model: saved.settings.tts_female_model,
          },
        })
        setUseSubscriptions(saved.generation.use_subscriptions)
      } catch (error) {
        console.error('加载用户生成偏好失败:', error)
      }
    }

    void loadPreferences()
  }, [generationCapabilities, ttsCapabilities, userId])

  return {
    rssSources,
    rssSource,
    setRssSource,
    preferences,
    setPreferences,
    ttsCapabilities,
    generationCapabilities,
    ttsCapabilityStatus,
    providerHealth,
    useSubscriptions,
    setUseSubscriptions,
    scriptApiKey,
    setScriptApiKey,
  }
}
