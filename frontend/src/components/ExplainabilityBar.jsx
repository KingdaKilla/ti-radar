import { useState } from 'react'

export default function ExplainabilityBar({ data }) {
  const [expanded, setExpanded] = useState(false)

  if (!data) return null

  const apiErrors = data.api_alerts?.filter(a => a.level === 'error') || []
  const apiWarnings = data.api_alerts?.filter(a => a.level === 'warning') || []

  return (
    <div className="bg-white/[0.03] border border-white/[0.08] rounded-xl overflow-hidden">
      {/* Compact bar — always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-6 py-3 flex flex-wrap items-center gap-4 text-sm text-[#9ca3af] hover:bg-white/[0.04] transition-colors cursor-pointer"
      >
        {data.sources_used?.length > 0 && (
          <span>
            <span className="text-[#5c6370]">Quellen:</span>{' '}
            {data.sources_used.join(', ')}
          </span>
        )}

        {data.deterministic && (
          <span className="px-2 py-0.5 bg-[#e8917a]/10 text-[#e8917a] border border-[#e8917a]/20 rounded text-xs">
            Deterministisch
          </span>
        )}

        {data.methods?.length > 0 && (
          <span className="text-[#5c6370] text-xs">
            {data.methods.length} Methode{data.methods.length > 1 ? 'n' : ''}
          </span>
        )}

        {apiErrors.length > 0 && (
          <span className="px-2 py-0.5 bg-red-500/10 text-red-400 border border-red-500/20 rounded text-xs">
            {apiErrors.length} API-Fehler
          </span>
        )}

        {apiWarnings.length > 0 && (
          <span className="px-2 py-0.5 bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 rounded text-xs">
            {apiWarnings.length} API-Warnung{apiWarnings.length > 1 ? 'en' : ''}
          </span>
        )}

        {data.warnings?.length > 0 && (
          <span className="px-2 py-0.5 bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 rounded text-xs">
            {data.warnings.length} Warnung{data.warnings.length > 1 ? 'en' : ''}
          </span>
        )}

        <span className="ml-auto flex items-center gap-2">
          {data.query_time_ms > 0 && (
            <span className="text-[#5c6370]">{data.query_time_ms}ms</span>
          )}
          <svg
            className={`w-4 h-4 text-[#5c6370] transition-transform ${expanded ? 'rotate-180' : ''}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </span>
      </button>

      {/* Expanded details */}
      {expanded && (
        <div className="px-6 pb-4 border-t border-white/[0.06] space-y-3">
          {data.methods?.length > 0 && (
            <div className="pt-3">
              <p className="text-xs text-[#5c6370] mb-2">Verwendete Methoden</p>
              <div className="flex flex-wrap gap-2">
                {data.methods.map((method, i) => (
                  <span key={i} className="px-2.5 py-1 bg-[#e8917a]/10 text-[#e8917a] border border-[#e8917a]/20 rounded-full text-xs">
                    {method}
                  </span>
                ))}
              </div>
            </div>
          )}

          {data.api_alerts?.length > 0 && (
            <div>
              <p className="text-xs text-[#5c6370] mb-2">API-Status</p>
              <ul className="space-y-1">
                {data.api_alerts.map((alert, i) => (
                  <li key={i} className={`flex items-start gap-2 text-xs ${
                    alert.level === 'error' ? 'text-red-400' : 'text-yellow-400/80'
                  }`}>
                    <span className="mt-0.5 shrink-0">
                      {alert.level === 'error' ? '\u2716' : '!'}
                    </span>
                    <span>
                      <strong>{alert.source}:</strong> {alert.message}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {data.warnings?.length > 0 && (
            <div>
              <p className="text-xs text-[#5c6370] mb-2">Warnungen</p>
              <ul className="space-y-1">
                {data.warnings.map((warning, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-yellow-400/80">
                    <span className="mt-0.5 shrink-0">!</span>
                    <span>{warning}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {data.sources_used?.length > 0 && (
            <div>
              <p className="text-xs text-[#5c6370] mb-2">Datenquellen</p>
              <div className="flex flex-wrap gap-2">
                {data.sources_used.map((source, i) => (
                  <span key={i} className="px-2.5 py-1 bg-white/[0.04] text-[#9ca3af] border border-white/[0.08] rounded-full text-xs">
                    {source}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
