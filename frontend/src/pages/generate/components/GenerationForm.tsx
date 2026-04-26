import type { FormEventHandler } from 'react'

import type { UserPreferences } from '../../../types/podcast'

interface RSSSource {
  id: string
  name: string
  url: string
  category: string
}

interface GenerationFormProps {
  userExists: boolean
  preferences: UserPreferences
  rssSources: RSSSource[]
  rssSource: string
  useSubscriptions: boolean
  scriptApiKey: string
  isGenerating: boolean
  hasAvailableTTSProvider: boolean
  onSubmit: FormEventHandler<HTMLFormElement>
  onCancel: () => void
  onUseSubscriptionsChange: (checked: boolean) => void
  onRssSourceChange: (value: string) => void
  onScriptApiKeyChange: (value: string) => void
}

export function GenerationForm({
  userExists,
  preferences,
  rssSources,
  rssSource,
  useSubscriptions,
  scriptApiKey,
  isGenerating,
  hasAvailableTTSProvider,
  onSubmit,
  onCancel,
  onUseSubscriptionsChange,
  onRssSourceChange,
  onScriptApiKeyChange,
}: GenerationFormProps) {
  return (
    <form onSubmit={onSubmit} style={{ marginBottom: '16px', display: 'grid', gridTemplateColumns: 'minmax(240px, 1.1fr) minmax(210px, 1fr) auto', gap: '12px', alignItems: 'flex-end' }} className="generation-form">
      <div style={{ border: '1px solid var(--border)', borderRadius: '18px', padding: '13px 14px', background: '#fff' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-h)', fontWeight: 800 }}>
          <input type="checkbox" checked={useSubscriptions} onChange={(event) => onUseSubscriptionsChange(event.target.checked)} />
          按我的订阅生成
        </label>
        <p style={{ marginTop: '6px', color: 'var(--text)', fontSize: '12px', lineHeight: 1.45 }}>
          已订阅 {preferences.subscription.rss_sources.length} 个内置源，{preferences.subscription.custom_rss.length} 个自定义源。
          {!userExists ? ' 请先登录后使用订阅偏好。' : ''}
        </p>
      </div>

      <div style={{ opacity: useSubscriptions ? 0.48 : 1 }}>
        <label style={{ display: 'block', marginBottom: '5px', color: 'var(--text-h)', fontWeight: 700 }}>手动 RSS 源</label>
        <select
          value={rssSource}
          onChange={(event) => onRssSourceChange(event.target.value)}
          disabled={useSubscriptions}
          style={{ width: '100%', padding: '10px 12px', borderRadius: '12px', border: '1px solid var(--border)', background: '#fff', color: 'var(--text-h)' }}
        >
          {rssSources.map((source) => (
            <option key={source.id} value={source.id}>
              {source.name} ({source.category})
            </option>
          ))}
        </select>
      </div>

      <div style={{ border: '1px solid var(--border)', borderRadius: '18px', padding: '13px 14px', background: '#fff' }}>
        <label style={{ display: 'block', marginBottom: '5px', color: 'var(--text-h)', fontWeight: 700 }}>临时脚本 API Key</label>
        <input
          type="password"
          value={scriptApiKey}
          onChange={(event) => onScriptApiKeyChange(event.target.value)}
          placeholder="留空则使用后端环境变量"
          style={{ width: '100%', padding: '10px 12px', borderRadius: '12px', border: '1px solid var(--border)', background: '#fff', color: 'var(--text-h)', boxSizing: 'border-box' }}
        />
        <p style={{ marginTop: '6px', color: 'var(--text)', fontSize: '12px', lineHeight: 1.45 }}>
          仅本次任务使用，不会保存到用户设置，也不会写入任务日志。
        </p>
      </div>

      <button
        type="submit"
        disabled={isGenerating || !hasAvailableTTSProvider}
        style={{
          padding: '8px 18px',
          borderRadius: '999px',
          backgroundColor: isGenerating || !hasAvailableTTSProvider ? '#ccc' : 'var(--accent)',
          color: 'white',
          border: 'none',
          cursor: isGenerating || !hasAvailableTTSProvider ? 'not-allowed' : 'pointer',
          minHeight: '42px',
          fontWeight: 800,
        }}
      >
        {isGenerating
          ? '正在执行...'
          : !hasAvailableTTSProvider
            ? '无可用 TTS 提供商'
            : useSubscriptions
              ? '按订阅生成'
              : '触发生成'}
      </button>

      {isGenerating && (
        <button type="button" onClick={onCancel} style={{ padding: '8px 18px', borderRadius: '999px', backgroundColor: '#dc3545', color: 'white', border: 'none', cursor: 'pointer', minHeight: '42px', fontWeight: 800 }}>
          取消任务
        </button>
      )}
    </form>
  )
}
