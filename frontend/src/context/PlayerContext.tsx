import React, { createContext, useContext, useState, useRef, useEffect } from 'react';
import type { Podcast } from '../types/podcast';
import { api } from '../services/api';
import { useUser } from './UserContext';

interface PlayerContextType {
  currentPodcast: Podcast | null;
  isPlaying: boolean;
  play: (podcast: Podcast) => void;
  pause: () => void;
  toggle: () => void;
  reportAction: (action: 'play' | 'pause' | 'resume' | 'complete' | 'skip' | 'like' | 'favorite', podcast?: Podcast, payload?: { listen_duration_ms?: number; progress_pct?: number; session_id?: string; recommendation_request_id?: string }) => Promise<unknown> | undefined;
  setRecommendationRequestId: (id: string) => void;
  progress: number; // 0-100
  duration: number; // in seconds
  currentTime: number; // in seconds
  seek: (time: number) => void;
  playbackRate: number;
  setPlaybackRate: (rate: number) => void;
  error: string;
}

const PlayerContext = createContext<PlayerContextType | undefined>(undefined);

function normalizeAudioPath(audioUrl: string) {
  if (!audioUrl) return '';
  if (audioUrl.startsWith('http')) return audioUrl;
  if (audioUrl.startsWith('/audio/podcasts/')) return audioUrl;

  const legacyPodcastMatch = audioUrl.match(/^\/audio\/([^/]+)\/(.+)\/podcast_full\.mp3$/);
  if (legacyPodcastMatch) {
    const [, category, slug] = legacyPodcastMatch;
    return `/audio/podcasts/${category}/${slug}/audio/podcast_full.mp3`;
  }

  return audioUrl;
}

