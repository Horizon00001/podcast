import { useState } from 'react'

import { parseSectionDescriptor, sectionKey } from './progressParsers'
import type { GenerationEventPayload, GroupProgress, SectionProgress } from './progressTypes'

export function useGenerationProgress() {
  const [rssStage, setRssStage] = useState<'idle' | 'running' | 'done'>('idle')
  const [activeGroupLabel, setActiveGroupLabel] = useState<string | null>(null)
  const [groupProgress, setGroupProgress] = useState<Record<string, GroupProgress>>({})
  const [sectionProgress, setSectionProgress] = useState<Record<string, SectionProgress>>({})

  function resetProgressState() {
    setRssStage('idle')
    setActiveGroupLabel(null)
    setGroupProgress({})
    setSectionProgress({})
  }

  function updateGroup(label: string, updater: (prev: GroupProgress) => GroupProgress) {
    setGroupProgress((prev) => {
      const current = prev[label] ?? {
        label,
        scriptStatus: 'idle',
        mergeStatus: 'idle',
      }

      return {
        ...prev,
        [label]: updater(current),
      }
    })
  }

  function handleStructuredEvent(event: GenerationEventPayload) {
    if (event.type === 'rss_started') {
      setRssStage('running')
      return
    }
    if (event.type === 'clustering_started' || event.type === 'clustering_completed') {
      setRssStage('done')
      return
    }

    const label = event.group_label
    if (!label) {
      return
    }

    if (event.type === 'group_started') {
      setActiveGroupLabel(label)
      updateGroup(label, (prev) => ({ ...prev, itemCount: event.item_count ?? prev.itemCount }))
      return
    }
    if (event.type === 'script_started') {
      setActiveGroupLabel(label)
      updateGroup(label, (prev) => ({ ...prev, scriptStatus: 'running' }))
      return
    }
    if (event.type === 'script_completed') {
      updateGroup(label, (prev) => ({ ...prev, scriptStatus: 'done' }))
      return
    }

    if (event.section_index && event.section_type && typeof event.line_count === 'number') {
      const descriptor = {
        sectionNumber: event.section_index,
        sectionType: event.section_type,
        lineCount: event.line_count,
      }
      const key = sectionKey(label, descriptor)

      if (event.type === 'section_ready') {
        setSectionProgress((prev) => ({
          ...prev,
          [key]: {
            key,
            groupLabel: label,
            sectionNumber: descriptor.sectionNumber,
            sectionType: descriptor.sectionType,
            lineCount: descriptor.lineCount,
            status: prev[key]?.status === 'done' ? 'done' : 'ready',
            audioPath: prev[key]?.audioPath,
          },
        }))
        return
      }

      if (event.type === 'tts_started') {
        setSectionProgress((prev) => ({
          ...prev,
          [key]: {
            key,
            groupLabel: label,
            sectionNumber: descriptor.sectionNumber,
            sectionType: descriptor.sectionType,
            lineCount: descriptor.lineCount,
            status: 'running',
            audioPath: prev[key]?.audioPath,
          },
        }))
        return
      }

      if (event.type === 'tts_completed') {
        setSectionProgress((prev) => ({
          ...prev,
          [key]: {
            key,
            groupLabel: label,
            sectionNumber: descriptor.sectionNumber,
            sectionType: descriptor.sectionType,
            lineCount: descriptor.lineCount,
            status: 'done',
            audioPath: event.audio_path,
          },
        }))
        return
      }
    }

    if (event.type === 'tts_waiting') {
      updateGroup(label, (prev) => ({ ...prev, waitingSections: event.waiting_sections ?? prev.waitingSections }))
      return
    }
    if (event.type === 'merge_started') {
      updateGroup(label, (prev) => ({ ...prev, mergeStatus: 'running', waitingSections: event.section_count ?? prev.waitingSections }))
      return
    }
    if (event.type === 'group_completed') {
      updateGroup(label, (prev) => ({
        ...prev,
        scriptStatus: 'done',
        mergeStatus: 'done',
        outputPath: event.output_path ?? prev.outputPath,
      }))
    }
  }

  function handleStructuredLogChunk(chunk: string) {
    const lines = chunk.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)

    for (const line of lines) {
      if (line.includes('[1/4] 抓取 RSS 数据')) {
        setRssStage('running')
        continue
      }

      if (line.includes('[2/4] 分类并聚类新闻')) {
        setRssStage('done')
        continue
      }

      let match = line.match(/^\[组开始\]\s+([^，]+)，新闻数=(\d+)$/)
      if (match) {
        const label = match[1]
        setActiveGroupLabel(label)
        updateGroup(label, (prev) => ({
          ...prev,
          itemCount: Number(match?.[2] ?? 0),
        }))
        continue
      }

      match = line.match(/^\[Script Start\]\s+(.+)$/)
      if (match) {
        const label = match[1]
        setActiveGroupLabel(label)
        updateGroup(label, (prev) => ({ ...prev, scriptStatus: 'running' }))
        continue
      }

      match = line.match(/^\[Script Done\]\s+(.+)$/)
      if (match) {
        const label = match[1]
        updateGroup(label, (prev) => ({ ...prev, scriptStatus: 'done' }))
        continue
      }

      match = line.match(/^\[Section Ready\]\s+(.+?)\s+(section=\d+ type=[^\s]+ lines=\d+)$/)
      if (match) {
        const groupLabel = match[1]
        const descriptor = parseSectionDescriptor(match[2])
        if (!descriptor) {
          continue
        }
        const key = sectionKey(groupLabel, descriptor)
        setSectionProgress((prev) => ({
          ...prev,
          [key]: {
            key,
            groupLabel,
            sectionNumber: descriptor.sectionNumber,
            sectionType: descriptor.sectionType,
            lineCount: descriptor.lineCount,
            status: prev[key]?.status === 'done' ? 'done' : 'ready',
            audioPath: prev[key]?.audioPath,
          },
        }))
        continue
      }

      match = line.match(/^\[TTS Start\]\s+(.+?)\s+(section=\d+ type=[^\s]+ lines=\d+)$/)
      if (match) {
        const groupLabel = match[1]
        const descriptor = parseSectionDescriptor(match[2])
        if (!descriptor) {
          continue
        }
        const key = sectionKey(groupLabel, descriptor)
        setSectionProgress((prev) => ({
          ...prev,
          [key]: {
            key,
            groupLabel,
            sectionNumber: descriptor.sectionNumber,
            sectionType: descriptor.sectionType,
            lineCount: descriptor.lineCount,
            status: 'running',
            audioPath: prev[key]?.audioPath,
          },
        }))
        continue
      }

      match = line.match(/^\[TTS Done\]\s+(.+?)\s+(section=\d+ type=[^\s]+ lines=\d+)\s+->\s+(.+)$/)
      if (match) {
        const groupLabel = match[1]
        const descriptor = parseSectionDescriptor(match[2])
        const audioPath = match[3]
        if (!descriptor) {
          continue
        }
        const key = sectionKey(groupLabel, descriptor)
        setSectionProgress((prev) => ({
          ...prev,
          [key]: {
            key,
            groupLabel,
            sectionNumber: descriptor.sectionNumber,
            sectionType: descriptor.sectionType,
            lineCount: descriptor.lineCount,
            status: 'done',
            audioPath,
          },
        }))
        continue
      }

      match = line.match(/^\[TTS Wait\]\s+(.+?)\s+waiting for\s+(\d+)\s+section tasks$/)
      if (match) {
        const label = match[1]
        updateGroup(label, (prev) => ({ ...prev, waitingSections: Number(match?.[2] ?? 0) }))
        continue
      }

      match = line.match(/^\[Merge Start\]\s+(.+?)\s+merging\s+(\d+)\s+section files$/)
      if (match) {
        const label = match[1]
        updateGroup(label, (prev) => ({
          ...prev,
          mergeStatus: 'running',
          waitingSections: Number(match?.[2] ?? 0),
        }))
        continue
      }

      match = line.match(/^\[Group Done\]\s+(.+?)\s+->\s+(.+)$/)
      if (match) {
        const label = match[1]
        updateGroup(label, (prev) => ({
          ...prev,
          scriptStatus: 'done',
          mergeStatus: 'done',
          outputPath: match?.[2],
        }))
      }
    }
  }

  return {
    rssStage,
    activeGroupLabel,
    groupProgress,
    sectionProgress,
    resetProgressState,
    handleStructuredEvent,
    handleStructuredLogChunk,
  }
}
