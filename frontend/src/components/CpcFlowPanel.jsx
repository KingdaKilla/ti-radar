import { useState, useMemo, useEffect, useRef } from 'react'
import MetricCard from './MetricCard'
import DownloadButton from './DownloadButton'
import FullscreenButton from './FullscreenButton'
import { useFullscreen } from '../hooks/useFullscreen'
import ChordDiagram from './ChordDiagram'
import { exportCSV } from '../utils/export'

function getHeatColor(value, max) {
  if (value === 0 || max === 0) return 'rgba(255,255,255,0.02)'
  const intensity = Math.min(value / max, 1)
  const r = Math.round(20 + intensity * (232 - 20))
  const g = Math.round(22 + intensity * (145 - 22))
  const b = Math.round(45 + intensity * (122 - 45))
  return `rgba(${r}, ${g}, ${b}, ${0.2 + intensity * 0.8})`
}

const CPC_COLORS = {
  A: '#fbbf24', B: '#e8917a', C: '#3b82f6', D: '#f0abfc',
  E: '#10b981', F: '#f97316', G: '#8b5cf6', H: '#ef4444', Y: '#6b7280',
}

const CPC_SECTIONS = {
  A: 'Human Necessities',
  B: 'Operations / Transport',
  C: 'Chemistry / Metallurgy',
  D: 'Textiles / Paper',
  E: 'Fixed Constructions',
  F: 'Mech. Engineering / Lighting / Heating',
  G: 'Physics',
  H: 'Electricity',
  Y: 'Emerging Technologies',
}

function cpcDescription(code, descriptions = {}) {
  if (!code) return ''
  if (descriptions[code]) return descriptions[code]
  if (code.length > 4 && descriptions[code.slice(0, 4)]) return descriptions[code.slice(0, 4)]
  if (code.length > 3 && descriptions[code.slice(0, 3)]) return descriptions[code.slice(0, 3)]
  const section = code[0]
  return CPC_SECTIONS[section] || ''
}

function recalcJaccard(yearData, yearMin, yearMax, topN) {
  if (!yearData?.pair_counts || !yearData?.cpc_counts) return null

  const totalPairs = {}
  const totalCpc = {}

  for (let y = yearMin; y <= yearMax; y++) {
    const yStr = String(y)
    const pairs = yearData.pair_counts[yStr] || {}
    const cpcs = yearData.cpc_counts[yStr] || {}

    for (const [key, count] of Object.entries(pairs)) {
      totalPairs[key] = (totalPairs[key] || 0) + count
    }
    for (const [code, count] of Object.entries(cpcs)) {
      totalCpc[code] = (totalCpc[code] || 0) + count
    }
  }

  const allLabels = yearData.all_labels || []
  const sorted = allLabels
    .filter(code => (totalCpc[code] || 0) > 0)
    .sort((a, b) => (totalCpc[b] || 0) - (totalCpc[a] || 0))
  const topLabels = sorted.slice(0, topN)

  if (topLabels.length < 2) return null

  const n = topLabels.length
  const matrix = Array.from({ length: n }, () => Array(n).fill(0))
  let connections = 0

  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      const a = topLabels[i]
      const b = topLabels[j]
      const key = a < b ? `${a}|${b}` : `${b}|${a}`
      const coOcc = totalPairs[key] || 0
      if (coOcc === 0) continue

      const countA = totalCpc[a] || 0
      const countB = totalCpc[b] || 0
      const union = countA + countB - coOcc
      const jaccard = union > 0 ? coOcc / union : 0
      const rounded = Math.round(jaccard * 10000) / 10000

      matrix[i][j] = rounded
      matrix[j][i] = rounded
      if (rounded > 0) connections++
    }
  }

  const colors = topLabels.map(l => CPC_COLORS[l[0]] || '#9ca3af')
  return { matrix, labels: topLabels, colors, connections }
}

