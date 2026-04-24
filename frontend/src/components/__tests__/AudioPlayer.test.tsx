import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AudioPlayer } from '../../components/AudioPlayer'

describe('AudioPlayer', () => {
  it('renders fallback message when no src', () => {
    render(<AudioPlayer />)
    expect(screen.getByText('暂无可播放音频')).toBeInTheDocument()
  })

  it('renders audio element when src provided', () => {
    const { container } = render(<AudioPlayer src="/audio/test.mp3" />)
    const audio = container.querySelector('audio') as HTMLAudioElement
    expect(audio).toBeInTheDocument()
    expect(audio.src).toContain('/audio/test.mp3')
  })

  it('uses src as-is when it starts with http', () => {
    const { container } = render(
      <AudioPlayer src="https://example.com/audio/test.mp3" />
    )
    const audio = container.querySelector('audio') as HTMLAudioElement
    expect(audio.src).toBe('https://example.com/audio/test.mp3')
  })
})
