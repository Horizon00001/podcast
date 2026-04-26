export interface SectionProgress {
  key: string
  groupLabel: string
  sectionNumber: number
  sectionType: string
  lineCount: number
  status: 'ready' | 'running' | 'done'
  audioPath?: string
}

export interface GroupProgress {
  label: string
  itemCount?: number
  scriptStatus: 'idle' | 'running' | 'done'
  mergeStatus: 'idle' | 'running' | 'done'
  waitingSections?: number
  outputPath?: string
}

export interface GenerationEventPayload {
  type: string
  group_label?: string
  item_count?: number
  section_index?: number
  section_type?: string
  line_count?: number
  audio_path?: string
  waiting_sections?: number
  section_count?: number
  output_path?: string
  category_count?: number
}
