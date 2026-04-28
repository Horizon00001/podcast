import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'

import { useLikes } from '../context/LikesContext'
import { usePlayer } from '../context/PlayerContext'
import { useUser } from '../context/UserContext'
import type { Podcast } from '../types/podcast'
import { getCategoryLabel, getCoverStyle } from '../utils/coverStyles'
import { truncateText } from '../utils/truncate'

export function LikesPage() {
  const { likes, toggleLike } = useLikes()
  const { currentPodcast, isPlaying, play, toggle, reportAction } = usePlayer()
  const { user } = useUser()

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

  if (likes.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        style={{ padding: '72px 48px', textAlign: 'center', color: 'var(--text)' }}
      >
        <h2>暂无喜欢的播客</h2>
        <p style={{ marginTop: '8px', marginBottom: '16px' }}>在播客库中点击“喜欢”即可添加到这里</p>
        <Link to="/" style={{ color: 'var(--text-h)', textDecoration: 'none', fontWeight: 600 }}>返回播客库</Link>
      </motion.div>
    )
  }

  return (
    <main style={{ padding: '28px 32px 40px', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ marginBottom: '30px' }}>
        <div style={{ fontSize: '12px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text)', marginBottom: '10px' }}>
          资料库
        </div>
        <h1 style={{ fontSize: '34px', margin: '0 0 8px', letterSpacing: '-0.04em' }}>我的喜欢</h1>
        <p style={{ color: 'var(--text)', fontSize: '15px', lineHeight: 1.6 }}>
          已标记 {likes.length} 个节目，保留那些你第一眼就想继续回来的内容。
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '18px' }}>
        {likes.map((podcast) => {
          const isActive = currentPodcast?.id === podcast.id
          return (
            <motion.div
              key={podcast.id}
              whileHover={{ y: -3, boxShadow: '0 10px 28px rgba(0,0,0,0.08)' }}
              transition={{ duration: 0.2 }}
              style={{
                border: '1px solid var(--border)',
                borderRadius: '18px',
                padding: '12px',
                background: 'var(--bg)',
                position: 'relative',
              }}
            >
              <motion.button
                whileHover={{ scale: 1.15 }}
                whileTap={{ scale: 0.9 }}
                onClick={() => toggleLike(podcast)}
                style={{
                  position: 'absolute',
                  top: '12px',
                  right: '12px',
                  background: 'rgba(255, 255, 255, 0.92)',
                  border: '1px solid rgba(8, 6, 13, 0.08)',
                  borderRadius: '999px',
                  padding: '6px 10px',
                  cursor: 'pointer',
                  zIndex: 1,
                  color: 'var(--text-h)',
                  fontSize: '12px',
                }}
                title="取消喜欢"
              >
                移除
              </motion.button>

              <div
                style={{
                  aspectRatio: '1 / 1',
                  borderRadius: '14px',
                  marginBottom: '12px',
                  padding: '14px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  ...getCoverStyle(podcast.category, podcast.id),
                  color: '#fff',
                }}
              >
                <span style={{ fontSize: '12px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'rgba(255, 255, 255, 0.82)', fontWeight: 700 }}>
                  Liked
                </span>
                <div style={{ textAlign: 'left' }}>
                  <div style={{ fontSize: '27px', fontWeight: 700, lineHeight: 1.04, letterSpacing: '-0.05em', color: '#ffffff', overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflowWrap: 'anywhere' }}>
                    {podcast.title}
                  </div>
                  <div style={{ marginTop: '10px', fontSize: '12px', color: 'rgba(255, 255, 255, 0.84)', fontWeight: 600 }}>{getCategoryLabel(podcast.category)}</div>
                </div>
              </div>

              <Link
                to={`/podcasts/${podcast.id}`}
                style={{
                  display: 'block',
                  fontWeight: 600,
                  color: 'var(--text-h)',
                  textDecoration: 'none',
                  flex: 1,
                  fontSize: '17px',
                  lineHeight: 1.25,
                  marginBottom: '8px',
                  textAlign: 'left',
                }}
              >
                {truncateText(podcast.title, 50)}
              </Link>
              <p style={{ fontSize: '14px', color: 'var(--text)', marginBottom: '12px', lineHeight: 1.5, textAlign: 'left' }}>
                {truncateText(podcast.summary, 100)}
              </p>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', textAlign: 'left' }}>
                <span style={{ fontSize: '12px', color: 'var(--text)' }}>
                  {new Date(podcast.published_at).toLocaleDateString()}
                </span>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <Link
                    to={`/podcasts/${podcast.id}`}
                    style={{ textDecoration: 'none', color: 'var(--text-h)', fontSize: '12px', fontWeight: 600 }}
                  >
                    详情
                  </Link>
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={() => handlePlay(podcast)}
                    style={{
                      background: isActive ? '#1d1d1f' : 'transparent',
                      color: isActive ? 'white' : '#1d1d1f',
                      border: '1px solid rgba(8, 6, 13, 0.08)',
                      borderRadius: '999px',
                      padding: '6px 12px',
                      cursor: 'pointer',
                      fontSize: '12px',
                      fontWeight: 600,
                    }}
                  >
                    {isActive && isPlaying ? '暂停' : '播放'}
                  </motion.button>
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>
    </main>
  )
}
