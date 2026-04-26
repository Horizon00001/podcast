import type { GenerationCapabilities, TTSProviderCapability, TTSProviderDetailCapability } from '../../services/api'
import type { UserPreferences } from '../../types/podcast'
import { defaultPreferences } from './defaultPreferences'

export function getProviderDetails(
  provider: 'dashscope' | 'edge',
  capabilities: GenerationCapabilities,
): TTSProviderDetailCapability | undefined {
  return capabilities.tts.find((item) => item.provider === provider)
}

export function canSelectTtsProvider(
  provider: 'dashscope' | 'edge',
  capabilities: Record<'dashscope' | 'edge', TTSProviderCapability>,
): boolean {
  return provider === 'edge' || capabilities[provider].available
}

export function getVoiceOptions(
  provider: 'dashscope' | 'edge',
  channel: 'male' | 'female',
  capabilities: GenerationCapabilities,
): string[] {
  return [...(getProviderDetails(provider, capabilities)?.voices[channel] ?? [])]
}

export function getModelOptions(
  provider: 'dashscope' | 'edge',
  capabilities: GenerationCapabilities,
): string[] {
  return [...(getProviderDetails(provider, capabilities)?.models ?? [])]
}

export function scriptProviderLabel(provider: string) {
  const labels: Record<string, string> = {
    pydantic_ai: 'PydanticAI',
    openai_compatible: 'OpenAI Compatible',
    openrouter: 'OpenRouter',
    ollama: 'Ollama',
  }
  return labels[provider] ?? provider
}

export function normalizeGeneratePagePreferences(
  savedPreferences: UserPreferences,
  generationCapabilities: GenerationCapabilities,
): UserPreferences {
  const merged: UserPreferences = {
    ...defaultPreferences,
    ...savedPreferences,
    subscription: {
      ...defaultPreferences.subscription,
      ...savedPreferences.subscription,
    },
    generation: {
      ...defaultPreferences.generation,
      ...savedPreferences.generation,
    },
    settings: {
      ...defaultPreferences.settings,
      ...savedPreferences.settings,
    },
  }

  const provider = merged.settings.tts_provider === 'edge' ? 'edge' : 'dashscope'
  merged.settings.tts_provider = provider
  merged.settings.tts_male_provider = merged.settings.tts_male_provider === 'edge' ? 'edge' : provider
  merged.settings.tts_female_provider = merged.settings.tts_female_provider === 'edge' ? 'edge' : provider
  const scriptProviders = generationCapabilities.script.map((item) => item.provider)
  if (!scriptProviders.includes(merged.generation.script_provider)) {
    merged.generation.script_provider = generationCapabilities.script[0]?.provider ?? defaultPreferences.generation.script_provider
  }
  const activeScriptCapability = generationCapabilities.script.find((item) => item.provider === merged.generation.script_provider)
  const defaultScriptModel = activeScriptCapability?.models[0] ?? generationCapabilities.script[0]?.models[0] ?? defaultPreferences.generation.script_llm_model
  if (activeScriptCapability && !activeScriptCapability.models.includes(merged.generation.script_llm_model)) {
    merged.generation.script_llm_model = defaultScriptModel
  }
  merged.generation.script_llm_model = merged.generation.script_llm_model || defaultScriptModel

  const normalizedMaleModels = getModelOptions(merged.settings.tts_male_provider, generationCapabilities)
  merged.settings.tts_male_model = normalizedMaleModels.includes(merged.settings.tts_male_model)
    ? merged.settings.tts_male_model
    : (normalizedMaleModels[0] ?? merged.settings.tts_model)

  const normalizedFemaleModels = getModelOptions(merged.settings.tts_female_provider, generationCapabilities)
  merged.settings.tts_female_model = normalizedFemaleModels.includes(merged.settings.tts_female_model)
    ? merged.settings.tts_female_model
    : (normalizedFemaleModels[0] ?? merged.settings.tts_model)

  const normalizedMaleVoices = getVoiceOptions(merged.settings.tts_male_provider, 'male', generationCapabilities)
  if (!merged.settings.tts_male_voice || !normalizedMaleVoices.includes(merged.settings.tts_male_voice)) {
    merged.settings.tts_male_voice = normalizedMaleVoices[0]
  }

  const normalizedFemaleVoices = getVoiceOptions(merged.settings.tts_female_provider, 'female', generationCapabilities)
  if (!merged.settings.tts_female_voice || !normalizedFemaleVoices.includes(merged.settings.tts_female_voice)) {
    merged.settings.tts_female_voice = normalizedFemaleVoices[0]
  }

  return merged
}

