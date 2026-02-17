import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid } from 'recharts'
import MetricCard from './MetricCard'
import DownloadButton from './DownloadButton'
import ForceGraph from './ForceGraph'
import SankeyDiagram from './SankeyDiagram'
import ActorTable from './ActorTable'
import { exportCSV } from '../utils/export'

const BAR_COLORS = ['#e8917a', '#e09b87', '#d8a594', '#d0afa1', '#c8b9ae', '#f0abfc', '#d4a0e0', '#9b8ab8', '#fbbf24', '#94a3b8']

const HHI_LABELS = {
  Low: { text: 'Gering konzentriert', style: 'bg-[#e8917a]/10 text-[#e8917a] border-[#e8917a]/20' },
  Moderate: { text: 'Mäßig konzentriert', style: 'bg-[#fbbf24]/10 text-[#fbbf24] border-[#fbbf24]/20' },
  High: { text: 'Hoch konzentriert', style: 'bg-[#f0abfc]/10 text-[#f0abfc] border-[#f0abfc]/20' },
}

const TOOLTIP = { backgroundColor: '#141c2e', border: '1px solid rgba(232,145,122,0.2)', borderRadius: 8 }

const VIEWS = [
  { key: 'chart', label: 'Diagramm' },
  { key: 'network', label: 'Netzwerk' },
  { key: 'sankey', label: 'Sankey' },
  { key: 'table', label: 'Tabelle' },
]

export default function CompetitivePanel({ data, onSelectActor }) {
  const [view, setView] = useState('chart')

  if (!data) return <PanelSkeleton title="Wettbewerb" />

  const actors = (data.top_actors || []).slice(0, 8).map(a => ({
    ...a,
    short: a.name?.length > 25 ? a.name.substring(0, 22) + '...' : a.name,
    pct: Math.round((a.share || 0) * 1000) / 10,
  }))

  const levelInfo = HHI_LABELS[data.concentration_level] || HHI_LABELS.Low

  // Verfuegbare Views filtern (nur anzeigen wenn Daten vorhanden)
  const availableViews = VIEWS.filter(v => {
    if (v.key === 'network') return data.network_nodes?.length > 1
    if (v.key === 'sankey') return data.sankey_nodes?.length > 1
    if (v.key === 'table') return data.full_actors?.length > 0
    return true
  })

  return (
    <div className="bg-white/[0.03] border border-white/[0.08] rounded-xl p-6">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <div className="flex items-center gap-1.5">
          <h3 className="text-lg font-semibold">Wettbewerb (UC3)</h3>
          <DownloadButton onClick={() => {
            const rows = (data.full_actors || data.top_actors || []).map(a => [
              a.rank || '', a.name || '', a.patents || 0, a.projects || 0,
              a.total || a.count || 0, ((a.share || 0) * 100).toFixed(1), a.country || '',
            ])
            exportCSV('uc3_wettbewerb.csv', ['Rang', 'Name', 'Patente', 'Projekte', 'Gesamt', 'Anteil%', 'Land'], rows)
          }} />
        </div>
        {data.concentration_level && (
          <span className={`px-2.5 py-0.5 border rounded-full text-xs ${levelInfo.style}`}>
            {levelInfo.text}
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <MetricCard title="HHI Index" value={Math.round(data.hhi_index || 0)} subtitle="0 = fragmentiert, 10000 = Monopol" info={"HHI = \u03A3(s\u1D62\u00B2) \u00D7 10.000\ns\u1D62 = Aktivit\u00E4ten eines Akteurs / Gesamt\nQuelle: DOJ/FTC Merger Guidelines"} />
        <MetricCard title="Top-3 Anteil" value={`${Math.round((data.top_3_share || 0) * 100)}%`} subtitle="Aktivitätsanteil der drei größten" info={"(\u03A3 Top-3 Aktivit\u00E4ten) / Gesamt \u00D7 100\nAktivit\u00E4ten = Patente + Projektbeteiligungen"} />
      </div>

      {/* View-Switcher */}
      {availableViews.length > 1 && (
        <div className="flex gap-1 mb-4 p-1 bg-white/[0.04] rounded-lg w-fit">
          {availableViews.map(v => (
            <button
              key={v.key}
              onClick={() => setView(v.key)}
              className={`px-3 py-1 text-xs rounded-md transition-all ${
                view === v.key
                  ? 'bg-[#e8917a]/20 text-[#e8917a] border border-[#e8917a]/30'
                  : 'text-[#5c6370] hover:text-[#9ca3af] border border-transparent'
              }`}
            >
              {v.label}
            </button>
          ))}
        </div>
      )}

      {/* Views */}
      {view === 'chart' && actors.length > 0 && (
        <div className="h-48 sm:h-56 md:h-64">
          <p className="text-xs text-[#5c6370] mb-1">Top Akteure</p>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={actors} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
              <XAxis type="number" tick={{ fill: '#5c6370', fontSize: 10 }} tickLine={false} axisLine={false} />
              <YAxis type="category" dataKey="short" tick={{ fill: '#5c6370', fontSize: 9 }} width={100} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={TOOLTIP}
                formatter={(value) => [value, 'Aktivitäten']}
                labelFormatter={(label) => {
                  const actor = actors.find(a => a.short === label)
                  return actor?.name || label
                }}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} onClick={(entry) => onSelectActor?.(entry?.name || null)} cursor="pointer">
                {actors.map((_, i) => (
                  <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {view === 'network' && (
        <ForceGraph nodes={data.network_nodes} edges={data.network_edges} />
      )}

      {view === 'sankey' && (
        <SankeyDiagram nodes={data.sankey_nodes} links={data.sankey_links} />
      )}

      {view === 'table' && (
        <ActorTable actors={data.full_actors} />
      )}

      <div className="mt-4 pt-3 border-t border-white/[0.06]">
        <p className="text-[10px] text-[#5c6370] leading-relaxed">
          Quellen: HHI (DOJ/FTC) — Marktkonzentration; Co-Partizipation — Netzwerkanalyse; EPO DOCDB, CORDIS
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
