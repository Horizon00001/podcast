import { useEffect, useRef, useState } from 'react'
import type { ScriptLine } from '../types/podcast'

interface TimelineHighlighterProps {
  scriptLines: ScriptLine[]
  currentTime: number        // 当前播放时间（秒）
  onSeek: (time: number) => void  // 跳转函数
}

export function TimelineHighlighter({ scriptLines, currentTime, onSeek }: TimelineHighlighterProps) {
  const [activeIndex, setActiveIndex] = useState(-1)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const currentMs = currentTime * 1000
    const index = scriptLines.findIndex(
      line => currentMs >= line.startTime && currentMs <= line.endTime
    )
    if (index !== activeIndex) {
      setActiveIndex(index)
      if (containerRef.current && index >= 0) {
        const activeEl = containerRef.current.children[index] as HTMLElement
        activeEl?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    }
  }, [currentTime, scriptLines, activeIndex])

  const handleLineClick = (startTime: number) => {
    onSeek(startTime / 1000)
  }

  if (!scriptLines.length) {
    return <p style={{ padding: '16px', textAlign: 'center' }}>暂无脚本数据，请先生成播客。</p>
  }

  return (
    <div ref={containerRef} style={{ maxHeight: '500px', overflowY: 'auto', padding: '8px' }}>
      {scriptLines.map((line, idx) => (
        <div
          key={line.id}
          onClick={() => handleLineClick(line.startTime)}
          style={{
            padding: '12px',
            margin: '8px 0',
            borderRadius: '12px',
            cursor: 'pointer',
            transition: 'all 0.2s',
            background: idx === activeIndex ? 'var(--accent-bg)' : 'var(--code-bg)',
            borderLeft: idx === activeIndex ? `4px solid var(--accent)` : '4px solid transparent'
          }}
        >
          <div style={{ fontSize: '12px', fontWeight: 'bold', marginBottom: '6px', color: 'var(--accent)' }}>
            {line.speaker === 'host' ? '🎙️ 主持人' : '🎧 嘉宾'}
          </div>
          <p style={{ margin: 0, lineHeight: 1.5 }}>{line.text}</p>
        </div>
      ))}
    </div>
  )
}