import React, { createContext, useContext, useState, useRef, useEffect } from 'react';
import type { Podcast } from '../types/podcast';

interface PlayerContextType {
  currentPodcast: Podcast | null;
  isPlaying: boolean;
  play: (podcast: Podcast) => void;
  pause: () => void;
  toggle: () => void;
  progress: number; // 0-100
  duration: number; // in seconds
  currentTime: number; // in seconds
  seek: (time: number) => void;
  playbackRate: number;
  setPlaybackRate: (rate: number) => void;
}

const PlayerContext = createContext<PlayerContextType | undefined>(undefined);

export const PlayerProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentPodcast, setCurrentPodcast] = useState<Podcast | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [playbackRate, setPlaybackRateState] = useState(1);
  const audioRef = useRef<HTMLAudioElement | null>(null);

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
      }
    }
    audioRef.current?.play();
    setIsPlaying(true);
  };

  const pause = () => {
    audioRef.current?.pause();
    setIsPlaying(false);
  };

  const toggle = () => {
    if (isPlaying) {
      pause();
    } else if (currentPodcast) {
      audioRef.current?.play();
      setIsPlaying(true);
    }
  };

  const seek = (time: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = time;
      setCurrentTime(time);
      setProgress((time / audioRef.current.duration) * 100);
    }
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
