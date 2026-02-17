import { useState } from 'react'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid, ReferenceArea, ReferenceLine } from 'recharts'
import MetricCard from './MetricCard'
import DownloadButton from './DownloadButton'
import { exportCSV } from '../utils/export'

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

const VIEWS = [
  { key: 'cumulative', label: 'Kumulativ' },
  { key: 'annual', label: 'Jährlich' },
]

export default function MaturityPanel({ data }) {
  const [viewMode, setViewMode] = useState('cumulative')

  if (!data) return <PanelSkeleton title="Reifegrad" />

  const phaseStyle = PHASE_COLORS[data.phase] || PHASE_COLORS.Growing

  const chartData = (data.time_series || []).map(entry => {
    const fitted = (data.s_curve_fitted || []).find(f => f.year === entry.year)
    return { ...entry, fitted: fitted ? fitted.fitted : null }
  })

  const r2Info = R2_LABEL(data.r_squared || 0)
  const satLevel = data.saturation_level || 0

  // Phase region boundaries (based on Lee et al. 2016 thresholds)
  const phaseRegions = satLevel > 0 ? [
    { y1: 0, y2: satLevel * 0.1, fill: '#fbbf24', label: 'Aufkommend' },
    { y1: satLevel * 0.1, y2: satLevel * 0.5, fill: '#e8917a', label: 'Wachstum' },
    { y1: satLevel * 0.5, y2: satLevel * 0.9, fill: '#f0abfc', label: 'Reife' },
    { y1: satLevel * 0.9, y2: satLevel, fill: '#94a3b8', label: 'Sättigung' },
  ] : []

  return (
    <div className="bg-white/[0.03] border border-white/[0.08] rounded-xl p-6">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <div className="flex items-center gap-1.5">
          <h3 className="text-lg font-semibold">Reifegrad (UC2)</h3>
          <DownloadButton onClick={() => {
            const rows = chartData.map(t => [
              t.year, t.count || 0, t.cumulative || 0, t.fitted ?? '',
            ])
            exportCSV('uc2_reifegrad.csv', ['Jahr', 'Patente', 'Kumulativ', 'S-Curve Fit'], rows)
          }} />
        </div>
        {data.phase && (
          <span className={`px-2.5 py-0.5 border rounded-full text-xs ${phaseStyle}`}>
            {data.phase_de || PHASE_DE[data.phase] || data.phase} — {Math.round((data.confidence || 0) * 100)}% Konfidenz
          </span>
        )}
      </div>

      {data.phase ? (
        <>
          {chartData.length > 0 && (
            <div className="h-56 sm:h-64 md:h-72 mb-4">
              <div className="flex items-center justify-between mb-1">
                <p className="text-xs text-[#5c6370]">
                  {viewMode === 'cumulative' ? 'Kumulative Patente' : 'Patente pro Jahr'}
                </p>
                <div className="flex gap-0.5 p-0.5 bg-white/[0.04] rounded-md">
                  {VIEWS.map(v => (
                    <button
                      key={v.key}
                      onClick={() => setViewMode(v.key)}
                      className={`px-2 py-0.5 text-[10px] rounded transition-all ${
                        viewMode === v.key
                          ? 'bg-[#e8917a]/20 text-[#e8917a]'
                          : 'text-[#5c6370] hover:text-[#9ca3af]'
                      }`}
                    >
                      {v.label}
                    </button>
                  ))}
                </div>
              </div>
              <ResponsiveContainer width="100%" height="100%">
                {viewMode === 'cumulative' ? (
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    {phaseRegions.map((region, i) => (
                      <ReferenceArea
                        key={i}
                        y1={region.y1}
                        y2={region.y2}
                        fill={region.fill}
                        fillOpacity={0.04}
                        ifOverflow="extendDomain"
                      />
                    ))}
                    {data.inflection_year && (
                      <ReferenceLine
                        x={data.inflection_year}
                        stroke="#e8917a"
                        strokeDasharray="4 4"
                        strokeOpacity={0.6}
                        label={{ value: 'Wendepunkt', fill: '#e8917a', fontSize: 10, position: 'top' }}
                      />
                    )}
                    <XAxis dataKey="year" tick={TICK} tickLine={false} />
                    <YAxis tick={TICK} tickLine={false} axisLine={false} label={{ value: 'Kumulativ', angle: -90, position: 'insideLeft', fill: '#5c6370', fontSize: 11 }} />
                    <Tooltip contentStyle={TOOLTIP} labelStyle={{ color: '#f1f0ee' }} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Line type="monotone" dataKey="cumulative" stroke="rgba(241,240,238,0.4)" strokeWidth={2} dot={{ r: 2, fill: 'rgba(241,240,238,0.5)' }} name="Kumulativ" />
                    {data.s_curve_fitted?.length > 0 && (
                      <Line type="monotone" dataKey="fitted" stroke="#e8917a" strokeWidth={2.5} dot={false} strokeDasharray="6 3" name="S-Curve Fit" />
                    )}
                  </LineChart>
                ) : (
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="year" tick={TICK} tickLine={false} />
                    <YAxis tick={TICK} tickLine={false} axisLine={false} label={{ value: 'Patente/Jahr', angle: -90, position: 'insideLeft', fill: '#5c6370', fontSize: 11 }} />
                    <Tooltip contentStyle={TOOLTIP} labelStyle={{ color: '#f1f0ee' }} />
                    <Bar dataKey="count" fill="#e8917a" radius={[3, 3, 0, 0]} name="Patente" fillOpacity={0.7} />
                  </BarChart>
                )}
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
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="h-16 bg-white/[0.04] rounded-lg" />
        <div className="h-16 bg-white/[0.04] rounded-lg" />
      </div>
      <div className="h-56 bg-white/[0.04] rounded-lg" />
    </div>
  )
}