export const PlayerProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useUser();
  const [currentPodcast, setCurrentPodcast] = useState<Podcast | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [playbackRate, setPlaybackRateState] = useState(1);
  const [error, setError] = useState('');
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const sessionIdRef = useRef(`session-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`);
  const recommendationRequestIdRef = useRef('');
  const currentPodcastRef = useRef<Podcast | null>(null);
  const userRef = useRef(user);

  useEffect(() => {
    currentPodcastRef.current = currentPodcast;
  }, [currentPodcast]);

  useEffect(() => {
    userRef.current = user;
  }, [user]);

  useEffect(() => {
    if (!audioRef.current) {
      audioRef.current = new Audio();
      audioRef.current.preload = 'auto';
    }

    const audio = audioRef.current;

    const updateProgress = () => {
      setCurrentTime(audio.currentTime);
      setProgress((audio.currentTime / audio.duration) * 100);
    };

    const handleLoadedMetadata = () => {
      setError('');
      setDuration(audio.duration);
    };

    const handleError = () => {
      setIsPlaying(false);
      setError('当前播客音频加载失败，请稍后重试');
    };

    const handleEnded = () => {
      if (currentPodcastRef.current && userRef.current) {
        void api.reportInteraction({
          user_id: userRef.current.id,
          podcast_id: currentPodcastRef.current.id,
          action: 'complete',
          listen_duration_ms: Math.round(audio.currentTime * 1000),
          progress_pct: 100,
          session_id: sessionIdRef.current,
          recommendation_request_id: recommendationRequestIdRef.current || undefined,
          context_hour: new Date().getHours(),
          context_weekday: new Date().getDay(),
          context_bucket: new Date().getHours() >= 6 && new Date().getHours() < 12
            ? 'morning'
            : new Date().getHours() >= 12 && new Date().getHours() < 18
              ? 'afternoon'
              : new Date().getHours() >= 18 && new Date().getHours() < 23
                ? 'evening'
                : 'night',
        })
      }
      setIsPlaying(false);
      setProgress(0);
      setCurrentTime(0);
    };

    audio.addEventListener('timeupdate', updateProgress);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);

    return () => {
      audio.removeEventListener('timeupdate', updateProgress);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('error', handleError);
    };
  }, []);

  const play = (podcast: Podcast) => {
    const audio = audioRef.current;
    if (!audio) return;

    const normalizedAudioUrl = normalizeAudioPath(podcast.audio_url);
    if (!normalizedAudioUrl) {
      setCurrentPodcast(podcast);
      setIsPlaying(false);
      setDuration(0);
      setCurrentTime(0);
      setProgress(0);
      setError('当前播客暂无可用音频');
      audio.pause();
      audio.removeAttribute('src');
      audio.load();
      return;
    }

    if (currentPodcast?.id !== podcast.id) {
      setCurrentPodcast(podcast);
      setError('');
      // Handle media base URL if needed
      const baseUrl = import.meta.env.VITE_API_BASE_URL?.replace('/api/v1', '') || 'http://localhost:8000';
      const fullUrl = normalizedAudioUrl.startsWith('http') ? normalizedAudioUrl : `${baseUrl}${normalizedAudioUrl}`;
      audio.src = fullUrl;
      audio.currentTime = 0;
      audio.preload = 'auto';
      // 新音频加载后，立即应用当前的播放速度
      audio.playbackRate = playbackRate;
      audio.load();
    }

    void audio.play().then(() => {
      setError('');
      setIsPlaying(true);
    }).catch((error) => {
      setIsPlaying(false);
      setError('当前播客暂时无法播放，请检查音频文件是否存在');
      console.error('音频播放失败', error);
    });
  };

  const pause = () => {
    if (currentPodcast) {
      reportAction('pause', currentPodcast, {
        listen_duration_ms: Math.round((audioRef.current?.currentTime ?? 0) * 1000),
        progress_pct: progress,
      })
    }
    audioRef.current?.pause();
    setIsPlaying(false);
  };

  const toggle = () => {
    if (isPlaying) {
      pause();
    } else if (currentPodcast) {
      reportAction('resume', currentPodcast, {
        listen_duration_ms: Math.round((audioRef.current?.currentTime ?? 0) * 1000),
        progress_pct: progress,
      })
      void audioRef.current?.play().then(() => {
        setIsPlaying(true);
      }).catch((error) => {
        setIsPlaying(false);
        console.error('音频继续播放失败', error);
      })
    }
  };

  const seek = (time: number) => {
    if (audioRef.current) {
      if (currentPodcast && Math.abs(time - audioRef.current.currentTime) > 5) {
        reportAction('skip', currentPodcast, {
          listen_duration_ms: Math.round(audioRef.current.currentTime * 1000),
          progress_pct: progress,
        })
      }
      audioRef.current.currentTime = time;
      setCurrentTime(time);
      setProgress((time / audioRef.current.duration) * 100);
    }
  };

  const reportAction = (
    action: 'play' | 'pause' | 'resume' | 'complete' | 'skip' | 'like' | 'favorite',
    podcast?: Podcast,
    payload?: { listen_duration_ms?: number; progress_pct?: number; session_id?: string; recommendation_request_id?: string },
  ) => {
    const currentUser = userRef.current;
    const target = podcast ?? currentPodcastRef.current;
    if (!currentUser || !target) return undefined;

    const now = new Date();
    return api.reportInteraction({
      user_id: currentUser.id,
      podcast_id: target.id,
      action,
      listen_duration_ms: payload?.listen_duration_ms,
      progress_pct: payload?.progress_pct,
      session_id: payload?.session_id ?? sessionIdRef.current,
      recommendation_request_id: payload?.recommendation_request_id || recommendationRequestIdRef.current || undefined,
      context_hour: now.getHours(),
      context_weekday: now.getDay(),
      context_bucket: now.getHours() >= 6 && now.getHours() < 12
        ? 'morning'
        : now.getHours() >= 12 && now.getHours() < 18
          ? 'afternoon'
          : now.getHours() >= 18 && now.getHours() < 23
            ? 'evening'
            : 'night',
    })
  }

  const setRecommendationRequestId = (id: string) => {
    recommendationRequestIdRef.current = id;
  };

  const setPlaybackRate = (rate: number) => {
    setPlaybackRateState(rate);
    if (audioRef.current) {
      audioRef.current.playbackRate = rate;
    }
  };

  return (
    <PlayerContext.Provider
      value={{
        currentPodcast,
        isPlaying,
        play,
        pause,
        toggle,
        reportAction,
        setRecommendationRequestId,
        progress,
        duration,
        currentTime,
        seek,
        playbackRate,
        setPlaybackRate,
        error,
      }}
    >
      {children}
    </PlayerContext.Provider>
  );
};

export const usePlayer = () => {
  const context = useContext(PlayerContext);
  if (context === undefined) {
    throw new Error('usePlayer must be used within a PlayerProvider');
  }
  return context;
};
