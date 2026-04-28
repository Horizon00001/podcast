import type { KeyboardEvent } from 'react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '../services/api'
import type { Podcast, ScriptLine } from '../types/podcast'
import { usePlayer } from '../context/PlayerContext'
import { useUser } from '../context/UserContext'
import { useFavorites } from '../context/FavoritesContext'
import { useLikes } from '../context/LikesContext'
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
      'radial-gradient(circle at 16% 14%, rgba(255, 255, 255, 0.52), transparent 24%), radial-gradient(circle at 82% 16%, rgba(255, 154, 210, 0.26), transparent 30%), radial-gradient(circle at 84% 84%, rgba(144, 166, 255, 0.24), transparent 36%), linear-gradient(148deg, #592786 0%, #7a35a5 30%, #a449b7 58%, #cf63ae 80%, #ea97b2 100%)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.28), inset 0 -24px 36px rgba(74,24,110,0.26)',
    accent: 'rgba(255, 245, 250, 0.95)',
  },
  {
    background:
      'radial-gradient(circle at 15% 12%, rgba(255, 255, 255, 0.58), transparent 22%), radial-gradient(circle at 84% 16%, rgba(108, 248, 226, 0.24), transparent 28%), radial-gradient(circle at 82% 84%, rgba(140, 136, 255, 0.26), transparent 34%), linear-gradient(148deg, #0d4f63 0%, #136f86 30%, #1c8f9f 56%, #297dbc 78%, #5956ea 100%)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -24px 38px rgba(16,36,92,0.28)',
    accent: 'rgba(245, 250, 255, 0.95)',
  },
  {
    background:
      'radial-gradient(circle at 18% 14%, rgba(255, 255, 255, 0.5), transparent 24%), radial-gradient(circle at 82% 18%, rgba(154, 240, 198, 0.24), transparent 30%), radial-gradient(circle at 82% 84%, rgba(164, 224, 255, 0.22), transparent 34%), linear-gradient(148deg, #174d3c 0%, #20624c 30%, #2d7760 56%, #40927b 78%, #72b5a8 100%)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.26), inset 0 -24px 36px rgba(20,68,52,0.24)',
    accent: 'rgba(250, 255, 245, 0.95)',
  },
  {
    background:
      'radial-gradient(circle at 18% 14%, rgba(255, 255, 255, 0.54), transparent 24%), radial-gradient(circle at 84% 16%, rgba(255, 204, 138, 0.28), transparent 30%), radial-gradient(circle at 82% 84%, rgba(255, 128, 142, 0.22), transparent 36%), linear-gradient(148deg, #93451e 0%, #b95d2a 28%, #d57a42 56%, #e59b63 78%, #edbc8d 100%)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.28), inset 0 -24px 36px rgba(104,48,20,0.24)',
    accent: 'rgba(255, 250, 240, 0.95)',
  },
  {
    background:
      'radial-gradient(circle at 18% 14%, rgba(255, 255, 255, 0.54), transparent 24%), radial-gradient(circle at 82% 16%, rgba(255, 178, 196, 0.24), transparent 30%), radial-gradient(circle at 84% 84%, rgba(255, 216, 128, 0.22), transparent 36%), linear-gradient(148deg, #973e52 0%, #b84d64 30%, #cf696d 56%, #db8b62 78%, #e7af74 100%)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.28), inset 0 -24px 36px rgba(103,34,50,0.24)',
    accent: 'rgba(255, 245, 245, 0.95)',
  },
  {
    background:
      'radial-gradient(circle at 18% 12%, rgba(255, 255, 255, 0.5), transparent 24%), radial-gradient(circle at 82% 18%, rgba(255, 223, 108, 0.24), transparent 30%), radial-gradient(circle at 84% 84%, rgba(96, 214, 174, 0.24), transparent 36%), linear-gradient(148deg, #345c25 0%, #4b7630 30%, #6a953d 56%, #90b44f 78%, #c5cf73 100%)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.26), inset 0 -24px 36px rgba(55,68,24,0.24)',
    accent: 'rgba(255, 255, 245, 0.95)',
  },
  {
    background:
      'radial-gradient(circle at 16% 12%, rgba(255, 255, 255, 0.52), transparent 24%), radial-gradient(circle at 84% 16%, rgba(190, 212, 255, 0.24), transparent 30%), radial-gradient(circle at 82% 84%, rgba(156, 168, 255, 0.24), transparent 34%), linear-gradient(148deg, #422765 0%, #583682 28%, #71449e 56%, #8060b9 76%, #8d95dc 100%)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.26), inset 0 -24px 38px rgba(44,30,82,0.26)',
    accent: 'rgba(245, 245, 255, 0.95)',
  },
  {
    background:
      'radial-gradient(circle at 20% 14%, rgba(255, 255, 255, 0.52), transparent 24%), radial-gradient(circle at 80% 18%, rgba(130, 244, 210, 0.26), transparent 30%), radial-gradient(circle at 84% 84%, rgba(254, 220, 92, 0.2), transparent 34%), linear-gradient(148deg, #075340 0%, #0a684f 30%, #0d8664 56%, #1fa983 78%, #73caaf 100%)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.26), inset 0 -24px 36px rgba(6,58,44,0.24)',
    accent: 'rgba(240, 255, 250, 0.95)',
  },
]

