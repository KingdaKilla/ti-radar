import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid } from 'recharts'
import MetricCard from './MetricCard'

const BAR_COLORS = ['#e8917a', '#e09b87', '#d8a594', '#d0afa1', '#c8b9ae', '#f0abfc', '#d4a0e0', '#9b8ab8', '#fbbf24', '#94a3b8']

const HHI_LABELS = {
  Low: { text: 'Gering konzentriert', style: 'bg-[#e8917a]/10 text-[#e8917a] border-[#e8917a]/20' },
  Moderate: { text: 'Mäßig konzentriert', style: 'bg-[#fbbf24]/10 text-[#fbbf24] border-[#fbbf24]/20' },
  High: { text: 'Hoch konzentriert', style: 'bg-[#f0abfc]/10 text-[#f0abfc] border-[#f0abfc]/20' },
}

const TOOLTIP = { backgroundColor: '#141c2e', border: '1px solid rgba(232,145,122,0.2)', borderRadius: 8 }

export default function CompetitivePanel({ data }) {
  if (!data) return <PanelSkeleton title="Wettbewerb" />

  const actors = (data.top_actors || []).slice(0, 8).map(a => ({
    ...a,
    short: a.name?.length > 25 ? a.name.substring(0, 22) + '...' : a.name,
    pct: Math.round((a.share || 0) * 1000) / 10,
  }))

  const levelInfo = HHI_LABELS[data.concentration_level] || HHI_LABELS.Low

  return (
    <div className="bg-white/[0.03] border border-white/[0.08] rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Wettbewerb (UC3)</h3>
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

      {actors.length > 0 && (
        <div className="h-64">
          <p className="text-xs text-[#5c6370] mb-1">Top Akteure</p>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={actors} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
              <XAxis type="number" tick={{ fill: '#5c6370', fontSize: 10 }} tickLine={false} axisLine={false} />
              <YAxis type="category" dataKey="short" tick={{ fill: '#5c6370', fontSize: 9 }} width={100} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={TOOLTIP}
                formatter={(value, name) => [value, 'Aktivitäten']}
                labelFormatter={(label) => {
                  const actor = actors.find(a => a.short === label)
                  return actor?.name || label
                }}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {actors.map((_, i) => (
                  <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="mt-4 pt-3 border-t border-white/[0.06]">
        <p className="text-[10px] text-[#5c6370] leading-relaxed">
          Quellen: Herfindahl-Hirschman Index (DOJ/FTC) — Aktivitätskonzentration; EPO DOCDB, CORDIS
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
