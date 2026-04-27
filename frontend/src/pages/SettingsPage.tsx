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
      <section className="settings-hero" style={{ padding: '20px 22px', borderRadius: '22px', background: '#f5f5f5', border: '1px solid rgba(0, 0, 0, 0.18)' }}>
        <div style={{ fontSize: '11px', letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--accent)', fontWeight: 800 }}>Settings</div>
        <h1 className="settings-title" style={{ margin: '8px 0 8px', fontSize: '38px', lineHeight: 1.05 }}>设置</h1>
        <p style={{ color: 'var(--text)', lineHeight: 1.6, maxWidth: '620px', fontSize: '15px' }}>
          当前暂无需要配置的设置项。
        </p>
      </section>

      {status && <div style={{ marginTop: '14px', padding: '10px 12px', borderRadius: '12px', background: 'var(--accent-bg)', color: '#ffffff', border: '1px solid var(--accent-border)', fontSize: '14px' }}>{status}</div>}

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
