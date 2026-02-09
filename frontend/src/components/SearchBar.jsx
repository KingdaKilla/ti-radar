import { useState, useEffect, useRef } from 'react'
import { fetchSuggestions } from '../api'

const YEAR_OPTIONS = [5, 10, 15, 20, 30]

export default function SearchBar({ onSearch, loading }) {
  const [query, setQuery] = useState('quantum computing')
  const [years, setYears] = useState(10)
  const [suggestions, setSuggestions] = useState([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const wrapperRef = useRef(null)
  const debounceRef = useRef(null)

  // Vorschlaege laden (leer = Default-Liste, sonst FTS5-Suche)
  const loadSuggestions = async (q) => {
    try {
      const results = await fetchSuggestions(q)
      setSuggestions(results)
      setShowSuggestions(results.length > 0)
      setSelectedIndex(-1)
    } catch {
      setSuggestions([])
    }
  }

  // Debounced fetch suggestions bei Eingabe
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)

    debounceRef.current = setTimeout(() => {
      loadSuggestions(query.trim())
    }, 300)

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [query])

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (query.trim()) {
      setShowSuggestions(false)
      onSearch(query.trim(), years)
    }
  }

  const handleSelect = (term) => {
    setQuery(term)
    setShowSuggestions(false)
    onSearch(term, years)
  }

  const handleKeyDown = (e) => {
    if (!showSuggestions || suggestions.length === 0) return

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex(i => Math.min(i + 1, suggestions.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex(i => Math.max(i - 1, -1))
    } else if (e.key === 'Enter' && selectedIndex >= 0) {
      e.preventDefault()
      handleSelect(suggestions[selectedIndex])
    } else if (e.key === 'Escape') {
      setShowSuggestions(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mb-8">
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1" ref={wrapperRef}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => {
              if (suggestions.length > 0) {
                setShowSuggestions(true)
              } else {
                loadSuggestions(query.trim())
              }
            }}
            onKeyDown={handleKeyDown}
            placeholder="Technologie eingeben (z.B. quantum computing, hydrogen fuel cells)"
            className="w-full px-6 py-4 bg-white/[0.04] border border-white/[0.08] rounded-xl text-white placeholder-[#5c6370] focus:outline-none focus:border-[#e8917a] focus:ring-2 focus:ring-[#e8917a]/20"
          />

          {showSuggestions && suggestions.length > 0 && (
            <ul className="absolute z-50 w-full mt-1 bg-[#141c2e] border border-white/[0.08] rounded-xl shadow-xl overflow-hidden">
              {suggestions.map((term, i) => (
                <li
                  key={term}
                  onClick={() => handleSelect(term)}
                  onMouseEnter={() => setSelectedIndex(i)}
                  className={`px-5 py-2.5 text-sm cursor-pointer transition-colors ${
                    i === selectedIndex
                      ? 'bg-[#e8917a]/20 text-white'
                      : 'text-[#9ca3af] hover:bg-white/[0.04]'
                  }`}
                >
                  {term}
                </li>
              ))}
            </ul>
          )}
        </div>

        <select
          value={years}
          onChange={(e) => setYears(Number(e.target.value))}
          className="px-4 py-4 bg-white/[0.04] border border-white/[0.08] rounded-xl text-white text-sm focus:outline-none focus:border-[#e8917a] cursor-pointer appearance-none"
          title="Analysezeitraum"
        >
          {YEAR_OPTIONS.map(y => (
            <option key={y} value={y} className="bg-[#0b1121]">{y} Jahre</option>
          ))}
        </select>

        <button
          type="submit"
          disabled={loading}
          className="px-6 py-4 bg-[#e8917a] hover:bg-[#d4785f] text-[#0b1121] disabled:opacity-50 rounded-xl font-medium transition-colors whitespace-nowrap"
        >
          {loading ? 'Analysiere...' : 'Analysieren'}
        </button>
      </div>
    </form>
  )
}
