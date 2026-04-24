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
}

const PlayerContext = createContext<PlayerContextType | undefined>(undefined);

export const PlayerProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useUser();
  const [currentPodcast, setCurrentPodcast] = useState<Podcast | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [playbackRate, setPlaybackRateState] = useState(1);
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
    }

    const audio = audioRef.current;

    const updateProgress = () => {
      setCurrentTime(audio.currentTime);
      setProgress((audio.currentTime / audio.duration) * 100);
    };

    const handleLoadedMetadata = () => {
      setDuration(audio.duration);
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

    return () => {
      audio.removeEventListener('timeupdate', updateProgress);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('ended', handleEnded);
    };
  }, []);

  const play = (podcast: Podcast) => {
    if (currentPodcast?.id !== podcast.id) {
      setCurrentPodcast(podcast);
      if (audioRef.current) {
        // Handle media base URL if needed
        const baseUrl = import.meta.env.VITE_API_BASE_URL?.replace('/api/v1', '') || 'http://localhost:8000';
        const fullUrl = podcast.audio_url.startsWith('http') ? podcast.audio_url : `${baseUrl}${podcast.audio_url}`;
        audioRef.current.src = fullUrl;
       // ✅ 新音频加载后，立即应用当前的播放速度
        audioRef.current.playbackRate = playbackRate;
      }
    }
    audioRef.current?.play();
    setIsPlaying(true);
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
      audioRef.current?.play();
      setIsPlaying(true);
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
