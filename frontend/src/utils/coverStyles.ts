const CATEGORY_LABELS: Record<string, string> = {
  technology: '科技洞察',
  finance: '商业观察',
  sports: '现场叙事',
  entertainment: '文化片段',
  health: '身心节律',
  all: '精选内容',
}

type CoverTheme = {
  background: string
  shadow: string
}

const COVER_THEME_VARIANTS: Record<string, readonly CoverTheme[]> = {
  technology: [
    {
      background: 'radial-gradient(circle at top left, rgba(255, 255, 255, 0.4), transparent 45%), radial-gradient(circle at bottom right, rgba(140, 180, 255, 0.25), transparent 50%), linear-gradient(145deg, #4b7bff 0%, #689aff 45%, #8ab2ff 100%)',
      shadow: 'inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -20px 32px rgba(30,60,130,0.2)',
    },
    {
      background: 'radial-gradient(circle at 18% 16%, rgba(255, 255, 255, 0.46), transparent 30%), radial-gradient(circle at 84% 18%, rgba(132, 236, 255, 0.22), transparent 34%), linear-gradient(150deg, #2747c7 0%, #3968ea 38%, #4f8ff5 68%, #78baff 100%)',
      shadow: 'inset 0 1px 0 rgba(255,255,255,0.28), inset 0 -24px 34px rgba(18,40,122,0.22)',
    },
    {
      background: 'radial-gradient(circle at 20% 18%, rgba(255, 255, 255, 0.4), transparent 28%), radial-gradient(circle at 82% 80%, rgba(165, 179, 255, 0.24), transparent 36%), linear-gradient(152deg, #1f5d8b 0%, #277ab1 34%, #3f96d2 66%, #84c4ff 100%)',
      shadow: 'inset 0 1px 0 rgba(255,255,255,0.25), inset 0 -24px 36px rgba(18,56,96,0.22)',
    },
  ],
  finance: [
    {
      background: 'radial-gradient(circle at top left, rgba(255, 255, 255, 0.4), transparent 45%), radial-gradient(circle at bottom right, rgba(255, 220, 190, 0.25), transparent 50%), linear-gradient(145deg, #cd9752 0%, #e0ad74 45%, #f2cca4 100%)',
      shadow: 'inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -20px 32px rgba(130,80,40,0.2)',
    },
    {
      background: 'radial-gradient(circle at 15% 18%, rgba(255, 255, 255, 0.45), transparent 28%), radial-gradient(circle at 84% 18%, rgba(255, 239, 176, 0.24), transparent 34%), linear-gradient(150deg, #8b5e2e 0%, #b6783a 38%, #d3924f 66%, #f0bf82 100%)',
      shadow: 'inset 0 1px 0 rgba(255,255,255,0.28), inset 0 -24px 34px rgba(96,60,22,0.22)',
    },
    {
      background: 'radial-gradient(circle at 18% 16%, rgba(255, 255, 255, 0.38), transparent 30%), radial-gradient(circle at 82% 82%, rgba(255, 206, 154, 0.2), transparent 34%), linear-gradient(152deg, #6c4d35 0%, #98694a 38%, #c18966 70%, #e2b495 100%)',
      shadow: 'inset 0 1px 0 rgba(255,255,255,0.24), inset 0 -24px 36px rgba(84,52,28,0.2)',
    },
  ],
  sports: [
    {
      background: 'radial-gradient(circle at top left, rgba(255, 255, 255, 0.4), transparent 45%), radial-gradient(circle at bottom right, rgba(130, 240, 225, 0.25), transparent 50%), linear-gradient(145deg, #2b9ebc 0%, #44b7cc 45%, #69cdd2 100%)',
      shadow: 'inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -20px 32px rgba(15,100,120,0.2)',
    },
    {
      background: 'radial-gradient(circle at 16% 14%, rgba(255, 255, 255, 0.44), transparent 28%), radial-gradient(circle at 84% 18%, rgba(153, 255, 188, 0.22), transparent 32%), linear-gradient(150deg, #0f7f74 0%, #189f89 38%, #31bc9b 68%, #79dbc1 100%)',
      shadow: 'inset 0 1px 0 rgba(255,255,255,0.28), inset 0 -24px 34px rgba(10,78,72,0.22)',
    },
    {
      background: 'radial-gradient(circle at 18% 18%, rgba(255, 255, 255, 0.42), transparent 28%), radial-gradient(circle at 82% 82%, rgba(114, 210, 255, 0.24), transparent 34%), linear-gradient(152deg, #17638f 0%, #1f85af 38%, #2da2c2 68%, #6cd0dd 100%)',
      shadow: 'inset 0 1px 0 rgba(255,255,255,0.26), inset 0 -24px 36px rgba(14,64,92,0.22)',
    },
  ],
  entertainment: [
    {
      background: 'radial-gradient(circle at top left, rgba(255, 255, 255, 0.4), transparent 45%), radial-gradient(circle at bottom right, rgba(255, 190, 200, 0.25), transparent 50%), linear-gradient(145deg, #e87b97 0%, #efa0b3 45%, #f6bcc8 100%)',
      shadow: 'inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -20px 32px rgba(160,80,110,0.2)',
    },
    {
      background: 'radial-gradient(circle at 16% 14%, rgba(255, 255, 255, 0.45), transparent 28%), radial-gradient(circle at 84% 18%, rgba(255, 216, 128, 0.24), transparent 34%), linear-gradient(150deg, #b63b7b 0%, #d55387 40%, #ea7386 68%, #f4b17c 100%)',
      shadow: 'inset 0 1px 0 rgba(255,255,255,0.28), inset 0 -24px 34px rgba(132,42,86,0.22)',
    },
    {
      background: 'radial-gradient(circle at 18% 18%, rgba(255, 255, 255, 0.42), transparent 28%), radial-gradient(circle at 82% 80%, rgba(196, 170, 255, 0.22), transparent 34%), linear-gradient(152deg, #7e3aa7 0%, #a14bc0 38%, #c760bf 68%, #f29ab5 100%)',
      shadow: 'inset 0 1px 0 rgba(255,255,255,0.26), inset 0 -24px 36px rgba(88,34,112,0.22)',
    },
  ],
  health: [
    {
      background: 'radial-gradient(circle at top left, rgba(255, 255, 255, 0.4), transparent 45%), radial-gradient(circle at bottom right, rgba(190, 240, 190, 0.25), transparent 50%), linear-gradient(145deg, #65af76 0%, #85c492 45%, #acd9ab 100%)',
      shadow: 'inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -20px 32px rgba(50,110,65,0.2)',
    },
    {
      background: 'radial-gradient(circle at 16% 15%, rgba(255, 255, 255, 0.46), transparent 28%), radial-gradient(circle at 84% 18%, rgba(244, 220, 128, 0.2), transparent 34%), linear-gradient(150deg, #3d8d53 0%, #56a96b 38%, #7cc284 68%, #c4dd8f 100%)',
      shadow: 'inset 0 1px 0 rgba(255,255,255,0.28), inset 0 -24px 34px rgba(34,82,46,0.22)',
    },
    {
      background: 'radial-gradient(circle at 20% 18%, rgba(255, 255, 255, 0.42), transparent 28%), radial-gradient(circle at 82% 82%, rgba(163, 233, 214, 0.24), transparent 36%), linear-gradient(152deg, #2c7a6b 0%, #3d9a81 38%, #5cb39a 68%, #9ed4c0 100%)',
      shadow: 'inset 0 1px 0 rgba(255,255,255,0.26), inset 0 -24px 36px rgba(28,76,64,0.22)',
    },
  ],
  all: [
    {
      background: 'radial-gradient(circle at 15% 15%, rgba(255, 255, 255, 0.6), transparent 30%), radial-gradient(circle at 85% 15%, rgba(120, 255, 230, 0.35), transparent 35%), radial-gradient(circle at 80% 85%, rgba(150, 130, 255, 0.4), transparent 40%), linear-gradient(148deg, #0a4c63 0%, #106c82 30%, #1b8996 55%, #2578b8 75%, #5650eb 100%)',
      shadow: 'inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -28px 42px rgba(15,25,80,0.3)',
    },
    {
      background: 'radial-gradient(circle at 15% 15%, rgba(255, 255, 255, 0.55), transparent 28%), radial-gradient(circle at 86% 18%, rgba(255, 182, 193, 0.28), transparent 34%), radial-gradient(circle at 78% 84%, rgba(154, 240, 198, 0.24), transparent 38%), linear-gradient(148deg, #5b2d91 0%, #7e39a7 30%, #b24aa8 60%, #db6d8c 82%, #f5b16a 100%)',
      shadow: 'inset 0 1px 0 rgba(255,255,255,0.28), inset 0 -28px 42px rgba(72,22,92,0.3)',
    },
    {
      background: 'radial-gradient(circle at 18% 16%, rgba(255, 255, 255, 0.54), transparent 28%), radial-gradient(circle at 82% 18%, rgba(255, 220, 128, 0.26), transparent 34%), radial-gradient(circle at 82% 84%, rgba(96, 214, 174, 0.24), transparent 38%), linear-gradient(148deg, #23415f 0%, #31577f 30%, #3f6fa3 58%, #5b86c9 80%, #9bb1e8 100%)',
      shadow: 'inset 0 1px 0 rgba(255,255,255,0.28), inset 0 -28px 42px rgba(22,34,78,0.28)',
    },
  ],
}

