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

const ONBOARDED_KEY = 'podcast_onboarded'
const PREFERENCE_CATEGORIES = CATEGORIES.filter(c => c.id !== 'all')

export function PodcastListPage() {
  const {isFavorite, toggleFavorite } = useFavorites();
  const [podcasts, setPodcasts] = useState<Podcast[]>([])
  const [recommendedIds, setRecommendedIds] = useState<number[]>([])
  const [recommendationRequestId, setRecommendationRequestId] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [error, setError] = useState('')
  const [strategy, setStrategy] = useState('')
  const [showPrefModal, setShowPrefModal] = useState(false)
  const [isEditingPrefs, setIsEditingPrefs] = useState(false)
  const [pickedTags, setPickedTags] = useState<string[]>([])
  const [saving, setSaving] = useState(false)
  const { currentPodcast, isPlaying, play, toggle, reportAction, setRecommendationRequestId: setPlayerRecommendationRequestId } = usePlayer()
  const { user, loading: userLoading } = useUser()

  useEffect(() => {
    api.listPodcasts()
      .then(setPodcasts)
      .catch((e) => setError((e as Error).message))
  }, [])

  useEffect(() => {
    if (!user) return
    api.getRecommendations(user.id)
      .then((response) => {
        setRecommendedIds(response.items.map((item) => item.podcast_id))
        setRecommendationRequestId(response.request_id)
        setPlayerRecommendationRequestId(response.request_id)
        setStrategy(response.strategy)
        if (response.strategy === 'cold-start' && !localStorage.getItem(ONBOARDED_KEY)) {
          setShowPrefModal(true)
          setIsEditingPrefs(false)
        }
      })
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
        void reportAction('play', podcast, { listen_duration_ms: 0, progress_pct: 0, recommendation_request_id: recommendationRequestId })
      }
    }
  }

  const handleAction = (podcastId: number, action: 'like' | 'favorite' | 'skip') => {
    if (!user) return
    const podcast = podcasts.find((item) => item.id === podcastId)
    const result = reportAction(action, podcast, {
      listen_duration_ms: 0,
      progress_pct: action === 'skip' ? 0 : 0,
      recommendation_request_id: recommendationRequestId,
    })
    if (result) {
      void result
        .then(() => api.getRecommendations(user.id))
        .then((response) => {
          setRecommendedIds(response.items.map((item) => item.podcast_id))
          setRecommendationRequestId(response.request_id)
          setPlayerRecommendationRequestId(response.request_id)
          setStrategy(response.strategy)
        })
        .catch((e) => setError((e as Error).message))
    }
  }

  const toggleTag = (tagId: string) => {
    setPickedTags((prev) =>
      prev.includes(tagId) ? prev.filter((t) => t !== tagId) : [...prev, tagId]
    )
  }

  const handleSavePreferences = async () => {
    if (!user || pickedTags.length === 0) return
    setSaving(true)
    try {
      await api.setPreferences(user.id, pickedTags)
      localStorage.setItem(ONBOARDED_KEY, '1')
      setShowPrefModal(false)
      const resp = await api.getRecommendations(user.id)
      setRecommendedIds(resp.items.map((item) => item.podcast_id))
      setRecommendationRequestId(resp.request_id)
      setPlayerRecommendationRequestId(resp.request_id)
      setStrategy(resp.strategy)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  const handleSkipOnboarding = () => {
    localStorage.setItem(ONBOARDED_KEY, '1')
    setShowPrefModal(false)
  }

  const handleOpenPrefEditor = () => {
    setIsEditingPrefs(true)
    setPickedTags([])
    setShowPrefModal(true)
  }

  const handleFavoriteToggle = (podcastId: number) => {
    const podcast = podcasts.find((item) => item.id === podcastId)
    if (!podcast || !user) return
    const wasFavorite = isFavorite(podcastId)
    toggleFavorite(podcast)
    if (!wasFavorite) {
      void reportAction('favorite', podcast, {
        recommendation_request_id: recommendationRequestId,
      })?.then(() => api.getRecommendations(user.id))
        .then((response) => {
          setRecommendedIds(response.items.map((item) => item.podcast_id))
          setRecommendationRequestId(response.request_id)
          setPlayerRecommendationRequestId(response.request_id)
          setStrategy(response.strategy)
        })
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
        {userLoading
          ? '正在同步用户身份...'
          : `当前推荐用户：${user?.username ?? '未设置'}${strategy ? ` · 推荐策略：${strategy}` : ''}`}
        {user && (
          <button
            onClick={handleOpenPrefEditor}
            style={{
              marginLeft: '12px',
              padding: '4px 12px',
              borderRadius: '12px',
              border: '1px solid var(--border)',
              background: 'transparent',
              color: 'var(--text)',
              cursor: 'pointer',
              fontSize: '12px',
            }}
          >
            编辑偏好
          </button>
        )}
      </div>

      {showPrefModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.55)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          <div
            style={{
              background: 'var(--bg)',
              borderRadius: '20px',
              padding: '32px',
              maxWidth: '480px',
              width: '90%',
              boxShadow: '0 8px 40px rgba(0,0,0,0.25)',
            }}
          >
            <h2 style={{ margin: '0 0 8px', fontSize: '22px' }}>{isEditingPrefs ? '编辑偏好' : '欢迎来到 AI 播客'}</h2>
            <p style={{ margin: '0 0 20px', color: 'var(--text)', fontSize: '14px' }}>
              {isEditingPrefs
                ? '调整你感兴趣的话题，推荐会同步更新'
                : '选几个你感兴趣的话题，我会为你推荐更合口味的播客内容'}
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginBottom: '24px' }}>
              {PREFERENCE_CATEGORIES.map((cat) => {
                const active = pickedTags.includes(cat.id)
                return (
                  <button
                    key={cat.id}
                    onClick={() => toggleTag(cat.id)}
                    style={{
                      padding: '8px 16px',
                      borderRadius: '40px',
                      border: `1px solid ${active ? 'var(--accent)' : 'var(--border)'}`,
                      background: active ? 'var(--accent-bg)' : 'transparent',
                      color: active ? 'var(--accent)' : 'var(--text)',
                      cursor: 'pointer',
                      fontSize: '14px',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                    }}
                  >
                    <span>{cat.icon}</span> {cat.name}
                  </button>
                )
              })}
            </div>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={isEditingPrefs ? (() => setShowPrefModal(false)) : handleSkipOnboarding}
                style={{
                  padding: '8px 20px',
                  borderRadius: '20px',
                  border: '1px solid var(--border)',
                  background: 'transparent',
                  color: 'var(--text)',
                  cursor: 'pointer',
                  fontSize: '14px',
                }}
              >
                {isEditingPrefs ? '取消' : '先看看'}
              </button>
              <button
                onClick={handleSavePreferences}
                disabled={pickedTags.length === 0 || saving}
                style={{
                  padding: '8px 20px',
                  borderRadius: '20px',
                  border: 'none',
                  background: pickedTags.length > 0 ? 'var(--accent)' : 'var(--border)',
                  color: 'white',
                  cursor: pickedTags.length > 0 ? 'pointer' : 'not-allowed',
                  fontSize: '14px',
                }}
              >
                {saving ? '保存中...' : isEditingPrefs ? '保存偏好' : '开启个性化推荐'}
              </button>
            </div>
          </div>
        </div>
      )}

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
                    onClick={() => handleFavoriteToggle(podcast.id)}
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