export function PodcastListPage() {
  const { isFavorite, toggleFavorite } = useFavorites()
  const { isLiked, toggleLike } = useLikes()
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

  const loadRecommendations = async (userId: number) => {
    const response = await api.getRecommendations(userId)
    setRecommendedIds(response.items.map((item) => item.podcast_id))
    setRecommendationRequestId(response.request_id)
    setPlayerRecommendationRequestId(response.request_id)
    if (response.strategy === 'cold-start' && !localStorage.getItem(ONBOARDED_KEY)) {
      setShowPrefModal(true)
      setIsEditingPrefs(false)
    }
    return response
  }

  useEffect(() => {
    if (!user) return
    loadRecommendations(user.id)
      .catch((e) => setError((e as Error).message))
  }, [user])

  const handlePlay = async (podcast: Podcast) => {
    if (currentPodcast?.id === podcast.id) {
      toggle()
      return
    }

    play(podcast)
    if (!user) return

    try {
      await reportAction('click', podcast, { recommendation_request_id: recommendationRequestId })
      await loadRecommendations(user.id)
    } catch (e) {
      setError((e as Error).message)
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
      await loadRecommendations(user.id)
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
      })
    }
  }

  const handleLikeToggle = (podcastId: number) => {
    const podcast = podcasts.find((item) => item.id === podcastId)
    if (!podcast || !user) return
    const wasLiked = isLiked(podcastId)
    toggleLike(podcast)
    if (!wasLiked) {
      void reportAction('like', podcast, {
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

            <div style={{ display: 'grid', gap: '12px', alignContent: 'start' }}>
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
                      marginTop: '-2px',
                      background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.28) 0%, rgba(255, 255, 255, 0.18) 100%)',
                      borderRadius: '18px',
                     padding: '14px',
                     border: '1px solid rgba(255, 255, 255, 0.22)',
                     boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.24), 0 14px 28px rgba(53, 42, 77, 0.12)',
                     backdropFilter: 'blur(12px)',
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
                        <div style={{ fontSize: '12px', color: 'rgba(58, 43, 81, 0.72)', marginBottom: '4px', fontWeight: 700 }}>继续推荐</div>
                        <Link
                          to={`/podcasts/${featuredSecondary.id}`}
                          onClick={(event) => event.stopPropagation()}
                          style={{ textDecoration: 'none', color: '#20172d', fontWeight: 700, lineHeight: 1.25 }}
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
                      padding: '12px 12px 54px',
                      display: 'flex',
                      flexDirection: 'column',
                      position: 'relative',
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
                  <div>
                    <div>
                      <Link
                        to={`/podcasts/${podcast.id}`}
                        onClick={(event) => event.stopPropagation()}
                        style={{ display: 'block', fontWeight: 700, color: 'var(--text-h)', textDecoration: 'none', fontSize: '16px', lineHeight: 1.25, textAlign: 'left' }}
                      >
                        {truncateText(podcast.title, 50)}
                      </Link>
                      <p style={{ fontSize: '13px', margin: '8px 0 10px', color: 'var(--text)', lineHeight: 1.5, textAlign: 'left' }}>{truncateText(podcast.summary, 100)}</p>
                    </div>
                    <div style={{ position: 'absolute', left: '12px', right: '12px', bottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px' }}>
                      <span style={{ fontSize: '12px', color: '#5f5967' }}>{new Date(podcast.published_at).toLocaleDateString()}</span>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <motion.button
                          whileHover={{ scale: 1.12 }}
                          whileTap={{ scale: 0.9 }}
                          onClick={(event) => {
                            event.stopPropagation()
                            handleLikeToggle(podcast.id)
                          }}
                          style={{ border: `1px solid ${isLiked(podcast.id) ? 'var(--accent-border)' : 'rgba(8, 6, 13, 0.08)'}`, background: isLiked(podcast.id) ? 'var(--accent-bg)' : 'transparent', borderRadius: '999px', padding: '6px 10px', cursor: 'pointer', fontSize: '12px', color: isLiked(podcast.id) ? '#ffffff' : 'var(--text-h)', fontWeight: 600 }}
                        >
                          {isLiked(podcast.id) ? '已喜欢' : '喜欢'}
                        </motion.button>
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
            border: '1px solid rgba(255, 255, 255, 0.72)',
            background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(247, 242, 255, 0.82) 100%)',
            boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.7), 0 10px 24px rgba(76, 58, 108, 0.08)',
            color: '#5a5167',
            cursor: 'default',
            fontSize: '14px',
            fontWeight: 700,
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
        {podcasts.map((podcast, index) => {
          const allCardSeed = podcast.id * 97 + index * 53 + podcast.title.length * 11
          const allCardStylePool = [
            getFeaturedHeroCoverStyle(allCardSeed),
            getFeaturedHeroSecondaryCoverStyle(allCardSeed + 7),
            getCoverStyle(podcast.category, allCardSeed + 13),
            getCoverStyle('all', allCardSeed + 19),
          ]
          const allCardCoverStyle = allCardStylePool[Math.abs(allCardSeed + index) % allCardStylePool.length]

          return (
            <motion.div
              key={podcast.id}
              whileHover={{ y: -4, boxShadow: '0 18px 36px rgba(33, 24, 54, 0.12)' }}
              onClick={() => handlePlay(podcast)}
              onKeyDown={(event) => handleCardKeyDown(event, podcast)}
              role="button"
              tabIndex={0}
              transition={{ duration: 0.2 }}
              style={{
                border: '1px solid rgba(255, 255, 255, 0.72)',
                borderRadius: '18px',
                padding: '12px',
                display: 'flex',
                flexDirection: 'column',
                height: '100%',
                background: 'linear-gradient(180deg, rgba(255, 255, 255, 0.94) 0%, rgba(248, 244, 251, 0.92) 100%)',
                boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.72), 0 10px 28px rgba(40, 24, 72, 0.06)',
                backdropFilter: 'blur(10px)',
                cursor: 'pointer',
              }}
            >
              <div
                style={{
                  aspectRatio: '1 / 1',
                  borderRadius: '16px',
                  marginBottom: '12px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  position: 'relative',
                  overflow: 'hidden',
                  ...allCardCoverStyle,
                }}
                >
                <div
                  style={{
                    position: 'absolute',
                    right: '-26px',
                    top: '-24px',
                    width: '128px',
                    height: '128px',
                    borderRadius: '50%',
                    background: 'radial-gradient(circle, rgba(255, 255, 255, 0.28) 0%, rgba(255, 255, 255, 0) 70%)',
                    pointerEvents: 'none',
                  }}
                />
                <div
                  style={{
                    position: 'absolute',
                    left: '-34px',
                    bottom: '-38px',
                    width: '148px',
                    height: '148px',
                    borderRadius: '50%',
                    background: 'radial-gradient(circle, rgba(255, 255, 255, 0.18) 0%, rgba(255, 255, 255, 0) 68%)',
                    pointerEvents: 'none',
                  }}
                />
                <span style={{ position: 'relative', zIndex: 1, fontSize: '12px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'rgba(255, 255, 255, 0.84)', fontWeight: 700 }}>
                  Podcast / {String(index + 1).padStart(2, '0')}
                </span>
                <div style={{ position: 'relative', zIndex: 1, textAlign: 'left' }}>
                  <div style={{ fontSize: '28px', fontWeight: 700, lineHeight: 1.05, letterSpacing: '-0.04em', color: '#ffffff', overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflowWrap: 'anywhere' }}>
                    {podcast.title}
                  </div>
                  <div style={{ marginTop: '10px', fontSize: '12px', color: 'rgba(255, 255, 255, 0.84)', fontWeight: 600 }}>{getCategoryLabel(podcast.category)}</div>
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateRows: 'auto 1fr auto', flex: 1, minHeight: 0 }}>
                <div>
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
                </div>
                <div />
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', textAlign: 'left', paddingTop: '12px', alignSelf: 'end' }}>
                  <div style={{ fontSize: '12px', color: 'var(--text)' }}>
                    {new Date(podcast.published_at).toLocaleDateString()}
                  </div>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <motion.button
                      whileHover={{ scale: 1.12 }}
                      whileTap={{ scale: 0.9 }}
                      onClick={(event) => {
                        event.stopPropagation()
                        handleLikeToggle(podcast.id)
                      }}
                      style={{ border: `1px solid ${isLiked(podcast.id) ? 'var(--accent-border)' : 'rgba(8, 6, 13, 0.08)'}`, background: isLiked(podcast.id) ? 'var(--accent-bg)' : 'transparent', borderRadius: '999px', padding: '6px 10px', cursor: 'pointer', fontSize: '12px', color: isLiked(podcast.id) ? '#ffffff' : 'var(--text-h)', fontWeight: 600 }}
                    >
                      {isLiked(podcast.id) ? '已喜欢' : '喜欢'}
                    </motion.button>
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
