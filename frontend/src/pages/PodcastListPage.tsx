import type { KeyboardEvent } from 'react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '../services/api'
import type { Podcast } from '../types/podcast'
import { usePlayer } from '../context/PlayerContext'
import { useUser } from '../context/UserContext'
import { useFavorites } from '../context/FavoritesContext'
import { getCategoryLabel, getCoverStyle } from '../utils/coverStyles'

const CATEGORIES = [
  { id: 'all', name: '全部' },
  { id: 'technology', name: '科技' },
  { id: 'finance', name: '财经' },
  { id: 'sports', name: '体育' },
  { id: 'entertainment', name: '娱乐' },
  { id: 'health', name: '健康' },
]

const ONBOARDED_KEY = 'podcast_onboarded'
const PREFERENCE_CATEGORIES = CATEGORIES.filter(c => c.id !== 'all')
const RECOMMENDATION_COVER_THEMES = [
  {
    background:
      'radial-gradient(circle at top right, rgba(255, 224, 247, 0.4), transparent 34%), linear-gradient(145deg, #cb5ca6 0%, #e287be 52%, #f7b7d5 100%)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.22), inset 0 -20px 32px rgba(128,39,91,0.18)',
    accent: 'rgba(255, 244, 250, 0.82)',
  },
  {
    background:
      'radial-gradient(circle at top right, rgba(206, 239, 255, 0.38), transparent 34%), linear-gradient(145deg, #3b86db 0%, #63a9ee 52%, #9ed4ff 100%)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.22), inset 0 -20px 32px rgba(28,84,143,0.18)',
    accent: 'rgba(241, 250, 255, 0.84)',
  },
  {
    background:
      'radial-gradient(circle at top right, rgba(221, 248, 201, 0.38), transparent 34%), linear-gradient(145deg, #4eab63 0%, #76c17c 50%, #b1e2a3 100%)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.22), inset 0 -20px 32px rgba(41,102,55,0.16)',
    accent: 'rgba(245, 255, 241, 0.84)',
  },
  {
    background:
      'radial-gradient(circle at top right, rgba(255, 227, 191, 0.4), transparent 34%), linear-gradient(145deg, #dd7f36 0%, #efa257 52%, #f7c189 100%)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.22), inset 0 -20px 32px rgba(140,78,28,0.16)',
    accent: 'rgba(255, 247, 238, 0.84)',
  },
  {
    background:
      'radial-gradient(circle at top right, rgba(255, 219, 207, 0.38), transparent 34%), linear-gradient(145deg, #d85f58 0%, #eb8474 50%, #f5b09c 100%)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.22), inset 0 -20px 32px rgba(129,53,46,0.16)',
    accent: 'rgba(255, 244, 240, 0.84)',
  },
  {
    background:
      'radial-gradient(circle at top right, rgba(246, 242, 182, 0.38), transparent 34%), linear-gradient(145deg, #9ca83f 0%, #bbc85c 52%, #dfe48f 100%)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.22), inset 0 -20px 32px rgba(93,101,31,0.16)',
    accent: 'rgba(252, 255, 241, 0.84)',
  },
]

