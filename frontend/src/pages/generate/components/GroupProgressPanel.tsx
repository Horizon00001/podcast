import { motion } from 'framer-motion'

import { countByStatus } from '../progressParsers'
import type { GroupProgress, SectionProgress } from '../progressTypes'

interface GroupProgressPanelProps {
  groupProgress: Record<string, GroupProgress>
  sectionProgress: Record<string, SectionProgress>
}

export function GroupProgressPanel({ groupProgress, sectionProgress }: GroupProgressPanelProps) {
  const groups = Object.values(groupProgress)

  if (groups.length === 0) {
    return null
  }

  return (
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
  )
}
