import { useState, useEffect, useRef, type FormEvent } from 'react'

import { api } from '../services/api'

interface RSSSource {
  id: string
  name: string
  url: string
  category: string
}

export function GeneratePage() {
  const [rssSources, setRssSources] = useState<RSSSource[]>([])
  const [rssSource, setRssSource] = useState('')
  const [topic, setTopic] = useState('daily-news')
  const [message, setMessage] = useState('')
  const [terminalOutput, setTerminalOutput] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
  const [eventSource, setEventSource] = useState<EventSource | null>(null)
  
  const logEndRef = useRef<HTMLDivElement>(null)

  function appendOutput(text: string) {
    setTerminalOutput((prev) => prev + text)
  }

  // 自动滚动逻辑
  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [terminalOutput])

  function cleanupEventSource() {
    if (eventSource) {
      eventSource.close()
      setEventSource(null)
    }
  }

  useEffect(() => {
    return () => {
      cleanupEventSource()
    }
  }, [])

  useEffect(() => {
    async function loadSources() {
      try {
        const response = await api.getRSSSources()
        setRssSources(response.sources)
        if (response.sources.length > 0) {
          setRssSource(response.sources[0].id)
        }
      } catch (error) {
        console.error('加载RSS源失败:', error)
      }
    }
    loadSources()
  }, [])

  function startListeningToLogs(taskId: string) {
    cleanupEventSource()
    
    const newEventSource = api.createEventSource(taskId)
    setEventSource(newEventSource)
    
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
          <input 
            value={topic} 
            onChange={(e) => setTopic(e.target.value)}
            style={{ width: '100%', padding: '8px', borderRadius: '4px' }}
          />
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
      </form>
      
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
