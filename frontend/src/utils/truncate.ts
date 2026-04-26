export function truncateText(text: string, maxLength: number): string {
  const characters = Array.from(text)

  if (characters.length <= maxLength) {
    return text
  }

  return `${characters.slice(0, maxLength).join('')}...`
}
