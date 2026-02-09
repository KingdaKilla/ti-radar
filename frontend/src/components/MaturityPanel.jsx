import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid } from 'recharts'
import MetricCard from './MetricCard'

const PHASE_COLORS = {
  Emerging: 'border-[#fbbf24]/30 text-[#fbbf24] bg-[#fbbf24]/10',
  Growing: 'border-[#e8917a]/30 text-[#e8917a] bg-[#e8917a]/10',
  Mature: 'border-[#f0abfc]/30 text-[#f0abfc] bg-[#f0abfc]/10',
  Declining: 'border-[#94a3b8]/30 text-[#94a3b8] bg-[#94a3b8]/10',
}

const PHASE_DE = { Emerging: 'Aufkommend', Growing: 'Wachstum', Mature: 'Reife', Declining: 'Sättigung' }

const R2_LABEL = (r2) => {
  if (r2 >= 0.9) return { text: 'Exzellent', color: 'text-[#e8917a]' }
  if (r2 >= 0.7) return { text: 'Gut', color: 'text-[#fbbf24]' }
  if (r2 >= 0.5) return { text: 'Akzeptabel', color: 'text-[#f0abfc]' }
  return { text: 'Schwach', color: 'text-[#94a3b8]' }
}

const TOOLTIP = { backgroundColor: '#141c2e', border: '1px solid rgba(232,145,122,0.2)', borderRadius: 8 }
const TICK = { fill: '#5c6370', fontSize: 11 }

export default function MaturityPanel({ data }) {
  if (!data) return <PanelSkeleton title="Reifegrad" />

  const phaseStyle = PHASE_COLORS[data.phase] || PHASE_COLORS.Growing

  const chartData = (data.time_series || []).map(entry => {
    const fitted = (data.s_curve_fitted || []).find(f => f.year === entry.year)
    return { ...entry, fitted: fitted ? fitted.fitted : null }
  })

  const r2Info = R2_LABEL(data.r_squared || 0)

  return (
    <div className="bg-white/[0.03] border border-white/[0.08] rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Reifegrad (UC2)</h3>
        {data.phase && (
          <span className={`px-2.5 py-0.5 border rounded-full text-xs ${phaseStyle}`}>
            {data.phase_de || PHASE_DE[data.phase] || data.phase} — {Math.round((data.confidence || 0) * 100)}% Konfidenz
          </span>
        )}
      </div>

      {data.phase ? (
        <>
          {chartData.length > 0 && (
            <div className="h-72 mb-4">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="year" tick={TICK} tickLine={false} />
                  <YAxis tick={TICK} tickLine={false} axisLine={false} label={{ value: 'Kumulativ', angle: -90, position: 'insideLeft', fill: '#5c6370', fontSize: 11 }} />
                  <Tooltip contentStyle={TOOLTIP} labelStyle={{ color: '#f1f0ee' }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line type="monotone" dataKey="cumulative" stroke="rgba(241,240,238,0.4)" strokeWidth={2} dot={{ r: 2, fill: 'rgba(241,240,238,0.5)' }} name="Kumulativ" />
                  {data.s_curve_fitted?.length > 0 && (
                    <Line type="monotone" dataKey="fitted" stroke="#e8917a" strokeWidth={2.5} dot={false} strokeDasharray="6 3" name="S-Curve Fit" />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <MetricCard
              title="Reifegrad"
              value={data.maturity_percent ? `${data.maturity_percent.toFixed(1)}%` : '\u2014'}
              subtitle="der Sättigung erreicht"
            />
            {data.r_squared > 0 && (
              <MetricCard
                title="R²"
                value={data.r_squared.toFixed(3)}
                subtitle={<span className={r2Info.color}>{r2Info.text}</span>}
              />
            )}
          </div>
        </>
      ) : (
        <p className="text-[#5c6370] text-sm">Keine Daten verfügbar</p>
      )}

      <div className="mt-4 pt-3 border-t border-white/[0.06]">
        <p className="text-[10px] text-[#5c6370] leading-relaxed">
          Quellen: Lee et al. (2016) — S-Curve-Phasenklassifikation; {data.fit_model === 'Gompertz' ? 'Gompertz' : 'Logistic'}-Algorithmus (TRF); EPO DOCDB
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
