import { useState } from 'react'

export default function MetricCard({ title, value, subtitle, info }) {
  const [showInfo, setShowInfo] = useState(false)

  return (
    <div className="bg-white/[0.03] border border-white/[0.08] rounded-lg p-3 relative">
      <div className="flex items-center gap-1">
        <p className="text-xs text-[#9ca3af] font-medium">{title}</p>
        {info && (
          <span
            className="w-3.5 h-3.5 inline-flex items-center justify-center rounded-full border border-[#5c6370]/40 text-[#5c6370] text-[9px] cursor-help leading-none select-none"
            onMouseEnter={() => setShowInfo(true)}
            onMouseLeave={() => setShowInfo(false)}
          >
            i
          </span>
        )}
      </div>
      <p className="text-lg font-bold text-[#e8917a] mt-0.5">{value}</p>
      {subtitle && <p className="text-[10px] text-[#5c6370] mt-0.5">{subtitle}</p>}
      {showInfo && info && (
        <div className="absolute z-50 bottom-full left-0 mb-1 px-3 py-2 bg-[#141c2e] border border-[rgba(232,145,122,0.2)] rounded-lg text-[11px] text-[#e5e7eb] whitespace-pre-line shadow-lg max-w-xs">
          {info}
        </div>
      )}
    </div>
  )
}
