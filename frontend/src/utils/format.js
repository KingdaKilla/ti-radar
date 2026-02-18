/** Shared text formatting utilities. */

export function toTitleCase(str) {
  if (!str) return ''
  return str.toLowerCase().replace(/(?:^|\s|[-/])\S/g, c => c.toUpperCase())
}
