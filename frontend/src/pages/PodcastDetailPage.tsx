import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { TimelineHighlighter } from '../components/TimelineHighlighter'
import { api } from '../services/api'
import type { Podcast, ScriptLine } from '../types/podcast'
import { usePlayer } from '../context/PlayerContext'
import { useUser } from '../context/UserContext'
import { getCategoryLabel, getCoverStyle } from '../utils/coverStyles'

const PLAYBACK_RATES = [0.75, 1, 1.25, 1.5, 2]

function formatTime(seconds: number) {
  if (!Number.isFinite(seconds) || seconds <= 0) return '0:00'
  const minutes = Math.floor(seconds / 60)
  const rest = Math.floor(seconds % 60)
  return `${minutes}:${rest.toString().padStart(2, '0')}`
}

export function PodcastDetailPage() {
  const { id } = useParams()
  const [podcast, setPodcast] = useState<Podcast | null>(null)
  const [scriptLines, setScriptLines] = useState<ScriptLine[]>([])
  const [pageError, setPageError] = useState('')
  const [viewportWidth, setViewportWidth] = useState(() => window.innerWidth)
  const {
    currentPodcast,
    isPlaying,
    play,
    toggle,
    currentTime,
    duration,
    progress,
    seek,
    playbackRate,
    setPlaybackRate,
    error: playerError,
    reportAction,
  } = usePlayer()
  const { user } = useUser()

  useEffect(() => {
    const handleResize = () => setViewportWidth(window.innerWidth)

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

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
      .catch((e) => setPageError((e as Error).message))
  }, [id])

  if (pageError) {
    return (
      <main style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: '24px' }}>
        <div style={{ maxWidth: '420px', textAlign: 'center', padding: '28px', borderRadius: '28px', border: '1px solid rgba(8, 6, 13, 0.08)', background: '#fff' }}>
          <div style={{ fontSize: '22px', fontWeight: 800, marginBottom: '8px', color: '#111111' }}>加载失败</div>
          <p style={{ margin: '0 0 18px', color: '#6b6375', lineHeight: 1.6 }}>{pageError}</p>
          <Link to="/" style={{ color: '#111111', fontWeight: 700, textDecoration: 'none' }}>返回新发现</Link>
        </div>
      </main>
    )
  }

  if (!podcast) {
    return (
      <main style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: '24px', color: '#6b6375' }}>
        正在打开播放器...
      </main>
    )
  }

  const isCurrent = currentPodcast?.id === podcast.id
  const isNarrow = viewportWidth < 1200
  const isCompact = viewportWidth < 760
  const coverSize = isCompact ? 220 : isNarrow ? 260 : 300
  const playButtonLabel = isCurrent ? (isPlaying ? '暂停播放' : '继续播放') : '开始播放'
  const activeTime = isCurrent ? currentTime : 0
  const activeProgress = isCurrent ? progress : 0
  const readingMinutes = Math.max(1, Math.ceil(scriptLines.length / 8))
  const progressTrack = `linear-gradient(90deg, #111111 ${Math.min(Math.max(activeProgress, 0), 100)}%, rgba(8, 6, 13, 0.1) ${Math.min(Math.max(activeProgress, 0), 100)}%)`

  const handlePlay = () => {
    if (isCurrent) {
      toggle()
    } else {
      play(podcast)
      if (user) {
        void reportAction('play', podcast, { listen_duration_ms: 0, progress_pct: 0 })
      }
    }
  }

  const handleProgressChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const nextProgress = Number(event.target.value)
    if (!duration) return
    seek((nextProgress / 100) * duration)
  }

  return (
    <main
      style={{
        minHeight: '100vh',
        width: '100%',
        boxSizing: 'border-box',
        padding: `${isCompact ? 18 : 30}px clamp(14px, 3vw, 32px) 36px`,
        maxWidth: '1240px',
        margin: '0 auto',
        textAlign: 'left',
        background: '#ffffff',
      }}
    >
      <Link
        to="/"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '18px',
          color: '#5f5967',
          textDecoration: 'none',
          fontSize: '13px',
          fontWeight: 700,
        }}
      >
        <span aria-hidden="true">←</span>
        返回新发现
      </Link>

      <section
        style={{
          borderRadius: isCompact ? '28px' : '36px',
          background: 'linear-gradient(135deg, #f8f7f4 0%, #ffffff 48%, #f1f2f7 100%)',
          border: '1px solid rgba(8, 6, 13, 0.06)',
          boxShadow: '0 24px 80px rgba(8, 6, 13, 0.08)',
          overflow: 'hidden',
          marginBottom: '24px',
        }}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: isNarrow ? 'minmax(0, 1fr)' : `${coverSize}px minmax(0, 1fr)`,
            gap: isCompact ? '20px' : '30px',
            padding: isCompact ? '18px' : '30px',
            alignItems: 'stretch',
          }}
        >
          <div
            style={{
              width: isNarrow ? '100%' : `${coverSize}px`,
              maxWidth: isCompact ? '100%' : `${coverSize}px`,
              minHeight: isCompact ? '260px' : `${coverSize}px`,
              justifySelf: isNarrow ? 'stretch' : 'start',
              ...getCoverStyle(podcast.category),
              borderRadius: '30px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              padding: isCompact ? '20px' : '24px',
              color: '#fff',
              boxSizing: 'border-box',
              boxShadow: '0 28px 60px rgba(8, 6, 13, 0.14)',
            }}
          >
            <span style={{ fontSize: '12px', letterSpacing: '0.12em', textTransform: 'uppercase', color: 'rgba(255, 255, 255, 0.82)', fontWeight: 800 }}>
              Immersive Player
            </span>
            <div>
              <div style={{ fontSize: isCompact ? '30px' : '34px', fontWeight: 800, lineHeight: 0.98, letterSpacing: '-0.07em', color: '#ffffff', overflowWrap: 'anywhere' }}>
                {podcast.title}
              </div>
              <div style={{ marginTop: '14px', fontSize: '14px', color: 'rgba(255, 255, 255, 0.84)', fontWeight: 700 }}>{getCategoryLabel(podcast.category)}</div>
            </div>
          </div>

          <div style={{ minWidth: 0, display: 'grid', alignContent: 'space-between', gap: '24px' }}>
            <div>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap', marginBottom: '14px' }}>
                <span style={{ padding: '7px 12px', borderRadius: '999px', background: 'rgba(255,255,255,0.82)', border: '1px solid rgba(8, 6, 13, 0.06)', color: '#4a4453', fontSize: '13px', fontWeight: 700 }}>
                  {getCategoryLabel(podcast.category)}
                </span>
                <span style={{ color: '#8b8494', fontSize: '13px', fontWeight: 600 }}>
                  {new Date(podcast.published_at).toLocaleDateString()}
                </span>
                <span style={{ color: '#8b8494', fontSize: '13px', fontWeight: 600 }}>
                  {scriptLines.length} 句文字稿 · 约 {readingMinutes} 分钟阅读
                </span>
              </div>
              <h1 style={{ fontSize: isCompact ? '34px' : isNarrow ? '44px' : '56px', margin: '0 0 16px', letterSpacing: '-0.07em', lineHeight: 0.95, overflowWrap: 'anywhere', color: '#111111' }}>{podcast.title}</h1>
              <p style={{ fontSize: isCompact ? '15px' : '17px', color: '#4a4453', margin: 0, lineHeight: 1.7, maxWidth: '760px' }}>{podcast.summary}</p>
            </div>

            <div
              style={{
                borderRadius: '28px',
                padding: isCompact ? '16px' : '18px',
                background: 'rgba(255,255,255,0.78)',
                border: '1px solid rgba(8, 6, 13, 0.06)',
                backdropFilter: 'blur(18px)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '16px', flexWrap: 'wrap' }}>
                <button
                  onClick={handlePlay}
                  aria-label={playButtonLabel}
                  style={{
                    background: '#111111',
                    color: 'white',
                    border: 'none',
                    borderRadius: '50%',
                    width: isCompact ? '58px' : '66px',
                    height: isCompact ? '58px' : '66px',
                    display: 'inline-grid',
                    placeItems: 'center',
                    fontSize: '20px',
                    fontWeight: 800,
                    cursor: 'pointer',
                    boxShadow: '0 18px 34px rgba(17, 17, 17, 0.22)',
                  }}
                >
                  {isCurrent && isPlaying ? 'II' : '>'}
                </button>
                  <div style={{ flex: '1 1 180px', minWidth: 0 }}>
                    <div style={{ color: '#111111', fontSize: '16px', fontWeight: 800, marginBottom: '4px' }}>{playButtonLabel}</div>
                  <div style={{ color: '#6b6375', fontSize: '13px' }}>{isCurrent ? '正在同步当前播放进度' : '点击后从这一集开始播放'}</div>
                </div>
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px', borderRadius: '999px', background: '#f2f1ee' }}>
                  {PLAYBACK_RATES.map((rate) => {
                    const selected = playbackRate === rate
                    return (
                      <button
                        key={rate}
                        onClick={() => setPlaybackRate(rate)}
                        aria-pressed={selected}
                        style={{
                          border: 'none',
                          background: selected ? '#111111' : 'transparent',
                          color: selected ? '#ffffff' : '#5f5967',
                          borderRadius: '999px',
                          padding: '7px 10px',
                          fontSize: '12px',
                          fontWeight: 700,
                          cursor: 'pointer',
                        }}
                      >
                        {rate}x
                      </button>
                    )
                  })}
                </div>
              </div>

              <div style={{ display: 'grid', gap: '9px' }}>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="0.1"
                  value={activeProgress || 0}
                  onChange={handleProgressChange}
                  disabled={!isCurrent || !duration}
                  aria-label="播放进度"
                  style={{
                    width: '100%',
                    accentColor: '#111111',
                    cursor: isCurrent && duration ? 'pointer' : 'not-allowed',
                    background: progressTrack,
                  }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', color: '#6b6375', fontSize: '12px', fontVariantNumeric: 'tabular-nums' }}>
                  <span>{formatTime(activeTime)}</span>
                  <span>{formatTime(isCurrent ? duration : 0)}</span>
                </div>
              </div>

              {isCurrent && playerError && (
                <div style={{ marginTop: '12px', color: '#9c3b2f', fontSize: '13px', lineHeight: 1.5 }}>
                  {playerError}
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      <section
        style={{
          display: 'grid',
          gridTemplateColumns: isNarrow ? 'minmax(0, 1fr)' : '300px minmax(0, 1fr)',
          gap: '20px',
          alignItems: 'start',
        }}
      >
        <aside
          style={{
            position: isNarrow ? 'static' : 'sticky',
            top: '24px',
            borderRadius: '26px',
            padding: '20px',
            background: '#f7f6f2',
            border: '1px solid rgba(8, 6, 13, 0.06)',
          }}
        >
          <div style={{ fontSize: '12px', letterSpacing: '0.12em', textTransform: 'uppercase', color: '#8b8494', fontWeight: 800, marginBottom: '12px' }}>Listening Notes</div>
          <h2 style={{ margin: '0 0 10px', fontSize: '26px', lineHeight: 1.05, letterSpacing: '-0.05em', color: '#111111' }}>文字稿同步</h2>
          <p style={{ margin: '0 0 16px', color: '#6b6375', fontSize: '14px', lineHeight: 1.7 }}>
            点击任意句子跳转到对应时间。播放当前节目时，正在播放的句子会自动高亮。
          </p>
          <div style={{ display: 'grid', gap: '10px' }}>
            <div style={{ padding: '13px 14px', borderRadius: '18px', background: '#ffffff', border: '1px solid rgba(8, 6, 13, 0.05)' }}>
              <div style={{ color: '#8b8494', fontSize: '12px', fontWeight: 700, marginBottom: '4px' }}>句子数量</div>
              <div style={{ color: '#111111', fontSize: '22px', fontWeight: 800 }}>{scriptLines.length}</div>
            </div>
            <div style={{ padding: '13px 14px', borderRadius: '18px', background: '#ffffff', border: '1px solid rgba(8, 6, 13, 0.05)' }}>
              <div style={{ color: '#8b8494', fontSize: '12px', fontWeight: 700, marginBottom: '4px' }}>当前状态</div>
              <div style={{ color: '#111111', fontSize: '15px', fontWeight: 800 }}>{isCurrent && isPlaying ? '正在播放' : isCurrent ? '已选中这一集' : '尚未播放'}</div>
            </div>
          </div>
        </aside>

        <div
          style={{
            minHeight: '420px',
            maxHeight: isCompact ? 'none' : 'calc(100vh - 72px)',
            overflow: 'hidden',
            borderRadius: '30px',
            padding: isCompact ? '14px' : '18px',
            background: '#f9f8f5',
            border: '1px solid rgba(8, 6, 13, 0.06)',
          }}
        >
          <TimelineHighlighter
            scriptLines={scriptLines}
            currentTime={activeTime}
            onSeek={seek}
            variant="detail"
            style={{ height: isCompact ? 'auto' : 'calc(100vh - 110px)' }}
          />
        </div>
      </section>
    </main>
  )
}
