const API_BASE = '/api/v1'

/**
 * Technology Radar Analyse ausfuehren.
 * @param {string} technology - Suchbegriff
 * @param {number} years - Analysezeitraum
 * @returns {Promise<object>} RadarResponse
 */
export async function fetchRadar(technology, years = 10) {
  const response = await fetch(`${API_BASE}/radar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ technology, years }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return response.json()
}

/**
 * Technologie-Vorschlaege abrufen.
 * @param {string} q - Suchbegriff (min. 2 Zeichen)
 * @param {number} limit - Max. Anzahl Vorschlaege
 * @returns {Promise<string[]>}
 */
export async function fetchSuggestions(q = '', limit = 8) {
  const params = new URLSearchParams({ limit: String(limit) })
  if (q) params.set('q', q)
  const response = await fetch(`${API_BASE}/suggestions?${params}`)
  if (!response.ok) return []
  return response.json()
}

/**
 * Health-Check abrufen.
 * @returns {Promise<object>}
 */
export async function fetchHealth() {
  const response = await fetch('/health')
  return response.json()
}
