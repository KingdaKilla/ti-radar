import { useRef, useEffect } from 'react'
import * as d3 from 'd3'
import { sankey as d3Sankey, sankeyLinkHorizontal, sankeyLeft } from 'd3-sankey'

const CATEGORY_COLORS = {
  actor: '#e8917a',
  cpc: '#3b82f6',
  programme: '#10b981',
}

const CATEGORY_LABELS = {
  actor: 'Akteure',
  cpc: 'CPC-Sektionen',
  programme: 'Programme',
}

export default function SankeyDiagram({ nodes, links }) {
  const svgRef = useRef(null)

  useEffect(() => {
    if (!nodes || nodes.length < 2 || !links || links.length === 0) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const width = 600
    const height = Math.max(350, nodes.length * 18)

    const g = svg
      .attr('viewBox', `0 0 ${width} ${height}`)
      .append('g')

    // Tooltip
    const tooltip = d3.select(svgRef.current.parentNode)
      .selectAll('.sankey-tooltip')
      .data([0])
      .join('div')
      .attr('class', 'sankey-tooltip')
      .style('position', 'absolute')
      .style('pointer-events', 'none')
      .style('background', '#141c2e')
      .style('border', '1px solid rgba(232,145,122,0.2)')
      .style('border-radius', '6px')
      .style('padding', '6px 10px')
      .style('font-size', '11px')
      .style('color', '#e5e7eb')
      .style('opacity', 0)
      .style('z-index', 50)

    // Sankey-Layout
    const sankeyLayout = d3Sankey()
      .nodeWidth(12)
      .nodePadding(8)
      .nodeAlign(sankeyLeft)
      .extent([[20, 20], [width - 20, height - 20]])

    // Daten kopieren (d3-sankey mutiert)
    const { nodes: sNodes, links: sLinks } = sankeyLayout({
      nodes: nodes.map(d => ({ ...d })),
      links: links.map(d => ({ ...d })),
    })

    // Links zeichnen
    g.append('g')
      .selectAll('path')
      .data(sLinks)
      .join('path')
      .attr('d', sankeyLinkHorizontal())
      .attr('fill', 'none')
      .attr('stroke', d => CATEGORY_COLORS[d.source.category] || '#6b7280')
      .attr('stroke-opacity', 0.3)
      .attr('stroke-width', d => Math.max(1, d.width))
      .style('cursor', 'pointer')
      .on('mouseover', function (event, d) {
        d3.select(this).attr('stroke-opacity', 0.6)
        tooltip.style('opacity', 1)
          .html(`${d.source.name} → ${d.target.name}<br/>Aktivitaeten: <strong>${d.value}</strong>`)
      })
      .on('mousemove', (event) => {
        const rect = svgRef.current.parentNode.getBoundingClientRect()
        tooltip
          .style('left', `${event.clientX - rect.left + 12}px`)
          .style('top', `${event.clientY - rect.top - 10}px`)
      })
      .on('mouseout', function () {
        d3.select(this).attr('stroke-opacity', 0.3)
        tooltip.style('opacity', 0)
      })

    // Knoten zeichnen
    g.append('g')
      .selectAll('rect')
      .data(sNodes)
      .join('rect')
      .attr('x', d => d.x0)
      .attr('y', d => d.y0)
      .attr('width', d => d.x1 - d.x0)
      .attr('height', d => Math.max(1, d.y1 - d.y0))
      .attr('fill', d => CATEGORY_COLORS[d.category] || '#6b7280')
      .attr('opacity', 0.8)

    // Labels
    g.append('g')
      .selectAll('text')
      .data(sNodes)
      .join('text')
      .attr('x', d => d.x0 < width / 2 ? d.x1 + 6 : d.x0 - 6)
      .attr('y', d => (d.y0 + d.y1) / 2)
      .attr('dy', '0.35em')
      .attr('text-anchor', d => d.x0 < width / 2 ? 'start' : 'end')
      .attr('font-size', '9px')
      .attr('fill', '#9ca3af')
      .text(d => d.name.length > 20 ? d.name.slice(0, 17) + '...' : d.name)

    return () => tooltip.remove()
  }, [nodes, links])

  if (!nodes || nodes.length < 2) {
    return <p className="text-[#5c6370] text-sm py-8 text-center">Keine Sankey-Daten verfuegbar</p>
  }

  return (
    <div className="relative">
      <svg ref={svgRef} className="w-full" style={{ minHeight: 280 }} />
      <div className="flex gap-3 mt-2 justify-center">
        {Object.entries(CATEGORY_COLORS).map(([cat, color]) => (
          <div key={cat} className="flex items-center gap-1 text-[10px] text-[#5c6370]">
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
            {CATEGORY_LABELS[cat]}
          </div>
        ))}
      </div>
    </div>
  )
}
