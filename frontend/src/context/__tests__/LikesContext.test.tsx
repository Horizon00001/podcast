import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import React from 'react'

import { LikesProvider, useLikes } from '../../context/LikesContext'
import { UserProvider } from '../../context/UserContext'
import { api } from '../../services/api'
import type { Podcast } from '../../types/podcast'

vi.mock('../../services/api', () => ({
  api: {
    getLikes: vi.fn(),
    addLike: vi.fn(),
    removeLike: vi.fn(),
    listPodcasts: vi.fn(),
    ensureUser: vi.fn(),
    getUserByUsername: vi.fn(),
  },
}))

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(UserProvider, null,
    React.createElement(LikesProvider, null, children),
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

async function waitForSync() {
  await waitFor(() => expect(api.getLikes).toHaveBeenCalled())
}

describe('LikesContext', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    vi.mocked(api.getLikes).mockResolvedValue([])
    vi.mocked(api.addLike).mockResolvedValue({ id: 1, user_id: 1, podcast_id: 1, created_at: '' })
    vi.mocked(api.removeLike).mockResolvedValue({ ok: true })
    vi.mocked(api.listPodcasts).mockResolvedValue([])
    vi.mocked(api.ensureUser).mockResolvedValue({ id: 1, username: 'demo', email: 'demo@podcast.local', created_at: '' })
    vi.mocked(api.getUserByUsername).mockResolvedValue({ id: 1, username: 'demo', email: 'demo@podcast.local', created_at: '' })
  })

  it('starts with empty likes', async () => {
    const { result } = renderHook(() => useLikes(), { wrapper })
    await waitForSync()
    expect(result.current.likes).toEqual([])
  })

  it('addLike adds a podcast and calls API', async () => {
    const { result } = renderHook(() => useLikes(), { wrapper })
    await waitForSync()

    act(() => result.current.addLike(podcast))
    expect(result.current.likes).toHaveLength(1)
    expect(result.current.isLiked(1)).toBe(true)
    expect(api.addLike).toHaveBeenCalledWith(1, 1)
  })

  it('addLike does not duplicate', async () => {
    const { result } = renderHook(() => useLikes(), { wrapper })
    await waitForSync()

    act(() => result.current.addLike(podcast))
    act(() => result.current.addLike(podcast))
    expect(result.current.likes).toHaveLength(1)
  })

  it('removeLike removes a podcast and calls API', async () => {
    const { result } = renderHook(() => useLikes(), { wrapper })
    await waitForSync()

    act(() => result.current.addLike(podcast))
    act(() => result.current.removeLike(1))
    expect(result.current.likes).toHaveLength(0)
    expect(result.current.isLiked(1)).toBe(false)
    expect(api.removeLike).toHaveBeenCalledWith(1, 1)
  })

  it('toggleLike toggles correctly', async () => {
    const { result } = renderHook(() => useLikes(), { wrapper })
    await waitForSync()

    act(() => result.current.toggleLike(podcast))
    expect(result.current.isLiked(1)).toBe(true)
    act(() => result.current.toggleLike(podcast))
    expect(result.current.isLiked(1)).toBe(false)
  })

  it('persists to localStorage', async () => {
    const { result } = renderHook(() => useLikes(), { wrapper })
    await waitForSync()

    act(() => result.current.addLike(podcast))
    const stored = JSON.parse(localStorage.getItem('podcast_likes')!)
    expect(stored).toHaveLength(1)
    expect(stored[0].id).toBe(1)
  })

  it('syncs likes from backend on mount', async () => {
    vi.mocked(api.getLikes).mockResolvedValue([
      { id: 10, user_id: 1, podcast_id: 1, created_at: '2026-01-01' },
    ])
    vi.mocked(api.listPodcasts).mockResolvedValue([podcast])

    const { result } = renderHook(() => useLikes(), { wrapper })
    await waitFor(() => {
      expect(result.current.likes).toHaveLength(1)
    })
    expect(result.current.likes[0].id).toBe(1)
  })

  it('loads from localStorage cache first then syncs from backend', async () => {
    localStorage.setItem('podcast_likes', JSON.stringify([podcast]))
    vi.mocked(api.getLikes).mockResolvedValue([])

    const { result } = renderHook(() => useLikes(), { wrapper })
    expect(result.current.likes).toHaveLength(1)

    await waitFor(() => {
      expect(result.current.likes).toHaveLength(0)
    })
  })

  it('useLikes throws outside provider', () => {
    expect(() => renderHook(() => useLikes())).toThrow(
      'useLikes must be used within a LikesProvider'
    )
  })
})