export function normalizeSettingsPagePreferences(
  savedPreferences: UserPreferences,
  generationCapabilities: GenerationCapabilities,
  ttsCapabilities: Record<'dashscope' | 'edge', TTSProviderCapability>,
): UserPreferences {
  const merged: UserPreferences = {
    ...defaultPreferences,
    ...savedPreferences,
    subscription: {
      ...defaultPreferences.subscription,
      ...savedPreferences.subscription,
    },
    generation: {
      ...defaultPreferences.generation,
      ...savedPreferences.generation,
    },
    settings: {
      ...defaultPreferences.settings,
      ...savedPreferences.settings,
    },
  }

  const fallbackProvider = canSelectTtsProvider('dashscope', ttsCapabilities) ? 'dashscope' : 'edge'
  const nextDefaultProvider = canSelectTtsProvider(merged.settings.tts_provider, ttsCapabilities)
    ? merged.settings.tts_provider
    : fallbackProvider
  const nextMaleProvider = canSelectTtsProvider(merged.settings.tts_male_provider, ttsCapabilities)
    ? merged.settings.tts_male_provider
    : fallbackProvider
  const nextFemaleProvider = canSelectTtsProvider(merged.settings.tts_female_provider, ttsCapabilities)
    ? merged.settings.tts_female_provider
    : fallbackProvider

  merged.settings.tts_provider = nextDefaultProvider
  merged.settings.tts_male_provider = nextMaleProvider
  merged.settings.tts_female_provider = nextFemaleProvider

  const scriptProviders = generationCapabilities.script.map((item) => item.provider)
  if (!scriptProviders.includes(merged.generation.script_provider)) {
    merged.generation.script_provider = generationCapabilities.script[0]?.provider ?? defaultPreferences.generation.script_provider
  }
  const activeScriptCapability = generationCapabilities.script.find((item) => item.provider === merged.generation.script_provider)
  const scriptModels = activeScriptCapability?.models ?? generationCapabilities.script[0]?.models ?? []
  if (!scriptModels.includes(merged.generation.script_llm_model)) {
    merged.generation.script_llm_model = scriptModels[0] ?? defaultPreferences.generation.script_llm_model
  }

  const defaultModels = getModelOptions(nextDefaultProvider, generationCapabilities)
  if (!defaultModels.includes(merged.settings.tts_model)) {
    merged.settings.tts_model = defaultModels[0] ?? merged.settings.tts_model
  }

  const maleModels = getModelOptions(nextMaleProvider, generationCapabilities)
  if (!maleModels.includes(merged.settings.tts_male_model)) {
    merged.settings.tts_male_model = maleModels[0] ?? merged.settings.tts_model
  }

  const femaleModels = getModelOptions(nextFemaleProvider, generationCapabilities)
  if (!femaleModels.includes(merged.settings.tts_female_model)) {
    merged.settings.tts_female_model = femaleModels[0] ?? merged.settings.tts_model
  }

  const maleVoices = getVoiceOptions(nextMaleProvider, 'male', generationCapabilities)
  if (!maleVoices.includes(merged.settings.tts_male_voice)) {
    merged.settings.tts_male_voice = maleVoices[0] ?? merged.settings.tts_male_voice
  }

  const femaleVoices = getVoiceOptions(nextFemaleProvider, 'female', generationCapabilities)
  if (!femaleVoices.includes(merged.settings.tts_female_voice)) {
    merged.settings.tts_female_voice = femaleVoices[0] ?? merged.settings.tts_female_voice
  }

  return merged
}
