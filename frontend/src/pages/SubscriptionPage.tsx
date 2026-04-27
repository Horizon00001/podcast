import { useEffect, useMemo, useState } from 'react'
import { api } from '../services/api'
import { useUser } from '../context/UserContext'
import type { UserPreferences } from '../types/podcast'

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

export function SubscriptionPage() {
  const { user } = useUser()
  const [sources, setSources] = useState<RSSSource[]>([])
  const [preferences, setPreferences] = useState<UserPreferences>(defaultPreferences)
  const [selectedCategory, setSelectedCategory] = useState('all')
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

  const builtinCount = preferences.subscription.rss_sources.length
  const customCount = preferences.subscription.custom_rss.length
  const totalCount = builtinCount + customCount

  return (
    <main className="subscription-page" style={{ padding: '78px 24px 24px', maxWidth: '1120px', margin: '0 auto', textAlign: 'left' }}>
      <section className="subscription-hero" style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '16px', alignItems: 'stretch' }}>
        <div className="subscription-hero-card" style={{ padding: '24px 26px', borderRadius: '24px', background: 'linear-gradient(180deg, #ffffff 0%, #faf9f7 100%)', border: '1px solid rgba(8, 6, 13, 0.08)', boxShadow: '0 20px 44px rgba(8, 6, 13, 0.05)' }}>
          <div style={{ fontSize: '11px', letterSpacing: '0.14em', textTransform: 'uppercase', color: '#7c7288', fontWeight: 800 }}>Subscription</div>
          <h1 className="subscription-title" style={{ margin: '10px 0 10px', fontSize: '38px', lineHeight: 1.02, letterSpacing: '-0.05em', fontWeight: 850, color: '#0f172a' }}>订阅中心</h1>
          <p style={{ color: 'var(--text)', maxWidth: '620px', lineHeight: 1.7, fontSize: '15px' }}>
            这里决定生成播客时默认读取哪些新闻来源。保存后，生成页里的“按我的订阅生成”会直接复用这些 RSS 源和你手动添加的自定义来源。
          </p>
          <div style={{ marginTop: '18px', display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '10px' }} className="subscription-summary-grid">
            {[
              ['总订阅数', totalCount],
              ['内置源', builtinCount],
              ['自定义源', customCount],
            ].map(([label, value]) => (
              <div key={label} style={{ borderRadius: '18px', border: '1px solid rgba(8, 6, 13, 0.08)', background: '#fff', padding: '14px 16px' }}>
                <div style={{ fontSize: '12px', color: '#7c7288', fontWeight: 700 }}>{label}</div>
                <div style={{ marginTop: '8px', fontSize: '30px', lineHeight: 1, color: 'var(--text-h)', fontWeight: 850 }}>{value}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {status && <div style={{ marginTop: '18px', padding: '12px 14px', borderRadius: '16px', background: '#f7f4ef', color: 'var(--text-h)', border: '1px solid rgba(8, 6, 13, 0.08)', fontSize: '14px' }}>{status}</div>}

      <section style={{ marginTop: '18px', border: '1px solid rgba(8, 6, 13, 0.08)', borderRadius: '22px', padding: '18px', background: '#fff' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'end', flexWrap: 'wrap' }}>
          <div>
            <h2>内置 RSS 源</h2>
            <p style={{ color: 'var(--text)', fontSize: '14px', lineHeight: 1.6 }}>
              先按分类筛选，再点击卡片切换订阅状态。这里只展示系统内置的新闻源。
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            <div style={{ color: '#7c7288', fontSize: '13px', fontWeight: 700 }}>
              当前显示 {filteredSources.length} / {sources.length} 个来源
            </div>
            <button onClick={saveSettings} style={{ padding: '9px 14px', background: 'var(--accent)', color: 'white', border: 'none', borderRadius: '999px', cursor: 'pointer', fontSize: '13px', fontWeight: 800, whiteSpace: 'nowrap' }}>
              保存订阅
            </button>
          </div>
        </div>

        <div style={{ marginTop: '16px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {categories.map((category) => (
            <button key={category} onClick={() => setSelectedCategory(category)} style={{ border: `1px solid ${selectedCategory === category ? 'rgba(8, 6, 13, 0.22)' : 'var(--border)'}`, color: selectedCategory === category ? 'var(--text-h)' : 'var(--text)', background: selectedCategory === category ? '#f4f1ec' : '#fff', borderRadius: '999px', padding: '8px 14px', cursor: 'pointer', fontWeight: 700, fontSize: '13px' }}>
              {category === 'all' ? '全部' : categoryLabel(category)}
            </button>
          ))}
        </div>

        <div style={{ marginTop: '14px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
          {filteredSources.map((source) => {
            const checked = preferences.subscription.rss_sources.includes(source.id)
            return (
              <button key={source.id} type="button" onClick={() => toggleSource(source)} style={{ textAlign: 'left', border: `1px solid ${checked ? 'rgba(8, 6, 13, 0.18)' : 'rgba(8, 6, 13, 0.08)'}`, borderRadius: '18px', padding: '16px', background: checked ? '#f7f4ef' : '#fff', cursor: 'pointer', boxShadow: checked ? '0 14px 32px rgba(8, 6, 13, 0.07)' : '0 10px 24px rgba(8, 6, 13, 0.03)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'start' }}>
                  <strong style={{ color: 'var(--text-h)', fontSize: '15px' }}>{source.name}</strong>
                  <span style={{ borderRadius: '999px', padding: '5px 9px', background: checked ? 'rgba(8, 6, 13, 0.08)' : '#f6f6f8', color: checked ? 'var(--text-h)' : '#7c7288', fontWeight: 800, fontSize: '12px', whiteSpace: 'nowrap' }}>{checked ? '已订阅' : '未订阅'}</span>
                </div>
                <div style={{ marginTop: '10px', color: '#7c7288', fontSize: '13px', fontWeight: 700 }}>{categoryLabel(source.category)}</div>
                <div style={{ marginTop: '10px', color: 'var(--text)', fontSize: '12px', lineHeight: 1.55, wordBreak: 'break-all' }}>{source.url}</div>
              </button>
            )
          })}
        </div>
      </section>

      <style>{`
        @media (max-width: 860px) {
          .subscription-page {
            padding: 16px !important;
          }

          .subscription-hero {
            grid-template-columns: 1fr !important;
          }

          .subscription-summary-grid {
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
