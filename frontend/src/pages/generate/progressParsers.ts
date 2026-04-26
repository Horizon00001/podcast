export function parseSectionDescriptor(text: string) {
  const match = text.match(/section=(\d+) type=([^\s]+) lines=(\d+)/)
  if (!match) {
    return null
  }

  return {
    sectionNumber: Number(match[1]),
    sectionType: match[2],
    lineCount: Number(match[3]),
  }
}

export function sectionKey(groupLabel: string, descriptor: { sectionNumber: number }) {
  return `${groupLabel}#${descriptor.sectionNumber}`
}

export function countByStatus<T extends { status: string }>(items: T[], status: T['status']) {
  return items.filter((item) => item.status === status).length
}
