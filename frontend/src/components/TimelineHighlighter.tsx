interface TimelineHighlighterProps {
  currentTime?: number
}

export function TimelineHighlighter({ currentTime = 0 }: TimelineHighlighterProps) {
  return (
    <section>
      <h3>脚本同步高亮占位</h3>
      <p>当前播放时间：{currentTime.toFixed(1)}s</p>
    </section>
  )
}
