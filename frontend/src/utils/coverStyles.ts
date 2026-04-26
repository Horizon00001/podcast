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
    background: 'radial-gradient(circle at 16% 12%, rgba(255, 255, 255, 0.58), transparent 22%), radial-gradient(circle at 82% 14%, rgba(99, 255, 227, 0.3), transparent 28%), radial-gradient(circle at 84% 86%, rgba(138, 122, 255, 0.34), transparent 34%), linear-gradient(148deg, #0e5a70 0%, #14819a 30%, #1fa2b2 56%, #2b8fd1 78%, #635eff 100%)',
    shadow: 'inset 0 1px 0 rgba(255,255,255,0.28), inset 0 -28px 42px rgba(20,36,96,0.3)',
  },
}

type HeroTheme = {
  primaryBackground: string
  primaryShadow: string
  secondaryBackground: string
  secondaryShadow: string
}

const FEATURED_HERO_THEMES: readonly HeroTheme[] = [
  {
    primaryBackground: 'radial-gradient(circle at 16% 12%, rgba(255, 255, 255, 0.58), transparent 22%), radial-gradient(circle at 82% 14%, rgba(99, 255, 227, 0.3), transparent 28%), radial-gradient(circle at 84% 86%, rgba(138, 122, 255, 0.34), transparent 34%), linear-gradient(148deg, #0e5a70 0%, #14819a 30%, #1fa2b2 56%, #2b8fd1 78%, #635eff 100%)',
    primaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.28), inset 0 -28px 42px rgba(20,36,96,0.3)',
    secondaryBackground: 'radial-gradient(circle at 18% 16%, rgba(255, 255, 255, 0.42), transparent 24%), radial-gradient(circle at 82% 20%, rgba(105, 244, 224, 0.22), transparent 30%), linear-gradient(150deg, #2a8090 0%, #3b98a7 46%, #62a5e6 100%)',
    secondaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.22), inset 0 -18px 28px rgba(22,52,108,0.18)',
  },
  {
    primaryBackground: 'radial-gradient(circle at 18% 14%, rgba(255, 255, 255, 0.52), transparent 24%), radial-gradient(circle at 86% 18%, rgba(255, 189, 132, 0.28), transparent 30%), radial-gradient(circle at 82% 84%, rgba(255, 113, 134, 0.24), transparent 36%), linear-gradient(148deg, #a14f29 0%, #ca6a37 28%, #e58a54 56%, #f1ab73 78%, #f4c598 100%)',
    primaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.26), inset 0 -28px 40px rgba(114,49,24,0.24)',
    secondaryBackground: 'radial-gradient(circle at 16% 14%, rgba(255, 255, 255, 0.4), transparent 24%), radial-gradient(circle at 84% 18%, rgba(255, 202, 146, 0.22), transparent 30%), linear-gradient(150deg, #bc693f 0%, #dc8b5f 48%, #efb889 100%)',
    secondaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.22), inset 0 -18px 28px rgba(118,60,28,0.18)',
  },
  {
    primaryBackground: 'radial-gradient(circle at 18% 12%, rgba(255, 255, 255, 0.54), transparent 22%), radial-gradient(circle at 82% 14%, rgba(255, 110, 201, 0.28), transparent 28%), radial-gradient(circle at 84% 84%, rgba(112, 139, 255, 0.28), transparent 36%), linear-gradient(148deg, #5c2b91 0%, #7c3cb3 30%, #a64bc4 56%, #d25db9 78%, #f08cb3 100%)',
    primaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.28), inset 0 -28px 42px rgba(73,28,110,0.28)',
    secondaryBackground: 'radial-gradient(circle at 18% 14%, rgba(255, 255, 255, 0.42), transparent 24%), radial-gradient(circle at 82% 18%, rgba(255, 126, 206, 0.2), transparent 30%), linear-gradient(150deg, #7b49a8 0%, #9a58c0 48%, #cf82c8 100%)',
    secondaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.22), inset 0 -18px 28px rgba(82,42,118,0.18)',
  },
  {
    primaryBackground: 'radial-gradient(circle at 16% 12%, rgba(255, 255, 255, 0.5), transparent 24%), radial-gradient(circle at 84% 16%, rgba(128, 233, 183, 0.24), transparent 28%), radial-gradient(circle at 82% 84%, rgba(152, 207, 255, 0.22), transparent 34%), linear-gradient(148deg, #1d5a47 0%, #27715a 30%, #36836d 54%, #4b9b87 76%, #7bb8b3 100%)',
    primaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.24), inset 0 -28px 40px rgba(20,70,56,0.24)',
    secondaryBackground: 'radial-gradient(circle at 16% 14%, rgba(255, 255, 255, 0.4), transparent 24%), radial-gradient(circle at 84% 20%, rgba(148, 232, 194, 0.2), transparent 30%), linear-gradient(150deg, #3d7a65 0%, #54917a 48%, #88b5a7 100%)',
    secondaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.22), inset 0 -18px 28px rgba(28,78,60,0.18)',
  },
  {
    primaryBackground: 'radial-gradient(circle at 15% 10%, rgba(255, 255, 255, 0.52), transparent 22%), radial-gradient(circle at 84% 14%, rgba(181, 219, 255, 0.24), transparent 28%), radial-gradient(circle at 82% 84%, rgba(141, 156, 255, 0.26), transparent 34%), linear-gradient(148deg, #513071 0%, #69408f 28%, #8553a9 56%, #8d68c4 76%, #98a0ea 100%)',
    primaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.24), inset 0 -28px 42px rgba(49,34,92,0.28)',
    secondaryBackground: 'radial-gradient(circle at 16% 14%, rgba(255, 255, 255, 0.4), transparent 24%), radial-gradient(circle at 82% 18%, rgba(189, 208, 255, 0.2), transparent 30%), linear-gradient(150deg, #70508d 0%, #8564a6 48%, #a093d6 100%)',
    secondaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.22), inset 0 -18px 28px rgba(58,42,98,0.2)',
  },
  {
    primaryBackground: 'radial-gradient(circle at 18% 12%, rgba(255, 255, 255, 0.54), transparent 22%), radial-gradient(circle at 82% 16%, rgba(255, 164, 185, 0.26), transparent 28%), radial-gradient(circle at 84% 84%, rgba(255, 209, 120, 0.24), transparent 36%), linear-gradient(148deg, #b34a5e 0%, #d05b72 30%, #e47a7d 56%, #efa06f 78%, #f5c181 100%)',
    primaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.28), inset 0 -28px 42px rgba(115,40,57,0.24)',
    secondaryBackground: 'radial-gradient(circle at 18% 14%, rgba(255, 255, 255, 0.42), transparent 24%), radial-gradient(circle at 82% 18%, rgba(255, 180, 192, 0.2), transparent 30%), linear-gradient(150deg, #c05f72 0%, #de7583 48%, #efad91 100%)',
    secondaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.22), inset 0 -18px 28px rgba(118,52,65,0.18)',
  },
]

function getFeaturedHeroTheme(seed: number) {
  const index = Math.abs(seed) % FEATURED_HERO_THEMES.length
  return FEATURED_HERO_THEMES[index]
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

export function getFeaturedHeroCoverStyle(seed: number) {
  const theme = getFeaturedHeroTheme(seed)

  return {
    background: theme.primaryBackground,
    boxShadow: theme.primaryShadow,
    color: '#ffffff',
    textShadow: '0 1px 2px rgba(20, 24, 38, 0.26)',
  }
}

export function getFeaturedHeroSecondaryCoverStyle(seed: number) {
  const theme = getFeaturedHeroTheme(seed)

  return {
    background: theme.secondaryBackground,
    boxShadow: theme.secondaryShadow,
    color: '#ffffff',
    textShadow: '0 1px 2px rgba(20, 24, 38, 0.26)',
  }
}
