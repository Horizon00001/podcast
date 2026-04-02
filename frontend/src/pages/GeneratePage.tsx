import { useState, type FormEvent } from 'react'

import { api } from '../services/api'

export function GeneratePage() {
  const [rssSource, setRssSource] = useState('default')
  const [topic, setTopic] = useState('daily-news')
  const [message, setMessage] = useState('')

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    try {
      const result = await api.triggerGeneration({ rss_source: rssSource, topic })
      setMessage(`任务已提交：${result.task_id}（${result.status}）`)
    } catch (error) {
      setMessage(`提交失败：${(error as Error).message}`)
    }
  }

  return (
    <main>
      <h1>手动生成播客</h1>
      <form onSubmit={handleSubmit}>
        <label>
          RSS 源
          <input value={rssSource} onChange={(e) => setRssSource(e.target.value)} />
        </label>
        <label>
          主题
          <input value={topic} onChange={(e) => setTopic(e.target.value)} />
        </label>
        <button type="submit">触发生成</button>
      </form>
      <p>{message}</p>
    </main>
  )
}
