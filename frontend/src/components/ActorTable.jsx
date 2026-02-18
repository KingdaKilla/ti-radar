import { useState, useMemo } from 'react'
import { toTitleCase } from '../utils/format'

const COLUMNS = [
  { key: 'rank', label: '#', align: 'text-right' },
  { key: 'name', label: 'Name', align: 'text-left' },
  { key: 'patents', label: 'Patente', align: 'text-right' },
  { key: 'projects', label: 'Projekte', align: 'text-right' },
  { key: 'total', label: 'Gesamt', align: 'text-right' },
  { key: 'share', label: 'Anteil', align: 'text-right' },
  { key: 'country', label: 'Land', align: 'text-left' },
]

export default function ActorTable({ actors }) {
  const [sortKey, setSortKey] = useState('rank')
  const [sortAsc, setSortAsc] = useState(true)
  const [filter, setFilter] = useState('')

  const sorted = useMemo(() => {
    let data = [...(actors || [])]
    if (filter) {
      const lower = filter.toLowerCase()
      data = data.filter(a =>
        a.name?.toLowerCase().includes(lower) ||
        a.country?.toLowerCase().includes(lower)
      )
    }
    data.sort((a, b) => {
      const va = a[sortKey] ?? ''
      const vb = b[sortKey] ?? ''
      if (typeof va === 'number' && typeof vb === 'number') {
        return sortAsc ? va - vb : vb - va
      }
      return sortAsc
        ? String(va).localeCompare(String(vb))
        : String(vb).localeCompare(String(va))
    })
    return data
  }, [actors, sortKey, sortAsc, filter])

  const handleSort = (key) => {
    if (key === sortKey) {
      setSortAsc(!sortAsc)
    } else {
      setSortKey(key)
      setSortAsc(key === 'rank' || key === 'name')
    }
  }

  if (!actors || actors.length === 0) {
    return <p className="text-[#5c6370] text-sm py-8 text-center">Keine Akteur-Daten verfuegbar</p>
  }

  return (
    <div>
      <input
        type="text"
        placeholder="Akteure filtern..."
        value={filter}
        onChange={e => setFilter(e.target.value)}
        className="w-full mb-3 px-3 py-1.5 bg-white/[0.04] border border-white/[0.08] rounded-lg text-sm text-[#e5e7eb] placeholder-[#5c6370] focus:outline-none focus:border-[#e8917a]/30"
      />
      <div className="overflow-x-auto max-h-80 overflow-y-auto">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-[#0b1121]">
            <tr className="border-b border-white/[0.08]">
              {COLUMNS.map(col => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  className={`py-2 px-2 font-medium cursor-pointer hover:text-[#9ca3af] transition-colors whitespace-nowrap ${col.align} ${
                    col.key === sortKey ? 'text-[#e8917a]' : 'text-[#5c6370]'
                  }`}
                >
                  {col.label}
                  {col.key === sortKey && (
                    <span className="ml-0.5">{sortAsc ? '\u25B2' : '\u25BC'}</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((actor, i) => (
              <tr key={i} className="border-b border-white/[0.04] hover:bg-white/[0.04] transition-colors">
                <td className="py-1.5 px-2 text-right text-[#5c6370]">{actor.rank}</td>
                <td className="py-1.5 px-2 text-[#e5e7eb] font-mono text-[10px]" title={toTitleCase(actor.name)}>
                  {(() => { const n = toTitleCase(actor.name); return n.length > 30 ? n.slice(0, 27) + '...' : n })()}
                </td>
                <td className="py-1.5 px-2 text-right text-[#9ca3af]">{actor.patents?.toLocaleString()}</td>
                <td className="py-1.5 px-2 text-right text-[#9ca3af]">{actor.projects?.toLocaleString()}</td>
                <td className="py-1.5 px-2 text-right text-[#e8917a] font-medium">{actor.total?.toLocaleString()}</td>
                <td className="py-1.5 px-2 text-right text-[#9ca3af]">{((actor.share || 0) * 100).toFixed(1)}%</td>
                <td className="py-1.5 px-2 text-[#5c6370]">{actor.country || '\u2014'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[10px] text-[#5c6370] mt-2">{sorted.length} von {actors.length} Akteuren</p>
    </div>
  )
}
