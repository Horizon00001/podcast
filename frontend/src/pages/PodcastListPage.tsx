import type { KeyboardEvent } from 'react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '../services/api'
import type { Podcast, ScriptLine } from '../types/podcast'
import { usePlayer } from '../context/PlayerContext'
import { useUser } from '../context/UserContext'
import { useFavorites } from '../context/FavoritesContext'
import { getCategoryLabel, getCoverStyle, getFeaturedHeroCoverStyle, getFeaturedHeroSecondaryCoverStyle } from '../utils/coverStyles'
import { truncateText } from '../utils/truncate'

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
      'radial-gradient(circle at top right, rgba(255, 230, 240, 0.5), transparent 45%), linear-gradient(145deg, #d45d9b 0%, #eb84b9 52%, #ffb6d8 100%)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -20px 32px rgba(140,50,100,0.25)',
    accent: 'rgba(255, 245, 250, 0.95)',
  },
  {
    background:
      'radial-gradient(circle at top right, rgba(220, 245, 255, 0.5), transparent 45%), linear-gradient(145deg, #428be5 0%, #6ba9f4 52%, #a8d5ff 100%)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -20px 32px rgba(35,90,150,0.25)',
    accent: 'rgba(245, 250, 255, 0.95)',
  },
  {
    background:
      'radial-gradient(circle at top right, rgba(230, 255, 210, 0.5), transparent 45%), linear-gradient(145deg, #55b86c 0%, #7dcb83 50%, #b8e6a9 100%)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -20px 32px rgba(45,110,60,0.25)',
    accent: 'rgba(250, 255, 245, 0.95)',
  },
  {
    background:
      'radial-gradient(circle at top right, rgba(255, 235, 200, 0.5), transparent 45%), linear-gradient(145deg, #e68840 0%, #f4aa65 52%, #fbc595 100%)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -20px 32px rgba(150,85,35,0.25)',
    accent: 'rgba(255, 250, 240, 0.95)',
  },
  {
    background:
      'radial-gradient(circle at top right, rgba(255, 225, 215, 0.5), transparent 45%), linear-gradient(145deg, #e26760 0%, #f48e7e 50%, #fcb6a5 100%)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -20px 32px rgba(140,60,50,0.25)',
    accent: 'rgba(255, 245, 245, 0.95)',
  },
  {
    background:
      'radial-gradient(circle at top right, rgba(255, 250, 190, 0.5), transparent 45%), linear-gradient(145deg, #a6b445 0%, #c4d265 52%, #e5e998 100%)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -20px 32px rgba(100,110,40,0.25)',
    accent: 'rgba(255, 255, 245, 0.95)',
  },
  {
    background:
      'radial-gradient(circle at top right, rgba(210, 210, 255, 0.5), transparent 45%), linear-gradient(145deg, #6c5ce7 0%, #8b7de9 52%, #b4abef 100%)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -20px 32px rgba(70,60,150,0.25)',
    accent: 'rgba(245, 245, 255, 0.95)',
  },
  {
    background:
      'radial-gradient(circle at top right, rgba(200, 255, 240, 0.5), transparent 45%), linear-gradient(145deg, #00b894 0%, #2bd0b0 52%, #6bedd4 100%)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -20px 32px rgba(10,120,90,0.25)',
    accent: 'rgba(240, 255, 250, 0.95)',
  },
]

