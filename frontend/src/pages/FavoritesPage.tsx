// src/pages/FavoritesPage.tsx
import { useFavorites } from '../context/FavoritesContext';
import { usePlayer } from '../context/PlayerContext';
import { useUser } from '../context/UserContext'; 
import { Link } from 'react-router-dom';
import type { Podcast } from '../types/podcast';

export function FavoritesPage() {
  const { favorites, toggleFavorite } = useFavorites();
  const { currentPodcast, isPlaying, play, toggle, reportAction } = usePlayer();
  const { user } = useUser(); // 如果需要上报，请导入 useUser

  const handlePlay = (podcast: Podcast) => {
    if (currentPodcast?.id === podcast.id) {
      toggle();
    } else {
      play(podcast);
      if (user) {
        void reportAction('play', podcast, { listen_duration_ms: 0, progress_pct: 0 });
      }
    }
  };

  if (favorites.length === 0) {
    return (
      <div style={{ padding: '48px', textAlign: 'center', color: 'var(--text)' }}>
        <div style={{ fontSize: '64px', marginBottom: '16px' }}>❤️</div>
        <h2>暂无收藏的播客</h2>
        <p style={{ marginTop: '8px' }}>在播客库中点击 🤍 即可添加收藏</p>
        <Link to="/" style={{ color: 'var(--accent)', textDecoration: 'none' }}>返回播客库</Link>
      </div>
    );
  }

  return (
    <main style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
        <span style={{ fontSize: '32px' }}>❤️</span>
        <h1 style={{ fontSize: '28px' }}>我的收藏 ({favorites.length})</h1>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
        gap: '20px'
      }}>
        {favorites.map(podcast => {
          const isActive = currentPodcast?.id === podcast.id;
          return (
            <div
              key={podcast.id}
              style={{
                border: '1px solid var(--border)',
                borderRadius: '16px',
                padding: '16px',
                background: isActive ? 'var(--accent-bg)' : 'var(--bg)',
                transition: 'all 0.2s',
                position: 'relative'
              }}
            >
              {/* 移除收藏的按钮 */}
              <button
                onClick={() => toggleFavorite(podcast)}
                style={{
                  position: 'absolute',
                  top: '12px',
                  right: '12px',
                  background: 'transparent',
                  border: 'none',
                  fontSize: '24px',
                  cursor: 'pointer',
                  zIndex: 1
                }}
                title="取消收藏"
              >
                ❌
              </button>

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
          );
        })}
      </div>
    </main>
  );
}