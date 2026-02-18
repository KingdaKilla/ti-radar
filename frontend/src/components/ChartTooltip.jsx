/**
 * Shared chart tooltip with incomplete-data warning.
 *
 * Replaces the default Recharts <Tooltip> content across all panels.
 * When the hovered year exceeds dataCompleteUntil, a warning line is appended.
 */

const TOOLTIP_STYLE = {
  backgroundColor: '#141c2e',
  border: '1px solid rgba(232,145,122,0.2)',
  borderRadius: 8,
}

export default function ChartTooltip({ active, payload, label, dataCompleteUntil, formatValue }) {
  if (!active || !payload?.length) return null
  const isIncomplete = dataCompleteUntil != null && Number(label) > dataCompleteUntil

  return (
    <div style={TOOLTIP_STYLE} className="px-3 py-2 text-xs">
      <p style={{ color: '#f1f0ee' }} className="font-medium mb-1">{label}</p>
      {payload.filter(e => e.value != null).map((entry, i) => (
        <p key={i} style={{ color: entry.color || '#e5e7eb' }}>
          {entry.name}: {formatValue ? formatValue(entry.value, entry.name) : entry.value}
        </p>
      ))}
      {isIncomplete && (
        <p style={{ color: '#fbbf24' }} className="mt-1.5 pt-1.5 border-t border-white/10 text-[10px]">
          Daten ab {dataCompleteUntil + 1} unvollständig
        </p>
      )}
    </div>
  )
}
