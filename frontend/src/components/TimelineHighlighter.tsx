import type { CSSProperties, UIEvent } from 'react'
import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import type { ScriptLine } from '../types/podcast'

interface TimelineHighlighterProps {
  scriptLines: ScriptLine[]
  currentTime: number        // 当前播放时间（秒）
  onSeek: (time: number) => void  // 跳转函数
  autoFollow?: boolean
  onManualScroll?: () => void
  variant?: 'default' | 'detail'
  style?: CSSProperties
}

export function TimelineHighlighter({
  scriptLines,
  currentTime,
  onSeek,
  autoFollow = true,
  onManualScroll,
  variant = 'default',
  style,
}: TimelineHighlighterProps) {
  const [activeIndex, setActiveIndex] = useState(-1)
  const containerRef = useRef<HTMLDivElement>(null)

  const isDetail = variant === 'detail'

  useEffect(() => {
    const currentMs = currentTime * 1000
    const index = scriptLines.findIndex(
      line => currentMs >= line.startTime && currentMs <= line.endTime
    )
    if (index !== activeIndex) {
      setActiveIndex(index)
      if (autoFollow && containerRef.current && index >= 0) {
        const activeEl = containerRef.current.children[index] as HTMLElement
        activeEl?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    }
  }, [currentTime, scriptLines, activeIndex, autoFollow])

  const handleLineClick = (startTime: number) => {
    onSeek(startTime / 1000)
  }

  const handleScroll = (event: UIEvent<HTMLDivElement>) => {
    if (!onManualScroll) return
    if (!event.isTrusted) return
    onManualScroll()
  }

  if (!scriptLines.length) {
    return <p style={{ padding: '16px', textAlign: 'center' }}>暂无脚本数据，请先生成播客。</p>
  }

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      style={{
        maxHeight: isDetail ? '100%' : '500px',
        overflowY: 'auto',
        padding: isDetail ? '0 4px 0 0' : '8px',
        ...style,
      }}
    >
      {scriptLines.map((line, idx) => (
        <motion.div
          key={line.id}
          onClick={() => handleLineClick(line.startTime)}
          whileHover={{ scale: isDetail ? 1 : 1.01 }}
          whileTap={{ scale: 0.99 }}
          animate={{
            boxShadow: idx === activeIndex
              ? isDetail
                ? '0 12px 28px rgba(8, 6, 13, 0.08)'
                : '0 0 12px rgba(0, 0, 0, 0.25)'
              : '0 0 0px rgba(0, 0, 0, 0)'
          }}
          transition={{ duration: 0.25 }}
          style={{
            padding: isDetail ? '18px 20px' : '12px',
            margin: isDetail ? '0 0 12px' : '8px 0',
            borderRadius: isDetail ? '20px' : '12px',
            cursor: 'pointer',
            background: idx === activeIndex
              ? isDetail
                ? 'rgba(255,255,255,0.92)'
                : 'var(--accent-bg)'
              : isDetail
                ? 'rgba(255,255,255,0.72)'
                : 'var(--code-bg)',
            borderLeft: idx === activeIndex
              ? isDetail
                ? '3px solid #111111'
                : `4px solid var(--accent)`
              : isDetail
                ? '3px solid transparent'
                : '4px solid transparent',
            border: isDetail ? '1px solid rgba(8, 6, 13, 0.06)' : 'none',
            transition: 'background 0.2s, border-left 0.2s, border 0.2s',
          }}
        >
          <div style={{ fontSize: '12px', fontWeight: 'bold', marginBottom: '8px', color: isDetail ? '#5f5967' : 'var(--accent)', letterSpacing: isDetail ? '0.04em' : undefined, textTransform: isDetail ? 'uppercase' : undefined }}>
            {line.speaker === 'host' ? '主持人' : '嘉宾'}
          </div>
          <p style={{ margin: 0, lineHeight: isDetail ? 1.8 : 1.5, fontSize: isDetail ? '16px' : 'inherit', color: isDetail ? '#1d1d1f' : 'inherit' }}>{line.text}</p>
        </motion.div>
      ))}
    </div>
  )
}
