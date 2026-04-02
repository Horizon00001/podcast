interface AudioPlayerProps {
  src?: string
}

export function AudioPlayer({ src }: AudioPlayerProps) {
  if (!src) {
    return <p>暂无可播放音频</p>
  }
  return <audio controls src={src} style={{ width: '100%' }} />
}
