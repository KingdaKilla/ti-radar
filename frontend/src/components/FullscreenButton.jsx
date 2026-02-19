export default function FullscreenButton({ isFullscreen, onClick }) {
  return (
    <button
      onClick={onClick}
      title={isFullscreen ? 'Normalansicht' : 'Vollbild'}
      className="p-1 text-[#5c6370] hover:text-[#e8917a] transition-colors"
    >
      {isFullscreen ? (
        /* Compress: 4 L-shapes pointing inward toward center */
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5" />
        </svg>
      ) : (
        /* Expand: 4 L-shapes at corners pointing outward */
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5" />
        </svg>
      )}
    </button>
  )
}
