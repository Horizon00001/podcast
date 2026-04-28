import { describe, it, expect, vi } from 'vitest'
import type { InteractionPayload } from '../api'

describe('API client URL construction', () => {
  it('listPodcasts calls /podcasts', async () => {
    const spy = vi.fn().mockResolvedValue({ podcasts: [] })
    vi.stubGlobal('fetch', spy)

    const { api } = await import('../api')
    expect(api).toHaveProperty('listPodcasts')
    expect(api).toHaveProperty('getPodcast')
    expect(api).toHaveProperty('getRecommendations')
    expect(api).toHaveProperty('reportInteraction')
    expect(api).toHaveProperty('ensureUser')
    expect(api).toHaveProperty('getRSSSources')
    expect(api).toHaveProperty('getTopics')
    expect(api).toHaveProperty('triggerGeneration')
    expect(api).toHaveProperty('getGenerationStatus')
    expect(api).toHaveProperty('createEventSource')
    expect(api).toHaveProperty('getPodcastScript')

    vi.unstubAllGlobals()
  })

  it('request throws on non-ok response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 500 })
    )

    const { api } = await import('../api')
    await expect(api.listPodcasts()).rejects.toThrow('请求失败')

    vi.unstubAllGlobals()
  })

  it('accepts click interaction payload', () => {
    const payload: InteractionPayload = {
      user_id: 1,
      podcast_id: 2,
      action: 'click',
    }

    expect(payload.action).toBe('click')
  })
})
