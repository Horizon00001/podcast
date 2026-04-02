import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../services/api'
import type { Podcast } from '../types/podcast'

export function PodcastListPage() {
  const [podcasts, setPodcasts] = useState<Podcast[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .listPodcasts()
      .then(setPodcasts)
      .catch((e) => setError((e as Error).message))
  }, [])

  return (
    <main>
      <h1>播客列表</h1>
      {error ? <p>加载失败：{error}</p> : null}
      <ul>
        {podcasts.map((item) => (
          <li key={item.id}>
            <Link to={`/podcasts/${item.id}`}>{item.title}</Link>
            <p>{item.summary}</p>
          </li>
        ))}
      </ul>
    </main>
  )
}
