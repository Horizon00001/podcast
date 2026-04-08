import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { ScriptPanel } from '../components/ScriptPanel'
import { TimelineHighlighter } from '../components/TimelineHighlighter'
import { api } from '../services/api'
import type { Podcast } from '../types/podcast'
import { usePlayer } from '../context/PlayerContext'

export function PodcastDetailPage() {
  const { id } = useParams()
  const [podcast, setPodcast] = useState<Podcast | null>(null)
  const [error, setError] = useState('')
  const { currentPodcast, isPlaying, play, toggle, currentTime } = usePlayer()

  useEffect(() => {
    if (!id) return
    api
      .getPodcast(Number(id))
      .then(setPodcast)
      .catch((e) => setError((e as Error).message))
  }, [id])

  if (error) {
    return <p style={{ padding: '40px', textAlign: 'center' }}>加载失败：{error}</p>
  }
  if (!podcast) {
    return <p style={{ padding: '40px', textAlign: 'center' }}>加载中...</p>
  }

  const isCurrent = currentPodcast?.id === podcast.id;

  const handlePlay = () => {
    if (isCurrent) {
      toggle()
    } else {
      play(podcast)
    }
  }

  return (
    <main style={{ padding: '40px', maxWidth: '1000px', margin: '0 auto', textAlign: 'left' }}>
      <div style={{ display: 'flex', gap: '40px', marginBottom: '40px' }}>
        <div style={{
          width: '240px',
          height: '240px',
          background: 'var(--accent-bg)',
          borderRadius: '12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '100px',
          boxShadow: 'var(--shadow)'
        }}>
          🎙️
        </div>
        <div style={{ flexGrow: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end' }}>
          <h1 style={{ fontSize: '48px', margin: '0 0 16px', letterSpacing: '-1px' }}>{podcast.title}</h1>
          <p style={{ fontSize: '18px', color: 'var(--text)', marginBottom: '24px' }}>{podcast.summary}</p>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <button
              onClick={handlePlay}
              style={{
                background: 'var(--accent)',
                color: 'white',
                border: 'none',
                borderRadius: '30px',
                padding: '12px 32px',
                fontSize: '18px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                transition: 'transform 0.2s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
              onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
            >
              {isCurrent && isPlaying ? '⏸️ 暂停' : '▶️ 播放'}
            </button>
          </div>
        </div>
      </div>

      <div style={{ borderTop: '1px solid var(--border)', paddingTop: '40px' }}>
        <h2 style={{ marginBottom: '24px' }}>播客脚本</h2>
        <ScriptPanel scriptPath={podcast.script_path} />
        <TimelineHighlighter currentTime={isCurrent ? currentTime : 0} />
      </div>
    </main>
  )
}
