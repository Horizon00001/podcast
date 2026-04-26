import { useEffect, useRef } from 'react'

import { api } from '../../services/api'
import type { GenerationEventPayload } from './progressTypes'

interface UseGenerationStreamOptions {
  currentTaskId: string | null
  isGenerating: boolean
  appendOutput: (text: string) => void
  onLog: (chunk: string) => void
  onEvent: (event: GenerationEventPayload) => void
  onFinish: () => void
}

export function useGenerationStream(options: UseGenerationStreamOptions) {
  const { currentTaskId, isGenerating, appendOutput, onLog, onEvent, onFinish } = options
  const eventSourceRef = useRef<EventSource | null>(null)
  const isGeneratingRef = useRef(isGenerating)
  const currentTaskIdRef = useRef(currentTaskId)

  useEffect(() => {
    isGeneratingRef.current = isGenerating
  }, [isGenerating])

  useEffect(() => {
    currentTaskIdRef.current = currentTaskId
  }, [currentTaskId])

  function cleanupEventSource() {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
  }

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
          appendOutput(data[1])
          onLog(data[1])
        } else if (data[0] === 'event') {
          onEvent(data[1] as GenerationEventPayload)
        } else if (data[0] === 'status') {
          const status = data[1]
          const statusMessage = data[2]

          if (status === 'succeeded') {
            appendOutput(`\n\n任务全部完成。\n`)
            onFinish()
            cleanupEventSource()
          } else if (status === 'failed') {
            appendOutput(`\n\n任务失败: ${statusMessage}\n`)
            onFinish()
            cleanupEventSource()
          } else if (status === 'cancelled') {
            appendOutput(`\n\n任务已取消\n`)
            onFinish()
            cleanupEventSource()
          }
        } else if (data[0] === 'error') {
          appendOutput(`\n系统错误: ${data[1]}\n`)
          onFinish()
          cleanupEventSource()
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
          startListeningToLogs(currentTaskIdRef.current)
        }
      }, 3000)
    }
  }

  useEffect(() => {
    return () => {
      cleanupEventSource()
    }
  }, [])

  return {
    cleanupEventSource,
    startListeningToLogs,
  }
}
