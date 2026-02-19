import { useMemo } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts'
import MetricCard from './MetricCard'
import DownloadButton from './DownloadButton'
import FullscreenButton from './FullscreenButton'
import { useFullscreen } from '../hooks/useFullscreen'
import { exportCSV } from '../utils/export'
import { COUNTRY_NAMES, NON_COUNTRY_CODES, isEuropean } from '../utils/countries'

const TOOLTIP = { backgroundColor: '#141c2e', border: '1px solid rgba(232,145,122,0.2)', borderRadius: 8 }

export default function GeographicPanel({ data }) {
  const { isFullscreen, toggleFullscreen } = useFullscreen()
  // Europa-Fokus: EU-Laender oben, Nicht-EU unten, jeweils nach total sortiert
  const countries = useMemo(() => {
    if (!data?.country_distribution) return []
    const raw = data.country_distribution.filter(c => !NON_COUNTRY_CODES.has(c.country)).slice(0, 15).map(c => ({
      ...c,
      label: COUNTRY_NAMES[c.country] || c.country,
      isEu: isEuropean(c.country),
    }))
    const eu = raw.filter(c => c.isEu).sort((a, b) => b.total - a.total)
    const nonEu = raw.filter(c => !c.isEu).sort((a, b) => b.total - a.total)
    return [...eu, ...nonEu]
  }, [data?.country_distribution])

  if (!data) return <PanelSkeleton />

  const cities = (data.city_distribution || []).slice(0, 10)
  const collabPairs = (data.collaboration_pairs || []).slice(0, 10)

  return (
    <div className={isFullscreen ? 'fixed inset-0 z-50 bg-[#0d1117] overflow-y-auto p-8' : 'bg-white/[0.03] border border-white/[0.08] rounded-xl p-6'}>
      <div className="flex items-center gap-1.5 mb-4">
        <h3 className="text-lg font-semibold">Geografie (UC6)</h3>
        <DownloadButton onClick={() => {
          const rows = countries.map(c => [c.country, c.label, c.patents || 0, c.projects || 0, c.total || 0, c.isEu ? 'EU' : ''])
          exportCSV('uc6_geografie.csv', ['Code', 'Land', 'Patente', 'Projekte', 'Gesamt', 'EU'], rows)
        }} />
        <FullscreenButton isFullscreen={isFullscreen} onClick={toggleFullscreen} />
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <MetricCard title="Länder" value={data.total_countries} subtitle="Aktive Länder" />
        <MetricCard title="Städte" value={data.total_cities} subtitle="CORDIS-Standorte" />
        <MetricCard
          title="Cross-Border"
          value={`${((data.cross_border_share ?? 0) * 100).toFixed(0)}%`}
          subtitle="Grenzübergreifend"
        />
      </div>

      {countries.length > 0 && (
        <div className={`${isFullscreen ? 'h-[60vh]' : 'h-56 sm:h-64'} mb-4`}>
          <div className="flex items-center gap-3 mb-1">
            <p className="text-xs text-[#5c6370]">Länderverteilung (Europa-Fokus)</p>
            <div className="flex items-center gap-3 text-[10px]">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#e8917a]" />EU/EEA</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#5c6370]" />Nicht-EU</span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={countries} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
              <XAxis type="number" tick={{ fill: '#5c6370', fontSize: 10 }} tickLine={false} axisLine={false} />
              <YAxis type="category" dataKey="label" tick={{ fill: '#5c6370', fontSize: 10 }} width={110} tickLine={false} axisLine={false} interval={0} />
              <Tooltip contentStyle={TOOLTIP} labelStyle={{ color: '#f1f0ee' }} itemStyle={{ color: '#e5e7eb' }} formatter={(value, name) => [value, name]} />
              <Bar dataKey="patents" stackId="geo" name="Patente" radius={[0, 0, 0, 0]}>
                {countries.map((c, i) => (
                  <Cell key={i} fill={c.isEu ? '#e8917a' : '#5c6370'} />
                ))}
              </Bar>
              <Bar dataKey="projects" stackId="geo" name="Projekte" radius={[0, 3, 3, 0]}>
                {countries.map((c, i) => (
                  <Cell key={i} fill={c.isEu ? '#818cf8' : '#3f4550'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {collabPairs.length > 0 && (
        <div className="mb-4">
          <p className="text-xs text-[#5c6370] mb-2">Top Kooperationsachsen</p>
          <div className="space-y-1.5">
            {collabPairs.map((p, i) => {
              const maxCount = collabPairs[0]?.count || 1
              const pct = Math.round((p.count / maxCount) * 100)
              const labelA = COUNTRY_NAMES[p.country_a] || p.country_a
              const labelB = COUNTRY_NAMES[p.country_b] || p.country_b
              return (
                <div key={i} className="flex items-center gap-2 text-xs">
                  <span className="w-44 sm:w-52 text-[#9ca3af] flex-shrink-0 text-[11px]">
                    {labelA} — {labelB}
                  </span>
                  <div className="flex-1 h-3 bg-white/[0.04] rounded-full overflow-hidden">
                    <div className="h-full bg-[#818cf8]/60 rounded-full" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="text-[#5c6370] w-8 text-right">{p.count}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {cities.length > 0 && (
        <div>
          <p className="text-xs text-[#5c6370] mb-2">Top Städte (CORDIS)</p>
          <div className="flex flex-wrap gap-1.5">
            {cities.map((c, i) => (
              <span key={i} className="px-2 py-0.5 bg-white/[0.04] border border-white/[0.06] rounded-full text-[10px] text-[#9ca3af]">
                {c.city} ({c.count})
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="mt-4 pt-3 border-t border-white/[0.06]">
        <p className="text-[10px] text-[#5c6370] leading-relaxed">
          Quellen: Narin (1994) — Patent-Bibliometrie; Luukkonen et al. (1993) — Internationale Kooperation; EPO DOCDB, CORDIS; Europa-Fokus (EU27 + EEA)
        </p>
      </div>
    </div>
  )
}

function PanelSkeleton() {
  return (
    <div className="bg-white/[0.03] border border-white/[0.08] rounded-xl p-6 animate-pulse">
      <h3 className="text-lg font-semibold mb-4">Geografie (UC6)</h3>
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="h-16 bg-white/[0.04] rounded-lg" />
        <div className="h-16 bg-white/[0.04] rounded-lg" />
        <div className="h-16 bg-white/[0.04] rounded-lg" />
      </div>
      <div className="h-48 bg-white/[0.04] rounded-lg" />
    </div>
  )
}
