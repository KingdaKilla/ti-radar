import { useRef, useEffect } from 'react'
import * as d3 from 'd3'

export default function ChordDiagram({ matrix, labels, colors, cpcSections = {}, cpcDescriptions = {} }) {
  const cpcLabel = (code) => {
    if (!code) return ''
    // Specific description from API (subclass/class level)
    if (cpcDescriptions[code]) return ` — ${cpcDescriptions[code]}`
    if (code.length > 4 && cpcDescriptions[code.slice(0, 4)]) return ` — ${cpcDescriptions[code.slice(0, 4)]}`
    if (code.length > 3 && cpcDescriptions[code.slice(0, 3)]) return ` — ${cpcDescriptions[code.slice(0, 3)]}`
    // Section fallback
    const sec = cpcSections[code[0]]
    return sec ? ` — ${sec}` : ''
  }
  const svgRef = useRef(null)

  useEffect(() => {
    if (!matrix || matrix.length < 2 || !labels || labels.length < 2) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const width = 380
    const height = 380
    const outerRadius = Math.min(width, height) * 0.5 - 40
    const innerRadius = outerRadius - 20

    const g = svg
      .attr('viewBox', `0 0 ${width} ${height}`)
      .append('g')
      .attr('transform', `translate(${width / 2}, ${height / 2})`)

    const chord = d3.chord().padAngle(0.04).sortSubgroups(d3.descending)
    const chords = chord(matrix)
    const arc = d3.arc().innerRadius(innerRadius).outerRadius(outerRadius)
    const ribbon = d3.ribbon().radius(innerRadius - 2)

    // Tooltip
    const tooltip = d3.select(svgRef.current.parentNode)
      .selectAll('.chord-tooltip')
      .data([0])
      .join('div')
      .attr('class', 'chord-tooltip')
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
      .style('white-space', 'pre-line')

    // Arcs (CPC groups)
    g.append('g')
      .selectAll('path')
      .data(chords.groups)
      .join('path')
      .attr('d', arc)
      .attr('fill', d => colors[d.index] || '#6b7280')
      .attr('stroke', 'rgba(255,255,255,0.1)')
      .style('cursor', 'pointer')
      .on('mouseover', function (event, d) {
        // Fade ribbons not connected to this group
        g.selectAll('.ribbon')
          .transition().duration(150)
          .style('opacity', r =>
            r.source.index === d.index || r.target.index === d.index ? 0.85 : 0.1
          )
        tooltip
          .style('opacity', 1)
          .html(`<strong>${labels[d.index]}</strong>${cpcLabel(labels[d.index])}`)
      })
      .on('mousemove', (event) => {
        const rect = svgRef.current.parentNode.getBoundingClientRect()
        tooltip
          .style('left', `${event.clientX - rect.left + 12}px`)
          .style('top', `${event.clientY - rect.top - 10}px`)
      })
      .on('mouseout', () => {
        g.selectAll('.ribbon')
          .transition().duration(150)
          .style('opacity', 0.65)
        tooltip.style('opacity', 0)
      })

    // Labels around arcs
    g.append('g')
      .selectAll('text')
      .data(chords.groups)
      .join('text')
      .each(d => { d.angle = (d.startAngle + d.endAngle) / 2 })
      .attr('dy', '0.35em')
      .attr('transform', d =>
        `rotate(${(d.angle * 180 / Math.PI - 90)})` +
        `translate(${outerRadius + 8})` +
        (d.angle > Math.PI ? 'rotate(180)' : '')
      )
      .attr('text-anchor', d => d.angle > Math.PI ? 'end' : 'start')
      .attr('fill', d => colors[d.index] || '#9ca3af')
      .attr('font-size', '9px')
      .attr('font-family', 'monospace')
      .text(d => labels[d.index])

    // Ribbons (connections)
    g.append('g')
      .selectAll('path')
      .data(chords)
      .join('path')
      .attr('class', 'ribbon')
      .attr('d', ribbon)
      .attr('fill', d => colors[d.source.index] || '#6b7280')
      .attr('fill-opacity', 0.65)
      .attr('stroke', 'rgba(255,255,255,0.05)')
      .style('cursor', 'pointer')
      .on('mouseover', function (event, d) {
        d3.select(this).attr('fill-opacity', 0.9)
        const val = matrix[d.source.index][d.target.index]
        tooltip
          .style('opacity', 1)
          .html(`${labels[d.source.index]}${cpcLabel(labels[d.source.index])}<br>${labels[d.target.index]}${cpcLabel(labels[d.target.index])}<br>Jaccard: <strong>${val.toFixed(4)}</strong>`)
      })
      .on('mousemove', (event) => {
        const rect = svgRef.current.parentNode.getBoundingClientRect()
        tooltip
          .style('left', `${event.clientX - rect.left + 12}px`)
          .style('top', `${event.clientY - rect.top - 10}px`)
      })
      .on('mouseout', function () {
        d3.select(this).attr('fill-opacity', 0.65)
        tooltip.style('opacity', 0)
      })

    return () => {
      tooltip.remove()
      svg.selectAll('*').remove()
    }
  }, [matrix, labels, colors])

  if (!matrix || matrix.length < 2) return null

  return (
    <div className="relative">
      <svg ref={svgRef} className="w-full h-auto" />
    </div>
  )
}
