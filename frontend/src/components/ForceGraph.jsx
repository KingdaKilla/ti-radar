import { useRef, useEffect } from 'react'
import * as d3 from 'd3'

const NODE_COLORS = {
  patent: '#e8917a',
  cordis: '#3b82f6',
  both: '#f0abfc',
}

const TYPE_LABELS = {
  patent: 'Patent',
  cordis: 'CORDIS',
  both: 'Beides',
}

export default function ForceGraph({ nodes, edges }) {
  const svgRef = useRef(null)

  useEffect(() => {
    if (!nodes || nodes.length < 2 || !edges || edges.length === 0) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const width = 500
    const height = 400

    const g = svg
      .attr('viewBox', `0 0 ${width} ${height}`)
      .append('g')

    // Zoom + Pan
    svg.call(
      d3.zoom()
        .scaleExtent([0.3, 3])
        .on('zoom', (event) => g.attr('transform', event.transform))
    )

    // Kopien erstellen (D3 mutiert die Objekte)
    const nodesCopy = nodes.map(d => ({ ...d }))
    const edgesCopy = edges.map(d => ({ ...d }))

    // Skalierung
    const maxCount = d3.max(nodesCopy, d => d.count) || 1
    const rScale = d3.scaleSqrt().domain([0, maxCount]).range([4, 24])
    const maxWeight = d3.max(edgesCopy, d => d.weight) || 1
    const wScale = d3.scaleLinear().domain([0, maxWeight]).range([0.5, 5])

    // Tooltip
    const tooltip = d3.select(svgRef.current.parentNode)
      .selectAll('.force-tooltip')
      .data([0])
      .join('div')
      .attr('class', 'force-tooltip')
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

    // Force-Simulation
    const simulation = d3.forceSimulation(nodesCopy)
      .force('link', d3.forceLink(edgesCopy).id(d => d.id).distance(80))
      .force('charge', d3.forceManyBody().strength(-120))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(d => rScale(d.count) + 2))

    // Kanten
    const link = g.append('g')
      .selectAll('line')
      .data(edgesCopy)
      .join('line')
      .attr('stroke', 'rgba(255,255,255,0.15)')
      .attr('stroke-width', d => wScale(d.weight))

    // Knoten
    const node = g.append('g')
      .selectAll('circle')
      .data(nodesCopy)
      .join('circle')
      .attr('r', d => rScale(d.count))
      .attr('fill', d => NODE_COLORS[d.type] || '#6b7280')
      .attr('stroke', 'rgba(255,255,255,0.2)')
      .attr('stroke-width', 0.5)
      .style('cursor', 'grab')
      .on('mouseover', (event, d) => {
        // Verbundene Kanten hervorheben
        link.attr('stroke', e =>
          e.source.id === d.id || e.target.id === d.id
            ? '#e8917a' : 'rgba(255,255,255,0.08)'
        ).attr('stroke-width', e =>
          e.source.id === d.id || e.target.id === d.id
            ? wScale(e.weight) * 2 : wScale(e.weight) * 0.5
        )
        tooltip.style('opacity', 1)
          .html(`<strong>${d.name}</strong><br/>Aktivitaeten: ${d.count}<br/>Typ: ${TYPE_LABELS[d.type] || d.type}`)
      })
      .on('mousemove', (event) => {
        const rect = svgRef.current.parentNode.getBoundingClientRect()
        tooltip
          .style('left', `${event.clientX - rect.left + 12}px`)
          .style('top', `${event.clientY - rect.top - 10}px`)
      })
      .on('mouseout', () => {
        link.attr('stroke', 'rgba(255,255,255,0.15)')
          .attr('stroke-width', d => wScale(d.weight))
        tooltip.style('opacity', 0)
      })
      .call(d3.drag()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart()
          d.fx = d.x; d.fy = d.y
        })
        .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0)
          d.fx = null; d.fy = null
        })
      )

    // Labels fuer Top-10-Knoten
    const topNodes = [...nodesCopy].sort((a, b) => b.count - a.count).slice(0, 10)
    const topSet = new Set(topNodes.map(n => n.id))
    const labels = g.append('g')
      .selectAll('text')
      .data(nodesCopy.filter(n => topSet.has(n.id)))
      .join('text')
      .attr('font-size', '8px')
      .attr('fill', '#9ca3af')
      .attr('text-anchor', 'middle')
      .attr('pointer-events', 'none')
      .text(d => d.name.length > 15 ? d.name.slice(0, 12) + '...' : d.name)

    // Tick-Update
    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y)
      node
        .attr('cx', d => d.x)
        .attr('cy', d => d.y)
      labels
        .attr('x', d => d.x)
        .attr('y', d => d.y - rScale(d.count) - 4)
    })

    return () => {
      simulation.stop()
      tooltip.remove()
    }
  }, [nodes, edges])

  if (!nodes || nodes.length < 2) {
    return <p className="text-[#5c6370] text-sm py-8 text-center">Keine Netzwerk-Daten verfuegbar</p>
  }

  return (
    <div className="relative">
      <svg ref={svgRef} className="w-full" style={{ minHeight: 300, maxHeight: 450 }} />
      <div className="flex gap-3 mt-2 justify-center">
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1 text-[10px] text-[#5c6370]">
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
            {TYPE_LABELS[type]}
          </div>
        ))}
      </div>
    </div>
  )
}
