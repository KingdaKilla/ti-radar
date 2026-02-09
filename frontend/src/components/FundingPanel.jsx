import { useMemo } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, PieChart, Pie, CartesianGrid, Legend } from 'recharts'
import MetricCard from './MetricCard'

const PROGRAMME_COLORS = {
  FP7: '#fbbf24',
  H2020: '#94a3b8',
  HORIZON: '#e8917a',
  UNKNOWN: '#5c6370',
}

const TOOLTIP = { backgroundColor: '#141c2e', border: '1px solid rgba(232,145,122,0.2)', borderRadius: 8 }

function formatCurrency(value) {
  if (value >= 1e9) return `\u20AC${(value / 1e9).toFixed(1)}B`
  if (value >= 1e6) return `\u20AC${(value / 1e6).toFixed(1)}M`
  if (value >= 1e3) return `\u20AC${(value / 1e3).toFixed(1)}K`
  return `\u20AC${Math.round(value)}`
}

function formatTooltipValue(value) {
  return formatCurrency(value)
}

export default function FundingPanel({ data }) {
  if (!data) return <PanelSkeleton title="Förderung" />

  const programmes = (data.by_programme || []).map(p => ({
    ...p,
    fill: PROGRAMME_COLORS[p.programme] || PROGRAMME_COLORS.UNKNOWN,
  }))

  const timeSeries = (data.time_series || []).map(t => ({
    ...t,
    funding_m: Math.round((t.funding || 0) / 1e6 * 10) / 10,
  }))

  // Stacked-Bar-Daten: Jahr × Programm → {year, FP7: x, H2020: y, HORIZON: z}
  const stackedData = useMemo(() => {
    const byProg = data.time_series_by_programme || []
    if (byProg.length === 0) return null
    const grouped = {}
    for (const row of byProg) {
      if (!grouped[row.year]) grouped[row.year] = { year: row.year }
      grouped[row.year][row.programme] = Math.round((row.funding || 0) / 1e6 * 10) / 10
    }
    return Object.values(grouped).sort((a, b) => a.year - b.year)
  }, [data.time_series_by_programme])

  const stackedProgrammes = useMemo(() => {
    if (!stackedData) return []
    const progs = new Set()
    for (const row of stackedData) {
      for (const key of Object.keys(row)) {
        if (key !== 'year') progs.add(key)
      }
    }
    return [...progs].sort()
  }, [stackedData])

  return (
    <div className="bg-white/[0.03] border border-white/[0.08] rounded-xl p-6">
      <h3 className="text-lg font-semibold mb-4">Förderung (UC4)</h3>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <MetricCard title="Gesamt" value={formatCurrency(data.total_funding_eur || 0)} subtitle="EU-Förderung" />
        <MetricCard title="Projekte" value={timeSeries.reduce((s, t) => s + (t.projects || 0), 0).toLocaleString()} subtitle="Geförderte Projekte" />
        <MetricCard title="Avg. Projekt" value={formatCurrency(data.avg_project_size || 0)} subtitle="Durchschnittl. Förderung" />
      </div>

      {programmes.length > 0 && (
        <div className="flex gap-4 mb-4">
          <div className="h-36 flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={programmes}
                  dataKey="funding"
                  nameKey="programme"
                  cx="50%"
                  cy="50%"
                  innerRadius={30}
                  outerRadius={55}
                  paddingAngle={2}
                >
                  {programmes.map((p, i) => (
                    <Cell key={i} fill={p.fill} />
                  ))}
                </Pie>
                <Tooltip contentStyle={TOOLTIP} formatter={formatTooltipValue} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-col justify-center gap-1.5">
            {programmes.map(p => (
              <div key={p.programme} className="flex items-center gap-2 text-xs">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: p.fill }} />
                <span className="text-[#9ca3af]">{p.programme}</span>
                <span className="text-[#5c6370]">{formatCurrency(p.funding)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {(stackedData || timeSeries.length > 0) && (
        <div className="h-48">
          <p className="text-xs text-[#5c6370] mb-1">Förderung pro Jahr (Mio. EUR)</p>
          <ResponsiveContainer width="100%" height="100%">
            {stackedData ? (
              <BarChart data={stackedData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={true} vertical={false} />
                <XAxis dataKey="year" tick={{ fill: '#5c6370', fontSize: 10 }} tickLine={false} />
                <YAxis tick={{ fill: '#5c6370', fontSize: 10 }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={TOOLTIP} formatter={(value, name) => [`${value}M EUR`, name]} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                {stackedProgrammes.map(prog => (
                  <Bar key={prog} dataKey={prog} stackId="funding" fill={PROGRAMME_COLORS[prog] || PROGRAMME_COLORS.UNKNOWN} />
                ))}
              </BarChart>
            ) : (
              <BarChart data={timeSeries}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={true} vertical={false} />
                <XAxis dataKey="year" tick={{ fill: '#5c6370', fontSize: 10 }} tickLine={false} />
                <YAxis tick={{ fill: '#5c6370', fontSize: 10 }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={TOOLTIP} formatter={(value) => [`${value}M EUR`, 'Förderung']} />
                <Bar dataKey="funding_m" fill="#e8917a" radius={[3, 3, 0, 0]} />
              </BarChart>
            )}
          </ResponsiveContainer>
        </div>
      )}

      <div className="mt-4 pt-3 border-t border-white/[0.06]">
        <p className="text-[10px] text-[#5c6370] leading-relaxed">
          Quellen: CORDIS (FP7, H2020, Horizon Europe)
        </p>
      </div>
    </div>
  )
}

function PanelSkeleton({ title }) {
  return (
    <div className="bg-white/[0.03] border border-white/[0.08] rounded-xl p-6 animate-pulse">
      <h3 className="text-lg font-semibold mb-4">{title}</h3>
      <div className="h-40 bg-white/[0.04] rounded-lg" />
    </div>
  )
}
