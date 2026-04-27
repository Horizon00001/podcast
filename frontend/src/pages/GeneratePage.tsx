import { useState, useEffect, useRef, type FormEvent } from 'react'

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

const ACTIVE_TASK_STORAGE_KEY = 'podcast_generate_active_task'

interface ActiveTaskSnapshot {
  taskId: string
  updatedAt: number
}

interface PersistedGenerationViewState {
  currentTaskId: string | null
  isGenerating: boolean
  terminalOutput: string
  rssStage: 'idle' | 'running' | 'done'
  rssQueueTotal: number
  rssSourcesQueued: string[]
  rssSourcesStarted: string[]
  rssSourcesCompleted: Array<{ name: string; status: string }>
  activeRssSource: string | null
  activeGroupLabel: string | null
  groupProgress: Record<string, GroupProgress>
  sectionProgress: Record<string, SectionProgress>
}

const GENERATION_VIEW_STORAGE_KEY = 'podcast_generate_view_state'

function loadActiveTaskSnapshot(): ActiveTaskSnapshot | null {
  try {
    const raw = window.sessionStorage.getItem(ACTIVE_TASK_STORAGE_KEY)
    if (!raw) {
      return null
    }
    const parsed = JSON.parse(raw) as Partial<ActiveTaskSnapshot>
    if (!parsed.taskId) {
      return null
    }
    return {
      taskId: parsed.taskId,
      updatedAt: typeof parsed.updatedAt === 'number' ? parsed.updatedAt : Date.now(),
    }
  } catch {
    return null
  }
}

function saveActiveTaskSnapshot(taskId: string) {
  const snapshot: ActiveTaskSnapshot = {
    taskId,
    updatedAt: Date.now(),
  }
  window.sessionStorage.setItem(ACTIVE_TASK_STORAGE_KEY, JSON.stringify(snapshot))
}

function clearActiveTaskSnapshot() {
  window.sessionStorage.removeItem(ACTIVE_TASK_STORAGE_KEY)
}

function loadPersistedGenerationViewState(): PersistedGenerationViewState | null {
  try {
    const raw = window.sessionStorage.getItem(GENERATION_VIEW_STORAGE_KEY)
    if (!raw) {
      return null
    }
    return JSON.parse(raw) as PersistedGenerationViewState
  } catch {
    return null
  }
}

function savePersistedGenerationViewState(state: PersistedGenerationViewState) {
  window.sessionStorage.setItem(GENERATION_VIEW_STORAGE_KEY, JSON.stringify(state))
}