export function PodcastListPage() {
  const {isFavorite, toggleFavorite } = useFavorites();
  const [podcasts, setPodcasts] = useState<Podcast[]>([])
  const [featuredScriptLines, setFeaturedScriptLines] = useState<ScriptLine[]>([])
  const [recommendedIds, setRecommendedIds] = useState<number[]>([])
  const [recommendationRequestId, setRecommendationRequestId] = useState('')
  const [error, setError] = useState('')
  const [showPrefModal, setShowPrefModal] = useState(false)
  const [isEditingPrefs, setIsEditingPrefs] = useState(false)
  const [pickedTags, setPickedTags] = useState<string[]>([])
  const [saving, setSaving] = useState(false)
  const [featuredHeroSeed] = useState(() => Math.floor(Math.random() * 1_000_000))
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
    toggleFavorite(podcast)
    if (isFavorite(podcastId)) {
      void reportAction('favorite', podcast, {
        recommendation_request_id: recommendationRequestId,
      })
    }
  }

  const recommendedPodcasts = recommendedIds
    .map((id) => podcasts.find((podcast) => podcast.id === id))
    .filter((podcast): podcast is Podcast => Boolean(podcast))

  const featuredPodcast = recommendedPodcasts[0] ?? podcasts[0] ?? null
  const featuredSecondary = recommendedPodcasts[1] ?? podcasts[1] ?? null
  const featuredHeroStyle = featuredPodcast ? getFeaturedHeroCoverStyle(featuredHeroSeed) : null
  const featuredHeroSecondaryStyle = featuredSecondary ? getFeaturedHeroSecondaryCoverStyle(featuredHeroSeed) : null
  const featuredScriptPreview = featuredScriptLines
    .slice(0, 4)
    .map((line) => line.text.trim())
    .filter(Boolean)
    .join(' ')

  useEffect(() => {
    if (!featuredPodcast) {
      setFeaturedScriptLines([])
      return
    }

    let cancelled = false
    api.getPodcastScript(featuredPodcast.id)
      .then((lines) => {
        if (cancelled) return
        setFeaturedScriptLines(lines)
      })
      .catch(() => {
        if (cancelled) return
        setFeaturedScriptLines([])
      })

    return () => {
      cancelled = true
    }
  }, [featuredPodcast])

  return (
    <main style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1
        style={{
          fontSize: '40px',
          lineHeight: 1.08,
          letterSpacing: '-0.03em',
          margin: '0 0 20px',
          fontWeight: 780,
          color: '#1d1d1f',
          fontFamily: '"Noto Sans SC", "PingFang SC", "SF Pro Display", "SF Pro Text", -apple-system, BlinkMacSystemFont, system-ui, sans-serif',
          textAlign: 'left',
        }}
      >
        新发现
      </h1>

      {featuredPodcast && (
        <section
          style={{
            marginBottom: '48px',
            borderRadius: '32px',
            overflow: 'hidden',
            background: 'linear-gradient(135deg, #f6ecdf 0%, #efe3f6 46%, #e7f0fb 100%)',
            boxShadow: '0 32px 80px rgba(8, 6, 13, 0.14)',
            border: '1px solid rgba(96, 78, 122, 0.12)',
            position: 'relative',
          }}
        >
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: 'radial-gradient(circle at top right, rgba(255,255,255,0.52) 0%, rgba(255,255,255,0) 34%), radial-gradient(circle at bottom left, rgba(255, 214, 170, 0.18) 0%, rgba(255, 214, 170, 0) 30%)',
              pointerEvents: 'none',
            }}
          />
          <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'minmax(0, 1.05fr) minmax(340px, 410px)',
                gap: '32px',
                padding: '36px',
                alignItems: 'stretch',
              position: 'relative',
              zIndex: 1,
            }}
          >
            <div style={{ display: 'grid', gap: '18px', alignContent: 'start', textAlign: 'left' }}>
              <div>
                <div style={{ fontSize: '12px', lineHeight: 1.4, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'rgba(17, 17, 17, 0.56)', marginBottom: '14px', fontWeight: 700, fontFamily: 'Inter, "Helvetica Neue", Arial, sans-serif' }}>
                  Feature / Weekly Edit
                </div>
                <h2 style={{ fontSize: '44px', lineHeight: 1.1, letterSpacing: '-0.025em', margin: '0 0 16px', maxWidth: '600px', color: '#111111', fontWeight: 780, fontFamily: '"Noto Sans SC", "PingFang SC", "SF Pro Display", "SF Pro Text", -apple-system, BlinkMacSystemFont, system-ui, sans-serif', overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflowWrap: 'anywhere', textRendering: 'optimizeLegibility' }}>
                  {featuredPodcast.title}
                </h2>
                <p style={{ maxWidth: '520px', color: 'rgba(17, 17, 17, 0.72)', fontSize: '16px', lineHeight: 1.78, margin: '0', fontFamily: '"Noto Serif SC", "Songti SC", serif' }}>
                  {featuredPodcast.summary}
                </p>
                {featuredScriptPreview && (
                  <div style={{ maxWidth: '540px', marginTop: '20px', paddingTop: '18px', borderTop: '1px solid rgba(17, 17, 17, 0.1)' }}>
                    <div style={{ fontSize: '12px', lineHeight: 1.4, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'rgba(17, 17, 17, 0.52)', marginBottom: '10px', fontWeight: 700, fontFamily: 'Inter, "Helvetica Neue", Arial, sans-serif' }}>
                      本期文稿
                    </div>
                    <p style={{ margin: 0, color: '#1a1820', fontSize: '15px', lineHeight: 1.72, fontFamily: '"Noto Serif SC", "Songti SC", serif', overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 6, WebkitBoxOrient: 'vertical' }}>
                      {featuredScriptPreview}
                    </p>
                  </div>
                )}
              </div>
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap', marginTop: '4px' }}>
                <Link
                  to={`/podcasts/${featuredPodcast.id}`}
                  style={{ textDecoration: 'none', color: 'rgba(17, 17, 17, 0.56)', fontSize: '13px', fontWeight: 700, padding: '6px 0' }}
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
                    minHeight: '344px',
                     borderRadius: '24px',
                    padding: '24px',
                     display: 'flex',
                     flexDirection: 'column',
                     justifyContent: 'space-between',
                    cursor: 'pointer',
                    ...(featuredHeroStyle ?? getCoverStyle(featuredPodcast.category)),
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
                  <div style={{ textAlign: 'left' }}>
                   <div style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'rgba(255, 255, 255, 0.84)', marginBottom: '12px', fontWeight: 700 }}>{getCategoryLabel(featuredPodcast.category)}</div>
                   <div style={{ fontSize: '35px', fontWeight: 780, lineHeight: 1.05, letterSpacing: '-0.03em', color: '#ffffff', marginBottom: '14px', fontFamily: '"Noto Sans SC", "PingFang SC", "SF Pro Display", "SF Pro Text", -apple-system, BlinkMacSystemFont, system-ui, sans-serif', overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflowWrap: 'anywhere', textRendering: 'optimizeLegibility' }}>
                     {featuredPodcast.title}
                    </div>
                   <div style={{ fontSize: '12px', color: 'rgba(255, 255, 255, 0.76)', fontWeight: 600 }}>
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
                       ...(featuredHeroSecondaryStyle ?? getCoverStyle(featuredSecondary.category)),
                     }}
                   >
                      <span style={{ fontSize: '10px', color: 'rgba(255, 255, 255, 0.8)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700 }}>Next Up</span>
                      <span style={{ fontSize: '12px', color: 'rgba(255, 255, 255, 0.95)', fontWeight: 800 }}>{getCategoryLabel(featuredSecondary.category)}</span>
                    </div>
                      <div style={{ textAlign: 'left' }}>
                        <div style={{ fontSize: '12px', color: '#6b6375', marginBottom: '4px', fontWeight: 600 }}>继续推荐</div>
                        <Link
                          to={`/podcasts/${featuredSecondary.id}`}
                          onClick={(event) => event.stopPropagation()}
                          style={{ textDecoration: 'none', color: '#111111', fontWeight: 700, lineHeight: 1.25 }}
                        >
                          <span style={{ overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflowWrap: 'anywhere' }}>
                            {featuredSecondary.title}
                          </span>
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
                        padding: '6px 12px',
                        borderRadius: '999px',
                        background: 'rgba(255, 255, 255, 0.25)',
                        border: '1px solid rgba(255, 255, 255, 0.3)',
                        backdropFilter: 'blur(8px)',
                        fontSize: '12px',
                        letterSpacing: '0.08em',
                        textTransform: 'uppercase',
                        fontWeight: 800,
                        color: '#ffffff',
                        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
                      }}
                      >
                        为你推荐
                      </div>
                      <div style={{ fontSize: '32px', lineHeight: 1, color: 'rgba(255, 255, 255, 0.5)', fontWeight: 800, textShadow: '0 2px 4px rgba(0,0,0,0.2)' }}>
                        {String(index + 1).padStart(2, '0')}
                      </div>
                    </div>
                    <div style={{ alignSelf: 'stretch', position: 'relative', zIndex: 1, textAlign: 'left' }}>
                      <div style={{ fontSize: '13px', color: 'rgba(255, 255, 255, 0.95)', fontWeight: 800, marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        {getCategoryLabel(podcast.category)}
                      </div>
                      <div style={{ fontSize: '28px', fontWeight: 700, lineHeight: 1.04, letterSpacing: '-0.05em', color: '#ffffff', overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflowWrap: 'anywhere' }}>
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
                        paddingTop: '12px',
                        borderTop: '1px solid rgba(255, 255, 255, 0.25)',
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
                     style={{ display: 'block', fontWeight: 700, color: 'var(--text-h)', textDecoration: 'none', fontSize: '16px', lineHeight: 1.25, textAlign: 'left' }}
                    >
                     {truncateText(podcast.title, 50)}
                   </Link>
                   <p style={{ fontSize: '13px', margin: '8px 0 10px', color: 'var(--text)', lineHeight: 1.5, textAlign: 'left' }}>{truncateText(podcast.summary, 100)}</p>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '12px', color: '#5f5967' }}>{new Date(podcast.published_at).toLocaleDateString()}</span>
                    <motion.button
                      whileHover={{ scale: 1.12 }}
                      whileTap={{ scale: 0.9 }}
                      onClick={(event) => {
                        event.stopPropagation()
                        handleFavoriteToggle(podcast.id)
                      }}
                      style={{ border: `1px solid ${isFavorite(podcast.id) ? 'var(--accent-border)' : 'rgba(8, 6, 13, 0.08)'}`, background: isFavorite(podcast.id) ? 'var(--accent-bg)' : 'transparent', borderRadius: '999px', padding: '6px 10px', cursor: 'pointer', fontSize: '12px', color: isFavorite(podcast.id) ? '#ffffff' : 'var(--text-h)', fontWeight: 600 }}
                    >
                      {isFavorite(podcast.id) ? '已收藏' : '收藏'}
                    </motion.button>
                  </div>
                </motion.div>
            )})}
          </div>
        </section>
      )}

      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '10px',
        marginBottom: '28px',
        paddingBottom: '14px',
        borderBottom: '1px solid var(--border)'
      }}>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          style={{
            padding: '8px 16px',
            borderRadius: '40px',
            border: '1px solid rgba(61, 56, 69, 0.12)',
            background: 'rgba(255, 255, 255, 0.9)',
            color: '#5f5967',
            cursor: 'default',
            fontSize: '14px',
            fontWeight: 600,
            transition: 'border 0.2s, background 0.2s, color 0.2s, transform 0.2s',
          }}
        >
          全部
        </motion.button>
      </div>

      {error && <p style={{ color: 'red' }}>加载失败：{error}</p>}

      {/* 卡片网格 */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
        gap: '18px'
      }}>
        {podcasts.map(podcast => {
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
                <div style={{ textAlign: 'left' }}>
                  <div style={{ fontSize: '28px', fontWeight: 700, lineHeight: 1.05, letterSpacing: '-0.04em', color: '#ffffff', overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflowWrap: 'anywhere' }}>
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
                  marginBottom: '8px',
                  textAlign: 'left'
                }}
              >
                {truncateText(podcast.title, 50)}
              </Link>
              <p style={{ fontSize: '14px', color: 'var(--text)', marginBottom: '12px', lineHeight: 1.5, textAlign: 'left' }}>
                {truncateText(podcast.summary, 100)}
              </p>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', textAlign: 'left' }}>
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
                    style={{ border: `1px solid ${isFavorite(podcast.id) ? 'var(--accent-border)' : 'rgba(8, 6, 13, 0.08)'}`, background: isFavorite(podcast.id) ? 'var(--accent-bg)' : 'transparent', borderRadius: '999px', padding: '6px 10px', cursor: 'pointer', fontSize: '12px', color: isFavorite(podcast.id) ? '#ffffff' : 'var(--text-h)', fontWeight: 600 }}
  >
                    {isFavorite(podcast.id) ? '已收藏' : '收藏'}
                  </motion.button>
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>

      {podcasts.length === 0 && (
        <div style={{ padding: '64px', textAlign: 'center', color: 'var(--text)' }}>
          暂无播客，请去生成内容后再来查看。
        </div>
      )}
    </main>
  )
}
