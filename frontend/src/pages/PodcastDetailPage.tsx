import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { AudioPlayer } from '../components/AudioPlayer'
import { ScriptPanel } from '../components/ScriptPanel'
import { TimelineHighlighter } from '../components/TimelineHighlighter'
import { api } from '../services/api'
import type { Podcast } from '../types/podcast'

export function PodcastDetailPage() {
  const { id } = useParams()
  const [podcast, setPodcast] = useState<Podcast | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    api
      .getPodcast(Number(id))
      .then(setPodcast)
      .catch((e) => setError((e as Error).message))
  }, [id])

  if (error) {
    return <p>加载失败：{error}</p>
  }
  if (!podcast) {
    return <p>加载中...</p>
  }

  return (
    <main>
      <h1>{podcast.title}</h1>
      <p>{podcast.summary}</p>
      <AudioPlayer src={podcast.audio_url} />
      <ScriptPanel scriptPath={podcast.script_path} />
      <TimelineHighlighter currentTime={0} />
    </main>
  )
}