function clearPersistedGenerationViewState() {
  window.sessionStorage.removeItem(GENERATION_VIEW_STORAGE_KEY)
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

type StepStatus = 'pending' | 'active' | 'done'

interface PipelineStep {
  id: number
  title: string
  subtitle: string
  status: StepStatus
}

function getPipelineSteps(args: {
  isGenerating: boolean
  terminalOutput: string
  rssStage: 'idle' | 'running' | 'done'
  groupProgress: Record<string, GroupProgress>
  sectionProgress: Record<string, SectionProgress>
}): PipelineStep[] {
  const { isGenerating, terminalOutput, rssStage, groupProgress, sectionProgress } = args
  const groups = Object.values(groupProgress)
  const sections = Object.values(sectionProgress)
  const hasActivity = isGenerating || terminalOutput.trim().length > 0
  const hasGroups = groups.length > 0
  const hasRunningScript = groups.some((group) => group.scriptStatus === 'running')
  const hasDoneScript = groups.some((group) => group.scriptStatus === 'done')
  const allScriptsDone = groups.length > 0 && groups.every((group) => group.scriptStatus === 'done')
  const hasRunningTts = sections.some((section) => section.status === 'running')
  const hasReadyTts = sections.some((section) => section.status === 'ready')
  const hasDoneTts = sections.some((section) => section.status === 'done')
  const allGroupsMerged = groups.length > 0 && groups.every((group) => group.mergeStatus === 'done')

  const step1Status: StepStatus = rssStage === 'done' ? 'done' : rssStage === 'running' ? 'active' : hasActivity ? 'active' : 'pending'
  const step2Status: StepStatus = hasGroups ? 'done' : rssStage === 'done' || hasActivity ? 'active' : 'pending'
  const step3Status: StepStatus = allScriptsDone ? 'done' : hasRunningScript || hasDoneScript ? 'active' : hasGroups ? 'active' : 'pending'

  let step4Status: StepStatus = 'pending'
  if (allGroupsMerged || (!isGenerating && hasDoneTts)) {
    step4Status = 'done'
  } else if (hasRunningTts || hasReadyTts || hasDoneTts) {
    step4Status = 'active'
  }

  return [
    { id: 1, title: '抓取 RSS', subtitle: '并发拉取 RSS 源与原始内容', status: step1Status },
    { id: 2, title: 'AI 策划剧本', subtitle: '整理新闻分组并决定本期结构', status: step2Status },
    { id: 3, title: '剧本生成中', subtitle: '分组生成播客段落与对白', status: step3Status },
    { id: 4, title: '语音合成中', subtitle: '逐段 TTS 后合并完整节目', status: step4Status },
  ]
}

function formatTerminalLines(output: string) {
  if (!output) {
    return []
  }

  return output.split(/\r?\n/)
}

export function GeneratePage() {
  const { user } = useUser()
  const [rssSources, setRssSources] = useState<RSSSource[]>([])
  const [rssSource, setRssSource] = useState('')
  const [preferences, setPreferences] = useState<UserPreferences>(defaultPreferences)
  const [useSubscriptions, setUseSubscriptions] = useState(true)
  const [terminalOutput, setTerminalOutput] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
  const [rssStage, setRssStage] = useState<'idle' | 'running' | 'done'>('idle')
  const [rssQueueTotal, setRssQueueTotal] = useState(0)
  const [rssSourcesQueued, setRssSourcesQueued] = useState<string[]>([])
  const [rssSourcesStarted, setRssSourcesStarted] = useState<string[]>([])
  const [rssSourcesCompleted, setRssSourcesCompleted] = useState<Array<{ name: string; status: string }>>([])
  const [activeRssSource, setActiveRssSource] = useState<string | null>(null)
  const [activeGroupLabel, setActiveGroupLabel] = useState<string | null>(null)
  const [groupProgress, setGroupProgress] = useState<Record<string, GroupProgress>>({})
  const [sectionProgress, setSectionProgress] = useState<Record<string, SectionProgress>>({})
  
  const terminalContainerRef = useRef<HTMLDivElement>(null)
  const shouldAutoScrollRef = useRef(true)
  const eventSourceRef = useRef<EventSource | null>(null)
  const isGeneratingRef = useRef(false)
  const currentTaskIdRef = useRef<string | null>(null)
  const processedLogCountRef = useRef(0)
  const restorationAttemptedRef = useRef(false)
  const hydratedFromStorageRef = useRef(false)

  function finishGeneration(statusText: string) {
    appendOutput(statusText)
    setIsGenerating(false)
    setCurrentTaskId(null)
    currentTaskIdRef.current = null
    processedLogCountRef.current = 0
    clearActiveTaskSnapshot()
    clearPersistedGenerationViewState()
    cleanupEventSource()
  }

  function appendOutput(text: string) {
    setTerminalOutput((prev) => prev + text)
  }

  function restoreFromLogs(logs: string[]) {
    processedLogCountRef.current = logs.length
    setTerminalOutput(logs.join(''))
    resetProgressState()
    for (const log of logs) {
      handleStructuredLogChunk(log)
    }
  }

  function resetProgressState() {
    setRssStage('idle')
    setRssQueueTotal(0)
    setRssSourcesQueued([])
    setRssSourcesStarted([])
    setRssSourcesCompleted([])
    setActiveRssSource(null)
    setActiveGroupLabel(null)
    setGroupProgress({})
    setSectionProgress({})
  }

  function isScrolledNearBottom(element: HTMLDivElement) {
    return element.scrollHeight - element.scrollTop - element.clientHeight < 48
  }

  function handleTerminalScroll() {
    const element = terminalContainerRef.current
    if (!element) {
      return
    }

    shouldAutoScrollRef.current = isScrolledNearBottom(element)
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

      let match = line.match(/^\[RSS Queue\]\s+本轮计划抓取\s+(\d+)\s+个 RSS 源$/)
      if (match) {
        setRssQueueTotal(Number(match[1]))
        continue
      }

      match = line.match(/^\[RSS Source\]\s+排队抓取\s+(.+?)\s+\([^)]+\)$/)
      if (match) {
        const sourceName = match[1]
        setRssSourcesQueued((prev) => (prev.includes(sourceName) ? prev : [...prev, sourceName]))
        continue
      }

      match = line.match(/^\[RSS Start\]\s+(.+?)\s+\([^)]+\)$/)
      if (match) {
        const sourceName = match[1]
        setActiveRssSource(sourceName)
        setRssStage('running')
        setRssSourcesStarted((prev) => (prev.includes(sourceName) ? prev : [...prev, sourceName]))
        continue
      }

      match = line.match(/^\[RSS Done\]\s+(.+?)\s+\([^)]+\)\s+->\s+(.+)$/)
      if (match) {
        const sourceName = match[1]
        const result = match[2]
        setRssSourcesCompleted((prev) => {
          const next = prev.filter((item) => item.name !== sourceName)
          return [...next, { name: sourceName, status: result }]
        })
        setActiveRssSource((prev) => (prev === sourceName ? null : prev))
        continue
      }

      if (line.includes('[2/4] 分类并聚类新闻')) {
        setRssStage('done')
        setActiveRssSource(null)
        continue
      }

      match = line.match(/^\[组开始\]\s+([^，]+)，新闻数=(\d+)$/)
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
    const element = terminalContainerRef.current
    if (!element || !shouldAutoScrollRef.current) {
      return
    }

    element.scrollTo({ top: element.scrollHeight, behavior: 'smooth' })
  }, [terminalOutput])

  useEffect(() => {
    isGeneratingRef.current = isGenerating
  }, [isGenerating])

  useEffect(() => {
    currentTaskIdRef.current = currentTaskId
  }, [currentTaskId])

  useEffect(() => {
    const persisted = loadPersistedGenerationViewState()
    hydratedFromStorageRef.current = true
    if (!persisted) {
      return
    }

    setCurrentTaskId(persisted.currentTaskId)
    currentTaskIdRef.current = persisted.currentTaskId
    setIsGenerating(persisted.isGenerating)
    isGeneratingRef.current = persisted.isGenerating
    setTerminalOutput(persisted.terminalOutput)
    setRssStage(persisted.rssStage)
    setRssQueueTotal(persisted.rssQueueTotal)
    setRssSourcesQueued(persisted.rssSourcesQueued)
    setRssSourcesStarted(persisted.rssSourcesStarted)
    setRssSourcesCompleted(persisted.rssSourcesCompleted)
    setActiveRssSource(persisted.activeRssSource)
    setActiveGroupLabel(persisted.activeGroupLabel)
    setGroupProgress(persisted.groupProgress)
    setSectionProgress(persisted.sectionProgress)
  }, [])

  useEffect(() => {
    if (!hydratedFromStorageRef.current) {
      return
    }

    const hasVisibleState = Boolean(
      currentTaskId ||
      terminalOutput ||
      isGenerating ||
      rssQueueTotal > 0 ||
      rssSourcesQueued.length > 0 ||
      rssSourcesStarted.length > 0 ||
      rssSourcesCompleted.length > 0 ||
      activeRssSource ||
      Object.keys(groupProgress).length ||
      Object.keys(sectionProgress).length
    )

    if (!hasVisibleState) {
      clearPersistedGenerationViewState()
      return
    }

    savePersistedGenerationViewState({
      currentTaskId,
      isGenerating,
      terminalOutput,
      rssStage,
      rssQueueTotal,
      rssSourcesQueued,
      rssSourcesStarted,
      rssSourcesCompleted,
      activeRssSource,
      activeGroupLabel,
      groupProgress,
      sectionProgress,
    })
  }, [activeGroupLabel, activeRssSource, currentTaskId, groupProgress, isGenerating, rssQueueTotal, rssSourcesCompleted, rssSourcesQueued, rssSourcesStarted, rssStage, sectionProgress, terminalOutput])

  useEffect(() => {
    if (currentTaskId) {
      saveActiveTaskSnapshot(currentTaskId)
      return
    }
    if (restorationAttemptedRef.current) {
      clearActiveTaskSnapshot()
    }
  }, [currentTaskId, isGenerating])

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
        const sourceResponse = await api.getRSSSources()
        setRssSources(sourceResponse.sources)
        if (sourceResponse.sources.length > 0) {
          setRssSource(sourceResponse.sources[0].id)
        }
      } catch (error) {
        console.error('加载生成选项失败:', error)
      }
    }
    loadOptions()
  }, [])

  useEffect(() => {
    async function loadPreferences() {
      if (!user) return
      try {
        const saved = await api.getUserPreferences(user.id)
        setPreferences(saved)
        setUseSubscriptions(saved.generation.use_subscriptions)
      } catch (error) {
        console.error('加载用户生成偏好失败:', error)
      }
    }
    void loadPreferences()
  }, [user])

  useEffect(() => {
    let cancelled = false

    async function restoreActiveTaskIfNeeded() {
      restorationAttemptedRef.current = true
      const snapshot = loadActiveTaskSnapshot()
      if (!snapshot?.taskId) {
        return
      }

      try {
        const status = await api.getGenerationStatus(snapshot.taskId)
        if (cancelled) {
          return
        }

        setCurrentTaskId(snapshot.taskId)
        currentTaskIdRef.current = snapshot.taskId
        restoreFromLogs(status.logs)

        if (status.status === 'queued' || status.status === 'running') {
          setIsGenerating(true)
          isGeneratingRef.current = true
          setTerminalOutput((prev) => `${prev}${prev ? '\n' : ''}检测到进行中的任务: ${snapshot.taskId}\n正在恢复实时日志连接...\n\n`)
          startListeningToLogs(snapshot.taskId, status.logs.length)
          return
        }

        setIsGenerating(false)
        isGeneratingRef.current = false
        if (status.status === 'succeeded') {
          setTerminalOutput((prev) => `${prev}${prev.endsWith('\n') ? '' : '\n'}\n任务全部完成。\n`)
        } else if (status.status === 'failed') {
          setTerminalOutput((prev) => `${prev}${prev.endsWith('\n') ? '' : '\n'}\n任务失败: ${status.message}\n`)
        } else if (status.status === 'cancelled') {
          setTerminalOutput((prev) => `${prev}${prev.endsWith('\n') ? '' : '\n'}\n任务已取消\n`)
        }
        if (status.status !== 'queued' && status.status !== 'running') {
          clearActiveTaskSnapshot()
        }
      } catch (error) {
        console.error('恢复历史任务失败:', error)
        clearActiveTaskSnapshot()
      }
    }

    void restoreActiveTaskIfNeeded()

    return () => {
      cancelled = true
    }
  }, [])

  function startListeningToLogs(taskId: string, fromLogIndex = 0) {
    cleanupEventSource()
    
    const newEventSource = api.createEventSource(taskId, fromLogIndex)
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
          processedLogCountRef.current += 1
          appendOutput(data[1])
          handleStructuredLogChunk(data[1])
        } else if (data[0] === 'status') {
          const status = data[1]
          const statusMessage = data[2]
          
          if (status === 'succeeded') {
            finishGeneration(`\n\n任务全部完成。\n`)
          } else if (status === 'failed') {
            finishGeneration(`\n\n任务失败: ${statusMessage}\n`)
          } else if (status === 'cancelled') {
            finishGeneration(`\n\n任务已取消\n`)
          }
        } else if (data[0] === 'error') {
          finishGeneration(`\n系统错误: ${data[1]}\n`)
        }
      } catch (error) {
        console.error('解析SSE消息失败:', error)
      }
    }
    
    newEventSource.onerror = (error) => {
      console.error('SSE连接错误:', error)
      appendOutput('\n连接中断，正在尝试重连...\n')
      
      newEventSource.close()
      setTimeout(() => {
        if (isGeneratingRef.current && currentTaskIdRef.current) {
          startListeningToLogs(currentTaskIdRef.current, Math.max(fromLogIndex, processedLogCountRef.current))
        }
      }, 3000)
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setTerminalOutput('')
    setIsGenerating(true)
    resetProgressState()
    appendOutput('准备启动生成流程...\n')

    try {
      const result = await api.triggerGeneration({
        rss_source: useSubscriptions ? 'subscribed' : rssSource,
        user_id: user?.id,
        use_subscriptions: useSubscriptions,
        custom_rss: useSubscriptions ? preferences.subscription.custom_rss : [],
      })
      saveActiveTaskSnapshot(result.task_id)
      setCurrentTaskId(result.task_id)
      currentTaskIdRef.current = result.task_id
      appendOutput(`任务已分配: ${result.task_id}\n`)
      appendOutput('正在建立实时日志连接...\n\n')

      setTimeout(() => startListeningToLogs(result.task_id), 500)
    } catch (error) {
      appendOutput(`任务提交失败: ${(error as Error).message}\n`)
      setIsGenerating(false)
      setCurrentTaskId(null)
      currentTaskIdRef.current = null
      processedLogCountRef.current = 0
      clearActiveTaskSnapshot()
      clearPersistedGenerationViewState()
    }
  }

  async function handleCancel() {
    if (!currentTaskId) return
    try {
      const result = await api.cancelGeneration(currentTaskId)
      finishGeneration(`\n\n${result.message} (状态: ${result.status})\n`)
    } catch (error) {
      try {
        const status = await api.getGenerationStatus(currentTaskId)
        if (status.status === 'cancelled') {
          finishGeneration(`\n\n任务已取消\n`)
          return
        }
        if (status.status === 'succeeded') {
          finishGeneration(`\n\n任务全部完成。\n`)
          return
        }
        if (status.status === 'failed') {
          finishGeneration(`\n\n任务失败: ${status.message}\n`)
          return
        }
      } catch (statusError) {
        console.error('取消后同步任务状态失败:', statusError)
      }

      appendOutput(`\n取消失败: ${(error as Error).message}\n`)
    }
  }

  const groups = Object.values(groupProgress)
  const sections = Object.values(sectionProgress)
  const rssSuccessCount = rssSourcesCompleted.filter((item) => item.status.includes('成功')).length
  const pipelineSteps = getPipelineSteps({
    isGenerating,
    terminalOutput,
    rssStage,
    groupProgress,
    sectionProgress,
  })
  const terminalLines = formatTerminalLines(terminalOutput)

  return (
    <main className="generation-page-clean" style={{ padding: '78px 28px 28px', maxWidth: '1040px', margin: '0 auto', textAlign: 'left' }}>
      <section style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 340px', gap: '18px', alignItems: 'stretch' }} className="generation-clean-hero">
        <div style={{ padding: '28px', borderRadius: '28px', background: '#ffffff', border: '1px solid #e8edf3', boxShadow: '0 18px 50px rgba(15, 23, 42, 0.07)' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', color: '#64748b', fontSize: '12px', fontWeight: 850, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '999px', background: isGenerating ? '#22c55e' : '#94a3b8' }} />
            Podcast Generator
          </div>
          <h1 className="generation-clean-title" style={{ margin: '18px 0 0', color: '#0f172a', fontSize: '48px', lineHeight: 1.02, letterSpacing: '-0.05em', fontWeight: 850 }}>
            生成播客
          </h1>
          <p style={{ marginTop: '14px', color: '#64748b', fontSize: '16px', lineHeight: 1.75, maxWidth: '620px' }}>
            从 RSS 源抓取内容，自动策划、生成脚本并合成语音。生成过程中只展示关键状态，详细日志放在底部。
          </p>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: '20px', borderRadius: '28px', background: '#f8fafc', border: '1px solid #e2e8f0', display: 'grid', gap: '14px', alignContent: 'start' }}>
          <div style={{ color: '#0f172a', fontSize: '18px', fontWeight: 850 }}>开始生成</div>
          <label style={{ display: 'flex', gap: '10px', alignItems: 'flex-start', color: '#0f172a', fontWeight: 800, fontSize: '14px' }}>
            <input type="checkbox" checked={useSubscriptions} onChange={(event) => setUseSubscriptions(event.target.checked)} style={{ marginTop: '3px' }} />
            <span>
              按我的订阅生成
              <span style={{ display: 'block', marginTop: '4px', color: '#64748b', fontWeight: 500, lineHeight: 1.45 }}>
                {preferences.subscription.rss_sources.length} 个内置源，{preferences.subscription.custom_rss.length} 个自定义源
              </span>
            </span>
          </label>
          <select
            value={rssSource}
            onChange={(e) => setRssSource(e.target.value)}
            disabled={useSubscriptions}
            style={{ width: '100%', padding: '11px 12px', borderRadius: '14px', border: '1px solid #d8e0ea', background: '#ffffff', color: '#0f172a', opacity: useSubscriptions ? 0.5 : 1 }}
          >
            {rssSources.map((source) => (
              <option key={source.id} value={source.id}>{source.name} ({source.category})</option>
            ))}
          </select>
          <div style={{ display: 'grid', gridTemplateColumns: isGenerating ? '1fr 1fr' : '1fr', gap: '10px' }}>
            <button type="submit" disabled={isGenerating} style={{ padding: '12px 16px', borderRadius: '999px', border: 'none', background: isGenerating ? '#cbd5e1' : '#0f172a', color: '#ffffff', fontWeight: 850, cursor: isGenerating ? 'not-allowed' : 'pointer' }}>
              {isGenerating ? '生成中' : '生成播客'}
            </button>
            {isGenerating && (
              <button type="button" onClick={handleCancel} style={{ padding: '12px 16px', borderRadius: '999px', border: '1px solid #fecdd3', background: '#fff1f2', color: '#be123c', fontWeight: 850, cursor: 'pointer' }}>
                取消
              </button>
            )}
          </div>
        </form>
      </section>

      {(isGenerating || terminalOutput) && (
        <section style={{ marginTop: '18px', display: 'grid', gap: '18px' }}>
          <div style={{ padding: '20px', borderRadius: '28px', background: '#ffffff', border: '1px solid #e8edf3', boxShadow: '0 14px 42px rgba(15, 23, 42, 0.055)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center', flexWrap: 'wrap', marginBottom: '16px' }}>
              <div>
                <div style={{ color: '#64748b', fontSize: '12px', fontWeight: 850, letterSpacing: '0.08em', textTransform: 'uppercase' }}>Progress</div>
                <h2 style={{ margin: '5px 0 0', color: '#0f172a', fontSize: '22px', fontWeight: 850 }}>生成进度</h2>
              </div>
              <div style={{ color: '#64748b', fontSize: '13px', fontWeight: 800 }}>
                {activeRssSource ? `正在抓取：${activeRssSource}` : activeGroupLabel ? `当前分组：${activeGroupLabel}` : isGenerating ? '任务运行中' : '任务已结束'}
              </div>
            </div>

            <div className="generation-clean-stepper" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: '10px' }}>
              {pipelineSteps.map((step) => {
                const isActive = step.status === 'active'
                const isDone = step.status === 'done'
                return (
                  <div key={step.id} style={{ padding: '14px', borderRadius: '18px', background: isActive ? '#eff6ff' : isDone ? '#f0fdf4' : '#f8fafc', border: `1px solid ${isActive ? '#bfdbfe' : isDone ? '#bbf7d0' : '#e2e8f0'}` }}>
                    <div style={{ width: '30px', height: '30px', borderRadius: '999px', display: 'grid', placeItems: 'center', background: isDone ? '#22c55e' : isActive ? '#2563eb' : '#e2e8f0', color: isDone || isActive ? '#ffffff' : '#64748b', fontSize: '12px', fontWeight: 900 }}>
                      {isDone ? '✓' : step.id}
                    </div>
                    <div style={{ marginTop: '10px', color: '#0f172a', fontSize: '14px', fontWeight: 850 }}>{step.title}</div>
                    <div style={{ marginTop: '5px', color: '#64748b', fontSize: '12px', lineHeight: 1.45 }}>{step.status === 'active' ? '进行中' : step.status === 'done' ? '已完成' : '等待中'}</div>
                  </div>
                )
              })}
            </div>

            <div style={{ marginTop: '16px', display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: '10px' }} className="generation-clean-stats">
              {[
                ['RSS 成功', rssSuccessCount],
                ['新闻分组', groups.length],
                ['TTS 完成', countByStatus(sections, 'done')],
                ['日志行数', terminalLines.length],
              ].map(([label, value]) => (
                <div key={label} style={{ padding: '12px', borderRadius: '16px', background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                  <div style={{ color: '#64748b', fontSize: '12px' }}>{label}</div>
                  <div style={{ marginTop: '5px', color: '#0f172a', fontSize: '22px', fontWeight: 900 }}>{value}</div>
                </div>
              ))}
            </div>
          </div>

          {groups.length > 0 && (
            <div style={{ padding: '20px', borderRadius: '28px', background: '#ffffff', border: '1px solid #e8edf3', boxShadow: '0 14px 42px rgba(15, 23, 42, 0.055)' }}>
              <div style={{ color: '#0f172a', fontSize: '18px', fontWeight: 850, marginBottom: '12px' }}>分组</div>
              <div style={{ display: 'grid', gap: '8px' }}>
                {groups.slice(0, 5).map((group) => {
                  const groupSections = Object.values(sectionProgress).filter((section) => section.groupLabel === group.label)
                  const done = countByStatus(groupSections, 'done')
                  return (
                    <div key={group.label} style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', padding: '12px', borderRadius: '16px', background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                      <div style={{ color: '#0f172a', fontWeight: 800, wordBreak: 'break-word' }}>{group.label}</div>
                      <div style={{ color: '#2563eb', fontWeight: 900, whiteSpace: 'nowrap' }}>{groupSections.length ? `${done}/${groupSections.length}` : group.scriptStatus}</div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          <div style={{ padding: '20px', borderRadius: '28px', background: '#ffffff', border: '1px solid #e8edf3', boxShadow: '0 14px 42px rgba(15, 23, 42, 0.055)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center', marginBottom: '12px' }}>
              <div>
                <div style={{ color: '#0f172a', fontSize: '18px', fontWeight: 850 }}>实时日志</div>
                <div style={{ marginTop: '4px', color: '#64748b', fontSize: '12px' }}>{currentTaskId ? currentTaskId.slice(0, 8) : 'preview'}</div>
              </div>
            </div>
            <div ref={terminalContainerRef} onScroll={handleTerminalScroll} style={{ height: '360px', overflowY: 'auto', padding: '14px', borderRadius: '18px', background: '#f8fafc', border: '1px solid #e2e8f0', fontFamily: 'var(--mono)', fontSize: '12px', lineHeight: 1.7 }}>
              {terminalLines.length > 0 ? terminalLines.map((line, index) => (
                <div key={`${index}-${line}`} style={{ display: 'grid', gridTemplateColumns: '36px minmax(0, 1fr)', gap: '10px', padding: '2px 0' }}>
                  <span style={{ color: '#94a3b8', textAlign: 'right' }}>{String(index + 1).padStart(3, '0')}</span>
                  <span style={{ color: line.includes('失败') || line.includes('错误') ? '#be123c' : line.startsWith('[RSS') ? '#047857' : line.startsWith('[') ? '#2563eb' : '#334155', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{line || ' '}</span>
                </div>
              )) : <div style={{ color: '#64748b' }}>启动后这里会显示 SSE 日志。</div>}
            </div>
          </div>
        </section>
      )}

      {!isGenerating && !terminalOutput && (
        <section style={{ marginTop: '18px', padding: '20px', borderRadius: '28px', background: '#ffffff', border: '1px solid #e8edf3', color: '#64748b', lineHeight: 1.7 }}>
          生成任务尚未开始。选择来源后点击“生成播客”，页面会自动切换到进度视图。
        </section>
      )}

      <style>{`
        @media (max-width: 900px) {
          .generation-clean-hero,
          .generation-clean-stepper,
          .generation-clean-stats {
            grid-template-columns: 1fr !important;
          }
        }

        @media (max-width: 640px) {
          .generation-page-clean {
            padding: 14px !important;
          }

          .generation-clean-title {
            font-size: 38px !important;
          }
        }
      `}</style>
    </main>
  )

  /* Previous white workbench layout kept out of compilation.
  return (
    <main className="generation-page-white" style={{ padding: '24px', maxWidth: '1240px', margin: '0 auto', textAlign: 'left' }}>
      <section
        className="generation-white-hero"
        style={{
          position: 'relative',
          overflow: 'hidden',
          borderRadius: '32px',
          border: '1px solid rgba(15, 23, 42, 0.08)',
          background: 'linear-gradient(135deg, #ffffff 0%, #f7f8fb 48%, #eef6ff 100%)',
          boxShadow: '0 28px 70px rgba(15, 23, 42, 0.10)',
          padding: '28px',
          marginBottom: '18px',
        }}
      >
        <div style={{ position: 'absolute', right: '-80px', top: '-110px', width: '280px', height: '280px', borderRadius: '999px', background: 'rgba(96, 165, 250, 0.18)', filter: 'blur(2px)' }} />
        <div style={{ position: 'absolute', left: '46%', bottom: '-120px', width: '260px', height: '260px', borderRadius: '999px', background: 'rgba(45, 212, 191, 0.13)', filter: 'blur(2px)' }} />

        <div style={{ position: 'relative', display: 'grid', gridTemplateColumns: 'minmax(0, 1.18fr) minmax(320px, 0.82fr)', gap: '24px', alignItems: 'stretch' }} className="generation-white-hero-grid">
          <div style={{ display: 'grid', alignContent: 'space-between', gap: '26px' }}>
            <div>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '7px 10px', borderRadius: '999px', background: '#ffffff', border: '1px solid rgba(15, 23, 42, 0.08)', color: '#475569', fontSize: '12px', fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                <span style={{ width: '7px', height: '7px', borderRadius: '999px', background: isGenerating ? '#22c55e' : '#94a3b8', boxShadow: isGenerating ? '0 0 0 5px rgba(34,197,94,0.13)' : 'none' }} />
                Generation Studio
              </div>
              <h1 className="generation-white-title" style={{ margin: '18px 0 0', color: '#0f172a', fontSize: '54px', lineHeight: 0.98, letterSpacing: '-0.055em', fontWeight: 850 }}>
                生成一档新的播客
              </h1>
              <p style={{ marginTop: '16px', color: '#526071', fontSize: '16px', lineHeight: 1.75, maxWidth: '680px' }}>
                选择 RSS 来源后启动后端 4 步流水线。页面会实时展示 RSS 抓取、AI 策划、剧本生成和语音合成进度。
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: '10px' }} className="generation-white-metrics">
              {[
                ['RSS 源', rssQueueTotal || rssSourcesQueued.length || (useSubscriptions ? preferences.subscription.rss_sources.length + preferences.subscription.custom_rss.length : rssSource ? 1 : 0)],
                ['分组', groups.length],
                ['TTS 完成', countByStatus(sections, 'done')],
                ['日志', terminalLines.length],
              ].map(([label, value]) => (
                <div key={label} style={{ padding: '14px', borderRadius: '20px', background: 'rgba(255,255,255,0.74)', border: '1px solid rgba(15,23,42,0.08)', backdropFilter: 'blur(14px)' }}>
                  <div style={{ color: '#64748b', fontSize: '12px', fontWeight: 800 }}>{label}</div>
                  <div style={{ marginTop: '8px', color: '#0f172a', fontSize: '28px', lineHeight: 1, fontWeight: 850 }}>{value}</div>
                </div>
              ))}
            </div>
          </div>

          <form onSubmit={handleSubmit} style={{ borderRadius: '28px', background: 'rgba(255,255,255,0.88)', border: '1px solid rgba(15,23,42,0.08)', boxShadow: '0 18px 42px rgba(15,23,42,0.10)', padding: '20px', display: 'grid', gap: '16px', alignContent: 'start' }}>
            <div>
              <div style={{ color: '#0f172a', fontSize: '20px', fontWeight: 850 }}>任务入口</div>
              <div style={{ marginTop: '6px', color: '#64748b', fontSize: '13px', lineHeight: 1.55 }}>
                {isGenerating ? '任务正在运行，可以取消或继续查看实时进度。' : '选择来源后点击生成，系统会自动进入完整流水线。'}
              </div>
            </div>

            <label style={{ display: 'flex', gap: '12px', alignItems: 'flex-start', padding: '14px', borderRadius: '18px', background: useSubscriptions ? '#eff6ff' : '#f8fafc', border: `1px solid ${useSubscriptions ? '#bfdbfe' : '#e2e8f0'}`, color: '#0f172a', cursor: 'pointer' }}>
              <input type="checkbox" checked={useSubscriptions} onChange={(event) => setUseSubscriptions(event.target.checked)} style={{ marginTop: '3px' }} />
              <span>
                <span style={{ display: 'block', fontWeight: 850 }}>按我的订阅生成</span>
                <span style={{ display: 'block', marginTop: '4px', color: '#64748b', fontSize: '13px', lineHeight: 1.45 }}>
                  {preferences.subscription.rss_sources.length} 个内置源，{preferences.subscription.custom_rss.length} 个自定义源。{!user ? ' 请先登录后使用订阅偏好。' : ''}
                </span>
              </span>
            </label>

            <div style={{ opacity: useSubscriptions ? 0.48 : 1 }}>
              <label style={{ display: 'block', color: '#334155', fontWeight: 800, fontSize: '13px', marginBottom: '7px' }}>手动 RSS 源</label>
              <select
                value={rssSource}
                onChange={(e) => setRssSource(e.target.value)}
                disabled={useSubscriptions}
                style={{ width: '100%', padding: '12px 13px', borderRadius: '15px', border: '1px solid #d8e0ea', background: '#fff', color: '#0f172a', fontWeight: 700 }}
              >
                {rssSources.map((source) => (
                  <option key={source.id} value={source.id}>
                    {source.name} ({source.category})
                  </option>
                ))}
              </select>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: isGenerating ? '1fr 1fr' : '1fr', gap: '10px' }}>
              <button
                type="submit"
                disabled={isGenerating}
                style={{
                  padding: '13px 18px',
                  borderRadius: '999px',
                  background: isGenerating ? '#cbd5e1' : '#0f172a',
                  color: '#ffffff',
                  border: 'none',
                  cursor: isGenerating ? 'not-allowed' : 'pointer',
                  fontWeight: 850,
                  boxShadow: isGenerating ? 'none' : '0 14px 28px rgba(15,23,42,0.18)',
                }}
              >
                {isGenerating ? '生成中' : useSubscriptions ? '按订阅生成' : '触发生成'}
              </button>
              {isGenerating && (
                <button type="button" onClick={handleCancel} style={{ padding: '13px 18px', borderRadius: '999px', background: '#fff1f2', color: '#be123c', border: '1px solid #fecdd3', cursor: 'pointer', fontWeight: 850 }}>
                  取消任务
                </button>
              )}
            </div>

            <div style={{ padding: '12px 14px', borderRadius: '18px', background: '#f8fafc', border: '1px solid #e2e8f0', color: '#64748b', fontSize: '12px', lineHeight: 1.55 }}>
              当前任务：{currentTaskId ? currentTaskId.slice(0, 8) : '尚未启动'}
            </div>
          </form>
        </div>
      </section>

      {(isGenerating || terminalOutput) && (
        <section style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.38fr) minmax(340px, 0.82fr)', gap: '18px', alignItems: 'start' }} className="generation-white-workbench">
          <div style={{ display: 'grid', gap: '18px' }}>
            <section style={{ padding: '18px', borderRadius: '28px', background: '#ffffff', border: '1px solid #e5eaf0', boxShadow: '0 14px 38px rgba(15,23,42,0.06)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
                <div>
                  <div style={{ color: '#64748b', fontSize: '12px', fontWeight: 850, letterSpacing: '0.08em', textTransform: 'uppercase' }}>Pipeline</div>
                  <h2 style={{ margin: '6px 0 0', color: '#0f172a', fontSize: '24px', fontWeight: 850 }}>4 步生成路径</h2>
                </div>
                <div style={{ padding: '8px 12px', borderRadius: '999px', background: isGenerating ? '#ecfdf5' : '#f1f5f9', color: isGenerating ? '#047857' : '#475569', border: `1px solid ${isGenerating ? '#bbf7d0' : '#e2e8f0'}`, fontSize: '12px', fontWeight: 850 }}>
                  {isGenerating ? '实时运行中' : '任务已结束'}
                </div>
              </div>

              <div className="generation-white-stepper" style={{ marginTop: '16px', display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: '10px' }}>
                {pipelineSteps.map((step) => {
                  const isActive = step.status === 'active'
                  const isDone = step.status === 'done'
                  return (
                    <div key={step.id} style={{ minHeight: '150px', padding: '15px', borderRadius: '22px', background: isActive ? '#eff6ff' : isDone ? '#f0fdf4' : '#f8fafc', border: `1px solid ${isActive ? '#bfdbfe' : isDone ? '#bbf7d0' : '#e2e8f0'}`, position: 'relative', overflow: 'hidden' }}>
                      {isActive && <motion.div initial={{ x: '-100%' }} animate={{ x: '130%' }} transition={{ duration: 1.9, repeat: Infinity, ease: 'linear' }} style={{ position: 'absolute', inset: 0, background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.75), transparent)' }} />}
                      <div style={{ position: 'relative', width: '34px', height: '34px', borderRadius: '999px', display: 'grid', placeItems: 'center', background: isDone ? '#22c55e' : isActive ? '#2563eb' : '#e2e8f0', color: isDone || isActive ? '#fff' : '#64748b', fontWeight: 900 }}>
                        {isDone ? 'OK' : step.id}
                      </div>
                      <div style={{ position: 'relative', marginTop: '14px', color: '#0f172a', fontWeight: 850, fontSize: '16px' }}>{step.title}</div>
                      <div style={{ position: 'relative', marginTop: '7px', color: '#64748b', fontSize: '12px', lineHeight: 1.55 }}>{step.subtitle}</div>
                    </div>
                  )
                })}
              </div>
            </section>

            <section style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.08fr) minmax(260px, 0.92fr)', gap: '14px' }} className="generation-white-rss-grid">
              <div style={{ padding: '18px', borderRadius: '28px', background: '#ffffff', border: '1px solid #e5eaf0', boxShadow: '0 14px 38px rgba(15,23,42,0.06)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ color: '#64748b', fontSize: '12px', fontWeight: 850, letterSpacing: '0.08em', textTransform: 'uppercase' }}>RSS Radar</div>
                    <h2 style={{ margin: '6px 0 0', color: '#0f172a', fontSize: '22px', fontWeight: 850 }}>当前抓取源</h2>
                  </div>
                  <div style={{ color: '#2563eb', fontWeight: 850, fontSize: '13px' }}>{rssQueueTotal > 0 ? `${rssCompletedCount}/${rssQueueTotal}` : '待启动'}</div>
                </div>
                <div style={{ marginTop: '16px', padding: '18px', borderRadius: '22px', background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                  <div style={{ color: '#64748b', fontSize: '12px', fontWeight: 800 }}>正在处理</div>
                  <div style={{ marginTop: '8px', color: '#0f172a', fontSize: '24px', lineHeight: 1.2, fontWeight: 900, wordBreak: 'break-word' }}>
                    {activeRssSource ?? (rssStage === 'done' ? 'RSS 抓取完成' : rssSourcesStarted.at(-1) ?? '等待 RSS 事件')}
                  </div>
                </div>
                <div style={{ marginTop: '14px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {rssSourcesQueued.length > 0 ? rssSourcesQueued.map((sourceName) => {
                    const isDone = rssSourcesCompleted.some((item) => item.name === sourceName && item.status.includes('成功'))
                    const isActive = activeRssSource === sourceName
                    return (
                      <span key={sourceName} style={{ padding: '7px 10px', borderRadius: '999px', background: isActive ? '#dbeafe' : isDone ? '#dcfce7' : '#f1f5f9', border: `1px solid ${isActive ? '#93c5fd' : isDone ? '#86efac' : '#e2e8f0'}`, color: isActive ? '#1d4ed8' : isDone ? '#15803d' : '#64748b', fontSize: '12px', fontWeight: 800 }}>
                        {sourceName}
                      </span>
                    )
                  }) : <span style={{ color: '#64748b', fontSize: '13px' }}>尚未收到源级别事件</span>}
                </div>
              </div>

              <div style={{ padding: '18px', borderRadius: '28px', background: '#ffffff', border: '1px solid #e5eaf0', boxShadow: '0 14px 38px rgba(15,23,42,0.06)' }}>
                <div style={{ color: '#64748b', fontSize: '12px', fontWeight: 850, letterSpacing: '0.08em', textTransform: 'uppercase' }}>Progress</div>
                <div style={{ marginTop: '14px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  {[
                    ['计划', rssQueueTotal],
                    ['成功', rssSuccessCount],
                    ['TTS 中', countByStatus(sections, 'running')],
                    ['等待', countByStatus(sections, 'ready')],
                  ].map(([label, value]) => (
                    <div key={label} style={{ padding: '13px', borderRadius: '18px', background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                      <div style={{ color: '#64748b', fontSize: '12px', fontWeight: 800 }}>{label}</div>
                      <div style={{ marginTop: '7px', color: '#0f172a', fontSize: '24px', lineHeight: 1, fontWeight: 900 }}>{value}</div>
                    </div>
                  ))}
                </div>
                <div style={{ marginTop: '14px', padding: '13px', borderRadius: '18px', background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                  <div style={{ color: '#64748b', fontSize: '12px', fontWeight: 800, marginBottom: '8px' }}>最近成功</div>
                  <div style={{ display: 'grid', gap: '8px' }}>
                    {recentSuccessfulRssResults.length > 0 ? recentSuccessfulRssResults.map((item) => (
                      <div key={`${item.name}-${item.status}`} style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', color: '#0f172a', fontSize: '13px' }}>
                        <span style={{ fontWeight: 800, wordBreak: 'break-word' }}>{item.name}</span>
                        <span style={{ color: '#15803d', whiteSpace: 'nowrap' }}>{item.status}</span>
                      </div>
                    )) : <div style={{ color: '#64748b', fontSize: '13px' }}>暂无成功记录</div>}
                  </div>
                </div>
              </div>
            </section>

            {groups.length > 0 && (
              <section style={{ padding: '18px', borderRadius: '28px', background: '#ffffff', border: '1px solid #e5eaf0', boxShadow: '0 14px 38px rgba(15,23,42,0.06)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center', marginBottom: '14px' }}>
                  <div>
                    <div style={{ color: '#64748b', fontSize: '12px', fontWeight: 850, letterSpacing: '0.08em', textTransform: 'uppercase' }}>Episode Groups</div>
                    <h2 style={{ margin: '6px 0 0', color: '#0f172a', fontSize: '22px', fontWeight: 850 }}>分组进度</h2>
                  </div>
                  <div style={{ color: '#64748b', fontWeight: 800, fontSize: '13px' }}>{activeGroupLabel ?? '等待分组'}</div>
                </div>
                <div style={{ display: 'grid', gap: '10px' }}>
                  {groups.map((group) => {
                    const groupSections = Object.values(sectionProgress).filter((section) => section.groupLabel === group.label).sort((a, b) => a.sectionNumber - b.sectionNumber)
                    const done = countByStatus(groupSections, 'done')
                    const total = groupSections.length
                    return (
                      <div key={group.label} style={{ padding: '14px', borderRadius: '20px', background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                          <div>
                            <div style={{ color: '#0f172a', fontWeight: 900, wordBreak: 'break-word' }}>{group.label}</div>
                            <div style={{ marginTop: '5px', color: '#64748b', fontSize: '13px' }}>
                              {group.itemCount ? `${group.itemCount} 条新闻` : '新闻数待定'} · 脚本 {group.scriptStatus === 'running' ? '生成中' : group.scriptStatus === 'done' ? '完成' : '未开始'} · 合并 {group.mergeStatus === 'done' ? '完成' : group.mergeStatus === 'running' ? '进行中' : '未开始'}
                            </div>
                          </div>
                          <div style={{ color: '#2563eb', fontWeight: 900 }}>{total > 0 ? `${done}/${total}` : '待解析'}</div>
                        </div>
                        {total > 0 && (
                          <div style={{ marginTop: '12px', height: '8px', borderRadius: '999px', background: '#e2e8f0', overflow: 'hidden' }}>
                            <div style={{ height: '100%', width: `${Math.round((done / total) * 100)}%`, background: 'linear-gradient(90deg, #2563eb, #22c55e)', borderRadius: '999px', transition: 'width 0.3s' }} />
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </section>
            )}
          </div>

          <aside style={{ position: 'sticky', top: '20px', display: 'grid', gap: '18px' }} className="generation-white-side">
            <section style={{ padding: '18px', borderRadius: '28px', background: '#ffffff', border: '1px solid #e5eaf0', boxShadow: '0 14px 38px rgba(15,23,42,0.06)' }}>
              <div style={{ color: '#64748b', fontSize: '12px', fontWeight: 850, letterSpacing: '0.08em', textTransform: 'uppercase' }}>Live Console</div>
              <div style={{ marginTop: '6px', color: '#0f172a', fontSize: '22px', fontWeight: 900 }}>流水线日志</div>
              <div style={{ marginTop: '12px', display: 'flex', justifyContent: 'space-between', gap: '10px', color: '#64748b', fontSize: '12px' }}>
                <span>{currentTaskId ? `task ${currentTaskId.slice(0, 8)}` : 'preview'}</span>
                <span>{terminalLines.length} lines</span>
              </div>
              <div
                ref={terminalContainerRef}
                onScroll={handleTerminalScroll}
                style={{ marginTop: '14px', height: '520px', overflowY: 'auto', padding: '14px', borderRadius: '20px', background: '#f8fafc', border: '1px solid #e2e8f0', fontFamily: 'var(--mono)', fontSize: '12px', lineHeight: 1.7 }}
              >
                {terminalLines.length > 0 ? terminalLines.map((line, index) => {
                  const trimmed = line.trim()
                  const isStage = /^\[[1-5]\/\d\]/.test(trimmed)
                  const isRss = /^\[RSS/.test(trimmed)
                  const isGroup = /^\[(组开始|Script Start|Script Done|Section Ready|TTS Start|TTS Done|TTS Wait|Merge Start|Group Done)\]/.test(trimmed)
                  const isError = trimmed.includes('失败') || trimmed.includes('错误')
                  const color = isError ? '#be123c' : isStage ? '#1d4ed8' : isRss ? '#047857' : isGroup ? '#6d28d9' : '#334155'
                  return (
                    <div key={`${index}-${line}`} style={{ display: 'grid', gridTemplateColumns: '38px minmax(0, 1fr)', gap: '10px', padding: '3px 0' }}>
                      <span style={{ color: '#94a3b8', textAlign: 'right', userSelect: 'none' }}>{String(index + 1).padStart(3, '0')}</span>
                      <span style={{ color, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{line || ' '}</span>
                    </div>
                  )
                }) : <div style={{ color: '#64748b' }}>启动任务后，SSE 日志会在这里逐行出现。</div>}
              </div>
            </section>
          </aside>
        </section>
      )}

      {!isGenerating && !terminalOutput && (
        <section style={{ marginTop: '18px', display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '14px' }} className="generation-white-empty-grid">
          {[
            ['1', '选择来源', '按订阅或手动 RSS 源启动生成。'],
            ['2', '实时追踪', 'SSE 会推送每个 RSS 源、分组、脚本和 TTS 状态。'],
            ['3', '自动入库', '完成后音频和脚本会保存到播客库。'],
          ].map(([index, title, desc]) => (
            <div key={title} style={{ padding: '18px', borderRadius: '24px', background: '#ffffff', border: '1px solid #e5eaf0', boxShadow: '0 12px 30px rgba(15,23,42,0.05)' }}>
              <div style={{ width: '34px', height: '34px', borderRadius: '999px', display: 'grid', placeItems: 'center', background: '#f1f5f9', color: '#0f172a', fontWeight: 900 }}>{index}</div>
              <div style={{ marginTop: '14px', color: '#0f172a', fontWeight: 900 }}>{title}</div>
              <div style={{ marginTop: '7px', color: '#64748b', fontSize: '13px', lineHeight: 1.6 }}>{desc}</div>
            </div>
          ))}
        </section>
      )}

      <style>{`
        @media (max-width: 1120px) {
          .generation-white-hero-grid,
          .generation-white-workbench,
          .generation-white-rss-grid {
            grid-template-columns: 1fr !important;
          }

          .generation-white-side {
            position: static !important;
          }
        }

        @media (max-width: 760px) {
          .generation-page-white {
            padding: 14px !important;
          }

          .generation-white-hero {
            padding: 18px !important;
            border-radius: 24px !important;
          }

          .generation-white-title {
            font-size: 38px !important;
          }

          .generation-white-metrics,
          .generation-white-stepper,
          .generation-white-empty-grid {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </main>
  )

  */

  /* Legacy dark layout kept out of compilation after the white redesign.
  return (
    <main className="generation-page" style={{ padding: '20px', maxWidth: '980px', margin: '0 auto', textAlign: 'left' }}>
      <section className="generation-hero" style={{ padding: '20px 22px', borderRadius: '22px', background: 'linear-gradient(135deg, #08060d, #23243a)', color: 'white', marginBottom: '16px' }}>
        <div style={{ fontSize: '11px', letterSpacing: '0.12em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.62)', fontWeight: 800 }}>Generation</div>
        <h1 className="generation-title" style={{ color: 'white', margin: '8px 0 8px', fontSize: '38px', lineHeight: 1.05 }}>生成播客</h1>
        <p style={{ color: 'rgba(255,255,255,0.74)', maxWidth: '620px', lineHeight: 1.6, fontSize: '15px' }}>
          可以直接按订阅中心保存的 RSS 源生成，也可以临时手动选择单个 RSS 源。任务启动后会通过实时日志展示脚本生成和 TTS 合成进度。
        </p>
      </section>

      <form onSubmit={handleSubmit} style={{ marginBottom: '16px', display: 'grid', gridTemplateColumns: 'minmax(240px, 1.1fr) minmax(210px, 1fr) auto', gap: '12px', alignItems: 'flex-end' }} className="generation-form">
        <div style={{ border: '1px solid var(--border)', borderRadius: '18px', padding: '13px 14px', background: '#fff' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-h)', fontWeight: 800 }}>
            <input type="checkbox" checked={useSubscriptions} onChange={(event) => setUseSubscriptions(event.target.checked)} />
            按我的订阅生成
          </label>
          <p style={{ marginTop: '6px', color: 'var(--text)', fontSize: '12px', lineHeight: 1.45 }}>
            已订阅 {preferences.subscription.rss_sources.length} 个内置源，{preferences.subscription.custom_rss.length} 个自定义源。
            {!user ? ' 请先登录后使用订阅偏好。' : ''}
          </p>
        </div>
        <div style={{ opacity: useSubscriptions ? 0.48 : 1 }}>
          <label style={{ display: 'block', marginBottom: '5px', color: 'var(--text-h)', fontWeight: 700 }}>手动 RSS 源</label>
          <select 
            value={rssSource} 
            onChange={(e) => setRssSource(e.target.value)}
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
        <button
          type="submit"
          disabled={isGenerating}
          style={{
            padding: '8px 18px',
            borderRadius: '999px',
            backgroundColor: isGenerating ? '#ccc' : 'var(--accent)',
            color: 'white',
            border: 'none',
            cursor: isGenerating ? 'not-allowed' : 'pointer',
            minHeight: '42px',
            fontWeight: 800,
          }}
        >
          {isGenerating ? '正在执行...' : useSubscriptions ? '按订阅生成' : '触发生成'}
        </button>
        {isGenerating && (
          <button type="button" onClick={handleCancel} style={{ padding: '8px 18px', borderRadius: '999px', backgroundColor: '#dc3545', color: 'white', border: 'none', cursor: 'pointer', minHeight: '42px', fontWeight: 800 }}>
            取消任务
          </button>
        )}
      </form>

      {(isGenerating || terminalOutput) && (
        <section style={{ marginTop: '16px', display: 'grid', gap: '12px' }}>
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.28 }}
            style={{
              padding: '16px',
              borderRadius: '20px',
              background: 'linear-gradient(180deg, #f8fbff, #f2f6fb)',
              border: '1px solid #d8e3f0',
              boxShadow: '0 18px 42px rgba(15, 23, 42, 0.08)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
              <div>
                <div style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#51606f', fontWeight: 800 }}>
                  Pipeline Stepper
                </div>
                <div style={{ marginTop: '6px', fontSize: '22px', fontWeight: 800, color: '#132238' }}>
                  4 步流水线实时追踪
                </div>
                <div style={{ marginTop: '8px', color: '#5a6a7b', fontSize: '14px', lineHeight: 1.6, maxWidth: '720px' }}>
                  不再只显示一个 loading 圈。这里会根据 SSE 实时日志，把抓取、策划、剧本生成和语音合成四个阶段逐步点亮。
                </div>
              </div>
              <div style={{ padding: '10px 14px', borderRadius: '999px', background: '#0f172a', color: '#e2e8f0', fontSize: '12px', fontWeight: 700 }}>
                {isGenerating ? 'AI 正在工作中' : '本轮任务已结束'}
              </div>
            </div>

            <div className="generation-stepper" style={{ marginTop: '16px', display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: '12px' }}>
              {pipelineSteps.map((step) => {
                const colors = getStepColors(step.status)

                return (
                  <div
                    key={step.id}
                    style={{
                      position: 'relative',
                      overflow: 'hidden',
                      borderRadius: '18px',
                      padding: '16px 14px 14px',
                      border: colors.border,
                      background: colors.background,
                      boxShadow: colors.glow,
                    }}
                  >
                    {step.status === 'active' && (
                      <motion.div
                        initial={{ opacity: 0.35, x: '-100%' }}
                        animate={{ opacity: 0.8, x: '120%' }}
                        transition={{ duration: 1.8, repeat: Infinity, ease: 'linear' }}
                        style={{
                          position: 'absolute',
                          inset: 0,
                          background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.14), transparent)',
                          pointerEvents: 'none',
                        }}
                      />
                    )}

                    <div style={{ position: 'relative', display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'flex-start' }}>
                      <div
                        style={{
                          width: '34px',
                          height: '34px',
                          borderRadius: '999px',
                          background: colors.badgeBackground,
                          color: colors.badgeColor,
                          display: 'grid',
                          placeItems: 'center',
                          fontSize: '14px',
                          fontWeight: 900,
                          flexShrink: 0,
                        }}
                      >
                        {step.status === 'done' ? '✓' : step.id}
                      </div>
                      <div style={{ fontSize: '11px', fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase', color: step.status === 'active' ? '#bfdbfe' : step.status === 'done' ? '#16a34a' : '#94a3b8' }}>
                        {step.status === 'done' ? 'Completed' : step.status === 'active' ? 'Running' : 'Pending'}
                      </div>
                    </div>
                    <div style={{ position: 'relative', marginTop: '14px', fontSize: '17px', fontWeight: 800, color: colors.titleColor }}>
                      {step.title}
                    </div>
                    <div style={{ position: 'relative', marginTop: '7px', color: colors.subtitleColor, fontSize: '13px', lineHeight: 1.55 }}>
                      {step.subtitle}
                    </div>
                  </div>
                )
              })}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '10px' }}
          >
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05, duration: 0.25 }}
              style={{ padding: '12px 14px', borderRadius: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', color: '#e2e8f0' }}
            >
              <div style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#94a3b8' }}>分组数</div>
              <motion.div
                key={Object.keys(groupProgress).length}
                initial={{ scale: 1.2 }}
                animate={{ scale: 1 }}
                transition={{ duration: 0.2 }}
                style={{ marginTop: '6px', fontSize: '24px', fontWeight: 800 }}
              >
                {groups.length}
              </motion.div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1, duration: 0.25 }}
              style={{ padding: '12px 14px', borderRadius: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', color: '#e2e8f0' }}
            >
              <div style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#94a3b8' }}>TTS 完成</div>
              <motion.div
                key={countByStatus(sections, 'done')}
                initial={{ scale: 1.2 }}
                animate={{ scale: 1 }}
                transition={{ duration: 0.2 }}
                style={{ marginTop: '6px', fontSize: '24px', fontWeight: 800 }}
              >
                {countByStatus(sections, 'done')}
              </motion.div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15, duration: 0.25 }}
              style={{ padding: '12px 14px', borderRadius: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', color: '#e2e8f0' }}
            >
              <div style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#94a3b8' }}>TTS 进行中</div>
              <motion.div
                key={countByStatus(sections, 'running')}
                initial={{ scale: 1.2 }}
                animate={{ scale: 1 }}
                transition={{ duration: 0.2 }}
                style={{ marginTop: '6px', fontSize: '24px', fontWeight: 800 }}
              >
                {countByStatus(sections, 'running')}
              </motion.div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, duration: 0.25 }}
              style={{ padding: '12px 14px', borderRadius: '10px', backgroundColor: '#0f172a', border: '1px solid #1e293b', color: '#e2e8f0' }}
            >
              <div style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#94a3b8' }}>等待中</div>
              <motion.div
                key={countByStatus(sections, 'ready')}
                initial={{ scale: 1.2 }}
                animate={{ scale: 1 }}
                transition={{ duration: 0.2 }}
                style={{ marginTop: '6px', fontSize: '24px', fontWeight: 800 }}
              >
                {countByStatus(sections, 'ready')}
              </motion.div>
            </motion.div>
          </motion.div>

          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.35fr) minmax(260px, 0.95fr)', gap: '12px' }} className="generation-rss-grid">
            <div style={{ padding: '16px', borderRadius: '16px', border: '1px solid #d6e4f2', background: 'linear-gradient(180deg, #081120, #10233d)', color: '#e2e8f0', boxShadow: '0 14px 36px rgba(15, 23, 42, 0.2)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#93c5fd', fontWeight: 800 }}>RSS Scanner</div>
                  <div style={{ marginTop: '6px', fontSize: '20px', fontWeight: 800 }}>正在爬取的源</div>
                </div>
                <div style={{ padding: '8px 12px', borderRadius: '999px', background: 'rgba(96,165,250,0.16)', color: '#bfdbfe', fontSize: '12px', fontWeight: 700 }}>
                  {rssQueueTotal > 0 ? `${rssCompletedCount}/${rssQueueTotal} 已完成` : '等待抓取计划'}
                </div>
              </div>

              <div style={{ marginTop: '14px', padding: '14px 16px', borderRadius: '14px', background: 'rgba(15, 23, 42, 0.72)', border: '1px solid rgba(125, 211, 252, 0.24)' }}>
                <div style={{ fontSize: '12px', color: '#7dd3fc', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Current Source</div>
                <div style={{ marginTop: '8px', fontSize: '22px', fontWeight: 800, color: '#f8fafc', wordBreak: 'break-word' }}>
                  {activeRssSource ?? (rssStage === 'done' ? 'RSS 抓取阶段已完成' : rssSourcesStarted.at(-1) ?? '等待后端返回抓取事件')}
                </div>
                <div style={{ marginTop: '8px', color: '#94a3b8', fontSize: '13px', lineHeight: 1.6 }}>
                  {activeRssSource
                    ? '一旦后端完成该源的抓取，这里会立刻切换到下一个源，并同步更新控制台。'
                    : rssStage === 'done'
                      ? '所有 RSS 源都已经抓取完成，流水线已进入后续阶段。'
                      : '当前还在等待第一批或下一批抓取结果返回。'}
                </div>
              </div>

              <div style={{ marginTop: '14px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {rssSourcesQueued.length > 0 ? rssSourcesQueued.map((sourceName) => {
                  const successfulItem = rssSourcesCompleted.find((item) => item.name === sourceName && item.status.includes('成功'))
                  const isDone = Boolean(successfulItem)
                  const isActive = activeRssSource === sourceName
                  return (
                    <div
                      key={sourceName}
                      style={{
                        padding: '8px 10px',
                        borderRadius: '999px',
                        fontSize: '12px',
                        border: isActive ? '1px solid #7dd3fc' : isDone ? '1px solid #86efac' : '1px solid rgba(148,163,184,0.25)',
                        background: isActive ? 'rgba(34, 211, 238, 0.12)' : isDone ? 'rgba(34,197,94,0.12)' : 'rgba(148,163,184,0.08)',
                        color: isActive ? '#67e8f9' : isDone ? '#bbf7d0' : '#cbd5e1',
                      }}
                    >
                      {isActive ? '>> ' : isDone ? 'OK ' : ''}
                      {sourceName}
                    </div>
                  )
                }) : (
                  <div style={{ color: '#94a3b8', fontSize: '13px' }}>SSE 尚未返回源级别抓取信息。</div>
                )}
              </div>
            </div>

            <div style={{ padding: '16px', borderRadius: '16px', border: '1px solid #dbe5f0', background: '#ffffff' }}>
              <div style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#64748b', fontWeight: 800 }}>RSS Summary</div>
              <div style={{ marginTop: '10px', display: 'grid', gap: '10px' }}>
                <div style={{ padding: '12px 14px', borderRadius: '14px', background: '#eff6ff', border: '1px solid #bfdbfe' }}>
                  <div style={{ color: '#4b5563', fontSize: '12px' }}>计划抓取</div>
                  <div style={{ marginTop: '4px', color: '#0f172a', fontWeight: 800, fontSize: '22px' }}>{rssQueueTotal}</div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '10px' }}>
                  <div style={{ padding: '12px 14px', borderRadius: '14px', background: '#f0fdf4', border: '1px solid #bbf7d0' }}>
                    <div style={{ color: '#4b5563', fontSize: '12px' }}>成功</div>
                    <div style={{ marginTop: '4px', color: '#166534', fontWeight: 800, fontSize: '20px' }}>{rssSuccessCount}</div>
                  </div>
                  <div style={{ padding: '12px 14px', borderRadius: '14px', background: '#eff6ff', border: '1px solid #bfdbfe' }}>
                    <div style={{ color: '#4b5563', fontSize: '12px' }}>已完成</div>
                    <div style={{ marginTop: '4px', color: '#1d4ed8', fontWeight: 800, fontSize: '20px' }}>{rssCompletedCount}</div>
                  </div>
                </div>
                <div style={{ padding: '12px 14px', borderRadius: '14px', background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                  <div style={{ color: '#4b5563', fontSize: '12px', marginBottom: '8px' }}>最近成功</div>
                  <div style={{ display: 'grid', gap: '8px' }}>
                    {recentSuccessfulRssResults.length > 0 ? recentSuccessfulRssResults.map((item) => (
                      <div key={`${item.name}-${item.status}`} style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center' }}>
                        <div style={{ color: '#0f172a', fontWeight: 700, fontSize: '13px', wordBreak: 'break-word' }}>{item.name}</div>
                        <div style={{ color: '#15803d', fontSize: '12px', whiteSpace: 'nowrap' }}>{item.status}</div>
                      </div>
                    )) : (
                      <div style={{ color: '#64748b', fontSize: '13px' }}>暂时还没有成功记录</div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '10px' }}>
            <div style={{ padding: '14px 16px', borderRadius: '10px', backgroundColor: '#f4f7fb', border: '1px solid #d7e3f1' }}>
              <div style={{ fontSize: '12px', color: '#5c6b7a', textTransform: 'uppercase', letterSpacing: '0.08em' }}>RSS 抓取</div>
              <div style={{ marginTop: '6px', fontSize: '18px', fontWeight: 700, color: '#17324d' }}>
                {rssStage === 'idle' ? '等待中' : rssStage === 'running' ? `并发抓取中 · ${rssCompletedCount}/${rssQueueTotal || rssSourcesQueued.length || '?'} 完成` : '已完成'}
              </div>
            </div>

            <div style={{ padding: '14px 16px', borderRadius: '10px', backgroundColor: '#f8f5ff', border: '1px solid #dfd6f7' }}>
              <div style={{ fontSize: '12px', color: '#6a5f8f', textTransform: 'uppercase', letterSpacing: '0.08em' }}>当前分组</div>
              <div style={{ marginTop: '6px', fontSize: '16px', fontWeight: 700, color: '#33265c', wordBreak: 'break-word' }}>
                {activeGroupLabel ?? '尚未开始'}
              </div>
            </div>
          </div>

          {groups.length > 0 && (
            <div style={{ display: 'grid', gap: '12px' }}>
              {groups.map((group) => {
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
                          <motion.div
                            key={section.key}
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.25 }}
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
                              transition: 'background-color 0.3s, border-color 0.3s',
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
                          </motion.div>
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
          marginTop: '16px', 
          backgroundColor: '#050816', 
          borderRadius: '16px', 
          boxShadow: '0 18px 48px rgba(2,6,23,0.45)',
          overflow: 'hidden',
          border: '1px solid rgba(100,116,139,0.3)'
        }}>
          <div style={{ 
            background: 'linear-gradient(180deg, #111827, #0f172a)', 
            padding: '10px 15px', 
            display: 'flex', 
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
            borderBottom: '1px solid rgba(148,163,184,0.18)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
              <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#ff5f56' }}></div>
              <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#ffbd2e' }}></div>
              <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#27c93f' }}></div>
              <span style={{ color: '#cbd5e1', fontSize: '12px', marginLeft: '10px', fontFamily: 'monospace', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                podcast-pipeline://generation/{currentTaskId?.slice(0, 8) ?? 'preview'}
              </span>
            </div>
            <div style={{ color: '#67e8f9', fontFamily: 'monospace', fontSize: '12px', whiteSpace: 'nowrap' }}>
              {terminalLines.length} lines streamed
            </div>
          </div>

          <div
            ref={terminalContainerRef}
            onScroll={handleTerminalScroll}
            style={{ 
              padding: '16px', 
              height: '420px', 
              overflowY: 'auto', 
              fontFamily: '"Fira Code", "Source Code Pro", Consolas, Monaco, monospace', 
              fontSize: '13px', 
              lineHeight: '1.65',
              color: '#e5eef9',
              background: 'radial-gradient(circle at top, rgba(14,165,233,0.1), transparent 28%), linear-gradient(180deg, #050816, #020617)'
            }}>
            <div style={{ display: 'grid', gap: '6px' }}>
              {terminalLines.map((line, index) => {
                const trimmed = line.trim()
                const isStage = /^\[[1-4]\/4\]/.test(trimmed)
                const isGroup = /^\[(组开始|Script Start|Script Done|Section Ready|TTS Start|TTS Done|TTS Wait|Merge Start|Group Done)\]/.test(trimmed)
                const isError = trimmed.includes('❌') || trimmed.includes('失败') || trimmed.includes('错误')
                const lineColor = isError ? '#fca5a5' : isStage ? '#67e8f9' : isGroup ? '#c4b5fd' : '#e5eef9'
                const prefixColor = isError ? '#ef4444' : isStage ? '#06b6d4' : isGroup ? '#8b5cf6' : '#334155'

                return (
                  <div key={`${index}-${line}`} style={{ display: 'grid', gridTemplateColumns: '52px minmax(0, 1fr)', gap: '12px', alignItems: 'start' }}>
                    <div style={{ color: prefixColor, textAlign: 'right', userSelect: 'none', opacity: 0.9 }}>
                      {String(index + 1).padStart(3, '0')}
                    </div>
                    <div style={{ color: lineColor, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                      {line || ' '}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}
      <style>{`
        @media (max-width: 1180px) {
          .generation-stepper {
            grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
          }
        }

        @media (max-width: 1100px) {
          .generation-form {
            grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) !important;
          }

          .generation-rss-grid {
            grid-template-columns: 1fr !important;
          }
        }

        @media (max-width: 920px) {
          .generation-page {
            padding: 16px !important;
          }

          .generation-form {
            grid-template-columns: 1fr !important;
          }
        }

        @media (max-width: 560px) {
          .generation-stepper {
            grid-template-columns: 1fr !important;
          }

          .generation-page {
            padding: 12px !important;
          }

          .generation-hero {
            padding: 16px !important;
            border-radius: 18px !important;
          }

          .generation-title {
            font-size: 30px !important;
          }
        }
      `}</style>
    </main>
  )
  */
}