export default function CpcFlowPanel({ data }) {
  if (!data) return <PanelSkeleton title="Technologiefluss" />

  const { total_patents_analyzed, year_data, cpc_descriptions = {} } = data
  const hasYearData = year_data && year_data.min_year && year_data.max_year
  const allLabels = year_data?.all_labels || data.labels || []
  const maxCpc = Math.min(allLabels.length, 15)

  const dataMin = year_data?.min_year || 2016
  const dataMax = year_data?.max_year || 2026
  const yearOptions = useMemo(() => {
    const opts = []
    for (let y = dataMin; y <= dataMax; y++) opts.push(y)
    return opts
  }, [dataMin, dataMax])

  const [topN, setTopN] = useState(Math.min(data.labels?.length || 15, maxCpc))
  const [yearMin, setYearMin] = useState(dataMin)
  const [yearMax, setYearMax] = useState(dataMax)
  const [hovered, setHovered] = useState(null)
  const { isFullscreen, toggleFullscreen } = useFullscreen()

  // Dynamic width via ResizeObserver
  const containerRef = useRef(null)
  const [containerWidth, setContainerWidth] = useState(0)

  useEffect(() => {
    if (!containerRef.current) return
    const observer = new ResizeObserver(entries => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width)
      }
    })
    observer.observe(containerRef.current)
    return () => observer.disconnect()
  }, [])

  // Count CPC codes with data in selected year range
  const availableCpcCount = useMemo(() => {
    if (!hasYearData || !year_data?.cpc_counts) return maxCpc
    const totalCpc = {}
    for (let y = yearMin; y <= yearMax; y++) {
      const cpcs = year_data.cpc_counts[String(y)] || {}
      for (const [code, count] of Object.entries(cpcs)) {
        totalCpc[code] = (totalCpc[code] || 0) + count
      }
    }
    const count = allLabels.filter(code => (totalCpc[code] || 0) > 0).length
    return Math.min(count, 15)
  }, [year_data, yearMin, yearMax, hasYearData, allLabels, maxCpc])

  // Clamp topN when available codes decrease
  useEffect(() => {
    if (topN > availableCpcCount) {
      setTopN(Math.max(2, availableCpcCount))
    }
  }, [availableCpcCount])

  const filtered = useMemo(() => {
    if (!hasYearData) return null
    return recalcJaccard(year_data, yearMin, yearMax, topN)
  }, [year_data, yearMin, yearMax, topN, hasYearData])

  const matrix = filtered?.matrix || data.matrix || []
  const labels = filtered?.labels || data.labels || []
  const colors = filtered?.colors || data.colors || []
  const total_connections = filtered?.connections ?? data.total_connections ?? 0

  if (matrix.length === 0 || labels.length === 0) {
    return (
      <div className="bg-white/[0.03] border border-white/[0.08] rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-4">Technologiefluss (UC5)</h3>
        <p className="text-[#5c6370] text-sm">Keine CPC-Daten verfügbar</p>
      </div>
    )
  }

  let maxVal = 0
  for (let i = 0; i < matrix.length; i++) {
    for (let j = 0; j < matrix[i].length; j++) {
      if (i !== j && matrix[i][j] > maxVal) maxVal = matrix[i][j]
    }
  }

  const pairs = []
  for (let i = 0; i < matrix.length; i++) {
    for (let j = i + 1; j < matrix[i].length; j++) {
      if (matrix[i][j] > 0) {
        pairs.push({ a: labels[i], b: labels[j], jaccard: matrix[i][j] })
      }
    }
  }
  pairs.sort((a, b) => b.jaccard - a.jaccard)
  const topPairs = pairs.slice(0, 8)

  const cellSize = labels.length > 10 ? 22 : 28
  const chartAreaHeight = cellSize * (2 + labels.length) + 20
  const sliderTrackLength = Math.round(chartAreaHeight * 2 / 3)

  // Calculate dynamic chart widths based on container
  const chartMaxWidth = containerWidth > 0
    ? Math.min(Math.floor((containerWidth - 80) / 2), isFullscreen ? 800 : 450)
    : 385

  const handleMinYear = (val) => setYearMin(Math.min(Number(val), yearMax))
  const handleMaxYear = (val) => setYearMax(Math.max(Number(val), yearMin))

  return (
    <div ref={containerRef} className={isFullscreen ? 'fixed inset-0 z-50 bg-[#0d1117] overflow-y-auto p-8' : 'bg-white/[0.03] border border-white/[0.08] rounded-xl p-6 md:col-span-2'}>
      <div className="flex items-center gap-1.5 mb-4">
        <h3 className="text-lg font-semibold">Technologiefluss (UC5)</h3>
        <DownloadButton onClick={() => {
          const rows = pairs.map(p => [p.a, cpcDescription(p.a, cpc_descriptions), p.b, cpcDescription(p.b, cpc_descriptions), p.jaccard.toFixed(4)])
          exportCSV('uc5_cpc_flow.csv', ['CPC A', 'Beschreibung A', 'CPC B', 'Beschreibung B', 'Jaccard'], rows)
        }} />
        <FullscreenButton isFullscreen={isFullscreen} onClick={toggleFullscreen} />
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <MetricCard
          title="Patente analysiert"
          value={total_patents_analyzed?.toLocaleString() || 0}
          subtitle="Stichprobe mit CPC-Codes"
        />
        <MetricCard
          title="Verbindungen"
          value={total_connections || 0}
          subtitle="CPC-Code-Paare"
        />
      </div>

      {/* Controls row: CPC slider + year range */}
      {hasYearData && (
        <div className="flex flex-col sm:flex-row gap-3 mb-4">
          <div className="flex-1 p-3 bg-white/[0.04] rounded-lg">
            <label className="text-xs text-[#5c6370] block mb-1">
              CPC-Klassen: <span className="text-[#9ca3af]">Top {topN} von {availableCpcCount}</span>
            </label>
            <div className="flex items-center gap-2">
              <input
                type="range"
                min={2}
                max={availableCpcCount}
                value={topN}
                onChange={e => setTopN(Number(e.target.value))}
                className="flex-1 cursor-pointer"
              />
              <input
                type="number"
                min={2}
                max={availableCpcCount}
                value={topN}
                onChange={e => {
                  const v = Math.max(2, Math.min(availableCpcCount, Number(e.target.value) || 2))
                  setTopN(v)
                }}
                className="w-12 px-1.5 py-0.5 bg-white/[0.04] border border-white/[0.08] rounded text-xs text-[#e5e7eb] text-center focus:outline-none focus:border-[#e8917a]/30"
              />
            </div>
          </div>
          <div className="p-3 bg-white/[0.04] rounded-lg">
            <label className="text-xs text-[#5c6370] block mb-1">Zeitraum</label>
            <div className="flex items-center gap-2">
              <select
                value={yearMin}
                onChange={e => handleMinYear(e.target.value)}
                className="px-2 py-0.5 bg-white/[0.04] border border-white/[0.08] rounded text-xs text-[#e5e7eb] focus:outline-none focus:border-[#e8917a]/30"
              >
                {yearOptions.map(y => (
                  <option key={y} value={y} disabled={y > yearMax}>{y}</option>
                ))}
              </select>
              <span className="text-[#5c6370] text-xs">—</span>
              <select
                value={yearMax}
                onChange={e => handleMaxYear(e.target.value)}
                className="px-2 py-0.5 bg-white/[0.04] border border-white/[0.08] rounded text-xs text-[#e5e7eb] focus:outline-none focus:border-[#e8917a]/30"
              >
                {yearOptions.map(y => (
                  <option key={y} value={y} disabled={y < yearMin}>{y}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Charts row: Heatmap | Chord */}
      <div className="flex flex-col xl:flex-row xl:items-start xl:justify-evenly gap-4">
        {/* Heatmap */}
        <div className="overflow-x-auto flex justify-center" style={{ width: '100%', maxWidth: chartMaxWidth }}>
          <div>
            <p className="text-xs text-[#5c6370] mb-2">CPC Co-Klassifikation (Jaccard-Index)</p>
            <div className="inline-block">
              {/* Column headers */}
              <div className="flex" style={{ marginLeft: cellSize * 2.5 }}>
                {labels.map((label, j) => (
                  <div
                    key={j}
                    className="text-center overflow-hidden"
                    style={{
                      width: cellSize,
                      height: cellSize * 2,
                      writingMode: 'vertical-rl',
                      transform: 'rotate(180deg)',
                    }}
                  >
                    <span
                      className="text-xs font-mono"
                      style={{ color: colors[j] || '#9ca3af' }}
                    >
                      {label}
                    </span>
                  </div>
                ))}
              </div>

              {/* Matrix rows */}
              {matrix.map((row, i) => (
                <div key={i} className="flex items-center">
                  <span
                    className="text-xs font-mono text-right pr-2 flex-shrink-0"
                    style={{ width: cellSize * 2.5, color: colors[i] || '#9ca3af' }}
                  >
                    {labels[i]}
                  </span>
                  {row.map((val, j) => (
                    <div
                      key={j}
                      className="border border-white/[0.06] relative"
                      style={{
                        width: cellSize,
                        height: cellSize,
                        backgroundColor: i === j ? 'rgba(255,255,255,0.05)' : getHeatColor(val, maxVal),
                        cursor: val > 0 && i !== j ? 'pointer' : 'default',
                      }}
                      onMouseEnter={() => val > 0 && i !== j && setHovered({ i, j, val })}
                      onMouseLeave={() => setHovered(null)}
                    >
                      {hovered?.i === i && hovered?.j === j && (
                        <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-[#141c2e] border border-[rgba(232,145,122,0.2)] rounded text-xs whitespace-nowrap shadow-lg">
                          {labels[i]} ({cpcDescription(labels[i], cpc_descriptions)}) + {labels[j]} ({cpcDescription(labels[j], cpc_descriptions)}): {val.toFixed(4)}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Chord Diagram */}
        <div style={{ width: '100%', maxWidth: chartMaxWidth }}>
          <p className="text-xs text-[#5c6370] mb-2">Chord-Diagramm</p>
          <ChordDiagram matrix={matrix} labels={labels} colors={colors} cpcSections={CPC_SECTIONS} cpcDescriptions={cpc_descriptions} />
        </div>
      </div>

      {/* Top pairs table */}
      {topPairs.length > 0 && (
        <div className="mt-4">
          <p className="text-xs text-[#5c6370] mb-2">Top CPC-Paare</p>
          <div className="grid grid-cols-2 xl:grid-cols-4 gap-1">
            {topPairs.map((pair, i) => (
              <div key={i} className="flex items-center justify-between text-xs px-2 py-1.5 bg-white/[0.04] rounded group relative">
                <span className="text-[#9ca3af] font-mono cursor-help">
                  {pair.a} + {pair.b}
                </span>
                <span className="text-[#e8917a] font-medium ml-2">
                  {pair.jaccard.toFixed(3)}
                </span>
                <div className="absolute z-50 bottom-full left-0 mb-1 px-2 py-1.5 bg-[#141c2e] border border-[rgba(232,145,122,0.2)] rounded text-[10px] text-[#e5e7eb] whitespace-nowrap shadow-lg opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity">
                  {pair.a}: {cpcDescription(pair.a, cpc_descriptions)} + {pair.b}: {cpcDescription(pair.b, cpc_descriptions)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mt-4 pt-3 border-t border-white/[0.06]">
        <p className="text-[10px] text-[#5c6370] leading-relaxed">
          Quellen: Curran & Leker (2011) — CPC-Koklassifikation; Jaccard (1901) — Ähnlichkeitskoeffizient; Yan & Luo (2019) — CPC-Level-4; EPO DOCDB ({total_patents_analyzed?.toLocaleString() || 0} Patente analysiert)
        </p>
      </div>
    </div>
  )
}

function PanelSkeleton({ title }) {
  return (
    <div className="bg-white/[0.03] border border-white/[0.08] rounded-xl p-6 md:col-span-2 animate-pulse">
      <h3 className="text-lg font-semibold mb-4">{title}</h3>
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="h-16 bg-white/[0.04] rounded-lg" />
        <div className="h-16 bg-white/[0.04] rounded-lg" />
      </div>
      <div className="h-64 bg-white/[0.04] rounded-lg" />
    </div>
  )
}
