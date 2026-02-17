/**
 * CSV-Export Utility fuer Panel-Daten.
 * Generiert CSV-Blob und triggert Browser-Download.
 */
export function exportCSV(filename, headers, rows) {
  const escape = (cell) => {
    const str = String(cell ?? '')
    return str.includes(',') || str.includes('"') || str.includes('\n')
      ? `"${str.replace(/"/g, '""')}"`
      : str
  }

  const csv = [
    headers.map(escape).join(','),
    ...rows.map(row => row.map(escape).join(',')),
  ].join('\n')

  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
