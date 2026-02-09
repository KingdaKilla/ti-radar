import SearchBar from './components/SearchBar'
import RadarGrid from './components/RadarGrid'
import ExplainabilityBar from './components/ExplainabilityBar'
import { useRadar } from './hooks/useRadar'

const EXAMPLE_TECHNOLOGIES = [
  'quantum computing',
  'solid-state batteries',
  'hydrogen fuel cells',
  'perovskite solar',
  'CRISPR',
  'carbon capture',
]

export default function App() {
  const { data, loading, error, analyze } = useRadar()

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-white/[0.08] px-4 sm:px-6 lg:px-8 xl:px-12 py-4">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-[#e8917a] to-[#f0a898] bg-clip-text text-transparent">
              Technology Intelligence Dashboard
            </h1>
            <p className="text-xs text-[#5c6370]">
              Technologieanalyse auf Basis öffentlicher Daten
            </p>
          </div>
          <span className="px-3 py-1 bg-[#e8917a]/10 border border-[#e8917a]/20 rounded-full text-xs text-[#e8917a]">
            Prototype 5
          </span>
        </div>
      </header>

      {/* Main */}
      <main className="px-4 sm:px-6 lg:px-8 xl:px-12 py-6">
        <SearchBar onSearch={(q, y) => analyze(q, y)} loading={loading} />

        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-300">
            Fehler: {error}
          </div>
        )}

        {/* Loading skeleton */}
        {loading && !data && (
          <>
            <div className="text-center mb-6">
              <div className="h-8 w-48 bg-white/[0.04] rounded-lg mx-auto mb-2 animate-pulse" />
              <div className="h-4 w-32 bg-white/[0.04] rounded mx-auto animate-pulse" />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="bg-white/[0.03] border border-white/[0.08] rounded-xl p-6 animate-pulse">
                  <div className="h-5 w-32 bg-white/[0.06] rounded mb-4" />
                  <div className="h-40 bg-white/[0.04] rounded-lg" />
                </div>
              ))}
            </div>
          </>
        )}

        {data && (
          <>
            <div className="text-center mb-6">
              <h2 className="text-2xl font-bold">{data.technology}</h2>
              <p className="text-sm text-[#5c6370]">{data.analysis_period}</p>
            </div>

            <RadarGrid data={data} />

            <div className="mt-6">
              <ExplainabilityBar data={data.explainability} />
            </div>
          </>
        )}

        {/* Empty state with example chips */}
        {!data && !loading && !error && (
          <div className="text-center mt-16">
            <div className="text-5xl mb-4 opacity-30">
              <svg className="w-16 h-16 mx-auto text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <p className="text-lg text-[#5c6370] mb-2">Technologie eingeben und analysieren</p>
            <p className="text-sm text-[#5c6370]/70 mb-6">
              Patente, Projekte und Förderungen auf einen Blick
            </p>

            <div className="flex flex-wrap justify-center gap-2">
              {EXAMPLE_TECHNOLOGIES.map(tech => (
                <button
                  key={tech}
                  onClick={() => analyze(tech)}
                  className="px-4 py-2 bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] hover:border-[#e8917a]/30 rounded-full text-sm text-[#9ca3af] hover:text-white transition-all cursor-pointer"
                >
                  {tech}
                </button>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
