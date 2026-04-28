import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'

import { api } from '../services/api'
import type { Podcast } from '../types/podcast'
import { useUser } from './UserContext'

interface LikesContextType {
  likes: Podcast[]
  isLiked: (podcastId: number) => boolean
  addLike: (podcast: Podcast) => void
  removeLike: (podcastId: number) => void
  toggleLike: (podcast: Podcast) => void
}

const LikesContext = createContext<LikesContextType | undefined>(undefined)

const STORAGE_KEY = 'podcast_likes'

function loadFromStorage(): Podcast[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored ? JSON.parse(stored) : []
  } catch {
    return []
  }
}

function saveToStorage(likes: Podcast[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(likes))
}

export const LikesProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { user } = useUser()
  const [likes, setLikes] = useState<Podcast[]>(loadFromStorage)
  const [syncedUserId, setSyncedUserId] = useState<number | null>(null)

  useEffect(() => {
    if (!user) {
      setSyncedUserId(null)
      return
    }

    if (syncedUserId === user.id) return

    api.getLikes(user.id)
      .then(async (items) => {
        if (items.length === 0) {
          setLikes([])
          saveToStorage([])
          setSyncedUserId(user.id)
          return
        }

        const podcastIds = items.map((item) => item.podcast_id)
        const allPodcasts = await api.listPodcasts()
        const likedPodcasts = allPodcasts.filter((podcast) => podcastIds.includes(podcast.id))
        setLikes(likedPodcasts)
        saveToStorage(likedPodcasts)
        setSyncedUserId(user.id)
      })
      .catch(() => {
        setSyncedUserId(user.id)
      })
  }, [user, syncedUserId])

  useEffect(() => {
    saveToStorage(likes)
  }, [likes])

  const isLiked = useCallback(
    (podcastId: number) => likes.some((liked) => liked.id === podcastId),
    [likes],
  )

  const addLike = useCallback(
    (podcast: Podcast) => {
      if (likes.some((liked) => liked.id === podcast.id)) return
      setLikes((prev) => [...prev, podcast])
      if (user) {
        api.addLike(user.id, podcast.id).catch(() => {})
      }
    },
    [likes, user],
  )

  const removeLike = useCallback(
    (podcastId: number) => {
      setLikes((prev) => prev.filter((podcast) => podcast.id !== podcastId))
      if (user) {
        api.removeLike(user.id, podcastId).catch(() => {})
      }
    },
    [user],
  )

  const toggleLike = useCallback(
    (podcast: Podcast) => {
      if (isLiked(podcast.id)) {
        removeLike(podcast.id)
      } else {
        addLike(podcast)
      }
    },
    [isLiked, addLike, removeLike],
  )

  return (
    <LikesContext.Provider value={{ likes, isLiked, addLike, removeLike, toggleLike }}>
      {children}
    </LikesContext.Provider>
  )
}

export const useLikes = () => {
  const context = useContext(LikesContext)
  if (context === undefined) {
    throw new Error('useLikes must be used within a LikesProvider')
  }
  return context
}
