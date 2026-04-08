import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import type { Podcast } from '../types/podcast'
import { usePlayer } from '../context/PlayerContext'

const CATEGORIES = [
  { id: 'all', name: '全部', icon: '📻' },
  { id: 'technology', name: '科技', icon: '💻' },
  { id: 'finance', name: '财经', icon: '📈' },
  { id: 'sports', name: '体育', icon: '⚽' },
  { id: 'entertainment', name: '娱乐', icon: '🎬' },
  { id: 'health', name: '健康', icon: '💪' },
]

export function PodcastListPage() {
  const [podcasts, setPodcasts] = useState<Podcast[]>([])
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [error, setError] = useState('')
  const { currentPodcast, isPlaying, play, toggle } = usePlayer()

  useEffect(() => {
    api.listPodcasts()
      .then(setPodcasts)
      .catch((e) => setError((e as Error).message))
  }, [])

  const filteredPodcasts = selectedCategory === 'all'
    ? podcasts
    : podcasts.filter(p => p.category === selectedCategory)

  const handlePlay = (podcast: Podcast) => {
    if (currentPodcast?.id === podcast.id) {
      toggle()
    } else {
      play(podcast)
    }
  }

  return (
    <main style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '32px', marginBottom: '24px' }}>我的播客库</h1>
      
      {/* 筛选栏 */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '12px',
        marginBottom: '32px',
        paddingBottom: '16px',
        borderBottom: '1px solid var(--border)'
      }}>
        {CATEGORIES.map(cat => (
          <button
            key={cat.id}
            onClick={() => setSelectedCategory(cat.id)}
            style={{
              padding: '8px 16px',
              borderRadius: '40px',
              border: `1px solid ${selectedCategory === cat.id ? 'var(--accent)' : 'var(--border)'}`,
              background: selectedCategory === cat.id ? 'var(--accent-bg)' : 'transparent',
              color: selectedCategory === cat.id ? 'var(--accent)' : 'var(--text)',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '14px'
            }}
          >
            <span>{cat.icon}</span> {cat.name}
          </button>
        ))}
      </div>

      {error && <p style={{ color: 'red' }}>加载失败：{error}</p>}

      {/* 卡片网格 */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
        gap: '20px'
      }}>
        {filteredPodcasts.map(podcast => {
          const isActive = currentPodcast?.id === podcast.id
          return (
            <div
              key={podcast.id}
              style={{
                border: '1px solid var(--border)',
                borderRadius: '16px',
                padding: '16px',
                background: isActive ? 'var(--accent-bg)' : 'var(--bg)',
                transition: 'all 0.2s'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                <div style={{
                  width: '48px',
                  height: '48px',
                  background: 'var(--accent-bg)',
                  borderRadius: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '24px'
                }}>
                  🎙️
                </div>
                <Link
                  to={`/podcasts/${podcast.id}`}
                  style={{
                    fontWeight: 600,
                    color: 'var(--text-h)',
                    textDecoration: 'none',
                    flex: 1,
                    fontSize: '16px'
                  }}
                >
                  {podcast.title}
                </Link>
              </div>
              <p style={{ fontSize: '14px', color: 'var(--text)', marginBottom: '12px', lineHeight: 1.4 }}>
                {podcast.summary}
              </p>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '12px', color: 'var(--text)' }}>
                  {new Date(podcast.published_at).toLocaleDateString()}
                </span>
                <button
                  onClick={() => handlePlay(podcast)}
                  style={{
                    background: isActive ? 'var(--accent)' : 'transparent',
                    color: isActive ? 'white' : 'var(--accent)',
                    border: `1px solid var(--accent)`,
                    borderRadius: '20px',
                    padding: '6px 12px',
                    cursor: 'pointer',
                    fontSize: '12px'
                  }}
                >
                  {isActive && isPlaying ? '暂停' : '播放'}
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {filteredPodcasts.length === 0 && (
        <div style={{ padding: '64px', textAlign: 'center', color: 'var(--text)' }}>
          暂无播客，请去生成或调整筛选条件。
        </div>
      )}
    </main>
  )
}