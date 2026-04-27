import { useEffect, useState } from 'react'

import { useUser } from '../context/UserContext'
import { api } from '../services/api'
import type { ModelConfig, UserPreferences } from '../types/podcast'
import { defaultPreferences } from './generate/defaultPreferences'

type ModelSectionKey = 'script' | 'speech' | 'embedding'

const modelSectionMeta: Array<{ key: ModelSectionKey; title: string; description: string }> = [
  {
    key: 'script',
    title: '脚本模型',
    description: '用于剧本生成服务的默认连接参数。',
  },
  {
    key: 'speech',
    title: '语音模型',
    description: '用于 TTS 合成服务的默认连接参数。',
  },
  {
    key: 'embedding',
    title: 'Embedding 模型',
    description: '用于向量化与相似度计算服务的默认连接参数。',
  },
]

function mergePreferences(saved: UserPreferences): UserPreferences {
  return {
    ...defaultPreferences,
    ...saved,
    subscription: {
      ...defaultPreferences.subscription,
      ...saved.subscription,
    },
    generation: {
      ...defaultPreferences.generation,
      ...saved.generation,
    },
    settings: {
      ...defaultPreferences.settings,
      ...saved.settings,
    },
    models: {
      ...defaultPreferences.models,
      ...saved.models,
      script: {
        ...defaultPreferences.models.script,
        ...saved.models?.script,
      },
      speech: {
        ...defaultPreferences.models.speech,
        ...saved.models?.speech,
      },
      embedding: {
        ...defaultPreferences.models.embedding,
        ...saved.models?.embedding,
      },
    },
  }
}

function updateModelConfig(
  preferences: UserPreferences,
  key: ModelSectionKey,
  field: keyof ModelConfig,
  value: string,
): UserPreferences {
  return {
    ...preferences,
    models: {
      ...preferences.models,
      [key]: {
        ...preferences.models[key],
        [field]: value,
      },
    },
  }
}

export function ModelsPage() {
  const { user } = useUser()
  const [preferences, setPreferences] = useState<UserPreferences>(defaultPreferences)
  const [status, setStatus] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    async function load() {
      if (!user) {
        setPreferences(defaultPreferences)
        return
      }

      try {
        const saved = await api.getUserPreferences(user.id)
        setPreferences(mergePreferences(saved))
      } catch (error) {
        setStatus((error as Error).message)
      }
    }

    void load()
  }, [user])

  async function saveModels() {
    if (!user) {
      setStatus('请先在右上角登录或创建用户')
      return
    }

    setSaving(true)
    setStatus('')
    try {
      const saved = await api.updateUserPreferences(user.id, preferences)
      setPreferences(mergePreferences(saved))
      setStatus('模型配置已保存，参数已提交到后端用户偏好')
    } catch (error) {
      setStatus((error as Error).message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="models-page" style={{ padding: '78px 24px 24px', maxWidth: '1120px', margin: '0 auto', textAlign: 'left' }}>
      <section className="models-hero" style={{ padding: '24px 26px', borderRadius: '24px', background: 'linear-gradient(180deg, #ffffff 0%, #faf9f7 100%)', border: '1px solid rgba(8, 6, 13, 0.08)', boxShadow: '0 20px 44px rgba(8, 6, 13, 0.05)' }}>
        <div style={{ fontSize: '11px', letterSpacing: '0.14em', textTransform: 'uppercase', color: '#7c7288', fontWeight: 800 }}>Models</div>
        <h1 className="models-title" style={{ margin: '10px 0 10px', fontSize: '38px', lineHeight: 1.02, letterSpacing: '-0.05em', fontWeight: 850, color: '#0f172a' }}>模型</h1>
        <p style={{ color: 'var(--text)', maxWidth: '700px', lineHeight: 1.7, fontSize: '15px' }}>
          这里保存你的脚本生成、语音合成和 Embedding 服务连接参数。当前版本会把这些字段写入后端用户偏好，供后续能力接入时复用。
        </p>
      </section>

      {status && <div style={{ marginTop: '18px', padding: '12px 14px', borderRadius: '16px', background: '#f7f4ef', color: 'var(--text-h)', border: '1px solid rgba(8, 6, 13, 0.08)', fontSize: '14px' }}>{status}</div>}

      <section style={{ marginTop: '18px', display: 'grid', gap: '16px' }}>
        {modelSectionMeta.map((section) => {
          const config = preferences.models[section.key]
          return (
            <article key={section.key} className="model-card" style={{ border: '1px solid rgba(8, 6, 13, 0.08)', borderRadius: '22px', padding: '20px', background: '#fff', boxShadow: '0 12px 28px rgba(8, 6, 13, 0.04)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', alignItems: 'start', flexWrap: 'wrap' }}>
                <div>
                  <h2 style={{ margin: 0, color: 'var(--text-h)' }}>{section.title}</h2>
                  <p style={{ margin: '8px 0 0', color: 'var(--text)', fontSize: '14px', lineHeight: 1.6 }}>{section.description}</p>
                </div>
              </div>

              <div className="model-grid" style={{ marginTop: '16px', display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '14px' }}>
                {[
                  ['provider', 'Provider', '例如 openai_compatible / dashscope / ollama'],
                  ['model', 'Model', '例如 deepseek-chat / cosyvoice-v2 / text-embedding-v3'],
                  ['base_url', 'Base URL', '例如 https://api.example.com/v1'],
                  ['api_key', 'API Key', '输入后会传给后端并保存到用户偏好'],
                ].map(([field, label, placeholder]) => (
                  <label key={field} style={{ display: 'grid', gap: '8px' }}>
                    <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-h)' }}>{label}</span>
                    <input
                      type={field === 'api_key' ? 'password' : 'text'}
                      value={config[field as keyof ModelConfig]}
                      onChange={(event) => setPreferences((prev) => updateModelConfig(prev, section.key, field as keyof ModelConfig, event.target.value))}
                      placeholder={placeholder}
                      autoComplete="off"
                      style={{
                        padding: '11px 12px',
                        borderRadius: '14px',
                        border: '1px solid rgba(8, 6, 13, 0.12)',
                        background: '#ffffff',
                        color: 'var(--text-h)',
                        fontSize: '14px',
                      }}
                    />
                  </label>
                ))}
              </div>
            </article>
          )
        })}
      </section>

      <button
        type="button"
        onClick={saveModels}
        disabled={saving}
        style={{ marginTop: '20px', padding: '12px 18px', background: 'var(--accent)', color: 'white', border: 'none', borderRadius: '999px', cursor: saving ? 'default' : 'pointer', fontSize: '14px', fontWeight: 800 }}
      >
        {saving ? '保存中...' : '保存模型配置'}
      </button>

      <style>{`
        @media (max-width: 860px) {
          .models-page {
            padding: 16px !important;
          }

          .model-grid {
            grid-template-columns: 1fr !important;
          }
        }

        @media (max-width: 560px) {
          .models-page {
            padding: 12px !important;
          }

          .models-hero,
          .model-card {
            padding: 16px !important;
            border-radius: 18px !important;
          }

          .models-title {
            font-size: 30px !important;
          }
        }
      `}</style>
    </main>
  )
}
