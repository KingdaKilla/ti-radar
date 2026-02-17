export default function DownloadButton({ onClick, title = 'Als CSV exportieren' }) {
  return (
    <button
      onClick={onClick}
      title={title}
      className="p-1 text-[#5c6370] hover:text-[#e8917a] transition-colors"
    >
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
      </svg>
    </button>
  )
}
