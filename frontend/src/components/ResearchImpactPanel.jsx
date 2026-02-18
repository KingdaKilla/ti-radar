import { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, BarChart, Bar, Legend, ReferenceArea, ReferenceLine } from 'recharts'
import MetricCard from './MetricCard'
import DownloadButton from './DownloadButton'
import { exportCSV } from '../utils/export'
import ChartTooltip from './ChartTooltip'

const TOOLTIP = { backgroundColor: '#141c2e', border: '1px solid rgba(232,145,122,0.2)', borderRadius: 8 }

const VIEWS = [
  { key: 'trend', label: 'Trend' },
  { key: 'papers', label: 'Papers' },
  { key: 'venues', label: 'Venues' },
]

export default function ResearchImpactPanel({ data, dataCompleteUntil }) {
  const [view, setView] = useState('trend')

  if (!data) return <PanelSkeleton />

  const citationTrend = data.citation_trend || []
  const topPapers = (data.top_papers || []).slice(0, 8)
  const topVenues = (data.top_venues || []).slice(0, 8)
  const pubTypes = data.publication_types || []

  return (
    <div className="bg-white/[0.03] border border-white/[0.08] rounded-xl p-6">
      <div className="flex items-center gap-1.5 mb-4">
        <h3 className="text-lg font-semibold">Forschungsimpact (UC7)</h3>
        <DownloadButton onClick={() => {
          const rows = topPapers.map(p => [p.title, p.year, p.citations, p.venue || ''])
          exportCSV('uc7_research_impact.csv', ['Titel', 'Jahr', 'Zitationen', 'Venue'], rows)
        }} />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <MetricCard
          title="h-Index"
          value={data.h_index}
          subtitle="Hirsch-Index"
          info={"h-Index: Größtes h, bei dem h Papers\nmindestens h Zitationen haben (Hirsch, 2005)"}
        />
        <MetricCard title="Papers" value={data.total_papers?.toLocaleString()} subtitle="Semantic Scholar" />
        <MetricCard
          title="Ø Zitationen"
          value={data.avg_citations?.toFixed(1)}
          subtitle="Pro Paper"
        />
        <MetricCard
          title="Einflussreich"
          value={`${((data.influential_ratio ?? 0) * 100).toFixed(0)}%`}
          subtitle="Influential Citations"
        />
      </div>

      {/* Empty state when Semantic Scholar is rate-limited or unavailable */}
      {data.total_papers === 0 && citationTrend.length === 0 && (
        <div className="py-8 text-center">
          <p className="text-[#5c6370] text-sm mb-1">Keine Publikationsdaten verfügbar</p>
          <p className="text-[#5c6370]/60 text-xs">Semantic Scholar API temporär nicht erreichbar (Rate Limit). Bitte später erneut versuchen.</p>
        </div>
      )}

      {/* View toggle */}
      {data.total_papers > 0 && <div className="flex items-center justify-between mb-2">
        <p className="text-xs text-[#5c6370]">
          {view === 'trend' && 'Zitationstrend pro Jahr'}
          {view === 'papers' && 'Meistzitierte Papers'}
          {view === 'venues' && 'Top Journals / Konferenzen'}
        </p>
        <div className="flex gap-0.5 p-0.5 bg-white/[0.04] rounded-md">
          {VIEWS.map(v => (
            <button
              key={v.key}
              onClick={() => setView(v.key)}
              className={`px-2 py-0.5 text-[10px] rounded transition-all ${
                view === v.key
                  ? 'bg-[#34d399]/20 text-[#34d399]'
                  : 'text-[#5c6370] hover:text-[#9ca3af]'
              }`}
            >
              {v.label}
            </button>
          ))}
        </div>
      </div>}

      {data.total_papers > 0 && view === 'trend' && citationTrend.length > 0 && (
        <div className="h-48 sm:h-56">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={citationTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              {dataCompleteUntil && <ReferenceArea x1={dataCompleteUntil + 1} fill="#5c6370" fillOpacity={0.08} />}
              {dataCompleteUntil && <ReferenceLine x={dataCompleteUntil + 1} stroke="#5c6370" strokeDasharray="4 4" strokeOpacity={0.5} label={{ value: 'unvollst.', fill: '#5c6370', fontSize: 9, position: 'top' }} />}
              <XAxis dataKey="year" tick={{ fill: '#5c6370', fontSize: 10 }} tickLine={false} />
              <YAxis tick={{ fill: '#5c6370', fontSize: 10 }} tickLine={false} axisLine={false} />
              <Tooltip content={<ChartTooltip dataCompleteUntil={dataCompleteUntil} />} />
              <Legend wrapperStyle={{ fontSize: 10 }} />
              <Line type="monotone" dataKey="paper_count" stroke="#34d399" strokeWidth={2} dot={false} name="Papers" />
              <Line type="monotone" dataKey="citations" stroke="#fbbf24" strokeWidth={2} dot={false} name="Zitationen" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {data.total_papers > 0 && view === 'papers' && topPapers.length > 0 && (
        <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
          {topPapers.map((p, i) => (
            <div key={i} className="flex items-start gap-2 text-xs p-2 bg-white/[0.02] rounded-lg">
              <span className="text-[#5c6370] font-mono w-5 flex-shrink-0 text-right">{i + 1}</span>
              <div className="flex-1 min-w-0">
                <p className="text-[#f1f0ee] truncate" title={p.title}>{p.title}</p>
                <p className="text-[#5c6370]">{p.venue || 'Unbekannt'} · {p.year}</p>
              </div>
              <span className="text-[#34d399] font-medium flex-shrink-0">{p.citations?.toLocaleString()}</span>
            </div>
          ))}
        </div>
      )}

      {data.total_papers > 0 && view === 'venues' && topVenues.length > 0 && (
        <div className="h-48 sm:h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={topVenues} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
              <XAxis type="number" tick={{ fill: '#5c6370', fontSize: 10 }} tickLine={false} axisLine={false} />
              <YAxis
                type="category"
                dataKey="venue"
                tick={{ fill: '#5c6370', fontSize: 9 }}
                width={120}
                tickLine={false}
                axisLine={false}
                interval={0}
                tickFormatter={(v) => v.length > 20 ? v.slice(0, 18) + '…' : v}
              />
              <Tooltip content={<ChartTooltip dataCompleteUntil={dataCompleteUntil} />} />
              <Bar dataKey="count" fill="#34d399" radius={[0, 3, 3, 0]} name="Papers" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {pubTypes.length > 0 && (
        <div className="mt-3">
          <p className="text-xs text-[#5c6370] mb-1.5">Publikationstypen</p>
          <div className="flex flex-wrap gap-1.5">
            {pubTypes.map((t, i) => (
              <span key={i} className="px-2 py-0.5 bg-white/[0.04] border border-white/[0.06] rounded-full text-[10px] text-[#9ca3af]">
                {t.type} ({t.count})
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="mt-4 pt-3 border-t border-white/[0.06]">
        <p className="text-[10px] text-[#5c6370] leading-relaxed">
          Quellen: Semantic Scholar Academic Graph API; h-Index nach Hirsch (2005)
        </p>
      </div>
    </div>
  )
}

function PanelSkeleton() {
  return (
    <div className="bg-white/[0.03] border border-white/[0.08] rounded-xl p-6 animate-pulse">
      <h3 className="text-lg font-semibold mb-4">Forschungsimpact (UC7)</h3>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <div className="h-16 bg-white/[0.04] rounded-lg" />
        <div className="h-16 bg-white/[0.04] rounded-lg" />
        <div className="h-16 bg-white/[0.04] rounded-lg" />
        <div className="h-16 bg-white/[0.04] rounded-lg" />
      </div>
      <div className="h-48 bg-white/[0.04] rounded-lg" />
    </div>
  )
}
