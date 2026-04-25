import { useEffect, useMemo, useState } from 'react'
import { api } from '../services/api'
import { useUser } from '../context/UserContext'
import type { CustomRSSSource, UserPreferences } from '../types/podcast'

interface RSSSource {
  id: string
  name: string
  url: string
  category: string
}

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

function categoryLabel(category: string) {
  const labels: Record<string, string> = {
    tech: '科技',
    technology: '科技',
    business: '商业',
    sports: '体育',
    general: '综合',
  }
  return labels[category] ?? category
}

function buildCustomSource(url: string, category: string): CustomRSSSource {
  const id = `custom-${btoa(url).replace(/[^a-zA-Z0-9]/g, '').slice(0, 12) || Date.now()}`
  return {
    id,
    name: new URL(url).hostname,
    url,
    category,
    enabled: true,
  }
}

export function SubscriptionPage() {
  const { user } = useUser()
  const [sources, setSources] = useState<RSSSource[]>([])
  const [preferences, setPreferences] = useState<UserPreferences>(defaultPreferences)
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [newRSS, setNewRSS] = useState('')
  const [newCategory, setNewCategory] = useState('tech')
  const [status, setStatus] = useState('')

  useEffect(() => {
    async function load() {
      try {
        const sourceResponse = await api.getRSSSources()
        setSources(sourceResponse.sources)
        if (user) {
          const saved = await api.getUserPreferences(user.id)
          setPreferences(saved)
        }
      } catch (error) {
        setStatus((error as Error).message)
      }
    }
    void load()
  }, [user])

  const categories = useMemo(() => {
    return Array.from(new Set(['all', ...sources.map((source) => source.category), ...preferences.subscription.categories]))
  }, [preferences.subscription.categories, sources])

  const filteredSources = selectedCategory === 'all'
    ? sources
    : sources.filter((source) => source.category === selectedCategory)

  function updateSubscription(updater: (current: UserPreferences['subscription']) => UserPreferences['subscription']) {
    setPreferences((prev) => ({ ...prev, subscription: updater(prev.subscription) }))
  }

  function toggleSource(source: RSSSource) {
    updateSubscription((current) => {
      const hasSource = current.rss_sources.includes(source.id)
      const nextSources = hasSource
        ? current.rss_sources.filter((id) => id !== source.id)
        : [...current.rss_sources, source.id]
      const categories = new Set(current.categories)
      if (!hasSource) categories.add(source.category)
      return { ...current, rss_sources: nextSources, categories: Array.from(categories) }
    })
  }

  function addCustomRSS() {
    try {
      const normalized = newRSS.trim()
      const parsed = new URL(normalized)
      if (!['http:', 'https:'].includes(parsed.protocol)) {
        setStatus('RSS 链接必须以 http 或 https 开头')
        return
      }
      const exists = preferences.subscription.custom_rss.some((source) => source.url === normalized)
      if (exists) {
        setStatus('这个 RSS 源已经添加过了')
        return
      }
      const source = buildCustomSource(normalized, newCategory)
      updateSubscription((current) => ({
        ...current,
        custom_rss: [...current.custom_rss, source],
        categories: Array.from(new Set([...current.categories, newCategory])),
      }))
      setNewRSS('')
      setStatus('自定义 RSS 已加入，记得保存')
    } catch {
      setStatus('请输入有效的 RSS URL')
    }
  }

  function removeCustomRSS(id: string) {
    updateSubscription((current) => ({
      ...current,
      custom_rss: current.custom_rss.filter((source) => source.id !== id),
    }))
  }

  async function saveSettings() {
    if (!user) {
      setStatus('请先在右上角登录或创建用户')
      return
    }
    try {
      const saved = await api.updateUserPreferences(user.id, preferences)
      setPreferences(saved)
      setStatus('订阅已保存，生成页可以直接使用“按我的订阅生成”')
    } catch (error) {
      setStatus((error as Error).message)
    }
  }

  return (
    <main className="subscription-page" style={{ padding: '20px', maxWidth: '980px', margin: '0 auto', textAlign: 'left' }}>
      <section style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.5fr) minmax(220px, 0.62fr)', gap: '14px', alignItems: 'stretch' }} className="subscription-hero">
        <div className="subscription-hero-card" style={{ padding: '20px 22px', borderRadius: '22px', background: 'linear-gradient(135deg, #121018, #3b1b66)', color: 'white' }}>
          <div style={{ fontSize: '11px', letterSpacing: '0.12em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.66)', fontWeight: 700 }}>Subscription</div>
          <h1 className="subscription-title" style={{ color: 'white', margin: '8px 0 8px', fontSize: '38px', lineHeight: 1.05 }}>订阅中心</h1>
          <p style={{ color: 'rgba(255,255,255,0.76)', maxWidth: '580px', lineHeight: 1.6, fontSize: '15px' }}>
            这里决定生成播客时读取哪些新闻来源。保存后，生成页的“按我的订阅生成”会使用这些 RSS 源和自定义来源。
          </p>
        </div>
        <aside style={{ border: '1px solid var(--border)', borderRadius: '22px', padding: '18px', background: '#fff', boxShadow: '0 12px 28px rgba(8, 6, 13, 0.05)' }}>
          <div style={{ color: 'var(--text)', fontSize: '13px', fontWeight: 700 }}>当前订阅</div>
          <div style={{ marginTop: '8px', fontSize: '30px', lineHeight: 1, color: 'var(--text-h)', fontWeight: 800 }}>{preferences.subscription.rss_sources.length}</div>
          <p style={{ marginTop: '8px', color: 'var(--text)', fontSize: '14px' }}>内置 RSS 源</p>
          <div style={{ marginTop: '12px', fontSize: '24px', lineHeight: 1, color: 'var(--text-h)', fontWeight: 800 }}>{preferences.subscription.custom_rss.length}</div>
          <p style={{ marginTop: '8px', color: 'var(--text)', fontSize: '14px' }}>自定义 RSS 源</p>
        </aside>
      </section>

      {status && <div style={{ marginTop: '18px', padding: '12px 14px', borderRadius: '14px', background: 'var(--accent-bg)', color: 'var(--text-h)', border: '1px solid var(--accent-border)' }}>{status}</div>}

      <section style={{ marginTop: '18px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        {categories.map((category) => (
          <button key={category} onClick={() => setSelectedCategory(category)} style={{ border: `1px solid ${selectedCategory === category ? 'var(--accent)' : 'var(--border)'}`, color: selectedCategory === category ? 'var(--accent)' : 'var(--text-h)', background: selectedCategory === category ? 'var(--accent-bg)' : '#fff', borderRadius: '999px', padding: '7px 12px', cursor: 'pointer', fontWeight: 700, fontSize: '13px' }}>
            {category === 'all' ? '全部' : categoryLabel(category)}
          </button>
        ))}
      </section>

      <section style={{ marginTop: '14px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '12px' }}>
        {filteredSources.map((source) => {
          const checked = preferences.subscription.rss_sources.includes(source.id)
          return (
            <button key={source.id} type="button" onClick={() => toggleSource(source)} style={{ textAlign: 'left', border: `1px solid ${checked ? 'rgba(170, 59, 255, 0.5)' : 'var(--border)'}`, borderRadius: '18px', padding: '14px', background: checked ? 'rgba(170, 59, 255, 0.08)' : '#fff', cursor: 'pointer', boxShadow: checked ? '0 12px 26px rgba(170, 59, 255, 0.1)' : '0 8px 22px rgba(8, 6, 13, 0.035)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                <strong style={{ color: 'var(--text-h)' }}>{source.name}</strong>
                <span style={{ color: checked ? 'var(--accent)' : 'var(--text)', fontWeight: 800 }}>{checked ? '已订阅' : '订阅'}</span>
              </div>
              <div style={{ marginTop: '8px', color: 'var(--text)', fontSize: '13px' }}>{categoryLabel(source.category)}</div>
              <div style={{ marginTop: '10px', color: '#777', fontSize: '12px', wordBreak: 'break-all' }}>{source.url}</div>
            </button>
          )
        })}
      </section>

      <section style={{ marginTop: '18px', border: '1px solid var(--border)', borderRadius: '20px', padding: '18px', background: '#fff' }}>
        <h2>自定义 RSS 源</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 130px auto', gap: '8px', marginTop: '12px' }} className="subscription-custom-form">
          <input value={newRSS} onChange={(event) => setNewRSS(event.target.value)} placeholder="https://example.com/feed.xml" style={{ padding: '10px 12px', borderRadius: '12px', border: '1px solid var(--border)', color: 'var(--text-h)' }} />
          <select value={newCategory} onChange={(event) => setNewCategory(event.target.value)} style={{ padding: '10px 12px', borderRadius: '12px', border: '1px solid var(--border)', color: 'var(--text-h)', background: '#fff' }}>
            <option value="tech">科技</option>
            <option value="business">商业</option>
            <option value="sports">体育</option>
            <option value="general">综合</option>
          </select>
          <button type="button" onClick={addCustomRSS} style={{ padding: '10px 16px', borderRadius: '12px', border: 'none', background: 'var(--text-h)', color: 'white', cursor: 'pointer', fontWeight: 700 }}>添加</button>
        </div>
        <div style={{ marginTop: '14px', display: 'grid', gap: '10px' }}>
          {preferences.subscription.custom_rss.map((source) => (
            <div key={source.id} style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center', border: '1px solid var(--border)', borderRadius: '16px', padding: '12px 14px' }}>
              <span style={{ color: 'var(--text-h)', wordBreak: 'break-all' }}>{source.name} · {source.url}</span>
              <button type="button" onClick={() => removeCustomRSS(source.id)} style={{ border: 'none', background: 'transparent', color: '#d93025', cursor: 'pointer', fontWeight: 700 }}>删除</button>
            </div>
          ))}
        </div>
      </section>

      <button onClick={saveSettings} style={{ marginTop: '18px', padding: '13px 22px', background: 'var(--accent)', color: 'white', border: 'none', borderRadius: '999px', width: '100%', cursor: 'pointer', fontSize: '15px', fontWeight: 800 }}>
        保存订阅
      </button>

      <style>{`
        @media (max-width: 860px) {
          .subscription-page {
            padding: 16px !important;
          }

          .subscription-hero,
          .subscription-custom-form {
            grid-template-columns: 1fr !important;
          }
        }

        @media (max-width: 560px) {
          .subscription-page {
            padding: 12px !important;
          }

          .subscription-hero-card {
            padding: 16px !important;
            border-radius: 18px !important;
          }

          .subscription-title {
            font-size: 30px !important;
          }
        }
      `}</style>
    </main>
  )
}
