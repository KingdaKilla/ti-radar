import { useState, useMemo } from 'react'
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, Cell, Legend, ReferenceLine, CartesianGrid } from 'recharts'
import MetricCard from './MetricCard'
import DownloadButton from './DownloadButton'
import { exportCSV } from '../utils/export'
import { COUNTRY_NAMES, NON_COUNTRY_CODES, isEuropean } from '../utils/countries'

const TOOLTIP = { backgroundColor: '#141c2e', border: '1px solid rgba(232,145,122,0.2)', borderRadius: 8 }
const TICK = { fill: '#5c6370', fontSize: 11 }

function GrowthTooltipContent({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const entry = payload[0]?.payload
  return (
    <div style={TOOLTIP} className="px-3 py-2 text-xs">
      <p className="text-[#f1f0ee] font-medium mb-1">{label}</p>
      {entry?.patents !== undefined && (
        <p className="text-[#e8917a]">Patente: {entry.patents?.toLocaleString()}{entry.patents_growth != null ? ` (${entry.patents_growth > 0 ? '+' : ''}${entry.patents_growth}%)` : ''}</p>
      )}
      {entry?.projects !== undefined && (
        <p className="text-[#f0abfc]">Projekte: {entry.projects?.toLocaleString()}{entry.projects_growth != null ? ` (${entry.projects_growth > 0 ? '+' : ''}${entry.projects_growth}%)` : ''}</p>
      )}
      {entry?.publications > 0 && (
        <p className="text-[#fbbf24]">Publikationen: {entry.publications?.toLocaleString()}{entry.publications_growth != null ? ` (${entry.publications_growth > 0 ? '+' : ''}${entry.publications_growth}%)` : ''}</p>
      )}
    </div>
  )
}

const MODES = [
  { key: 'wachstum', label: 'Wachstum' },
  { key: 'absolut', label: 'Absolut' },
]

export default function LandscapePanel({ data }) {
  const [chartMode, setChartMode] = useState('wachstum')

  const countries = useMemo(() => {
    if (!data?.top_countries) return []
    const raw = data.top_countries.filter(c => !NON_COUNTRY_CODES.has(c.country)).slice(0, 12).map(c => ({
      ...c,
      country_name: COUNTRY_NAMES[c.country] || c.country,
      isEu: isEuropean(c.country),
    }))
    const eu = raw.filter(c => c.isEu).sort((a, b) => (b.patents + b.projects) - (a.patents + a.projects))
    const nonEu = raw.filter(c => !c.isEu).sort((a, b) => (b.patents + b.projects) - (a.patents + a.projects))
    return [...eu, ...nonEu]
  }, [data?.top_countries])

  if (!data) return <PanelSkeleton title="Landschaft" />

  const hasPublications = data.total_publications > 0
  const growthData = (data.time_series || []).filter(d => d.patents_growth !== undefined)
  const absoluteData = data.time_series || []

  return (
    <div className="bg-white/[0.03] border border-white/[0.08] rounded-xl p-6">
      <div className="flex items-center gap-1.5 mb-4">
        <h3 className="text-lg font-semibold">Landschaft (UC1)</h3>
        <DownloadButton onClick={() => {
          const rows = (data.time_series || []).map(t => [
            t.year, t.patents || 0, t.projects || 0, t.publications || 0,
            t.patents_growth ?? '', t.projects_growth ?? '', t.publications_growth ?? '',
          ])
          exportCSV('uc1_landschaft.csv', ['Jahr', 'Patente', 'Projekte', 'Publikationen', 'Pat.Wachstum%', 'Proj.Wachstum%', 'Pub.Wachstum%'], rows)
        }} />
      </div>

      <div className={`grid ${hasPublications ? 'grid-cols-3' : 'grid-cols-2'} gap-3 mb-4`}>
        <MetricCard title="Patente" value={data.total_patents?.toLocaleString() || 0} subtitle="EPO DOCDB" />
        <MetricCard title="Projekte" value={data.total_projects?.toLocaleString() || 0} subtitle="EU CORDIS" />
        {hasPublications && (
          <MetricCard title="Publikationen" value={data.total_publications?.toLocaleString() || 0} subtitle="OpenAIRE" />
        )}
      </div>

      {(growthData.length > 1 || absoluteData.length > 1) && (
        <div className="h-48 sm:h-56 md:h-64 mb-4">
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs text-[#5c6370]">
              {chartMode === 'wachstum' ? 'Wachstumsraten (% YoY)' : 'Absolute Werte'}
            </p>
            <div className="flex gap-0.5 p-0.5 bg-white/[0.04] rounded-md">
              {MODES.map(m => (
                <button
                  key={m.key}
                  onClick={() => setChartMode(m.key)}
                  className={`px-2 py-0.5 text-[10px] rounded transition-all ${
                    chartMode === m.key
                      ? 'bg-[#e8917a]/20 text-[#e8917a]'
                      : 'text-[#5c6370] hover:text-[#9ca3af]'
                  }`}
                >
                  {m.label}
                </button>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height="100%">
            {chartMode === 'wachstum' ? (
              <LineChart data={growthData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="year" tick={TICK} tickLine={false} />
                <YAxis tick={TICK} tickLine={false} axisLine={false} unit="%" />
                <Tooltip content={<GrowthTooltipContent />} />
                <ReferenceLine y={0} stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="patents_growth" stroke="#e8917a" strokeWidth={2} dot={false} name="Patente" connectNulls />
                <Line type="monotone" dataKey="projects_growth" stroke="#f0abfc" strokeWidth={2} dot={false} name="Projekte" connectNulls />
                {hasPublications && (
                  <Line type="monotone" dataKey="publications_growth" stroke="#fbbf24" strokeWidth={2} dot={false} name="Publikationen" connectNulls />
                )}
              </LineChart>
            ) : (
              <AreaChart data={absoluteData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="year" tick={TICK} tickLine={false} />
                <YAxis tick={TICK} tickLine={false} axisLine={false} />
                <Tooltip content={<GrowthTooltipContent />} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Area type="monotone" dataKey="patents" stroke="#e8917a" fill="#e8917a" fillOpacity={0.15} strokeWidth={2} name="Patente" />
                <Area type="monotone" dataKey="projects" stroke="#f0abfc" fill="#f0abfc" fillOpacity={0.15} strokeWidth={2} name="Projekte" />
                {hasPublications && (
                  <Area type="monotone" dataKey="publications" stroke="#fbbf24" fill="#fbbf24" fillOpacity={0.15} strokeWidth={2} name="Publikationen" />
                )}
              </AreaChart>
            )}
          </ResponsiveContainer>
        </div>
      )}

      {countries.length > 0 && (
        <div className="h-56 sm:h-64">
          <div className="flex items-center gap-3 mb-1">
            <p className="text-xs text-[#5c6370]">Top Länder (Europa-Fokus)</p>
            <div className="flex items-center gap-3 text-[10px]">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#e8917a]" />EU/EEA</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#5c6370]" />Nicht-EU</span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={countries} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
              <XAxis type="number" tick={{ fill: '#5c6370', fontSize: 10 }} tickLine={false} axisLine={false} />
              <YAxis type="category" dataKey="country_name" tick={{ fill: '#5c6370', fontSize: 10 }} width={110} tickLine={false} axisLine={false} interval={0} />
              <Tooltip contentStyle={TOOLTIP} labelStyle={{ color: '#f1f0ee' }} itemStyle={{ color: '#e5e7eb' }} formatter={(value, name) => [value, name === 'patents' ? 'Patente' : 'Projekte']} />
              <Bar dataKey="patents" stackId="1" name="Patente" radius={[0, 0, 0, 0]}>
                {countries.map((c, i) => (
                  <Cell key={i} fill={c.isEu ? '#e8917a' : '#5c6370'} />
                ))}
              </Bar>
              <Bar dataKey="projects" stackId="1" name="Projekte" radius={[0, 3, 3, 0]}>
                {countries.map((c, i) => (
                  <Cell key={i} fill={c.isEu ? '#f0abfc' : '#3f4550'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="mt-4 pt-3 border-t border-white/[0.06]">
        <p className="text-[10px] text-[#5c6370] leading-relaxed">
          Quellen: Watts & Porter (1997) — Normalisierte YoY-Wachstumsraten; EPO DOCDB, CORDIS, OpenAIRE
        </p>
      </div>
    </div>
  )
}

function PanelSkeleton({ title }) {
  return (
    <div className="bg-white/[0.03] border border-white/[0.08] rounded-xl p-6 animate-pulse">
      <h3 className="text-lg font-semibold mb-4">{title}</h3>
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="h-16 bg-white/[0.04] rounded-lg" />
        <div className="h-16 bg-white/[0.04] rounded-lg" />
      </div>
      <div className="h-48 bg-white/[0.04] rounded-lg" />
    </div>
  )
}
