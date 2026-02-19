export default function AnalysisText({ text }) {
  if (!text) return null

  return (
    <div className="mt-4 mb-1 px-4 py-3 bg-white/[0.02] border border-white/[0.06] rounded-lg">
      <p className="text-xs text-[#9ca3af] leading-relaxed">
        {text}
      </p>
    </div>
  )
}
