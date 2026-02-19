import { useState, useMemo } from 'react'
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend, BarChart, Bar, ReferenceArea, ReferenceLine } from 'recharts'
import MetricCard from './MetricCard'
import DownloadButton from './DownloadButton'
import FullscreenButton from './FullscreenButton'
import { useFullscreen } from '../hooks/useFullscreen'
import { exportCSV } from '../utils/export'
import { toTitleCase } from '../utils/format'
import ChartTooltip from './ChartTooltip'
import AnalysisText from './AnalysisText'

const TOOLTIP = { backgroundColor: '#141c2e', border: '1px solid rgba(232,145,122,0.2)', borderRadius: 8 }

const INSTRUMENT_COLORS = [
  '#e8917a', '#818cf8', '#34d399', '#fbbf24', '#f0abfc',
  '#94a3b8', '#fb923c', '#a78bfa', '#38bdf8', '#f87171',
]

const VIEWS = [
  { key: 'dynamics', label: 'Dynamik' },
  { key: 'programmes', label: 'Programme' },
  { key: 'breadth', label: 'Breite' },
]

export default function TemporalPanel({ data, dataCompleteUntil }) {
  const [view, setView] = useState('dynamics')
  const { isFullscreen, toggleFullscreen } = useFullscreen()

  if (!data) return <PanelSkeleton />

  const actorTimeline = data.actor_timeline || []
  const progEvolution = data.programme_evolution || []
  const entrantTrend = data.entrant_persistence_trend || []
  const breadth = data.technology_breadth || []

  // Dynamik-Daten: total_actors aus entrant_persistence_trend
  const dynamicsData = useMemo(() => {
    return entrantTrend.map(d => ({
      year: d.year,
      total_actors: d.total_actors || 0,
      new_pct: Math.round((d.new_entrant_rate || 0) * 100),
      persist_pct: Math.round((d.persistence_rate || 0) * 100),
    }))
  }, [entrantTrend])

  // Programme: dynamisch die Top-Instrumente extrahieren
  const topInstruments = useMemo(() => {
    const totals = {}
    for (const row of progEvolution) {
      for (const [key, val] of Object.entries(row)) {
        if (key !== 'year' && typeof val === 'number') {
          totals[key] = (totals[key] || 0) + val
        }
      }
    }
    return Object.entries(totals)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8)
      .map(([name]) => name)
  }, [progEvolution])

  return (
    <div className={isFullscreen ? 'fixed inset-0 z-50 bg-[#0d1117] overflow-y-auto p-8' : 'bg-white/[0.03] border border-white/[0.08] rounded-xl p-6'}>
      <div className="flex items-center gap-1.5 mb-4">
        <h3 className="text-lg font-semibold">Temporale Dynamik (UC8)</h3>
        <DownloadButton onClick={() => {
          const rows = entrantTrend.map(t => [t.year, t.total_actors || 0, ((t.new_entrant_rate || 0) * 100).toFixed(1), ((t.persistence_rate || 0) * 100).toFixed(1)])
          exportCSV('uc8_temporal.csv', ['Jahr', 'Akteure gesamt', 'Neueintrittsrate%', 'Verbleibrate%'], rows)
        }} />
        <FullscreenButton isFullscreen={isFullscreen} onClick={toggleFullscreen} />
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <MetricCard
          title="Neue Akteure"
          value={`${((data.new_entrant_rate ?? 0) * 100).toFixed(0)}%`}
          subtitle="Neueintrittsrate"
        />
        <MetricCard
          title="Persistenz"
          value={`${((data.persistence_rate ?? 0) * 100).toFixed(0)}%`}
          subtitle="Verbleibquote"
        />
        <MetricCard
          title="Programm"
          value={data.dominant_programme || '\u2014'}
          subtitle="Dominantes Programm"
        />
      </div>

      {/* View toggle */}
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs text-[#5c6370]">
          {view === 'dynamics' && 'Akteur-Dynamik pro Jahr'}
          {view === 'programmes' && 'Förderinstrumente pro Jahr'}
          {view === 'breadth' && 'Technologiebreite (CPC-Sektionen + Subklassen)'}
        </p>
        <div className="flex gap-0.5 p-0.5 bg-white/[0.04] rounded-md">
          {VIEWS.map(v => (
            <button
              key={v.key}
              onClick={() => setView(v.key)}
              className={`px-2 py-0.5 text-[10px] rounded transition-all ${
                view === v.key
                  ? 'bg-[#a78bfa]/20 text-[#a78bfa]'
                  : 'text-[#5c6370] hover:text-[#9ca3af]'
              }`}
            >
              {v.label}
            </button>
          ))}
        </div>
      </div>

      {view === 'dynamics' && dynamicsData.length > 0 && (
        <>
          <div className={isFullscreen ? 'h-[40vh]' : 'h-40 sm:h-48'}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={dynamicsData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                {dataCompleteUntil && <ReferenceArea x1={dataCompleteUntil + 1} fill="#5c6370" fillOpacity={0.08} />}
                {dataCompleteUntil && <ReferenceLine x={dataCompleteUntil + 1} stroke="#5c6370" strokeDasharray="4 4" strokeOpacity={0.5} label={{ value: 'unvollst.', fill: '#5c6370', fontSize: 9, position: 'top' }} />}
                <XAxis dataKey="year" tick={{ fill: '#5c6370', fontSize: 10 }} tickLine={false} />
                <YAxis tick={{ fill: '#5c6370', fontSize: 10 }} tickLine={false} axisLine={false} />
                <Tooltip content={<ChartTooltip dataCompleteUntil={dataCompleteUntil} />} />
                <Area type="monotone" dataKey="total_actors" stroke="#a78bfa" fill="#a78bfa" fillOpacity={0.15} strokeWidth={2} name="Akteure gesamt" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className={`${isFullscreen ? 'h-[30vh]' : 'h-32'} mt-2`}>
            <p className="text-[10px] text-[#5c6370] mb-1">Eintritts- & Verbleibrate (%)</p>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={dynamicsData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                {dataCompleteUntil && <ReferenceArea x1={dataCompleteUntil + 1} fill="#5c6370" fillOpacity={0.08} />}
                <XAxis dataKey="year" tick={{ fill: '#5c6370', fontSize: 9 }} tickLine={false} />
                <YAxis tick={{ fill: '#5c6370', fontSize: 9 }} tickLine={false} axisLine={false} unit="%" domain={[0, 100]} />
                <Tooltip content={<ChartTooltip dataCompleteUntil={dataCompleteUntil} formatValue={(v) => `${v}%`} />} />
                <Legend wrapperStyle={{ fontSize: 9 }} />
                <Line type="monotone" dataKey="new_pct" stroke="#34d399" strokeWidth={1.5} dot={false} name="Eintrittsrate" />
                <Line type="monotone" dataKey="persist_pct" stroke="#a78bfa" strokeWidth={1.5} dot={false} name="Verbleibrate" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}

      {view === 'dynamics' && actorTimeline.length > 0 && (
        <div className="mt-3">
          <p className="text-[10px] text-[#5c6370] mb-1.5">Top Akteure (Patente)</p>
          <div className="space-y-1">
            {actorTimeline.slice(0, 6).map((a, i) => {
              const maxCount = actorTimeline[0]?.total_count || 1
              const pct = Math.round((a.total_count / maxCount) * 100)
              return (
                <div key={i} className="flex items-center gap-2 text-xs">
                  <span className="w-28 text-[#9ca3af] flex-shrink-0 truncate" title={a.name}>{toTitleCase(a.name)}</span>
                  <div className="flex-1 h-2.5 bg-white/[0.04] rounded-full overflow-hidden">
                    <div className="h-full bg-[#a78bfa]/50 rounded-full" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="text-[#5c6370] w-8 text-right">{a.total_count}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {view === 'programmes' && progEvolution.length > 0 && (
        <div className={isFullscreen ? 'h-[65vh]' : 'h-48 sm:h-56'}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={progEvolution}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={true} vertical={false} />
              {dataCompleteUntil && <ReferenceArea x1={dataCompleteUntil + 1} fill="#5c6370" fillOpacity={0.08} />}
              {dataCompleteUntil && <ReferenceLine x={dataCompleteUntil + 1} stroke="#5c6370" strokeDasharray="4 4" strokeOpacity={0.5} label={{ value: 'unvollst.', fill: '#5c6370', fontSize: 9, position: 'top' }} />}
              <XAxis dataKey="year" tick={{ fill: '#5c6370', fontSize: 10 }} tickLine={false} />
              <YAxis tick={{ fill: '#5c6370', fontSize: 10 }} tickLine={false} axisLine={false} />
              <Tooltip content={<ChartTooltip dataCompleteUntil={dataCompleteUntil} />} />
              <Legend wrapperStyle={{ fontSize: 9 }} />
              {topInstruments.map((inst, i) => (
                <Bar key={inst} dataKey={inst} stackId="prog" fill={INSTRUMENT_COLORS[i % INSTRUMENT_COLORS.length]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {view === 'breadth' && breadth.length > 0 && (
        <div className={isFullscreen ? 'h-[65vh]' : 'h-48 sm:h-56'}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={breadth}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              {dataCompleteUntil && <ReferenceArea x1={dataCompleteUntil + 1} yAxisId="left" fill="#5c6370" fillOpacity={0.08} />}
              {dataCompleteUntil && <ReferenceLine x={dataCompleteUntil + 1} yAxisId="left" stroke="#5c6370" strokeDasharray="4 4" strokeOpacity={0.5} label={{ value: 'unvollst.', fill: '#5c6370', fontSize: 9, position: 'top' }} />}
              <XAxis dataKey="year" tick={{ fill: '#5c6370', fontSize: 10 }} tickLine={false} />
              <YAxis yAxisId="left" tick={{ fill: '#5c6370', fontSize: 10 }} tickLine={false} axisLine={false} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: '#5c6370', fontSize: 10 }} tickLine={false} axisLine={false} />
              <Tooltip content={<ChartTooltip dataCompleteUntil={dataCompleteUntil} />} />
              <Legend wrapperStyle={{ fontSize: 9 }} />
              <Area yAxisId="right" type="monotone" dataKey="unique_cpc_subclasses" stroke="#34d399" fill="#34d399" fillOpacity={0.1} strokeWidth={2} name="CPC-Subklassen (Level 4)" />
              <Area yAxisId="left" type="monotone" dataKey="unique_cpc_sections" stroke="#fbbf24" fill="#fbbf24" fillOpacity={0.15} strokeWidth={2} name="CPC-Sektionen (A-H)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {isFullscreen && <AnalysisText text={data.analysis_text} />}

      <div className="mt-4 pt-3 border-t border-white/[0.06]">
        <p className="text-[10px] text-[#5c6370] leading-relaxed">
          Quellen: Malerba & Orsenigo (1999) — Akteur-Dynamik; Leydesdorff et al. (2015) — Technologiebreite (CPC); EPO DOCDB, CORDIS
        </p>
      </div>
    </div>
  )
}

function PanelSkeleton() {
  return (
    <div className="bg-white/[0.03] border border-white/[0.08] rounded-xl p-6 animate-pulse">
      <h3 className="text-lg font-semibold mb-4">Temporale Dynamik (UC8)</h3>
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="h-16 bg-white/[0.04] rounded-lg" />
        <div className="h-16 bg-white/[0.04] rounded-lg" />
        <div className="h-16 bg-white/[0.04] rounded-lg" />
      </div>
      <div className="h-48 bg-white/[0.04] rounded-lg" />
    </div>
  )
}
