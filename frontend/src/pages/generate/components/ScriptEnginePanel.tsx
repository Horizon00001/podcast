import type { GenerationCapabilities, ProviderHealthResponse } from '../../../services/api'
import type { UserPreferences } from '../../../types/podcast'
import { scriptProviderLabel } from '../capabilityUtils'

interface ScriptEnginePanelProps {
  preferences: UserPreferences
  availableScriptProviders: GenerationCapabilities['script']
  activeScriptModels: string[]
  providerHealth: ProviderHealthResponse
  onScriptProviderChange: (provider: string) => void
  onScriptModelChange: (model: string) => void
  onScriptBaseUrlChange: (baseUrl: string) => void
}

function formatScriptModelSummary(preferences: UserPreferences) {
  const model = preferences.generation.script_llm_model.trim()
  return model || '未设置，将回退到后端默认值'
}

function formatScriptProviderSummary(preferences: UserPreferences) {
  return preferences.generation.script_provider || 'pydantic_ai'
}

function formatScriptBaseUrlSummary(preferences: UserPreferences) {
  const baseUrl = preferences.generation.script_llm_base_url.trim()
  return baseUrl || '未设置，将回退到后端环境变量'
}

export function ScriptEnginePanel({
  preferences,
  availableScriptProviders,
  activeScriptModels,
  providerHealth,
  onScriptProviderChange,
  onScriptModelChange,
  onScriptBaseUrlChange,
}: ScriptEnginePanelProps) {
  return (
    <section style={{ marginBottom: '16px', display: 'grid', gridTemplateColumns: 'minmax(0, 1.1fr) minmax(0, 0.9fr)', gap: '12px' }} className="generation-script-grid">
      <div style={{ padding: '14px 16px', borderRadius: '18px', border: '1px solid var(--border)', background: '#fff' }}>
        <div style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text)', fontWeight: 800 }}>Script Engine</div>
        <h2 style={{ margin: '8px 0 0', fontSize: '20px', color: 'var(--text-h)' }}>脚本引擎即时切换</h2>
        <p style={{ marginTop: '8px', color: 'var(--text)', fontSize: '13px', lineHeight: 1.6 }}>
          不用回到设置页，这里可以直接切换本次任务的脚本 Provider、模型和 Base URL。适合临时测试 `pydantic_ai` 与 `openai_compatible` 的差异。
        </p>
        {providerHealth.script.length > 0 && (
          <div style={{ marginTop: '10px', padding: '10px 12px', borderRadius: '14px', background: '#f7f7f8', border: '1px solid var(--border)', color: 'var(--text)', fontSize: '12px', lineHeight: 1.6 }}>
            {providerHealth.script.map((item) => `${scriptProviderLabel(item.provider)}：${item.message}`).join('；')}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(180px, 0.9fr) minmax(220px, 1fr)', gap: '10px', marginTop: '14px' }} className="generation-script-controls">
          <div>
            <label style={{ display: 'block', marginBottom: '5px', color: 'var(--text-h)', fontWeight: 700 }}>脚本 Provider</label>
            <select
              value={preferences.generation.script_provider}
              onChange={(event) => onScriptProviderChange(event.target.value)}
              style={{ width: '100%', padding: '10px 12px', borderRadius: '12px', border: '1px solid var(--border)', background: '#fff', color: 'var(--text-h)' }}
            >
              {availableScriptProviders.map((item) => (
                <option key={item.provider} value={item.provider}>
                  {scriptProviderLabel(item.provider)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '5px', color: 'var(--text-h)', fontWeight: 700 }}>脚本模型</label>
            <select
              value={preferences.generation.script_llm_model}
              onChange={(event) => onScriptModelChange(event.target.value)}
              style={{ width: '100%', padding: '10px 12px', borderRadius: '12px', border: '1px solid var(--border)', background: '#fff', color: 'var(--text-h)' }}
            >
              {activeScriptModels.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ marginTop: '10px' }}>
          <label style={{ display: 'block', marginBottom: '5px', color: 'var(--text-h)', fontWeight: 700 }}>脚本 Base URL</label>
          <input
            type="text"
            value={preferences.generation.script_llm_base_url}
            onChange={(event) => onScriptBaseUrlChange(event.target.value)}
            placeholder="留空则使用后端环境变量"
            style={{ width: '100%', padding: '10px 12px', borderRadius: '12px', border: '1px solid var(--border)', background: '#fff', color: 'var(--text-h)', boxSizing: 'border-box' }}
          />
        </div>
      </div>

      <div style={{ padding: '14px 16px', borderRadius: '18px', border: '1px solid var(--border)', background: '#fff' }}>
        <div style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text)', fontWeight: 800 }}>Current Script Config</div>
        <div style={{ marginTop: '12px', display: 'grid', gap: '10px' }}>
          <div style={{ padding: '10px 12px', borderRadius: '14px', background: '#f7f7f8', border: '1px solid var(--border)' }}>
            <div style={{ color: 'var(--text)', fontSize: '12px' }}>Provider</div>
            <div style={{ marginTop: '4px', color: 'var(--text-h)', fontWeight: 800 }}>{scriptProviderLabel(formatScriptProviderSummary(preferences))}</div>
          </div>
          <div style={{ padding: '10px 12px', borderRadius: '14px', background: '#f7f7f8', border: '1px solid var(--border)' }}>
            <div style={{ color: 'var(--text)', fontSize: '12px' }}>Model</div>
            <div style={{ marginTop: '4px', color: 'var(--text-h)', fontWeight: 800, wordBreak: 'break-word' }}>{formatScriptModelSummary(preferences)}</div>
          </div>
          <div style={{ padding: '10px 12px', borderRadius: '14px', background: '#f7f7f8', border: '1px solid var(--border)' }}>
            <div style={{ color: 'var(--text)', fontSize: '12px' }}>Base URL</div>
            <div style={{ marginTop: '4px', color: 'var(--text-h)', fontWeight: 800, wordBreak: 'break-word' }}>{formatScriptBaseUrlSummary(preferences)}</div>
          </div>
        </div>
      </div>
    </section>
  )
}
