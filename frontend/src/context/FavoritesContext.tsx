import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import type { Podcast } from '../types/podcast';
import { api } from '../services/api';
import { useUser } from './UserContext';

interface FavoritesContextType {
  favorites: Podcast[];
  isFavorite: (podcastId: number) => boolean;
  addFavorite: (podcast: Podcast) => void;
  removeFavorite: (podcastId: number) => void;
  toggleFavorite: (podcast: Podcast) => void;
}

const FavoritesContext = createContext<FavoritesContextType | undefined>(undefined);

const STORAGE_KEY = 'podcast_favorites';

function loadFromStorage(): Podcast[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

function saveToStorage(favorites: Podcast[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites));
}

export const FavoritesProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { user } = useUser();
  const [favorites, setFavorites] = useState<Podcast[]>(loadFromStorage);
  const [synced, setSynced] = useState(false);

  // Sync from backend when user becomes available
  useEffect(() => {
    if (!user || synced) return;
    api.getFavorites(user.id)
      .then(async (items) => {
        if (items.length === 0) {
          setFavorites([]);
          saveToStorage([]);
          setSynced(true);
          return;
        }
        // Fetch full podcast details for each favorite
        const podcastIds = items.map((item) => item.podcast_id);
        const allPodcasts = await api.listPodcasts();
        const favPodcasts = allPodcasts.filter((p) => podcastIds.includes(p.id));
        setFavorites(favPodcasts);
        saveToStorage(favPodcasts);
        setSynced(true);
      })
      .catch(() => {
        // Backend unavailable, keep localStorage data
        setSynced(true);
      });
  }, [user, synced]);

  useEffect(() => {
    saveToStorage(favorites);
  }, [favorites]);

  const isFavorite = useCallback(
    (podcastId: number) => favorites.some((fav) => fav.id === podcastId),
    [favorites],
  );

  const addFavorite = useCallback(
    (podcast: Podcast) => {
      if (favorites.some((fav) => fav.id === podcast.id)) return;
      setFavorites((prev) => [...prev, podcast]);
      if (user) {
        api.addFavorite(user.id, podcast.id).catch(() => {});
      }
    },
    [favorites, user],
  );

  const removeFavorite = useCallback(
    (podcastId: number) => {
      setFavorites((prev) => prev.filter((p) => p.id !== podcastId));
      if (user) {
        api.removeFavorite(user.id, podcastId).catch(() => {});
      }
    },
    [user],
  );

  const toggleFavorite = useCallback(
    (podcast: Podcast) => {
      if (isFavorite(podcast.id)) {
        removeFavorite(podcast.id);
      } else {
        addFavorite(podcast);
      }
    },
    [isFavorite, addFavorite, removeFavorite],
  );

  return (
    <FavoritesContext.Provider value={{ favorites, isFavorite, addFavorite, removeFavorite, toggleFavorite }}>
      {children}
    </FavoritesContext.Provider>
  );
};

export const useFavorites = () => {
  const context = useContext(FavoritesContext);
  if (context === undefined) {
    throw new Error('useFavorites must be used within a FavoritesProvider');
  }
  return context;
};
