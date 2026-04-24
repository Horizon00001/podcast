import { useState, useEffect, useRef, type FormEvent } from 'react'

import { api } from '../services/api'

interface RSSSource {
  id: string
  name: string
  url: string
  category: string
}

interface TopicOption {
  id: string
  name: string
  description: string
}

interface SectionProgress {
  key: string
  groupLabel: string
  sectionNumber: number
  sectionType: string
  lineCount: number
  status: 'ready' | 'running' | 'done'
  audioPath?: string
}

interface GroupProgress {
  label: string
  itemCount?: number
  scriptStatus: 'idle' | 'running' | 'done'
  mergeStatus: 'idle' | 'running' | 'done'
  waitingSections?: number
  outputPath?: string
}

function parseSectionDescriptor(text: string) {
  const match = text.match(/section=(\d+) type=([^\s]+) lines=(\d+)/)
  if (!match) {
    return null
  }

  return {
    sectionNumber: Number(match[1]),
    sectionType: match[2],
    lineCount: Number(match[3]),
  }
}

  function sectionKey(groupLabel: string, descriptor: { sectionNumber: number }) {
  return `${groupLabel}#${descriptor.sectionNumber}`
}

function countByStatus<T extends { status: string }>(items: T[], status: T['status']) {
  return items.filter((item) => item.status === status).length
}

