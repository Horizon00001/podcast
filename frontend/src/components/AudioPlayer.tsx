import { MEDIA_BASE_URL } from '../services/api'
interface AudioPlayerProps {
  src?: string
}

export function AudioPlayer({ src }: AudioPlayerProps) {
  if (!src) {
    return <p>暂无可播放音频</p>
  }
  const fullSrc = src.startsWith('http') ? src : `${MEDIA_BASE_URL}${src}`
  return <audio controls src={fullSrc} style={{ width: '100%' }} />
}
