import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import React from 'react'
import { FavoritesProvider, useFavorites } from '../../context/FavoritesContext'
import { UserProvider } from '../../context/UserContext'
import { api } from '../../services/api'
import type { Podcast } from '../../types/podcast'

vi.mock('../../services/api', () => ({
  api: {
    getFavorites: vi.fn(),
    addFavorite: vi.fn(),
    removeFavorite: vi.fn(),
    listPodcasts: vi.fn(),
    ensureUser: vi.fn(),
    getUserByUsername: vi.fn(),
  },
}))

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(UserProvider, null,
    React.createElement(FavoritesProvider, null, children),
  )

const podcast: Podcast = {
  id: 1,
  title: 'Test Podcast',
  summary: 'A test',
  category: 'tech',
  audio_url: '/audio/test.mp3',
  script_path: '',
  published_at: '2026-01-01',
}

// Helper to wait until user is loaded and backend sync completes
async function waitForSync() {
  await waitFor(() => expect(api.getFavorites).toHaveBeenCalled())
}

describe('FavoritesContext', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    vi.mocked(api.getFavorites).mockResolvedValue([])
    vi.mocked(api.addFavorite).mockResolvedValue({ id: 1, user_id: 1, podcast_id: 1, created_at: '' })
    vi.mocked(api.removeFavorite).mockResolvedValue({ ok: true })
    vi.mocked(api.listPodcasts).mockResolvedValue([])
    vi.mocked(api.ensureUser).mockResolvedValue({ id: 1, username: 'demo', email: 'demo@podcast.local', created_at: '' })
    vi.mocked(api.getUserByUsername).mockResolvedValue({ id: 1, username: 'demo', email: 'demo@podcast.local', created_at: '' })
  })

  it('starts with empty favorites', async () => {
    const { result } = renderHook(() => useFavorites(), { wrapper })
    await waitForSync()
    expect(result.current.favorites).toEqual([])
  })

  it('addFavorite adds a podcast and calls API', async () => {
    const { result } = renderHook(() => useFavorites(), { wrapper })
    await waitForSync()

    act(() => result.current.addFavorite(podcast))
    expect(result.current.favorites).toHaveLength(1)
    expect(result.current.isFavorite(1)).toBe(true)
    expect(api.addFavorite).toHaveBeenCalledWith(1, 1)
  })

  it('addFavorite does not duplicate', async () => {
    const { result } = renderHook(() => useFavorites(), { wrapper })
    await waitForSync()

    act(() => result.current.addFavorite(podcast))
    act(() => result.current.addFavorite(podcast))
    expect(result.current.favorites).toHaveLength(1)
  })

  it('removeFavorite removes a podcast and calls API', async () => {
    const { result } = renderHook(() => useFavorites(), { wrapper })
    await waitForSync()

    act(() => result.current.addFavorite(podcast))
    act(() => result.current.removeFavorite(1))
    expect(result.current.favorites).toHaveLength(0)
    expect(result.current.isFavorite(1)).toBe(false)
    expect(api.removeFavorite).toHaveBeenCalledWith(1, 1)
  })

  it('toggleFavorite toggles correctly', async () => {
    const { result } = renderHook(() => useFavorites(), { wrapper })
    await waitForSync()

    act(() => result.current.toggleFavorite(podcast))
    expect(result.current.isFavorite(1)).toBe(true)
    act(() => result.current.toggleFavorite(podcast))
    expect(result.current.isFavorite(1)).toBe(false)
  })

  it('persists to localStorage', async () => {
    const { result } = renderHook(() => useFavorites(), { wrapper })
    await waitForSync()

    act(() => result.current.addFavorite(podcast))
    const stored = JSON.parse(localStorage.getItem('podcast_favorites')!)
    expect(stored).toHaveLength(1)
    expect(stored[0].id).toBe(1)
  })

  it('syncs favorites from backend on mount', async () => {
    vi.mocked(api.getFavorites).mockResolvedValue([
      { id: 10, user_id: 1, podcast_id: 1, created_at: '2026-01-01' },
    ])
    vi.mocked(api.listPodcasts).mockResolvedValue([podcast])

    const { result } = renderHook(() => useFavorites(), { wrapper })
    await waitFor(() => {
      expect(result.current.favorites).toHaveLength(1)
    })
    expect(result.current.favorites[0].id).toBe(1)
  })

  it('loads from localStorage cache first then syncs from backend', async () => {
    localStorage.setItem('podcast_favorites', JSON.stringify([podcast]))
    vi.mocked(api.getFavorites).mockResolvedValue([])

    const { result } = renderHook(() => useFavorites(), { wrapper })
    // localStorage cache is loaded immediately
    expect(result.current.favorites).toHaveLength(1)

    // Then backend sync clears it
    await waitFor(() => {
      expect(result.current.favorites).toHaveLength(0)
    })
  })

  it('useFavorites throws outside provider', () => {
    expect(() => renderHook(() => useFavorites())).toThrow(
      'useFavorites must be used within a FavoritesProvider'
    )
  })
})
