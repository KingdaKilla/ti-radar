import MaturityPanel from './MaturityPanel'
import LandscapePanel from './LandscapePanel'
import CompetitivePanel from './CompetitivePanel'
import FundingPanel from './FundingPanel'
import CpcFlowPanel from './CpcFlowPanel'

export default function RadarGrid({ data }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 lg:gap-6">
      <LandscapePanel data={data?.landscape} />
      <MaturityPanel data={data?.maturity} />
      <CompetitivePanel data={data?.competitive} />
      <FundingPanel data={data?.funding} />
      <CpcFlowPanel data={data?.cpc_flow} />
    </div>
  )
}
