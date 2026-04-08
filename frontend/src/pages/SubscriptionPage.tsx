import { useState, useEffect } from 'react'
import type { SubscriptionSettings } from '../types/podcast'

const ALL_CATEGORIES = [
  { id: 'technology', name: '科技', icon: '💻' },
  { id: 'finance', name: '财经', icon: '📈' },
  { id: 'sports', name: '体育', icon: '⚽' },
  { id: 'entertainment', name: '娱乐', icon: '🎬' },
  { id: 'health', name: '健康', icon: '💪' },
]

export function SubscriptionPage() {
  const [settings, setSettings] = useState<SubscriptionSettings>({
    categories: ['technology', 'sports'],
    frequency: 'daily',
    customRSS: [],
  })
  const [newRSS, setNewRSS] = useState('')

  useEffect(() => {
    const saved = localStorage.getItem('subscription')
    if (saved) setSettings(JSON.parse(saved))
  }, [])

  const saveSettings = () => {
    localStorage.setItem('subscription', JSON.stringify(settings))
    alert('订阅设置已保存')
  }

  const toggleCategory = (catId: string) => {
    setSettings(prev => ({
      ...prev,
      categories: prev.categories.includes(catId)
        ? prev.categories.filter(c => c !== catId)
        : [...prev.categories, catId]
    }))
  }

  const addCustomRSS = () => {
    if (newRSS && !settings.customRSS.includes(newRSS)) {
      setSettings(prev => ({
        ...prev,
        customRSS: [...prev.customRSS, newRSS]
      }))
      setNewRSS('')
    }
  }

  const removeCustomRSS = (url: string) => {
    setSettings(prev => ({
      ...prev,
      customRSS: prev.customRSS.filter(u => u !== url)
    }))
  }

  return (
    <div style={{ padding: '24px', maxWidth: '600px', margin: '0 auto' }}>
      <h1>📋 订阅管理</h1>
      
      <section style={{ marginBottom: '32px' }}>
        <h2>选择感兴趣的领域</h2>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginTop: '16px' }}>
          {ALL_CATEGORIES.map(cat => (
            <button
              key={cat.id}
              onClick={() => toggleCategory(cat.id)}
              style={{
                padding: '8px 16px',
                borderRadius: '40px',
                border: `1px solid ${settings.categories.includes(cat.id) ? 'var(--accent)' : 'var(--border)'}`,
                background: settings.categories.includes(cat.id) ? 'var(--accent-bg)' : 'transparent',
                color: settings.categories.includes(cat.id) ? 'var(--accent)' : 'var(--text)',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <span>{cat.icon}</span> {cat.name}
            </button>
          ))}
        </div>
      </section>

      <section style={{ marginBottom: '32px' }}>
        <h2>生成频率</h2>
        <select
          value={settings.frequency}
          onChange={(e) => setSettings({ ...settings, frequency: e.target.value as any })}
          style={{ padding: '8px', borderRadius: '8px', width: '100%', background: 'var(--bg)', border: '1px solid var(--border)' }}
        >
          <option value="daily">每日更新</option>
          <option value="weekly">每周更新</option>
        </select>
      </section>

      <section style={{ marginBottom: '32px' }}>
        <h2>自定义 RSS 源</h2>
        <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
          <input
            type="url"
            placeholder="输入 RSS 链接"
            value={newRSS}
            onChange={(e) => setNewRSS(e.target.value)}
            style={{ flex: 1, padding: '8px', borderRadius: '8px', border: '1px solid var(--border)', background: 'var(--bg)' }}
          />
          <button onClick={addCustomRSS} style={{ padding: '8px 16px', borderRadius: '8px', background: 'var(--accent)', color: 'white', border: 'none', cursor: 'pointer' }}>
            + 添加
          </button>
        </div>
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {settings.customRSS.map(url => (
            <li key={url} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
              <span style={{ fontSize: '14px', overflow: 'hidden', textOverflow: 'ellipsis' }}>{url}</span>
              <button onClick={() => removeCustomRSS(url)} style={{ background: 'none', border: 'none', color: 'red', cursor: 'pointer' }}>删除</button>
            </li>
          ))}
        </ul>
      </section>

      <button onClick={saveSettings} style={{ padding: '12px 24px', background: 'var(--accent)', color: 'white', border: 'none', borderRadius: '30px', width: '100%', cursor: 'pointer' }}>
        保存设置
      </button>
    </div>
  )
}