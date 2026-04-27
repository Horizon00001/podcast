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
        padding: isDetail ? '16px 20px' : '12px',
        ...style,
      }}
    >
      {scriptLines.map((line, idx) => {
        const isHost = line.speaker === 'host' || line.speaker === 'A'
        return (
          <div
            key={line.id}
            style={{
              display: 'flex',
              flexDirection: isHost ? 'row' : 'row-reverse',
              alignItems: 'flex-start',
              marginBottom: isDetail ? '24px' : '16px',
            }}
          >
            <motion.div
              onClick={() => handleLineClick(line.startTime)}
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              animate={{
                opacity: idx === activeIndex ? 1 : 0.65,
                y: idx === activeIndex ? 0 : 0,
              }}
              transition={{ duration: 0.25 }}
              style={{
                maxWidth: '82%',
                padding: isDetail ? '14px 18px' : '10px 14px',
                borderRadius: isHost 
                  ? (isDetail ? '4px 20px 20px 20px' : '4px 16px 16px 16px') 
                  : (isDetail ? '20px 4px 20px 20px' : '16px 4px 16px 16px'),
                cursor: 'pointer',
                background: idx === activeIndex
                  ? isDetail
                    ? 'rgba(255,255,255,0.98)'
                    : 'var(--accent-bg)'
                  : isDetail
                    ? 'rgba(255,255,255,0.6)'
                    : 'var(--code-bg)',
                boxShadow: idx === activeIndex
                  ? isDetail
                    ? '0 12px 28px rgba(8, 6, 13, 0.08)'
                    : '0 4px 12px rgba(0, 0, 0, 0.15)'
                  : isDetail
                    ? '0 2px 8px rgba(8, 6, 13, 0.04)'
                    : 'none',
                border: isDetail 
                  ? idx === activeIndex ? '1px solid rgba(8, 6, 13, 0.12)' : '1px solid rgba(8, 6, 13, 0.05)'
                  : 'none',
                transition: 'background 0.2s, box-shadow 0.2s, border 0.2s',
                textAlign: 'left',
              }}
            >
              <div style={{ 
                fontSize: '12px', 
                fontWeight: 700, 
                marginBottom: '6px', 
                color: idx === activeIndex ? (isDetail ? '#111111' : 'var(--accent)') : '#8b8494', 
                letterSpacing: '0.04em' 
              }}>
                {isHost ? '主持人' : '嘉宾'}
              </div>
              <p style={{ 
                margin: 0, 
                lineHeight: isDetail ? 1.7 : 1.5, 
                fontSize: isDetail ? '16px' : '14px', 
                color: isDetail ? '#1d1d1f' : 'inherit' 
              }}>
                {line.text}
              </p>
            </motion.div>
          </div>
        )
      })}
    </div>
  )
}