export function PodcastListPage() {
  const {isFavorite, toggleFavorite } = useFavorites();
  const [podcasts, setPodcasts] = useState<Podcast[]>([])
  const [recommendedIds, setRecommendedIds] = useState<number[]>([])
  const [recommendationRequestId, setRecommendationRequestId] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [error, setError] = useState('')
  const [showPrefModal, setShowPrefModal] = useState(false)
  const [isEditingPrefs, setIsEditingPrefs] = useState(false)
  const [pickedTags, setPickedTags] = useState<string[]>([])
  const [saving, setSaving] = useState(false)
  const { currentPodcast, play, toggle, reportAction, setRecommendationRequestId: setPlayerRecommendationRequestId } = usePlayer()
  const { user } = useUser()

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

  const handleCardKeyDown = (event: KeyboardEvent<HTMLElement>, podcast: Podcast) => {
    if (event.key !== 'Enter' && event.key !== ' ') return
    event.preventDefault()
    handlePlay(podcast)
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
        })
        .catch((e) => setError((e as Error).message))
    }
  }

  const recommendedPodcasts = recommendedIds
    .map((id) => podcasts.find((podcast) => podcast.id === id))
    .filter((podcast): podcast is Podcast => Boolean(podcast))

  const featuredPodcast = recommendedPodcasts[0] ?? podcasts[0] ?? null
  const featuredSecondary = recommendedPodcasts[1] ?? podcasts[1] ?? null

  return (
    <main style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1
        style={{
          fontSize: '38px',
          lineHeight: 1.02,
          letterSpacing: '-0.06em',
          margin: '0 0 20px',
          fontWeight: 700,
          color: '#1d1d1f',
          fontFamily: 'SF Pro Display, SF Pro Text, -apple-system, BlinkMacSystemFont, system-ui, sans-serif',
          textAlign: 'left',
        }}
      >
        新发现
      </h1>

      {featuredPodcast && (
        <section
          style={{
            marginBottom: '40px',
            borderRadius: '32px',
            overflow: 'hidden',
            background: 'linear-gradient(135deg, #faf6ef 0%, #f4eef8 48%, #eef4fb 100%)',
            boxShadow: '0 28px 72px rgba(8, 6, 13, 0.08)',
            border: '1px solid rgba(8, 6, 13, 0.06)',
            position: 'relative',
          }}
        >
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: 'radial-gradient(circle at top right, rgba(255,255,255,0.45) 0%, rgba(255,255,255,0) 36%)',
              pointerEvents: 'none',
            }}
          />
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(0, 1.1fr) minmax(320px, 380px)',
              gap: '28px',
              padding: '32px',
              alignItems: 'stretch',
              position: 'relative',
              zIndex: 1,
            }}
          >
            <div style={{ display: 'grid', gap: '20px', alignContent: 'space-between' }}>
              <div>
                <h2 style={{ fontSize: '44px', lineHeight: 1.02, letterSpacing: '-0.06em', margin: '0 0 14px', maxWidth: '560px', color: '#111111' }}>
                  {featuredPodcast.title}
                </h2>
                <p style={{ maxWidth: '520px', color: '#36313a', fontSize: '16px', lineHeight: 1.7, marginBottom: '18px' }}>
                  {featuredPodcast.summary}
                </p>
              </div>
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
                <Link
                  to={`/podcasts/${featuredPodcast.id}`}
                  style={{ textDecoration: 'none', color: '#1d1d1f', fontSize: '13px', fontWeight: 700, padding: '8px 0' }}
                >
                  查看详情
                </Link>
              </div>
            </div>

            <div style={{ display: 'grid', gap: '16px', alignContent: 'space-between' }}>
              <motion.div
                 whileHover={{ y: -4, boxShadow: '0 18px 40px rgba(8, 6, 13, 0.12)' }}
                 onClick={() => handlePlay(featuredPodcast)}
                 onKeyDown={(event) => handleCardKeyDown(event, featuredPodcast)}
                 role="button"
                 tabIndex={0}
                  style={{
                    minHeight: '310px',
                    borderRadius: '24px',
                    padding: '22px',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                    ...getCoverStyle(featuredPodcast.category),
                   }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
                    <span style={{ fontSize: '12px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'rgba(255, 255, 255, 0.82)', fontWeight: 700 }}>
                      Editors' Pick
                    </span>
                    <span
                      style={{
                        minWidth: '40px',
                        height: '40px',
                        borderRadius: '50%',
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        background: 'rgba(255,255,255,0.16)',
                        border: '1px solid rgba(255,255,255,0.16)',
                        fontSize: '13px',
                        fontWeight: 700,
                        color: '#ffffff',
                      }}
                    >
                      P
                    </span>
                  </div>
                  <div>
                   <div style={{ fontSize: '12px', color: 'rgba(255, 255, 255, 0.88)', marginBottom: '10px', fontWeight: 700 }}>{getCategoryLabel(featuredPodcast.category)}</div>
                   <div style={{ fontSize: '35px', fontWeight: 700, lineHeight: 0.98, letterSpacing: '-0.06em', color: '#ffffff', marginBottom: '14px' }}>
                     {featuredPodcast.title}
                   </div>
                   <div style={{ fontSize: '12px', color: 'rgba(255, 255, 255, 0.8)', fontWeight: 600 }}>
                     点击卡片即可播放
                   </div>
                 </div>
               </motion.div>

              {featuredSecondary && (
                <motion.div
                   whileHover={{ y: -2, boxShadow: '0 10px 24px rgba(8, 6, 13, 0.08)' }}
                   onClick={() => handlePlay(featuredSecondary)}
                   onKeyDown={(event) => handleCardKeyDown(event, featuredSecondary)}
                   role="button"
                   tabIndex={0}
                   style={{
                     display: 'grid',
                     gridTemplateColumns: '84px minmax(0, 1fr)',
                     gap: '12px',
                     alignItems: 'center',
                     background: 'rgba(255,255,255,0.86)',
                     borderRadius: '18px',
                     padding: '14px',
                     border: '1px solid rgba(8, 6, 13, 0.06)',
                     cursor: 'pointer',
                    }}
                   >
                   <div
                     style={{
                       aspectRatio: '1 / 1',
                      borderRadius: '16px',
                      padding: '12px',
                       display: 'flex',
                       flexDirection: 'column',
                       justifyContent: 'space-between',
                      ...getCoverStyle(featuredSecondary.category),
                    }}
                  >
                      <span style={{ fontSize: '10px', color: 'rgba(255, 255, 255, 0.8)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700 }}>Next Up</span>
                      <span style={{ fontSize: '11px', color: 'rgba(255, 255, 255, 0.84)', fontWeight: 600 }}>{getCategoryLabel(featuredSecondary.category)}</span>
                    </div>
                      <div>
                        <div style={{ fontSize: '12px', color: '#6b6375', marginBottom: '4px', fontWeight: 600 }}>继续推荐</div>
                        <Link
                          to={`/podcasts/${featuredSecondary.id}`}
                          onClick={(event) => event.stopPropagation()}
                          style={{ textDecoration: 'none', color: '#111111', fontWeight: 700, lineHeight: 1.25 }}
                        >
                          {featuredSecondary.title}
                        </Link>
                     </div>
                </motion.div>
              )}
            </div>
          </div>
        </section>
      )}

      <AnimatePresence>
      {showPrefModal && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
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
          <motion.div
            initial={{ opacity: 0, scale: 0.92 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.92 }}
            transition={{ duration: 0.25 }}
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
                  <motion.button
                    key={cat.id}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
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
                      transition: 'border 0.2s, background 0.2s, color 0.2s',
                    }}
                  >
                    {cat.name}
                  </motion.button>
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
          </motion.div>
        </motion.div>
      )}
      </AnimatePresence>

      {recommendedPodcasts.length > 0 && (
        <section style={{ marginBottom: '36px' }}>
          <h2 style={{ fontSize: '22px', marginBottom: '14px', color: '#111111' }}>为你推荐</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '16px' }}>
            {recommendedPodcasts.slice(0, 12).map((podcast, index) => {
              const recommendationTheme = RECOMMENDATION_COVER_THEMES[index % RECOMMENDATION_COVER_THEMES.length]

              return (
                <motion.div
                  key={`rec-${podcast.id}`}
                  whileHover={{ y: -3, boxShadow: '0 14px 32px rgba(8, 6, 13, 0.08)' }}
                  onClick={() => handlePlay(podcast)}
                  onKeyDown={(event) => handleCardKeyDown(event, podcast)}
                  role="button"
                  tabIndex={0}
                  style={{
                     border: '1px solid var(--border)',
                     borderRadius: '18px',
                     padding: '12px',
                     background: 'var(--bg)',
                     boxShadow: '0 10px 28px rgba(8, 6, 13, 0.04)',
                     cursor: 'pointer',
                   }}
                 >
                  <div
                    style={{
                      aspectRatio: '1 / 1',
                      borderRadius: '14px',
                      marginBottom: '12px',
                      padding: '14px',
                      display: 'grid',
                      gridTemplateRows: 'auto 1fr auto',
                      background: recommendationTheme.background,
                      boxShadow: recommendationTheme.boxShadow,
                      color: '#ffffff',
                      textShadow: '0 1px 2px rgba(36, 42, 56, 0.22)',
                      position: 'relative',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        position: 'absolute',
                        right: '-18px',
                        top: '-18px',
                        width: '116px',
                        height: '116px',
                        borderRadius: '50%',
                        background: 'radial-gradient(circle, rgba(255, 255, 255, 0.3) 0%, rgba(255, 255, 255, 0) 72%)',
                        pointerEvents: 'none',
                      }}
                    />
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px', position: 'relative', zIndex: 1 }}>
                      <div
                        style={{
                          padding: '6px 10px',
                          borderRadius: '999px',
                          background: 'rgba(255, 255, 255, 0.2)',
                          border: '1px solid rgba(255, 255, 255, 0.18)',
                          fontSize: '11px',
                          letterSpacing: '0.08em',
                          textTransform: 'uppercase',
                          fontWeight: 700,
                        }}
                      >
                        为你推荐
                      </div>
                      <div style={{ fontSize: '30px', lineHeight: 1, color: 'rgba(255, 255, 255, 0.34)', fontWeight: 700 }}>
                        {String(index + 1).padStart(2, '0')}
                      </div>
                    </div>
                    <div style={{ alignSelf: 'center', position: 'relative', zIndex: 1 }}>
                      <div style={{ fontSize: '12px', color: 'rgba(255, 255, 255, 0.88)', fontWeight: 700, marginBottom: '10px' }}>
                        {getCategoryLabel(podcast.category)}
                      </div>
                      <div style={{ fontSize: '28px', fontWeight: 700, lineHeight: 1.04, letterSpacing: '-0.05em', color: '#ffffff' }}>
                        {podcast.title}
                      </div>
                    </div>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        gap: '10px',
                        position: 'relative',
                        zIndex: 1,
                        paddingTop: '10px',
                        borderTop: '1px solid rgba(255, 255, 255, 0.18)',
                      }}
                    >
                      <div>
                        <div style={{ fontSize: '10px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'rgba(255, 255, 255, 0.74)', fontWeight: 700 }}>
                          Curated For You
                        </div>
                        <div style={{ marginTop: '4px', fontSize: '12px', color: recommendationTheme.accent, fontWeight: 600 }}>
                          {new Date(podcast.published_at).toLocaleDateString()}
                        </div>
                      </div>
                      <div
                        style={{
                          minWidth: '42px',
                          height: '42px',
                          borderRadius: '50%',
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          background: 'rgba(255, 255, 255, 0.18)',
                          border: '1px solid rgba(255, 255, 255, 0.16)',
                          color: '#ffffff',
                          fontSize: '14px',
                          fontWeight: 700,
                        }}
                      >
                        P
                      </div>
                    </div>
                  </div>
                   <Link
                     to={`/podcasts/${podcast.id}`}
                     onClick={(event) => event.stopPropagation()}
                     style={{ fontWeight: 700, color: 'var(--text-h)', textDecoration: 'none', fontSize: '16px', lineHeight: 1.25 }}
                   >
                    {podcast.title}
                  </Link>
                  <p style={{ fontSize: '13px', margin: '8px 0 10px', color: 'var(--text)', lineHeight: 1.5 }}>{podcast.summary}</p>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '12px', color: '#5f5967' }}>{new Date(podcast.published_at).toLocaleDateString()}</span>
                  </div>
                </motion.div>
            )})}
          </div>
        </section>
      )}
      
      {/* 筛选栏 */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '10px',
        marginBottom: '28px',
        paddingBottom: '14px',
        borderBottom: '1px solid var(--border)'
      }}>
        {CATEGORIES.map(cat => (
          <motion.button
            key={cat.id}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setSelectedCategory(cat.id)}
            style={{
              padding: '8px 16px',
              borderRadius: '40px',
               border: `1px solid ${selectedCategory === cat.id ? 'rgba(122, 51, 255, 0.26)' : 'var(--border)'}`,
               background: selectedCategory === cat.id ? 'rgba(170, 59, 255, 0.12)' : '#ffffff',
               color: selectedCategory === cat.id ? '#6f2cf3' : '#3d3845',
               cursor: 'pointer',
               fontSize: '14px',
               fontWeight: 600,
               transition: 'border 0.2s, background 0.2s, color 0.2s, transform 0.2s',
             }}
           >
             {cat.name}
           </motion.button>
        ))}
      </div>

      {error && <p style={{ color: 'red' }}>加载失败：{error}</p>}

      {/* 卡片网格 */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
        gap: '18px'
      }}>
        {filteredPodcasts.map(podcast => {
          return (
            <motion.div
              key={podcast.id}
              whileHover={{ y: -4, boxShadow: '0 14px 34px rgba(8, 6, 13, 0.08)' }}
              onClick={() => handlePlay(podcast)}
              onKeyDown={(event) => handleCardKeyDown(event, podcast)}
              role="button"
              tabIndex={0}
              transition={{ duration: 0.2 }}
              style={{
                  border: '1px solid var(--border)',
                borderRadius: '18px',
                padding: '12px',
                background: 'var(--bg)',
                boxShadow: '0 10px 28px rgba(8, 6, 13, 0.04)',
                cursor: 'pointer',
              }}
            >
              <div
                style={{
                  aspectRatio: '1 / 1',
                  borderRadius: '14px',
                  marginBottom: '12px',
                  padding: '14px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  ...getCoverStyle(podcast.category),
                }}
                >
                <span style={{ fontSize: '12px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'rgba(255, 255, 255, 0.84)', fontWeight: 700 }}>
                  New Release
                </span>
                <div>
                  <div style={{ fontSize: '28px', fontWeight: 700, lineHeight: 1.05, letterSpacing: '-0.04em', color: '#ffffff' }}>
                    {podcast.title}
                  </div>
                  <div style={{ marginTop: '10px', fontSize: '12px', color: 'rgba(255, 255, 255, 0.84)', fontWeight: 600 }}>{getCategoryLabel(podcast.category)}</div>
                </div>
              </div>
              <Link
                to={`/podcasts/${podcast.id}`}
                onClick={(event) => event.stopPropagation()}
                style={{
                  display: 'block',
                  fontWeight: 600,
                  color: 'var(--text-h)',
                  textDecoration: 'none',
                  fontSize: '18px',
                  lineHeight: 1.25,
                  marginBottom: '8px'
                }}
              >
                {podcast.title}
              </Link>
              <p style={{ fontSize: '14px', color: 'var(--text)', marginBottom: '12px', lineHeight: 1.5 }}>
                {podcast.summary}
              </p>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
                <div style={{ fontSize: '12px', color: 'var(--text)' }}>
                  {new Date(podcast.published_at).toLocaleDateString()}
                </div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <motion.button
                    whileHover={{ scale: 1.12 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={(event) => {
                      event.stopPropagation()
                      handleFavoriteToggle(podcast.id)
                    }}
                    style={{ border: '1px solid rgba(8, 6, 13, 0.08)', background: isFavorite(podcast.id) ? 'rgba(170, 59, 255, 0.12)' : 'transparent', borderRadius: '999px', padding: '6px 10px', cursor: 'pointer', fontSize: '12px', color: isFavorite(podcast.id) ? '#6f2cf3' : 'var(--text-h)', fontWeight: 600 }}
  >
                    {isFavorite(podcast.id) ? '已收藏' : '收藏'}
                  </motion.button>
                </div>
              </div>
            </motion.div>
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
