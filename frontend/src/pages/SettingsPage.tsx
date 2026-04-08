import { useState, useEffect } from 'react'
import type { UserSettings } from '../types/podcast'

export function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings>({
    voice: 'male',
    language: 'zh',
    autoCover: true,
  })

  useEffect(() => {
    const saved = localStorage.getItem('userSettings')
    if (saved) setSettings(JSON.parse(saved))
  }, [])

  const save = () => {
    localStorage.setItem('userSettings', JSON.stringify(settings))
    alert('设置已保存')
  }

  return (
    <div style={{ padding: '24px', maxWidth: '600px', margin: '0 auto' }}>
      <h1>⚙️ 设置</h1>
      
      <section style={{ marginBottom: '32px' }}>
        <h2>音色选择</h2>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', marginTop: '12px' }}>
          {[
            { id: 'male', name: '男声' },
            { id: 'female', name: '女声' },
            { id: 'style1', name: '活泼风格' },
            { id: 'style2', name: '沉稳风格' },
          ].map(opt => (
            <label key={opt.id} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <input
                type="radio"
                name="voice"
                value={opt.id}
                checked={settings.voice === opt.id}
                onChange={() => setSettings({ ...settings, voice: opt.id as any })}
              />
              {opt.name}
            </label>
          ))}
        </div>
      </section>

      <section style={{ marginBottom: '32px' }}>
        <h2>语言设置</h2>
        <select
          value={settings.language}
          onChange={(e) => setSettings({ ...settings, language: e.target.value as any })}
          style={{ padding: '8px', borderRadius: '8px', width: '100%', background: 'var(--bg)', border: '1px solid var(--border)' }}
        >
          <option value="zh">中文</option>
          <option value="en">英文（实验性）</option>
        </select>
      </section>

      <section style={{ marginBottom: '32px' }}>
        <h2>封面图生成</h2>
        <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <input
            type="checkbox"
            checked={settings.autoCover}
            onChange={(e) => setSettings({ ...settings, autoCover: e.target.checked })}
          />
          自动为播客生成封面图
        </label>
      </section>

      <button onClick={save} style={{ padding: '12px 24px', background: 'var(--accent)', color: 'white', border: 'none', borderRadius: '30px', width: '100%', cursor: 'pointer' }}>
        保存设置
      </button>
    </div>
  )
}