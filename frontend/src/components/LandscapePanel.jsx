import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, Legend, ReferenceLine, CartesianGrid } from 'recharts'
import MetricCard from './MetricCard'

const TOOLTIP = { backgroundColor: '#141c2e', border: '1px solid rgba(232,145,122,0.2)', borderRadius: 8 }
const TICK = { fill: '#5c6370', fontSize: 11 }

const COUNTRY_NAMES = {
  DE: 'Deutschland', FR: 'Frankreich', US: 'USA', GB: 'Großbritannien',
  JP: 'Japan', CN: 'China', KR: 'Südkorea', NL: 'Niederlande',
  CH: 'Schweiz', IT: 'Italien', SE: 'Schweden', ES: 'Spanien',
  AT: 'Österreich', BE: 'Belgien', FI: 'Finnland', DK: 'Dänemark',
  NO: 'Norwegen', IL: 'Israel', CA: 'Kanada', AU: 'Australien',
  TW: 'Taiwan', IN: 'Indien', SG: 'Singapur', IE: 'Irland',
  PT: 'Portugal', PL: 'Polen', CZ: 'Tschechien', HU: 'Ungarn',
  RO: 'Rumänien', GR: 'Griechenland', LU: 'Luxemburg', EP: 'Europa (EP)',
}

function GrowthTooltipContent({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const entry = payload[0]?.payload
  return (
    <div style={TOOLTIP} className="px-3 py-2 text-xs">
      <p className="text-[#f1f0ee] font-medium mb-1">{label}</p>
      {entry?.patents !== undefined && (
        <p className="text-[#e8917a]">Patente: {entry.patents?.toLocaleString()}{entry.patents_growth != null ? ` (${entry.patents_growth > 0 ? '+' : ''}${entry.patents_growth}%)` : ''}</p>
      )}
      {entry?.projects !== undefined && (
        <p className="text-[#f0abfc]">Projekte: {entry.projects?.toLocaleString()}{entry.projects_growth != null ? ` (${entry.projects_growth > 0 ? '+' : ''}${entry.projects_growth}%)` : ''}</p>
      )}
      {entry?.publications > 0 && (
        <p className="text-[#fbbf24]">Publikationen: {entry.publications?.toLocaleString()}{entry.publications_growth != null ? ` (${entry.publications_growth > 0 ? '+' : ''}${entry.publications_growth}%)` : ''}</p>
      )}
    </div>
  )
}

export default function LandscapePanel({ data }) {
  if (!data) return <PanelSkeleton title="Landschaft" />

  const countries = (data.top_countries || []).slice(0, 8).map(c => ({
    ...c,
    country_name: COUNTRY_NAMES[c.country] || c.country,
  }))
  const hasPublications = data.total_publications > 0
  const growthData = (data.time_series || []).filter(d => d.patents_growth !== undefined)

  return (
    <div className="bg-white/[0.03] border border-white/[0.08] rounded-xl p-6">
      <h3 className="text-lg font-semibold mb-4">Landschaft (UC1)</h3>

      <div className={`grid ${hasPublications ? 'grid-cols-3' : 'grid-cols-2'} gap-3 mb-4`}>
        <MetricCard title="Patente" value={data.total_patents?.toLocaleString() || 0} subtitle="EPO DOCDB" />
        <MetricCard title="Projekte" value={data.total_projects?.toLocaleString() || 0} subtitle="EU CORDIS" />
        {hasPublications && (
          <MetricCard title="Publikationen" value={data.total_publications?.toLocaleString() || 0} subtitle="OpenAIRE" />
        )}
      </div>

      {growthData.length > 1 && (
        <div className="h-64 mb-4">
          <p className="text-xs text-[#5c6370] mb-1">Wachstumsraten (% YoY)</p>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={growthData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="year" tick={TICK} tickLine={false} />
              <YAxis tick={TICK} tickLine={false} axisLine={false} unit="%" />
              <Tooltip content={<GrowthTooltipContent />} />
              <ReferenceLine y={0} stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="patents_growth" stroke="#e8917a" strokeWidth={2} dot={false} name="Patente" connectNulls />
              <Line type="monotone" dataKey="projects_growth" stroke="#f0abfc" strokeWidth={2} dot={false} name="Projekte" connectNulls />
              {hasPublications && (
                <Line type="monotone" dataKey="publications_growth" stroke="#fbbf24" strokeWidth={2} dot={false} name="Publikationen" connectNulls />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {countries.length > 0 && (
        <div className="h-48">
          <p className="text-xs text-[#5c6370] mb-1">Top Länder</p>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={countries} layout="vertical">
              <XAxis type="number" tick={{ fill: '#5c6370', fontSize: 10 }} tickLine={false} axisLine={false} />
              <YAxis type="category" dataKey="country_name" tick={{ fill: '#5c6370', fontSize: 10 }} width={100} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={TOOLTIP} />
              <Bar dataKey="patents" stackId="1" fill="#e8917a" name="Patente" />
              <Bar dataKey="projects" stackId="1" fill="#f0abfc" name="Projekte" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="mt-4 pt-3 border-t border-white/[0.06]">
        <p className="text-[10px] text-[#5c6370] leading-relaxed">
          Quellen: Watts & Porter (1997) — Normalisierte YoY-Wachstumsraten; EPO DOCDB, CORDIS, OpenAIRE
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
