import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { useUser } from '../context/UserContext'
import type { UserPreferences } from '../types/podcast'

const defaultPreferences: UserPreferences = {
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
  },
  settings: {
    voice: 'female',
    language: 'zh',
    auto_cover: false,
    console_mode: 'compact',
  },
}

export function SettingsPage() {
  const { user } = useUser()
  const [preferences, setPreferences] = useState<UserPreferences>(defaultPreferences)
  const [status, setStatus] = useState('')

  useEffect(() => {
    async function load() {
      try {
        if (user) {
          setPreferences(await api.getUserPreferences(user.id))
        }
      } catch (error) {
        setStatus((error as Error).message)
      }
    }
    void load()
  }, [user])

  async function save() {
    if (!user) {
      setStatus('请先在右上角登录或创建用户')
      return
    }
    try {
      const saved = await api.updateUserPreferences(user.id, {
        ...preferences,
        settings: { ...preferences.settings, console_mode: 'compact' },
      })
      setPreferences(saved)
      setStatus('设置已保存，下一次生成播客会使用这些默认值')
    } catch (error) {
      setStatus((error as Error).message)
    }
  }

  return (
    <main className="settings-page" style={{ padding: '20px', maxWidth: '900px', margin: '0 auto', textAlign: 'left' }}>
      <section className="settings-hero" style={{ padding: '20px 22px', borderRadius: '22px', background: '#f4f0ff', border: '1px solid rgba(170, 59, 255, 0.18)' }}>
        <div style={{ fontSize: '11px', letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--accent)', fontWeight: 800 }}>Settings</div>
        <h1 className="settings-title" style={{ margin: '8px 0 8px', fontSize: '38px', lineHeight: 1.05 }}>生成设置</h1>
        <p style={{ color: 'var(--text)', lineHeight: 1.6, maxWidth: '620px', fontSize: '15px' }}>
          这些设置会作为生成播客的默认参数。注意：TTS 引擎本身仍由后端环境变量控制，这里先控制前端传入的默认偏好。
        </p>
      </section>

      {status && <div style={{ marginTop: '14px', padding: '10px 12px', borderRadius: '12px', background: 'var(--accent-bg)', color: 'var(--text-h)', border: '1px solid var(--accent-border)', fontSize: '14px' }}>{status}</div>}

      <section style={{ marginTop: '16px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '12px' }}>
        <div style={{ border: '1px solid var(--border)', borderRadius: '20px', padding: '18px', background: '#fff' }}>
          <h2>生成来源</h2>
          <label style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '12px', color: 'var(--text-h)', fontWeight: 700, fontSize: '14px' }}>
            <input type="checkbox" checked={preferences.generation.use_subscriptions} onChange={(event) => setPreferences((prev) => ({ ...prev, generation: { ...prev.generation, use_subscriptions: event.target.checked } }))} />
            默认按我的订阅生成
          </label>
          <label style={{ display: 'block', marginTop: '16px', color: 'var(--text)', fontSize: '13px' }}>单集新闻数量上限</label>
          <input type="number" min={2} max={8} value={preferences.generation.max_items} onChange={(event) => setPreferences((prev) => ({ ...prev, generation: { ...prev.generation, max_items: Number(event.target.value) } }))} style={{ marginTop: '8px', padding: '10px 12px', borderRadius: '12px', width: '100%', boxSizing: 'border-box', border: '1px solid var(--border)', color: 'var(--text-h)' }} />
        </div>

        <div style={{ border: '1px solid var(--border)', borderRadius: '20px', padding: '18px', background: '#fff' }}>
          <h2>播报偏好</h2>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: '12px' }}>
            {(['male', 'female'] as const).map((voice) => (
              <button key={voice} type="button" onClick={() => setPreferences((prev) => ({ ...prev, settings: { ...prev.settings, voice } }))} style={{ border: `1px solid ${preferences.settings.voice === voice ? 'var(--accent)' : 'var(--border)'}`, background: preferences.settings.voice === voice ? 'var(--accent-bg)' : '#fff', color: preferences.settings.voice === voice ? 'var(--accent)' : 'var(--text-h)', borderRadius: '14px', padding: '10px', cursor: 'pointer', fontWeight: 800 }}>
                {voice === 'male' ? '男声' : '女声'}
              </button>
            ))}
          </div>
          <select value={preferences.settings.language} onChange={(event) => setPreferences((prev) => ({ ...prev, settings: { ...prev.settings, language: event.target.value as 'zh' | 'en' } }))} style={{ marginTop: '12px', padding: '10px 12px', borderRadius: '12px', width: '100%', background: '#fff', border: '1px solid var(--border)', color: 'var(--text-h)' }}>
            <option value="zh">中文</option>
            <option value="en">英文（实验性）</option>
          </select>
        </div>

        <div style={{ border: '1px solid var(--border)', borderRadius: '20px', padding: '18px', background: '#fff' }}>
          <h2>界面行为</h2>
          <label style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '12px', color: 'var(--text-h)', fontWeight: 700, fontSize: '14px' }}>
            <input type="checkbox" checked={preferences.settings.auto_cover} onChange={(event) => setPreferences((prev) => ({ ...prev, settings: { ...prev.settings, auto_cover: event.target.checked } }))} />
            自动生成封面图
          </label>
        </div>
      </section>

      <button onClick={save} style={{ marginTop: '18px', padding: '13px 22px', background: 'var(--accent)', color: 'white', border: 'none', borderRadius: '999px', width: '100%', cursor: 'pointer', fontSize: '15px', fontWeight: 800 }}>
        保存设置
      </button>
      <style>{`
        @media (max-width: 860px) {
          .settings-page {
            padding: 16px !important;
          }
        }

        @media (max-width: 560px) {
          .settings-page {
            padding: 12px !important;
          }

          .settings-hero {
            padding: 16px !important;
            border-radius: 18px !important;
          }

          .settings-title {
            font-size: 30px !important;
          }
        }
      `}</style>
    </main>
  )
}
