import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { TimelineHighlighter } from '../components/TimelineHighlighter'
import { api } from '../services/api'
import type { Podcast, ScriptLine } from '../types/podcast'
import { usePlayer } from '../context/PlayerContext'
import { useUser } from '../context/UserContext'

export function PodcastDetailPage() {
  const { id } = useParams()
  const [podcast, setPodcast] = useState<Podcast | null>(null)
  const [scriptLines, setScriptLines] = useState<ScriptLine[]>([])
  const [error, setError] = useState('')
  const { currentPodcast, isPlaying, play, toggle, currentTime, seek } = usePlayer()
  const { user } = useUser()

  useEffect(() => {
    if (!id) return
    api.getPodcast(Number(id))
      .then(async (pod) => {
        setPodcast(pod)
        try {
          const lines = await api.getPodcastScript(Number(id))
          setScriptLines(lines)
        } catch {
          setScriptLines([])
        }
      })
      .catch((e) => setError((e as Error).message))
  }, [id])

  if (error) return <p style={{ padding: '40px', textAlign: 'center' }}>加载失败：{error}</p>
  if (!podcast) return <p style={{ padding: '40px', textAlign: 'center' }}>加载中...</p>

  const isCurrent = currentPodcast?.id === podcast.id

  const handlePlay = () => {
    if (isCurrent) {
      toggle()
    } else {
      play(podcast)
      if (user) {
        void api.reportInteraction({ user_id: user.id, podcast_id: podcast.id, action: 'play' })
      }
    }
  }

  return (
    <main style={{ padding: '40px', maxWidth: '1000px', margin: '0 auto', textAlign: 'left' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '40px', marginBottom: '40px' }}>
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
        <div style={{ flexGrow: 1 }}>
          <h1 style={{ fontSize: '48px', margin: '0 0 16px', letterSpacing: '-1px' }}>{podcast.title}</h1>
          <p style={{ fontSize: '18px', color: 'var(--text)', marginBottom: '24px' }}>{podcast.summary}</p>
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
              cursor: 'pointer'
            }}
          >
            {isCurrent && isPlaying ? '⏸️ 暂停' : '▶️ 播放'}
          </button>
        </div>
      </div>

      <div style={{ borderTop: '1px solid var(--border)', paddingTop: '40px' }}>
        <h2 style={{ marginBottom: '24px' }}>播客脚本（点击句子可跳转）</h2>
        <TimelineHighlighter 
          scriptLines={scriptLines} 
          currentTime={isCurrent ? currentTime : 0} 
          onSeek={seek} 
        />
      </div>
    </main>
  )
}