export function GeneratePage() {
  const [rssSources, setRssSources] = useState<RSSSource[]>([])
  const [topics, setTopics] = useState<TopicOption[]>([])
  const [rssSource, setRssSource] = useState('')
  const [topic, setTopic] = useState('daily-news')
  const [terminalOutput, setTerminalOutput] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
  const [rssStage, setRssStage] = useState<'idle' | 'running' | 'done'>('idle')
  const [activeGroupLabel, setActiveGroupLabel] = useState<string | null>(null)
  const [groupProgress, setGroupProgress] = useState<Record<string, GroupProgress>>({})
  const [sectionProgress, setSectionProgress] = useState<Record<string, SectionProgress>>({})
  
  const logEndRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  function appendOutput(text: string) {
    setTerminalOutput((prev) => prev + text)
  }

  function resetProgressState() {
    setRssStage('idle')
    setActiveGroupLabel(null)
    setGroupProgress({})
    setSectionProgress({})
  }

  function updateGroup(label: string, updater: (prev: GroupProgress) => GroupProgress) {
    setGroupProgress((prev) => {
      const current = prev[label] ?? {
        label,
        scriptStatus: 'idle',
        mergeStatus: 'idle',
      }

      return {
        ...prev,
        [label]: updater(current),
      }
    })
  }

  function handleStructuredLogChunk(chunk: string) {
    const lines = chunk.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)

    for (const line of lines) {
      if (line.includes('[1/4] 抓取 RSS 数据')) {
        setRssStage('running')
        continue
      }

      if (line.includes('[2/4] 分类并聚类新闻')) {
        setRssStage('done')
        continue
      }

      let match = line.match(/^\[组开始\]\s+([^，]+)，新闻数=(\d+)$/)
      if (match) {
        const label = match[1]
        setActiveGroupLabel(label)
        updateGroup(label, (prev) => ({
          ...prev,
          itemCount: Number(match?.[2] ?? 0),
        }))
        continue
      }

      match = line.match(/^\[Script Start\]\s+(.+)$/)
      if (match) {
        const label = match[1]
        setActiveGroupLabel(label)
        updateGroup(label, (prev) => ({ ...prev, scriptStatus: 'running' }))
        continue
      }

      match = line.match(/^\[Script Done\]\s+(.+)$/)
      if (match) {
        const label = match[1]
        updateGroup(label, (prev) => ({ ...prev, scriptStatus: 'done' }))
        continue
      }

      match = line.match(/^\[Section Ready\]\s+(.+?)\s+(section=\d+ type=[^\s]+ lines=\d+)$/)
      if (match) {
        const groupLabel = match[1]
        const descriptor = parseSectionDescriptor(match[2])
        if (!descriptor) {
          continue
        }
        const key = sectionKey(groupLabel, descriptor)
        setSectionProgress((prev) => ({
          ...prev,
          [key]: {
            key,
            groupLabel,
            sectionNumber: descriptor.sectionNumber,
            sectionType: descriptor.sectionType,
            lineCount: descriptor.lineCount,
            status: prev[key]?.status === 'done' ? 'done' : 'ready',
            audioPath: prev[key]?.audioPath,
          },
        }))
        continue
      }

      match = line.match(/^\[TTS Start\]\s+(.+?)\s+(section=\d+ type=[^\s]+ lines=\d+)$/)
      if (match) {
        const groupLabel = match[1]
        const descriptor = parseSectionDescriptor(match[2])
        if (!descriptor) {
          continue
        }
        const key = sectionKey(groupLabel, descriptor)
        setSectionProgress((prev) => ({
          ...prev,
          [key]: {
            key,
            groupLabel,
            sectionNumber: descriptor.sectionNumber,
            sectionType: descriptor.sectionType,
            lineCount: descriptor.lineCount,
            status: 'running',
            audioPath: prev[key]?.audioPath,
          },
        }))
        continue
      }

      match = line.match(/^\[TTS Done\]\s+(.+?)\s+(section=\d+ type=[^\s]+ lines=\d+)\s+->\s+(.+)$/)
      if (match) {
        const groupLabel = match[1]
        const descriptor = parseSectionDescriptor(match[2])
        const audioPath = match[3]
        if (!descriptor) {
          continue
        }
        const key = sectionKey(groupLabel, descriptor)
        setSectionProgress((prev) => ({
          ...prev,
          [key]: {
            key,
            groupLabel,
            sectionNumber: descriptor.sectionNumber,
            sectionType: descriptor.sectionType,
            lineCount: descriptor.lineCount,
            status: 'done',
            audioPath,
          },
        }))
        continue
      }

      match = line.match(/^\[TTS Wait\]\s+(.+?)\s+waiting for\s+(\d+)\s+section tasks$/)
      if (match) {
        const label = match[1]
        updateGroup(label, (prev) => ({ ...prev, waitingSections: Number(match?.[2] ?? 0) }))
        continue
      }

      match = line.match(/^\[Merge Start\]\s+(.+?)\s+merging\s+(\d+)\s+section files$/)
      if (match) {
        const label = match[1]
        updateGroup(label, (prev) => ({
          ...prev,
          mergeStatus: 'running',
          waitingSections: Number(match?.[2] ?? 0),
        }))
        continue
      }

      match = line.match(/^\[Group Done\]\s+(.+?)\s+->\s+(.+)$/)
      if (match) {
        const label = match[1]
        updateGroup(label, (prev) => ({
          ...prev,
          scriptStatus: 'done',
          mergeStatus: 'done',
          outputPath: match?.[2],
        }))
      }
    }
  }

  // 自动滚动逻辑
  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [terminalOutput])

  function cleanupEventSource() {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
  }

  useEffect(() => {
    return () => {
      cleanupEventSource()
    }
  }, [])

  useEffect(() => {
    async function loadOptions() {
      try {
        const [sourceResponse, topicResponse] = await Promise.all([
          api.getRSSSources(),
          api.getTopics(),
        ])
        setRssSources(sourceResponse.sources)
        if (sourceResponse.sources.length > 0) {
          setRssSource(sourceResponse.sources[0].id)
        }
        setTopics(topicResponse.topics)
        if (topicResponse.topics.length > 0) {
          setTopic(topicResponse.topics[0].id)
        }
      } catch (error) {
        console.error('加载生成选项失败:', error)
      }
    }
    loadOptions()
  }, [])

  function startListeningToLogs(taskId: string) {
    cleanupEventSource()
    
    const newEventSource = api.createEventSource(taskId)
    eventSourceRef.current = newEventSource
    
    newEventSource.onmessage = (event) => {
      try {
        const dataStr = event.data
        
        if (dataStr === '[DONE]') {
          return
        }
        
        const data = JSON.parse(dataStr)
        
        if (data[0] === 'log') {
          // 直接追加后端传来的文本块
          appendOutput(data[1])
          handleStructuredLogChunk(data[1])
        } else if (data[0] === 'status') {
          const status = data[1]
          const statusMessage = data[2]
          
          if (status === 'succeeded') {
            appendOutput(`\n\n✅ 任务全部完成！\n`)
            setIsGenerating(false)
            cleanupEventSource()
          } else if (status === 'failed') {
            appendOutput(`\n\n❌ 任务失败: ${statusMessage}\n`)
            setIsGenerating(false)
            cleanupEventSource()
          } else if (status === 'cancelled') {
            appendOutput(`\n\n🛑 任务已取消\n`)
            setIsGenerating(false)
            cleanupEventSource()
          }
        } else if (data[0] === 'error') {
          appendOutput(`\n❌ 系统错误: ${data[1]}\n`)
          setIsGenerating(false)
          cleanupEventSource()
        }
      } catch (error) {
        console.error('解析SSE消息失败:', error)
      }
    }
    
    newEventSource.onerror = (error) => {
      console.error('SSE连接错误:', error)
      appendOutput('\n⚠️ 连接中断，正在尝试重连...\n')
      
      newEventSource.close()
      setTimeout(() => {
        if (isGenerating && currentTaskId) {
          startListeningToLogs(currentTaskId)
        }
      }, 3000)
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setTerminalOutput('')
    setIsGenerating(true)
    resetProgressState()
    appendOutput('🚀 准备启动生成流程...\n')

    try {
      const result = await api.triggerGeneration({ rss_source: rssSource, topic })
      setCurrentTaskId(result.task_id)
      appendOutput(`📋 任务已分配: ${result.task_id}\n`)
      appendOutput('⏳ 正在建立实时日志连接...\n\n')

      setTimeout(() => startListeningToLogs(result.task_id), 500)
    } catch (error) {
      appendOutput(`❌ 任务提交失败: ${(error as Error).message}\n`)
      setIsGenerating(false)
    }
  }

  async function handleCancel() {
    if (!currentTaskId) return
    try {
      const result = await api.cancelGeneration(currentTaskId)
      appendOutput(`\n\n🛑 ${result.message} (状态: ${result.status})\n`)
      setIsGenerating(false)
      cleanupEventSource()
    } catch (error) {
      appendOutput(`\n⚠️ 取消失败: ${(error as Error).message}\n`)
    }
  }

  return (
    <main style={{ padding: '20px', maxWidth: '1000px', margin: '0 auto' }}>
      <h1>生成播客</h1>
      <form onSubmit={handleSubmit} style={{ marginBottom: '20px', display: 'flex', gap: '15px', alignItems: 'flex-end' }}>
        <div style={{ flex: 1 }}>
          <label style={{ display: 'block', marginBottom: '5px' }}>RSS 源</label>
          <select 
            value={rssSource} 
            onChange={(e) => setRssSource(e.target.value)}
            style={{ width: '100%', padding: '8px', borderRadius: '4px' }}
          >
            {rssSources.map((source) => (
              <option key={source.id} value={source.id}>
                {source.name} ({source.category})
              </option>
            ))}
          </select>
        </div>
        <div style={{ flex: 1 }}>
          <label style={{ display: 'block', marginBottom: '5px' }}>主题</label>
          <select
            value={topic} 
            onChange={(e) => setTopic(e.target.value)}
            style={{ width: '100%', padding: '8px', borderRadius: '4px' }}
          >
            {topics.map((option) => (
              <option key={option.id} value={option.id}>
                {option.name}
              </option>
            ))}
          </select>
          {topics.length > 0 && (
            <p style={{ marginTop: '6px', marginBottom: 0, color: '#666', fontSize: '12px' }}>
              {topics.find((option) => option.id === topic)?.description}
            </p>
          )}
        </div>
        <button
          type="submit"
          disabled={isGenerating}
          style={{
            padding: '8px 20px',
            borderRadius: '4px',
            backgroundColor: isGenerating ? '#ccc' : '#007bff',
            color: 'white',
            border: 'none',
            cursor: isGenerating ? 'not-allowed' : 'pointer'
          }}
        >
          {isGenerating ? '正在执行...' : '触发生成'}
        </button>
        {isGenerating && (
          <button
            type="button"
            onClick={handleCancel}
            style={{
              padding: '8px 20px',
              borderRadius: '4px',
              backgroundColor: '#dc3545',
              color: 'white',
              border: 'none',
              cursor: 'pointer'
            }}
          >
            取消任务
          </button>
        )}
      </form>

      {(isGenerating || terminalOutput) && (
        <section style={{ marginTop: '20px', display: 'grid', gap: '16px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
            <div style={{ padding: '14px 16px', borderRadius: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', color: '#e2e8f0' }}>
              <div style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#94a3b8' }}>分组数</div>
              <div style={{ marginTop: '6px', fontSize: '24px', fontWeight: 800 }}>{Object.keys(groupProgress).length}</div>
            </div>

            <div style={{ padding: '14px 16px', borderRadius: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', color: '#e2e8f0' }}>
              <div style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#94a3b8' }}>TTS 完成</div>
              <div style={{ marginTop: '6px', fontSize: '24px', fontWeight: 800 }}>{countByStatus(Object.values(sectionProgress), 'done')}</div>
            </div>

            <div style={{ padding: '14px 16px', borderRadius: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', color: '#e2e8f0' }}>
              <div style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#94a3b8' }}>TTS 进行中</div>
              <div style={{ marginTop: '6px', fontSize: '24px', fontWeight: 800 }}>{countByStatus(Object.values(sectionProgress), 'running')}</div>
            </div>

            <div style={{ padding: '14px 16px', borderRadius: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', color: '#e2e8f0' }}>
              <div style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#94a3b8' }}>等待中</div>
              <div style={{ marginTop: '6px', fontSize: '24px', fontWeight: 800 }}>{countByStatus(Object.values(sectionProgress), 'ready')}</div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
            <div style={{ padding: '14px 16px', borderRadius: '10px', backgroundColor: '#f4f7fb', border: '1px solid #d7e3f1' }}>
              <div style={{ fontSize: '12px', color: '#5c6b7a', textTransform: 'uppercase', letterSpacing: '0.08em' }}>RSS 抓取</div>
              <div style={{ marginTop: '6px', fontSize: '18px', fontWeight: 700, color: '#17324d' }}>
                {rssStage === 'idle' ? '等待中' : rssStage === 'running' ? '并发抓取中' : '已完成'}
              </div>
            </div>

            <div style={{ padding: '14px 16px', borderRadius: '10px', backgroundColor: '#f8f5ff', border: '1px solid #dfd6f7' }}>
              <div style={{ fontSize: '12px', color: '#6a5f8f', textTransform: 'uppercase', letterSpacing: '0.08em' }}>当前分组</div>
              <div style={{ marginTop: '6px', fontSize: '16px', fontWeight: 700, color: '#33265c', wordBreak: 'break-word' }}>
                {activeGroupLabel ?? '尚未开始'}
              </div>
            </div>
          </div>

          {Object.values(groupProgress).length > 0 && (
            <div style={{ display: 'grid', gap: '12px' }}>
              {Object.values(groupProgress).map((group) => {
                const sections = Object.values(sectionProgress)
                  .filter((section) => section.groupLabel === group.label)
                  .sort((a, b) => a.sectionNumber - b.sectionNumber)

                return (
                  <div
                    key={group.label}
                    style={{
                      border: '1px solid #e4e8ef',
                      borderRadius: '12px',
                      padding: '14px 16px',
                      backgroundColor: '#fff',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                      <div>
                        <div style={{ fontWeight: 700, color: '#1f2937' }}>{group.label}</div>
                        <div style={{ marginTop: '4px', color: '#6b7280', fontSize: '13px' }}>
                          {group.itemCount ? `${group.itemCount} 条新闻` : '新闻数待定'}
                          {' · '}
                          脚本 {group.scriptStatus === 'idle' ? '未开始' : group.scriptStatus === 'running' ? '生成中' : '完成'}
                          {' · '}
                          合并 {group.mergeStatus === 'idle' ? '未开始' : group.mergeStatus === 'running' ? '进行中' : '完成'}
                        </div>
                        <div style={{ marginTop: '4px', color: '#6b7280', fontSize: '13px' }}>
                          {sections.length > 0
                            ? (() => {
                                const done = countByStatus(sections, 'done')
                                const running = countByStatus(sections, 'running')
                                const ready = countByStatus(sections, 'ready')
                                return `Section 进度 ${done}/${sections.length} 完成${running > 0 ? ` · ${running} 进行中` : ''}${ready > 0 ? ` · ${ready} 等待中` : ''}`
                              })()
                            : 'Section 进度待解析'}
                        </div>
                      </div>
                      {group.outputPath && (
                        <div style={{ fontSize: '12px', color: '#4b5563', maxWidth: '420px', wordBreak: 'break-word', textAlign: 'right' }}>
                          输出: {group.outputPath}
                        </div>
                      )}
                    </div>

                    {typeof group.waitingSections === 'number' && (
                      <div style={{ marginTop: '10px', fontSize: '12px', color: '#6b7280' }}>
                        当前等待 {group.waitingSections} 个 section TTS 任务完成
                      </div>
                    )}

                    {sections.length > 0 && (
                      <div style={{ marginTop: '12px', display: 'grid', gap: '8px' }}>
                        {sections.map((section) => (
                          <div
                            key={section.key}
                            style={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              gap: '12px',
                              padding: '10px 12px',
                              borderRadius: '8px',
                              backgroundColor:
                                section.status === 'done'
                                  ? '#eefaf1'
                                  : section.status === 'running'
                                    ? '#fff6e8'
                                    : '#f5f7fa',
                              border:
                                section.status === 'done'
                                  ? '1px solid #c7ebd0'
                                  : section.status === 'running'
                                    ? '1px solid #f4d7a8'
                                    : '1px solid #e6eaf0',
                              alignItems: 'center',
                              flexWrap: 'wrap',
                            }}
                          >
                            <div>
                              <div style={{ fontWeight: 600, color: '#1f2937' }}>
                                Section {section.sectionNumber} · {section.sectionType}
                              </div>
                              <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '2px' }}>
                                {section.lineCount} 句对白
                              </div>
                            </div>
                            <div style={{ fontSize: '12px', color: '#374151', textAlign: 'right' }}>
                              <div>
                                {section.status === 'ready' ? '已出段落，等待 TTS' : section.status === 'running' ? 'TTS 处理中' : 'TTS 完成'}
                              </div>
                              {section.audioPath && (
                                <div style={{ marginTop: '2px', color: '#6b7280', maxWidth: '420px', wordBreak: 'break-word' }}>
                                  {section.audioPath}
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </section>
      )}
      
      {terminalOutput && (
        <div style={{ 
          marginTop: '20px', 
          backgroundColor: '#0c0c0c', 
          borderRadius: '8px', 
          boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
          overflow: 'hidden'
        }}>
          {/* 终端顶部栏 */}
          <div style={{ 
            backgroundColor: '#333', 
            padding: '8px 15px', 
            display: 'flex', 
            alignItems: 'center',
            gap: '8px'
          }}>
            <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#ff5f56' }}></div>
            <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#ffbd2e' }}></div>
            <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#27c93f' }}></div>
            <span style={{ color: '#aaa', fontSize: '12px', marginLeft: '10px', fontFamily: 'monospace' }}>
              Podcast Pipeline Console - {currentTaskId?.slice(0, 8)}
            </span>
          </div>

          {/* 终端内容区 */}
          <div style={{ 
            padding: '15px', 
            height: '600px', 
            overflowY: 'auto', 
            fontFamily: '"Fira Code", "Source Code Pro", Consolas, Monaco, monospace', 
            fontSize: '14px', 
            lineHeight: '1.5',
            color: '#f0f0f0',
            backgroundColor: '#0c0c0c'
          }}>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
              {terminalOutput}
            </pre>
            <div ref={logEndRef} />
          </div>
        </div>
      )}
    </main>
  )
}
