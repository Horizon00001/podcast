import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import type { Podcast } from '../types/podcast'
import { usePlayer } from '../context/PlayerContext'
import { useUser } from '../context/UserContext'
import { useFavorites } from '../context/FavoritesContext'

const CATEGORIES = [
  { id: 'all', name: '全部', icon: '📻' },
  { id: 'technology', name: '科技', icon: '💻' },
  { id: 'finance', name: '财经', icon: '📈' },
  { id: 'sports', name: '体育', icon: '⚽' },
  { id: 'entertainment', name: '娱乐', icon: '🎬' },
  { id: 'health', name: '健康', icon: '💪' },
]

export function PodcastListPage() {
  const {isFavorite, toggleFavorite } = useFavorites();
  const [podcasts, setPodcasts] = useState<Podcast[]>([])
  const [recommendedIds, setRecommendedIds] = useState<number[]>([])
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [error, setError] = useState('')
  const { currentPodcast, isPlaying, play, toggle, reportAction } = usePlayer()
  const { user, loading: userLoading } = useUser()

  useEffect(() => {
    api.listPodcasts()
      .then(setPodcasts)
      .catch((e) => setError((e as Error).message))
  }, [])

  useEffect(() => {
    if (!user) return
    api.getRecommendations(user.id)
      .then((response) => setRecommendedIds(response.items.map((item) => item.podcast_id)))
      .catch((e) => setError((e as Error).message))
  }, [user])

  const filteredPodcasts = selectedCategory === 'all'
    ? podcasts
    : podcasts.filter(p => p.category === selectedCategory)

  const handlePlay = (podcast: Podcast) => {
    if (currentPodcast?.id === podcast.id) {
      toggle()
    } else {
      play(podcast)
      if (user) {
        void reportAction('play', podcast, { listen_duration_ms: 0, progress_pct: 0 })
      }
    }
  }

  const handleAction = (podcastId: number, action: 'like' | 'favorite' | 'skip') => {
    if (!user) return
    const podcast = podcasts.find((item) => item.id === podcastId)
    const result = reportAction(action, podcast, { listen_duration_ms: 0, progress_pct: action === 'skip' ? 0 : 0 })
    if (result) {
      void result
        .then(() => api.getRecommendations(user.id))
        .then((response) => setRecommendedIds(response.items.map((item) => item.podcast_id)))
        .catch((e) => setError((e as Error).message))
    }
  }

  const recommendedPodcasts = recommendedIds
    .map((id) => podcasts.find((podcast) => podcast.id === id))
    .filter((podcast): podcast is Podcast => Boolean(podcast))

  return (
    <main style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '32px', marginBottom: '24px' }}>我的播客库</h1>

      <div style={{ marginBottom: '20px', color: 'var(--text)' }}>
        {userLoading ? '正在同步用户身份...' : `当前推荐用户：${user?.username ?? '未设置'}`}
      </div>

      {recommendedPodcasts.length > 0 && (
        <section style={{ marginBottom: '28px' }}>
          <h2 style={{ fontSize: '20px', marginBottom: '12px' }}>为你推荐</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '16px' }}>
            {recommendedPodcasts.slice(0, 6).map((podcast) => (
              <div
                key={`rec-${podcast.id}`}
                style={{
                  border: '1px solid var(--border)',
                  borderRadius: '14px',
                  padding: '14px',
                  background: 'var(--accent-bg)',
                }}
              >
                <Link
                  to={`/podcasts/${podcast.id}`}
                  style={{ fontWeight: 700, color: 'var(--text-h)', textDecoration: 'none' }}
                >
                  {podcast.title}
                </Link>
                <p style={{ fontSize: '13px', margin: '8px 0', color: 'var(--text)' }}>{podcast.summary}</p>
                <button
                  onClick={() => handlePlay(podcast)}
                  style={{
                    background: 'var(--accent)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '20px',
                    padding: '6px 12px',
                    cursor: 'pointer',
                    fontSize: '12px',
                  }}
                >
                  立即播放
                </button>
              </div>
            ))}
          </div>
        </section>
      )}
      
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
                <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                  <button
                    onClick={() => handleAction(podcast.id, 'like')}
                    style={{ border: '1px solid var(--border)', background: 'transparent', borderRadius: '20px', padding: '4px 8px', cursor: 'pointer' }}
                  >
                    👍
                  </button>
                  <button
                    onClick={() => toggleFavorite(podcast)}
                    style={{ border: '1px solid var(--border)', background: 'transparent', borderRadius: '20px', padding: '4px 8px', cursor: 'pointer' }}
  >
                    {isFavorite(podcast.id) ? '❤️' : '🤍'}
                  </button>
                  <button
                    onClick={() => handleAction(podcast.id, 'skip')}
                    style={{ border: '1px solid var(--border)', background: 'transparent', borderRadius: '20px', padding: '4px 8px', cursor: 'pointer' }}
                  >
                    ⏭️
                  </button>
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
