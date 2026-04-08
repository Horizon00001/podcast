import React from 'react';
import { usePlayer } from '../context/PlayerContext';

const PLAYBACK_RATES = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];

export function GlobalPlayer() {
  const { currentPodcast, isPlaying, toggle, progress, duration, currentTime, seek, playbackRate, setPlaybackRate } = usePlayer();

  if (!currentPodcast) return null;

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleProgressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseFloat(e.target.value);
    const time = (value / 100) * duration;
    seek(time);
  };

  return (
    <div style={{
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      height: '90px',
      background: 'var(--bg)',
      borderTop: '1px solid var(--border)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px',
      zIndex: 1000,
      boxShadow: '0 -4px 12px rgba(0,0,0,0.1)'
    }}>
      {/* Track Info */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', width: '30%' }}>
        <div style={{
          width: '56px',
          height: '56px',
          background: 'var(--accent-bg)',
          borderRadius: '4px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '24px'
        }}>
          🎙️
        </div>
        <div style={{ textAlign: 'left', overflow: 'hidden' }}>
          <div style={{ fontWeight: 600, color: 'var(--text-h)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {currentPodcast.title}
          </div>
          <div style={{ fontSize: '14px', color: 'var(--text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {currentPodcast.summary}
          </div>
        </div>
      </div>

      {/* Controls */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', width: '40%' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
          <button
            onClick={toggle}
            style={{
              background: 'var(--accent)',
              color: 'white',
              border: 'none',
              borderRadius: '50%',
              width: '40px',
              height: '40px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              fontSize: '18px'
            }}
          >
            {isPlaying ? '⏸️' : '▶️'}
          </button>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', width: '100%' }}>
          <span style={{ fontSize: '12px', minWidth: '35px' }}>{formatTime(currentTime)}</span>
          <input
            type="range"
            min="0"
            max="100"
            step="0.1"
            value={progress}
            onChange={handleProgressChange}
            style={{
              flexGrow: 1,
              height: '4px',
              accentColor: 'var(--accent)',
              cursor: 'pointer'
            }}
          />
          <span style={{ fontSize: '12px', minWidth: '35px' }}>{formatTime(duration || 0)}</span>
        </div>
      </div>

      {/* Volume & Speed */}
      <div style={{ width: '30%', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '12px' }}>
        <select
          value={playbackRate}
          onChange={(e) => setPlaybackRate(parseFloat(e.target.value))}
          style={{
            background: 'var(--accent-bg)',
            color: 'var(--text)',
            border: '1px solid var(--border)',
            borderRadius: '4px',
            padding: '4px 8px',
            fontSize: '12px',
            cursor: 'pointer',
            outline: 'none'
          }}
        >
          {PLAYBACK_RATES.map(rate => (
            <option key={rate} value={rate}>{rate}x</option>
          ))}
        </select>
        <span style={{ fontSize: '18px' }}>🔊</span>
        <div style={{ width: '100px', height: '4px', background: 'var(--border)', borderRadius: '2px', position: 'relative' }}>
          <div style={{ position: 'absolute', top: 0, left: 0, height: '100%', width: '80%', background: 'var(--accent)', borderRadius: '2px' }} />
        </div>
      </div>
    </div>
  );
}
