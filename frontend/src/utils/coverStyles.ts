const CATEGORY_LABELS: Record<string, string> = {
  technology: '科技洞察',
  finance: '商业观察',
  sports: '现场叙事',
  entertainment: '文化片段',
  health: '身心节律',
  all: '精选内容',
}

const COVER_THEMES: Record<string, { background: string; shadow: string }> = {
  technology: {
    background: 'radial-gradient(circle at top left, rgba(255, 255, 255, 0.34), transparent 38%), radial-gradient(circle at bottom right, rgba(116, 161, 255, 0.2), transparent 42%), linear-gradient(145deg, #638dff 0%, #7ea7ff 42%, #9bb7ff 100%)',
    shadow: 'inset 0 1px 0 rgba(255,255,255,0.2), inset 0 -20px 32px rgba(43,72,145,0.18)',
  },
  finance: {
    background: 'radial-gradient(circle at top left, rgba(255, 255, 255, 0.36), transparent 40%), radial-gradient(circle at bottom right, rgba(255, 215, 188, 0.22), transparent 42%), linear-gradient(145deg, #d8a86d 0%, #e6bb8a 46%, #f2d5b7 100%)',
    shadow: 'inset 0 1px 0 rgba(255,255,255,0.24), inset 0 -20px 32px rgba(150,101,54,0.18)',
  },
  sports: {
    background: 'radial-gradient(circle at top left, rgba(255, 255, 255, 0.32), transparent 38%), radial-gradient(circle at bottom right, rgba(114, 233, 220, 0.22), transparent 42%), linear-gradient(145deg, #35aac8 0%, #4bc2d7 48%, #78dbc8 100%)',
    shadow: 'inset 0 1px 0 rgba(255,255,255,0.2), inset 0 -20px 32px rgba(19,111,133,0.18)',
  },
  entertainment: {
    background: 'radial-gradient(circle at top left, rgba(255, 255, 255, 0.34), transparent 40%), radial-gradient(circle at bottom right, rgba(255, 182, 193, 0.2), transparent 42%), linear-gradient(145deg, #f08ca6 0%, #f3a7b8 45%, #f6c2cb 100%)',
    shadow: 'inset 0 1px 0 rgba(255,255,255,0.22), inset 0 -20px 32px rgba(184,95,124,0.18)',
  },
  health: {
    background: 'radial-gradient(circle at top left, rgba(255, 255, 255, 0.34), transparent 40%), radial-gradient(circle at bottom right, rgba(184, 232, 185, 0.22), transparent 42%), linear-gradient(145deg, #76b985 0%, #92c89d 45%, #b6dcb3 100%)',
    shadow: 'inset 0 1px 0 rgba(255,255,255,0.22), inset 0 -20px 32px rgba(69,125,82,0.16)',
  },
  all: {
    background: 'radial-gradient(circle at top left, rgba(255,255,255,0.34), transparent 40%), radial-gradient(circle at bottom right, rgba(181, 194, 255, 0.18), transparent 42%), linear-gradient(145deg, #9ea9c9 0%, #bcc7dd 48%, #dce3ef 100%)',
    shadow: 'inset 0 1px 0 rgba(255,255,255,0.24), inset 0 -20px 32px rgba(99,112,148,0.14)',
  },
}

export function getCategoryLabel(category: string) {
  return CATEGORY_LABELS[category] ?? CATEGORY_LABELS.all
}

export function getCoverTheme(category: string) {
  return COVER_THEMES[category] ?? COVER_THEMES.all
}

export function getCoverStyle(category: string) {
  const theme = getCoverTheme(category)
  return {
    background: theme.background,
    boxShadow: theme.shadow,
    color: '#ffffff',
    textShadow: '0 1px 2px rgba(36, 42, 56, 0.22)',
  }
}