type HeroTheme = {
  primaryBackground: string
  primaryShadow: string
  secondaryBackground: string
  secondaryShadow: string
}

const FEATURED_HERO_THEMES: readonly HeroTheme[] = [
  {
    primaryBackground: 'radial-gradient(circle at 15% 15%, rgba(255, 255, 255, 0.65), transparent 25%), radial-gradient(circle at 85% 15%, rgba(100, 255, 230, 0.35), transparent 35%), radial-gradient(circle at 80% 85%, rgba(150, 130, 255, 0.4), transparent 40%), linear-gradient(148deg, #094050 0%, #0f5c70 30%, #187784 55%, #1f64a2 75%, #4640d9 100%)',
    primaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.35), inset 0 -28px 42px rgba(10,20,70,0.35)',
    secondaryBackground: 'radial-gradient(circle at 20% 20%, rgba(255, 255, 255, 0.5), transparent 30%), radial-gradient(circle at 80% 25%, rgba(120, 250, 230, 0.25), transparent 35%), linear-gradient(150deg, #1c6575 0%, #2a7c8c 45%, #4b8cc9 100%)',
    secondaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.25), inset 0 -18px 28px rgba(15,40,90,0.2)',
  },
  {
    primaryBackground: 'radial-gradient(circle at 20% 15%, rgba(255, 255, 255, 0.55), transparent 25%), radial-gradient(circle at 85% 20%, rgba(255, 200, 140, 0.35), transparent 35%), radial-gradient(circle at 80% 85%, rgba(255, 120, 140, 0.3), transparent 40%), linear-gradient(148deg, #8b3c1a 0%, #b25424 28%, #cc723c 56%, #da9259 78%, #e0ad7b 100%)',
    primaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -28px 40px rgba(90,35,15,0.3)',
    secondaryBackground: 'radial-gradient(circle at 20% 20%, rgba(255, 255, 255, 0.45), transparent 30%), radial-gradient(circle at 80% 25%, rgba(255, 210, 150, 0.25), transparent 35%), linear-gradient(150deg, #a2522c 0%, #c47244 48%, #d89f6d 100%)',
    secondaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.25), inset 0 -18px 28px rgba(90,45,20,0.2)',
  },
  {
    primaryBackground: 'radial-gradient(circle at 15% 15%, rgba(255, 255, 255, 0.6), transparent 25%), radial-gradient(circle at 85% 15%, rgba(255, 120, 210, 0.35), transparent 35%), radial-gradient(circle at 80% 85%, rgba(130, 150, 255, 0.35), transparent 40%), linear-gradient(148deg, #481e7a 0%, #642a96 30%, #8d3aa8 56%, #b5499f 78%, #d5729a 100%)',
    primaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -28px 42px rgba(55,20,90,0.3)',
    secondaryBackground: 'radial-gradient(circle at 20% 20%, rgba(255, 255, 255, 0.5), transparent 30%), radial-gradient(circle at 80% 25%, rgba(255, 140, 220, 0.25), transparent 35%), linear-gradient(150deg, #62368c 0%, #8244a5 48%, #b368ac 100%)',
    secondaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.25), inset 0 -18px 28px rgba(65,30,100,0.2)',
  },
  {
    primaryBackground: 'radial-gradient(circle at 20% 15%, rgba(255, 255, 255, 0.55), transparent 25%), radial-gradient(circle at 80% 20%, rgba(140, 240, 190, 0.35), transparent 35%), radial-gradient(circle at 85% 85%, rgba(160, 220, 255, 0.3), transparent 40%), linear-gradient(148deg, #134434 0%, #1c5844 30%, #286854 54%, #3a806d 76%, #629c97 100%)',
    primaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -28px 40px rgba(15,55,40,0.3)',
    secondaryBackground: 'radial-gradient(circle at 20% 20%, rgba(255, 255, 255, 0.45), transparent 30%), radial-gradient(circle at 80% 25%, rgba(160, 240, 200, 0.25), transparent 35%), linear-gradient(150deg, #2d6250 0%, #447a64 48%, #729d8f 100%)',
    secondaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.25), inset 0 -18px 28px rgba(20,65,45,0.2)',
  },
  {
    primaryBackground: 'radial-gradient(circle at 15% 15%, rgba(255, 255, 255, 0.6), transparent 25%), radial-gradient(circle at 85% 15%, rgba(200, 230, 255, 0.35), transparent 35%), radial-gradient(circle at 80% 85%, rgba(150, 170, 255, 0.35), transparent 40%), linear-gradient(148deg, #3f225e 0%, #54307a 28%, #6d4094 56%, #7552ac 76%, #8088d1 100%)',
    primaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -28px 42px rgba(40,25,75,0.3)',
    secondaryBackground: 'radial-gradient(circle at 20% 20%, rgba(255, 255, 255, 0.5), transparent 30%), radial-gradient(circle at 80% 25%, rgba(210, 220, 255, 0.25), transparent 35%), linear-gradient(150deg, #5b3e7a 0%, #725292 48%, #887bc1 100%)',
    secondaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.25), inset 0 -18px 28px rgba(45,30,85,0.2)',
  },
  {
    primaryBackground: 'radial-gradient(circle at 20% 15%, rgba(255, 255, 255, 0.55), transparent 25%), radial-gradient(circle at 80% 20%, rgba(255, 180, 200, 0.35), transparent 35%), radial-gradient(circle at 85% 85%, rgba(255, 220, 130, 0.3), transparent 40%), linear-gradient(148deg, #95394b 0%, #b2465c 30%, #c66265 56%, #d38557 78%, #dba96b 100%)',
    primaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -28px 42px rgba(95,30,45,0.3)',
    secondaryBackground: 'radial-gradient(circle at 20% 20%, rgba(255, 255, 255, 0.45), transparent 30%), radial-gradient(circle at 80% 25%, rgba(255, 190, 200, 0.25), transparent 35%), linear-gradient(150deg, #a4495c 0%, #c25f6e 48%, #d49579 100%)',
    secondaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.25), inset 0 -18px 28px rgba(100,40,55,0.2)',
  },
  {
    primaryBackground: 'radial-gradient(circle at 15% 15%, rgba(255, 255, 255, 0.45), transparent 25%), radial-gradient(circle at 85% 20%, rgba(255, 42, 133, 0.35), transparent 35%), radial-gradient(circle at 80% 85%, rgba(0, 225, 255, 0.3), transparent 40%), linear-gradient(148deg, #0f172a 0%, #1e1b4b 30%, #4c1d95 60%, #9d174d 100%)',
    primaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.2), inset 0 -28px 42px rgba(15,23,42,0.4)',
    secondaryBackground: 'radial-gradient(circle at 18% 18%, rgba(255, 255, 255, 0.35), transparent 25%), radial-gradient(circle at 82% 20%, rgba(255, 113, 206, 0.25), transparent 32%), linear-gradient(150deg, #1e293b 0%, #312e81 50%, #701a75 100%)',
    secondaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.18), inset 0 -18px 28px rgba(15,23,42,0.3)',
  },
  {
    primaryBackground: 'radial-gradient(circle at 20% 15%, rgba(255, 255, 255, 0.5), transparent 25%), radial-gradient(circle at 80% 20%, rgba(250, 204, 21, 0.25), transparent 35%), radial-gradient(circle at 85% 85%, rgba(52, 211, 153, 0.3), transparent 35%), linear-gradient(148deg, #064e3b 0%, #065f46 30%, #059669 60%, #10b981 85%, #fbbf24 100%)',
    primaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.25), inset 0 -28px 42px rgba(2,44,34,0.35)',
    secondaryBackground: 'radial-gradient(circle at 20% 18%, rgba(255, 255, 255, 0.4), transparent 25%), radial-gradient(circle at 80% 22%, rgba(253, 224, 71, 0.2), transparent 32%), linear-gradient(150deg, #065f46 0%, #059669 50%, #34d399 100%)',
    secondaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.2), inset 0 -18px 28px rgba(2,44,34,0.25)',
  },
  {
    primaryBackground: 'radial-gradient(circle at 15% 15%, rgba(255, 255, 255, 0.55), transparent 25%), radial-gradient(circle at 85% 15%, rgba(255, 237, 74, 0.3), transparent 35%), radial-gradient(circle at 80% 85%, rgba(255, 107, 107, 0.35), transparent 40%), linear-gradient(148deg, #c53030 0%, #e53e3e 30%, #ed8936 60%, #f6ad55 85%, #faf089 100%)',
    primaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.28), inset 0 -28px 42px rgba(116,42,42,0.3)',
    secondaryBackground: 'radial-gradient(circle at 18% 18%, rgba(255, 255, 255, 0.45), transparent 25%), radial-gradient(circle at 82% 20%, rgba(255, 243, 130, 0.25), transparent 32%), linear-gradient(150deg, #d53f8c 0%, #ed64a6 50%, #f6ad55 100%)',
    secondaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.22), inset 0 -18px 28px rgba(116,42,42,0.2)',
  },
  {
    primaryBackground: 'radial-gradient(circle at 10% 20%, rgba(255, 255, 255, 0.4), transparent 30%), radial-gradient(circle at 90% 10%, rgba(255, 115, 115, 0.3), transparent 40%), radial-gradient(circle at 80% 90%, rgba(255, 200, 100, 0.35), transparent 45%), linear-gradient(148deg, #4a154b 0%, #902d41 35%, #cc444b 65%, #ff7f50 100%)',
    primaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.25), inset 0 -28px 42px rgba(45,15,45,0.4)',
    secondaryBackground: 'radial-gradient(circle at 15% 25%, rgba(255, 255, 255, 0.3), transparent 30%), radial-gradient(circle at 85% 15%, rgba(255, 150, 150, 0.25), transparent 35%), linear-gradient(150deg, #601a40 0%, #a0354a 50%, #df5e55 100%)',
    secondaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.2), inset 0 -18px 28px rgba(45,15,45,0.3)',
  },
  {
    primaryBackground: 'radial-gradient(circle at 25% 15%, rgba(255, 255, 255, 0.5), transparent 25%), radial-gradient(circle at 75% 25%, rgba(100, 255, 218, 0.25), transparent 35%), radial-gradient(circle at 85% 85%, rgba(10, 25, 47, 0.4), transparent 45%), linear-gradient(148deg, #0a192f 0%, #112240 40%, #233554 70%, #64ffda 100%)',
    primaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.2), inset 0 -28px 42px rgba(5,10,20,0.5)',
    secondaryBackground: 'radial-gradient(circle at 20% 20%, rgba(255, 255, 255, 0.35), transparent 25%), radial-gradient(circle at 80% 30%, rgba(100, 255, 218, 0.15), transparent 35%), linear-gradient(150deg, #0f2443 0%, #1c3359 50%, #45b3a3 100%)',
    secondaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.15), inset 0 -18px 28px rgba(5,10,20,0.4)',
  },
  {
    primaryBackground: 'radial-gradient(circle at 15% 20%, rgba(255, 255, 255, 0.45), transparent 30%), radial-gradient(circle at 85% 15%, rgba(250, 163, 7, 0.3), transparent 40%), radial-gradient(circle at 80% 85%, rgba(208, 0, 0, 0.25), transparent 40%), linear-gradient(148deg, #370617 0%, #6a040f 30%, #9d0208 60%, #dc2f02 85%, #f48c06 100%)',
    primaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.25), inset 0 -28px 42px rgba(35,5,15,0.4)',
    secondaryBackground: 'radial-gradient(circle at 18% 25%, rgba(255, 255, 255, 0.35), transparent 30%), radial-gradient(circle at 82% 20%, rgba(250, 163, 7, 0.2), transparent 35%), linear-gradient(150deg, #53030d 0%, #85020a 50%, #e85d04 100%)',
    secondaryShadow: 'inset 0 1px 0 rgba(255,255,255,0.2), inset 0 -18px 28px rgba(35,5,15,0.3)',
  }
]

function getFeaturedHeroTheme(seed: number) {
  const index = Math.abs(seed) % FEATURED_HERO_THEMES.length
  return FEATURED_HERO_THEMES[index]
}

export function getCategoryLabel(category: string) {
  return CATEGORY_LABELS[category] ?? CATEGORY_LABELS.all
}

export function getCoverTheme(category: string) {
  const themes = COVER_THEME_VARIANTS[category] ?? COVER_THEME_VARIANTS.all
  return themes[0]
}

export function getCoverStyle(category: string, variantSeed?: number | string) {
  const themes = COVER_THEME_VARIANTS[category] ?? COVER_THEME_VARIANTS.all
  const normalizedSeed = typeof variantSeed === 'string'
    ? variantSeed.split('').reduce((total, char) => total + char.charCodeAt(0), 0)
    : variantSeed ?? 0
  const theme = themes[Math.abs(normalizedSeed) % themes.length] ?? themes[0]

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
