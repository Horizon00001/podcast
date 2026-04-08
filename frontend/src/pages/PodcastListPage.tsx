import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import type { Podcast } from '../types/podcast'
import { usePlayer } from '../context/PlayerContext'

export function PodcastListPage() {
  const [podcasts, setPodcasts] = useState<Podcast[]>([])
  const [error, setError] = useState('')
  const { currentPodcast, isPlaying, play, toggle } = usePlayer()

  useEffect(() => {
    api
      .listPodcasts()
      .then(setPodcasts)
      .catch((e) => setError((e as Error).message))
  }, [])

  const handlePlay = (podcast: Podcast) => {
    if (currentPodcast?.id === podcast.id) {
      toggle()
    } else {
      play(podcast)
    }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'Asia/Shanghai'
    });
  };

  return (
    <main style={{
      padding: '24px',
      maxWidth: '1200px',
      margin: '0 auto',
      textAlign: 'left'
    }}>
      <h1 style={{ fontSize: '32px', marginBottom: '24px' }}>我的播客库</h1>
      {error ? <p style={{ color: 'red' }}>加载失败：{error}</p> : null}

      <div style={{
        background: 'var(--bg)',
        borderRadius: '12px',
        overflow: 'hidden',
        border: '1px solid var(--border)',
        boxShadow: 'var(--shadow)'
      }}>
        <table style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: '15px'
        }}>
          <thead>
            <tr style={{
              borderBottom: '1px solid var(--border)',
              color: 'var(--text)',
              fontSize: '12px',
              textTransform: 'uppercase',
              letterSpacing: '1px'
            }}>
              <th style={{ padding: '12px 24px', textAlign: 'center', width: '60px' }}>#</th>
              <th style={{ padding: '12px 24px', textAlign: 'left' }}>标题</th>
              <th style={{ padding: '12px 24px', textAlign: 'left' }}>简介</th>
              <th style={{ padding: '12px 24px', textAlign: 'left', width: '180px' }}>发布日期</th>
              <th style={{ padding: '12px 24px', textAlign: 'center', width: '100px' }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {podcasts.map((item, index) => {
              const isActive = currentPodcast?.id === item.id;
              return (
                <tr
                  key={item.id}
                  style={{
                    borderBottom: '1px solid var(--border)',
                    background: isActive ? 'var(--accent-bg)' : 'transparent',
                    transition: 'background 0.2s',
                    cursor: 'default'
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) e.currentTarget.style.background = 'var(--social-bg)';
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) e.currentTarget.style.background = 'transparent';
                  }}
                >
                  <td style={{ padding: '16px 24px', textAlign: 'center', color: isActive ? 'var(--accent)' : 'inherit' }}>
                    {isActive && isPlaying ? (
                      <span style={{ fontSize: '18px' }}>🎵</span>
                    ) : (
                      index + 1
                    )}
                  </td>
                  <td style={{ padding: '16px 24px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div style={{
                        width: '40px',
                        height: '40px',
                        background: 'var(--border)',
                        borderRadius: '4px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '20px'
                      }}>
                        🎙️
                      </div>
                      <Link
                        to={`/podcasts/${item.id}`}
                        style={{
                          textDecoration: 'none',
                          color: isActive ? 'var(--accent)' : 'var(--text-h)',
                          fontWeight: 500
                        }}
                      >
                        {item.title}
                      </Link>
                    </div>
                  </td>
                  <td style={{ padding: '16px 24px', color: 'var(--text)', maxWidth: '300px' }}>
                    <div style={{
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}>
                      {item.summary}
                    </div>
                  </td>
                  <td style={{ padding: '16px 24px', color: 'var(--text)' }}>
                    {formatDate(item.published_at)}
                  </td>
                  <td style={{ padding: '16px 24px', textAlign: 'center' }}>
                    <button
                      onClick={() => handlePlay(item)}
                      style={{
                        background: isActive ? 'var(--accent)' : 'transparent',
                        color: isActive ? 'white' : 'var(--accent)',
                        border: `1px solid var(--accent)`,
                        borderRadius: '50%',
                        width: '32px',
                        height: '32px',
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: 'pointer',
                        fontSize: '14px',
                        transition: 'all 0.2s'
                      }}
                    >
                      {isActive && isPlaying ? '⏸️' : '▶️'}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {podcasts.length === 0 && (
          <div style={{ padding: '64px', textAlign: 'center', color: 'var(--text)' }}>
            目前还没有播客，去生成一个吧！
          </div>
        )}
      </div>
    </main>
  )
}
