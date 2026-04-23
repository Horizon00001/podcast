// src/context/FavoritesContext.tsx
import React, { createContext, useContext, useState, useEffect, } from 'react';
import type { ReactNode } from 'react'; 
import type { Podcast } from '../types/podcast';

interface FavoritesContextType {
  favorites: Podcast[];
  isFavorite: (podcastId: number) => boolean;
  addFavorite: (podcast: Podcast) => void;
  removeFavorite: (podcastId: number) => void;
  toggleFavorite: (podcast: Podcast) => void;
}

const FavoritesContext = createContext<FavoritesContextType | undefined>(undefined);

const STORAGE_KEY = 'podcast_favorites';

export const FavoritesProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [favorites, setFavorites] = useState<Podcast[]>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch (e) {
        console.error('Failed to parse favorites', e);
        return [];
      }
    }
    return [];
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites));
  }, [favorites]);

  const isFavorite = (podcastId: number) => favorites.some(fav => fav.id === podcastId);

  const addFavorite = (podcast: Podcast) => {
    if (!isFavorite(podcast.id)) {
      setFavorites(prev => [...prev, podcast]);
    }
  };

  const removeFavorite = (podcastId: number) => {
    setFavorites(prev => prev.filter(p => p.id !== podcastId));
  };

  const toggleFavorite = (podcast: Podcast) => {
    if (isFavorite(podcast.id)) {
      removeFavorite(podcast.id);
    } else {
      addFavorite(podcast);
    }
  };

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