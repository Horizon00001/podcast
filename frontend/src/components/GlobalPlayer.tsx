import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { usePlayer } from '../context/PlayerContext';
import { motion, AnimatePresence } from 'framer-motion';
import { TimelineHighlighter } from './TimelineHighlighter';
import { api } from '../services/api';
import { getCategoryLabel, getCoverStyle } from '../utils/coverStyles';
import type { ScriptLine } from '../types/podcast';

const PLAYBACK_RATES = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];

function useWindowWidth() {
  const [width, setWidth] = useState(window.innerWidth);
  useEffect(() => {
    const handler = () => setWidth(window.innerWidth);
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);
  return width;
}

interface GlobalPlayerProps {
  sidebarWidth?: number;
  desktopScale?: number;
}

export function GlobalPlayer({ sidebarWidth = 256, desktopScale = 1 }: GlobalPlayerProps) {
  const { currentPodcast, isPlaying, toggle, progress, duration, currentTime, seek, playbackRate, setPlaybackRate } = usePlayer();
  const [isExpanded, setIsExpanded] = useState(false);
  const [scriptLines, setScriptLines] = useState<ScriptLine[]>([]);
  const [scriptLoading, setScriptLoading] = useState(false);
  const [scriptError, setScriptError] = useState('');
  const [autoFollowEnabled, setAutoFollowEnabled] = useState(true);
  const [showReturnToCurrent, setShowReturnToCurrent] = useState(false);
  const autoFollowTimerRef = useRef<number | null>(null);
  const windowWidth = useWindowWidth();
  const isNarrow = windowWidth < 560;
  const isCompact = windowWidth < 720;
  const expandedScale = windowWidth > 900 ? 0.88 : 1;
  const playerLeft = windowWidth > 900 ? `calc(${sidebarWidth}px + (100vw - ${sidebarWidth}px) / 2)` : '50%';
  const playerWidth = windowWidth > 900
    ? `min(${Math.round(980 * desktopScale)}px, calc(100vw - ${sidebarWidth}px - 32px))`
    : 'min(980px, calc(100vw - 32px))';

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

  const playbackLabel = isPlaying ? '正在播放' : '已暂停';
  const scriptCount = scriptLines.length;
  const readingMinutes = Math.max(1, Math.ceil(scriptCount / 8));
  const progressStyle = {
    flexGrow: 1,
    height: '4px',
    cursor: 'pointer',
    ['--progress' as string]: `${progress}%`,
  } as React.CSSProperties;

  useEffect(() => {
    if (!currentPodcast) {
      setIsExpanded(false);
      setScriptLines([]);
      setScriptLoading(false);
      setScriptError('');
      setAutoFollowEnabled(true);
      setShowReturnToCurrent(false);
      return;
    }

    let cancelled = false;
    setScriptLoading(true);
    setScriptError('');
    setScriptLines([]);
    setAutoFollowEnabled(true);
    setShowReturnToCurrent(false);

    api.getPodcastScript(currentPodcast.id)
      .then((lines) => {
        if (cancelled) return;
        setScriptLines(lines);
      })
      .catch(() => {
        if (cancelled) return;
        setScriptLines([]);
        setScriptError('文字稿暂时加载失败');
      })
      .finally(() => {
        if (cancelled) return;
        setScriptLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [currentPodcast]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsExpanded(false);
        return;
      }

      if (event.key === ' ' && isExpanded) {
        const target = event.target as HTMLElement | null;
        const tagName = target?.tagName;
        if (tagName === 'INPUT' || tagName === 'TEXTAREA' || tagName === 'SELECT' || target?.isContentEditable) {
          return;
        }
        event.preventDefault();
        toggle();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isExpanded, toggle]);

  useEffect(() => {
    return () => {
      if (autoFollowTimerRef.current) {
        window.clearTimeout(autoFollowTimerRef.current);
      }
    };
  }, []);

  const pauseAutoFollow = () => {
    setAutoFollowEnabled(false);
    setShowReturnToCurrent(true);
    if (autoFollowTimerRef.current) {
      window.clearTimeout(autoFollowTimerRef.current);
    }
    autoFollowTimerRef.current = window.setTimeout(() => {
      setAutoFollowEnabled(true);
      setShowReturnToCurrent(false);
    }, 5000);
  };

  const resumeAutoFollow = () => {
    if (autoFollowTimerRef.current) {
      window.clearTimeout(autoFollowTimerRef.current);
    }
    setAutoFollowEnabled(true);
    setShowReturnToCurrent(false);
  };

  const openDetail = () => {
    if (!currentPodcast) return;
    setIsExpanded(true);
  };

  return (
    <AnimatePresence>
      {currentPodcast && (
        <>
          <AnimatePresence>
            {isExpanded && (
              <>
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  onClick={() => setIsExpanded(false)}
                  style={{
                    position: 'fixed',
                    inset: 0,
                    background: 'rgba(247, 246, 249, 0.58)',
                    backdropFilter: 'blur(10px)',
                    zIndex: 999,
                  }}
                />
                <motion.section
                  initial={{ opacity: 0, y: 36, x: '-50%' }}
                  animate={{ opacity: 1, y: 0, x: '-50%' }}
                  exit={{ opacity: 0, y: 36, x: '-50%' }}
                  transition={{ type: 'spring', damping: 28, stiffness: 240 }}
                  style={{
                    position: 'fixed',
                    left: '50%',
                    top: windowWidth > 900 ? '14px' : '18px',
                    bottom: windowWidth > 900 ? '14px' : '18px',
                    width: `min(${Math.round(1120 * (windowWidth > 900 ? desktopScale : 1))}px, calc((100vw - 32px) / ${expandedScale}))`,
                    maxHeight: `calc((100vh - ${windowWidth > 900 ? 28 : 36}px) / ${expandedScale})`,
                    background: 'linear-gradient(180deg, rgba(255,255,255,0.95) 0%, rgba(248,248,250,0.94) 100%)',
                    borderRadius: '34px',
                    border: '1px solid rgba(8, 6, 13, 0.06)',
                    boxShadow: '0 24px 70px rgba(8, 6, 13, 0.12)',
                    backdropFilter: 'blur(24px)',
                    zIndex: 1001,
                    boxSizing: 'border-box',
                    overflow: isCompact ? 'auto' : 'hidden',
                    display: 'grid',
                    gridTemplateRows: 'auto 1fr',
                    transform: windowWidth > 900 ? `scale(${expandedScale})` : undefined,
                    transformOrigin: 'top center',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '16px',
                        padding: windowWidth > 900 ? '12px 18px 10px' : '14px 20px 12px',
                      borderBottom: '1px solid rgba(8, 6, 13, 0.06)',
                    }}
                  >
                    <button
                      onClick={() => setIsExpanded(false)}
                      style={{
                        border: '1px solid rgba(8, 6, 13, 0.08)',
                        background: 'rgba(255,255,255,0.8)',
                        color: '#1d1d1f',
                        borderRadius: '999px',
                        padding: '8px 14px',
                        fontSize: '13px',
                        fontWeight: 600,
                        cursor: 'pointer',
                      }}
                    >
                      收起
                    </button>
                    <div style={{ fontSize: '12px', letterSpacing: '0.08em', textTransform: 'uppercase', color: '#8b8494', fontWeight: 700 }}>
                      播放详情
                    </div>
                    <Link
                      to={`/podcasts/${currentPodcast.id}`}
                      onClick={() => setIsExpanded(false)}
                      style={{ textDecoration: 'none', color: '#1d1d1f', fontSize: '13px', fontWeight: 700 }}
                    >
                      节目详情
                    </Link>
                  </div>

                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: isCompact
                        ? 'minmax(0, 1fr)'
                        : 'minmax(320px, 0.95fr) minmax(0, 1.55fr)',
                      minHeight: 0,
                      overflow: isCompact ? 'auto' : undefined,
                    }}
                  >
                    <div
                      style={{
                        padding: windowWidth > 900 ? '14px 18px 16px' : '18px 22px 20px',
                        borderRight: isCompact ? 'none' : '1px solid rgba(8, 6, 13, 0.05)',
                        borderBottom: isCompact ? '1px solid rgba(8, 6, 13, 0.05)' : 'none',
                        display: 'grid',
                        alignContent: 'start',
                        gap: windowWidth > 900 ? '14px' : '20px',
                      }}
                    >
                      <div
                        style={{
                          width: '100%',
                          maxWidth: windowWidth > 900 ? '210px' : '240px',
                          aspectRatio: '1 / 1',
                          ...getCoverStyle(currentPodcast.category),
                          borderRadius: '22px',
                          padding: '16px',
                          display: 'flex',
                          flexDirection: 'column',
                          justifyContent: 'space-between',
                          boxSizing: 'border-box',
                          boxShadow: '0 26px 46px rgba(8, 6, 13, 0.16)',
                        }}
                      >
                        <span style={{ fontSize: '12px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.84)', fontWeight: 700 }}>
                          Now Playing
                        </span>
                        <div>
                          <div style={{ fontSize: '25px', fontWeight: 700, lineHeight: 1.02, letterSpacing: '-0.06em', color: '#ffffff', overflowWrap: 'anywhere' }}>
                            {currentPodcast.title}
                          </div>
                          <div style={{ marginTop: '12px', fontSize: '13px', color: 'rgba(255,255,255,0.84)', fontWeight: 600 }}>
                            {getCategoryLabel(currentPodcast.category)}
                          </div>
                        </div>
                      </div>

                      <div style={{ textAlign: 'left' }}>
                        <div style={{ fontSize: '12px', letterSpacing: '0.08em', textTransform: 'uppercase', color: '#8b8494', marginBottom: '10px', fontWeight: 700 }}>
                          正在收听
                        </div>
                        <div style={{ fontSize: '24px', lineHeight: 1.08, letterSpacing: '-0.05em', color: '#111111', fontWeight: 700, marginBottom: '8px', overflowWrap: 'anywhere' }}>
                          {currentPodcast.title}
                        </div>
                        <div style={{ fontSize: '14px', color: '#6b6375', lineHeight: 1.6 }}>
                          {getCategoryLabel(currentPodcast.category)} · {playbackLabel} · {new Date(currentPodcast.published_at).toLocaleDateString()}
                        </div>
                      </div>

                      <div style={{ display: 'grid', gap: '14px' }}>
                        <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                          <motion.button
                            whileHover={{ scale: 1.04, y: -1 }}
                            whileTap={{ scale: 0.95 }}
                            onClick={toggle}
                            style={{
                              background: '#111111',
                              color: 'white',
                              border: 'none',
                              borderRadius: '50%',
                            width: windowWidth > 900 ? '56px' : '64px',
                            height: windowWidth > 900 ? '56px' : '64px',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              cursor: 'pointer',
                              fontSize: '20px',
                              fontWeight: 700,
                              padding: 0,
                              boxShadow: '0 16px 30px rgba(17, 17, 17, 0.22)',
                            }}
                            aria-label={isPlaying ? '暂停播放' : '开始播放'}
                          >
                            {isPlaying ? 'II' : '>'}
                          </motion.button>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', width: '100%', minWidth: 0 }}>
                          <span style={{ fontSize: '12px', minWidth: '35px', color: '#6b6375', fontVariantNumeric: 'tabular-nums' }}>{formatTime(currentTime)}</span>
                          <input
                            className="global-player-progress"
                            type="range"
                            min="0"
                            max="100"
                            step="0.1"
                            value={progress}
                            onChange={handleProgressChange}
                            style={progressStyle}
                          />
                          <span style={{ fontSize: '12px', minWidth: '35px', color: '#6b6375', fontVariantNumeric: 'tabular-nums' }}>{formatTime(duration || 0)}</span>
                        </div>

                        <div style={{ display: 'grid', gap: '10px' }}>
                          <div style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: '#8b8494', fontWeight: 700 }}>
                            Speed
                          </div>
                          <div
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '6px',
                              padding: '4px',
                              borderRadius: '999px',
                              background: 'rgba(255,255,255,0.8)',
                              border: '1px solid rgba(8, 6, 13, 0.06)',
                              width: 'fit-content',
                            }}
                          >
                            {PLAYBACK_RATES.filter((rate) => [0.75, 1, 1.25, 1.5, 2].includes(rate)).map((rate) => {
                              const isSelected = playbackRate === rate
                              return (
                                <button
                                  key={rate}
                                  onClick={() => setPlaybackRate(rate)}
                                  style={{
                                    border: 'none',
                                    background: isSelected ? '#111111' : 'transparent',
                                    color: isSelected ? '#ffffff' : '#5f5967',
                                    borderRadius: '999px',
                                    padding: '6px 10px',
                                    fontSize: '12px',
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                    transition: 'background 0.2s ease, color 0.2s ease',
                                  }}
                                  aria-pressed={isSelected}
                                >
                                  {rate}x
                                </button>
                              )
                            })}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div
                      style={{
                        padding: windowWidth > 900 ? '22px 22px 24px' : '28px 28px 30px',
                        minHeight: 0,
                        display: 'grid',
                        gridTemplateRows: 'auto auto 1fr',
                        gap: windowWidth > 900 ? '12px' : '16px',
                      }}
                    >
                      <div>
                        <h2 style={{ fontSize: windowWidth > 900 ? '25px' : '28px', lineHeight: 1.05, letterSpacing: '-0.04em', margin: '0 0 6px', color: '#111111' }}>
                          文字稿
                        </h2>
                        <p style={{ fontSize: '14px', color: '#6b6375', lineHeight: 1.6 }}>
                          {scriptCount} 句文字稿，约 {readingMinutes} 分钟阅读。点击任意句子可跳转到对应时间。
                        </p>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
                        <div style={{ fontSize: '12px', color: '#8b8494', fontWeight: 600 }}>
                          {autoFollowEnabled ? '已同步当前播放进度' : '你正在浏览其他段落'}
                        </div>
                        {showReturnToCurrent && (
                          <button
                            onClick={resumeAutoFollow}
                            style={{
                              border: '1px solid rgba(8, 6, 13, 0.08)',
                              background: 'rgba(255,255,255,0.92)',
                              color: '#1d1d1f',
                              borderRadius: '999px',
                              padding: '7px 12px',
                              fontSize: '12px',
                              fontWeight: 600,
                              cursor: 'pointer',
                            }}
                          >
                            回到当前播放
                          </button>
                        )}
                      </div>

                      <div
                        style={{
                          minHeight: 0,
                          overflow: 'hidden',
                        }}
                      >
                        {scriptLoading ? (
                          <div style={{ height: '100%', display: 'grid', placeItems: 'center', color: '#6b6375', fontSize: '14px' }}>
                            文字稿加载中...
                          </div>
                        ) : scriptError ? (
                          <div style={{ height: '100%', display: 'grid', placeItems: 'center' }}>
                            <div style={{ textAlign: 'center' }}>
                              <div style={{ color: '#1d1d1f', fontWeight: 600, marginBottom: '8px' }}>{scriptError}</div>
                              <div style={{ color: '#6b6375', fontSize: '14px' }}>播放器仍可继续使用，你也可以稍后再试。</div>
                            </div>
                          </div>
                        ) : scriptLines.length === 0 ? (
                          <div style={{ height: '100%', display: 'grid', placeItems: 'center' }}>
                            <div style={{ textAlign: 'center' }}>
                              <div style={{ color: '#1d1d1f', fontWeight: 600, marginBottom: '8px' }}>暂时还没有可同步的文字稿</div>
                              <div style={{ color: '#6b6375', fontSize: '14px' }}>你仍然可以继续播放当前节目。</div>
                            </div>
                          </div>
                        ) : (
                          <TimelineHighlighter
                            scriptLines={scriptLines}
                            currentTime={currentTime}
                            onSeek={seek}
                            autoFollow={autoFollowEnabled}
                            onManualScroll={pauseAutoFollow}
                            variant="detail"
                            style={{ height: '100%' }}
                          />
                        )}
                      </div>
                    </div>
                  </div>
                </motion.section>
              </>
            )}
          </AnimatePresence>

          {!isExpanded && (
            <motion.div
              initial={{ y: 90, x: '-50%' }}
              animate={{ y: 0, x: '-50%' }}
              exit={{ y: 90, x: '-50%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              style={{
                position: 'fixed',
                bottom: '16px',
                left: playerLeft,
                width: playerWidth,
                minHeight: '62px',
                background: 'linear-gradient(180deg, rgba(255,255,255,0.92) 0%, rgba(248,248,250,0.9) 100%)',
                border: '1px solid rgba(8, 6, 13, 0.06)',
                borderRadius: '28px',
                backdropFilter: 'blur(22px)',
                display: 'grid',
                gridTemplateColumns: isNarrow
                  ? 'minmax(0, 0.95fr) minmax(0, 1.45fr) auto'
                  : isCompact
                    ? 'minmax(0, 0.95fr) minmax(0, 1.8fr) auto'
                    : 'minmax(0, 1fr) minmax(0, 2.1fr) auto',
                alignItems: 'center',
                gap: isNarrow ? '7px' : isCompact ? '9px' : '12px',
                padding: isNarrow ? '8px 12px' : '9px 16px',
                zIndex: 1000,
                boxShadow: '0 14px 30px rgba(8, 6, 13, 0.08), 0 30px 80px rgba(8, 6, 13, 0.12)',
                boxSizing: 'border-box',
              }}
            >
            <button
              onClick={openDetail}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: isNarrow ? '10px' : '12px',
                minWidth: 0,
                border: 'none',
                background: 'transparent',
                padding: 0,
                cursor: 'pointer',
                textAlign: 'left',
              }}
              aria-label="展开播放详情"
            >
              <div style={{
                width: isNarrow ? '44px' : '48px',
                height: isNarrow ? '44px' : '48px',
                ...getCoverStyle(currentPodcast.category),
                borderRadius: '14px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                color: '#fff',
                padding: '8px',
                boxSizing: 'border-box',
                fontSize: '9px',
                fontWeight: 700,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                boxShadow: '0 10px 20px rgba(8, 6, 13, 0.14)'
              }}>
                <span style={{ color: 'rgba(255,255,255,0.86)', textShadow: '0 1px 2px rgba(0, 0, 0, 0.28)' }}>Now</span>
                <span style={{ color: '#ffffff', textShadow: '0 1px 2px rgba(0, 0, 0, 0.28)' }}>播客</span>
              </div>
              <div style={{ textAlign: 'left', overflow: 'hidden' }}>
                <div style={{ fontSize: isNarrow ? '14px' : '15px', fontWeight: 700, color: 'var(--text-h)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', letterSpacing: '-0.02em' }}>
                  {currentPodcast.title}
                </div>
                <div style={{ fontSize: isNarrow ? '11px' : '12px', color: '#6b6375', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', marginTop: '3px' }}>
                  {getCategoryLabel(currentPodcast.category)} · {playbackLabel}
                </div>
              </div>
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: isNarrow ? '7px' : '10px', minWidth: 0, width: '100%' }}>
              <motion.button
                whileHover={{ scale: 1.05, y: -1 }}
                whileTap={{ scale: 0.95 }}
                onClick={toggle}
                style={{
                  flexShrink: 0,
                  background: '#111111',
                  color: 'white',
                  border: 'none',
                  borderRadius: '50%',
                  width: isNarrow ? '34px' : '36px',
                  height: isNarrow ? '34px' : '36px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  fontSize: isNarrow ? '12px' : '13px',
                  fontWeight: 600,
                  padding: 0,
                  boxShadow: '0 10px 24px rgba(17, 17, 17, 0.24)'
                }}
                aria-label={isPlaying ? '暂停播放' : '开始播放'}
              >
                {isPlaying ? 'II' : '>'}
              </motion.button>
              <div style={{ display: 'flex', alignItems: 'center', gap: isNarrow ? '7px' : '10px', width: '100%', minWidth: 0 }}>
                <span style={{ fontSize: '11px', minWidth: '32px', color: '#6b6375', fontVariantNumeric: 'tabular-nums' }}>{formatTime(currentTime)}</span>
                <input
                  className="global-player-progress"
                  type="range"
                  min="0"
                  max="100"
                  step="0.1"
                  value={progress}
                  onChange={handleProgressChange}
                  style={progressStyle}
                />
                <span style={{ fontSize: '11px', minWidth: '32px', color: '#6b6375', fontVariantNumeric: 'tabular-nums' }}>{formatTime(duration || 0)}</span>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: isCompact ? '7px' : '8px', minWidth: 0, flexShrink: 0 }}>
              <button
                onClick={openDetail}
                style={{
                  border: '1px solid rgba(8, 6, 13, 0.08)',
                  background: 'rgba(255,255,255,0.82)',
                  color: '#1d1d1f',
                  borderRadius: '999px',
                  padding: isCompact ? '6px 9px' : '6px 11px',
                  fontSize: '11px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                }}
              >
                展开
              </button>
              {!isCompact && (
                <>
                  <div style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: '#8b8494', fontWeight: 700 }}>
                    Speed
                  </div>
                  <div
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '3px',
                      borderRadius: '999px',
                      background: 'rgba(255,255,255,0.76)',
                      border: '1px solid rgba(8, 6, 13, 0.06)',
                    }}
                  >
                    {(isCompact
                      ? PLAYBACK_RATES.filter((rate) => [1, 1.5, 2].includes(rate))
                      : PLAYBACK_RATES.filter((rate) => [0.75, 1, 1.25, 1.5, 2].includes(rate))
                    ).map((rate) => {
                      const isSelected = playbackRate === rate
                      return (
                        <button
                          key={rate}
                          onClick={() => setPlaybackRate(rate)}
                          style={{
                            border: 'none',
                            background: isSelected ? '#111111' : 'transparent',
                            color: isSelected ? '#ffffff' : '#5f5967',
                            borderRadius: '999px',
                            padding: '5px 8px',
                            fontSize: '11px',
                            fontWeight: 600,
                            cursor: 'pointer',
                            transition: 'background 0.2s ease, color 0.2s ease',
                          }}
                          aria-pressed={isSelected}
                        >
                          {rate}x
                        </button>
                      )
                    })}
                  </div>
                </>
              )}
            </div>
            </motion.div>
          )}
        </>
      )}
    </AnimatePresence>
  );
}
