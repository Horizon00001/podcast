import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import React from 'react'
import { FavoritesProvider, useFavorites } from '../../context/FavoritesContext'
import type { Podcast } from '../../types/podcast'

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(FavoritesProvider, null, children)

const podcast: Podcast = {
  id: 1,
  title: 'Test Podcast',
  summary: 'A test',
  category: 'tech',
  audio_url: '/audio/test.mp3',
  script_path: null,
  published_at: '2026-01-01',
}

describe('FavoritesContext', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('starts with empty favorites', () => {
    const { result } = renderHook(() => useFavorites(), { wrapper })
    expect(result.current.favorites).toEqual([])
  })

  it('addFavorite adds a podcast', () => {
    const { result } = renderHook(() => useFavorites(), { wrapper })
    act(() => result.current.addFavorite(podcast))
    expect(result.current.favorites).toHaveLength(1)
    expect(result.current.isFavorite(1)).toBe(true)
  })

  it('addFavorite does not duplicate', () => {
    const { result } = renderHook(() => useFavorites(), { wrapper })
    act(() => result.current.addFavorite(podcast))
    act(() => result.current.addFavorite(podcast))
    expect(result.current.favorites).toHaveLength(1)
  })

  it('removeFavorite removes a podcast', () => {
    const { result } = renderHook(() => useFavorites(), { wrapper })
    act(() => result.current.addFavorite(podcast))
    act(() => result.current.removeFavorite(1))
    expect(result.current.favorites).toHaveLength(0)
    expect(result.current.isFavorite(1)).toBe(false)
  })

  it('toggleFavorite toggles correctly', () => {
    const { result } = renderHook(() => useFavorites(), { wrapper })
    act(() => result.current.toggleFavorite(podcast))
    expect(result.current.isFavorite(1)).toBe(true)
    act(() => result.current.toggleFavorite(podcast))
    expect(result.current.isFavorite(1)).toBe(false)
  })

  it('persists to localStorage', () => {
    const { result } = renderHook(() => useFavorites(), { wrapper })
    act(() => result.current.addFavorite(podcast))
    const stored = JSON.parse(localStorage.getItem('podcast_favorites')!)
    expect(stored).toHaveLength(1)
    expect(stored[0].id).toBe(1)
  })

  it('useFavorites throws outside provider', () => {
    expect(() => renderHook(() => useFavorites())).toThrow(
      'useFavorites must be used within a FavoritesProvider'
    )
  })
})
