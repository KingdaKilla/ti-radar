import { useState } from 'react'
import MaturityPanel from './MaturityPanel'
import LandscapePanel from './LandscapePanel'
import CompetitivePanel from './CompetitivePanel'
import FundingPanel from './FundingPanel'
import CpcFlowPanel from './CpcFlowPanel'
import GeographicPanel from './GeographicPanel'
import ResearchImpactPanel from './ResearchImpactPanel'
import TemporalPanel from './TemporalPanel'

export default function RadarGrid({ data, compact }) {
  const [selectedActor, setSelectedActor] = useState(null)

  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 gap-4 lg:gap-6 ${compact ? 'text-sm' : ''}`}>
      <LandscapePanel data={data?.landscape} compact={compact} />
      <MaturityPanel data={data?.maturity} compact={compact} />
      <CompetitivePanel data={data?.competitive} onSelectActor={setSelectedActor} compact={compact} />
      <FundingPanel data={data?.funding} selectedActor={selectedActor} compact={compact} />
      <GeographicPanel data={data?.geographic} compact={compact} />
      <TemporalPanel data={data?.temporal} compact={compact} />
      <CpcFlowPanel data={data?.cpc_flow} compact={compact} />
      <ResearchImpactPanel data={data?.research_impact} compact={compact} />
    </div>
  )
}
