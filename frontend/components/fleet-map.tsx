"use client"

import { type CSSProperties, useLayoutEffect, useMemo, useRef, useState } from "react"
import { type RebalanceMove, type Zone } from "@/lib/fleet-data"
import { cn } from "@/lib/utils"

interface FleetMapProps {
  mode: "before" | "proposed"
  zones: Zone[]
  moves: RebalanceMove[]
}

const rightLabelCommunities = new Set([
  "Edgewater",
  "Uptown",
  "Lake View",
  "Lincoln Park",
])

const zoneCircleScale = 0.5625
const labelViewportInset = 8
const labelGap = 8

type Rect = { left: number; top: number; width: number; height: number }
type Point = { x: number; y: number }
type LabelCandidate = "right" | "left" | "below" | "above"
type LabelPosition = Rect & { alignment: "left" | "right" | "center" }

function rectsIntersect(a: Rect, b: Rect) {
  return a.left < b.left + b.width && a.left + a.width > b.left && a.top < b.top + b.height && a.top + a.height > b.top
}

function pointInRect(point: Point, rect: Rect) {
  return point.x >= rect.left && point.x <= rect.left + rect.width && point.y >= rect.top && point.y <= rect.top + rect.height
}

function orientation(a: Point, b: Point, c: Point) {
  return Math.sign((b.y - a.y) * (c.x - b.x) - (b.x - a.x) * (c.y - b.y))
}

function segmentsIntersect(a: Point, b: Point, c: Point, d: Point) {
  const abC = orientation(a, b, c)
  const abD = orientation(a, b, d)
  const cdA = orientation(c, d, a)
  const cdB = orientation(c, d, b)
  return abC !== abD && cdA !== cdB
}

function segmentIntersectsRect(start: Point, end: Point, rect: Rect) {
  if (pointInRect(start, rect) || pointInRect(end, rect)) return true
  const topLeft = { x: rect.left, y: rect.top }
  const topRight = { x: rect.left + rect.width, y: rect.top }
  const bottomLeft = { x: rect.left, y: rect.top + rect.height }
  const bottomRight = { x: rect.left + rect.width, y: rect.top + rect.height }
  return segmentsIntersect(start, end, topLeft, topRight)
    || segmentsIntersect(start, end, topRight, bottomRight)
    || segmentsIntersect(start, end, bottomRight, bottomLeft)
    || segmentsIntersect(start, end, bottomLeft, topLeft)
}

function labelCandidateOrder(zone: Zone): LabelCandidate[] {
  return rightLabelCommunities.has(zone.community)
    ? ["right", "left", "below", "above"]
    : ["below", "right", "left", "above"]
}

function labelCandidatePosition(zone: Zone, candidate: LabelCandidate, center: Point, radius: Point, label: Pick<Rect, "width" | "height">): LabelPosition {
  const verticalNudge = zone.community === "West Town" || zone.community === "Lincoln Park" ? -15 : 0

  switch (candidate) {
    case "right":
      return { left: center.x + radius.x + labelGap - (zone.community === "Lake View" ? 30 : 0), top: center.y - label.height / 2 + verticalNudge, width: label.width, height: label.height, alignment: "left" }
    case "left":
      return { left: center.x - radius.x - labelGap - label.width + (zone.community === "Logan Square" ? 10 : 0), top: center.y - label.height / 2 + verticalNudge, width: label.width, height: label.height, alignment: "right" }
    case "above":
      return { left: center.x - label.width / 2, top: center.y - radius.y - labelGap - label.height + verticalNudge, width: label.width, height: label.height, alignment: "center" }
    default:
      return { left: center.x - label.width / 2, top: center.y + radius.y + labelGap + verticalNudge, width: label.width, height: label.height, alignment: "center" }
  }
}

function isInsideViewport(rect: Rect, width: number, height: number) {
  return rect.left >= labelViewportInset
    && rect.top >= labelViewportInset
    && rect.left + rect.width <= width - labelViewportInset
    && rect.top + rect.height <= height - labelViewportInset
}

function positionsMatch(current: Map<string, LabelPosition>, next: Map<string, LabelPosition>) {
  if (current.size !== next.size) return false
  for (const [id, position] of next) {
    const existing = current.get(id)
    if (!existing || existing.left !== position.left || existing.top !== position.top || existing.alignment !== position.alignment) return false
  }
  return true
}

function applyMoves(zones: Zone[], moves: RebalanceMove[]) {
  const next = new Map(zones.map((zone) => [zone.community, { ...zone }]))
  for (const move of moves) {
    const source = next.get(move.source)
    const destination = next.get(move.destination)
    if (source) source.available_scooters -= move.scooters
    if (destination) destination.available_scooters += move.scooters
  }

  const totalSupply = Math.max(Array.from(next.values()).reduce((total, zone) => total + zone.available_scooters, 0), 1)
  for (const zone of next.values()) {
    zone.supply_share_pct = 100 * zone.available_scooters / totalSupply
    zone.share_gap_pct_points = zone.predicted_demand_share_pct - zone.supply_share_pct
  }
  return Array.from(next.values())
}

function gapColor(shareGapPctPoints: number, maxGap: number) {
  if (shareGapPctPoints >= maxGap * 0.55) return "#ef4444"
  if (shareGapPctPoints > 0) return "#f59e0b"
  if (shareGapPctPoints <= -maxGap * 0.4) return "#0ea5e9"
  return "#52525b"
}

function gapTone(shareGapPctPoints: number, maxGap: number) {
  if (shareGapPctPoints >= maxGap * 0.55) return "under"
  if (shareGapPctPoints > 0) return "gap"
  if (shareGapPctPoints <= -maxGap * 0.4) return "over"
  return "balanced"
}

function formatSignedGap(shareGapPctPoints: number) {
  return `${shareGapPctPoints >= 0 ? "+" : "−"}${Math.abs(shareGapPctPoints).toFixed(1)}`
}

function curvePath(from: Zone, to: Zone) {
  const mx = (from.x + to.x) / 2
  const my = (from.y + to.y) / 2
  const dx = to.x - from.x
  const dy = to.y - from.y
  const len = Math.sqrt(dx * dx + dy * dy) || 1
  const nx = -dy / len
  const ny = dx / len
  const bend = Math.min(len * 0.28, 14)
  const cx = mx + nx * bend
  const cy = my + ny * bend
  return { d: `M ${from.x} ${from.y} Q ${cx} ${cy} ${to.x} ${to.y}`, cx, cy }
}

function routeSegments(moves: RebalanceMove[], zoneMap: Map<string, Zone>, width: number, height: number) {
  const segments: Array<[Point, Point]> = []
  for (const move of moves) {
    const from = zoneMap.get(move.source)
    const to = zoneMap.get(move.destination)
    if (!from || !to) continue
    const { cx, cy } = curvePath(from, to)
    let previous = { x: from.x * width / 100, y: from.y * height / 100 }
    for (let step = 1; step <= 20; step += 1) {
      const t = step / 20
      const inverseT = 1 - t
      const next = {
        x: (inverseT * inverseT * from.x + 2 * inverseT * t * cx + t * t * to.x) * width / 100,
        y: (inverseT * inverseT * from.y + 2 * inverseT * t * cy + t * t * to.y) * height / 100,
      }
      segments.push([previous, next])
      previous = next
    }
  }
  return segments
}

function detailPlacement(zone: Zone, radius: number) {
  const placeLeft = zone.x > 68
  const placeAbove = zone.y > 76

  return {
    left: `calc(${zone.x}% ${placeLeft ? "-" : "+"} ${radius + 3.5}%)`,
    top: `calc(${zone.y}% ${placeAbove ? "-" : "+"} ${radius + 2.5}%)`,
    transform: `translate(${placeLeft ? "-100%" : "0"}, ${placeAbove ? "-100%" : "0"})`,
  }
}

export function FleetMap({ mode, zones: baseZones, moves }: FleetMapProps) {
  const [hoveredZoneId, setHoveredZoneId] = useState<string | null>(null)
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null)
  const [labelPositions, setLabelPositions] = useState<Map<string, LabelPosition>>(new Map())
  const mapRef = useRef<HTMLDivElement>(null)
  const labelRefs = useRef(new Map<string, HTMLButtonElement>())
  const badgeRefs = useRef(new Map<string, HTMLDivElement>())
  const zones = useMemo(
    () => (mode === "proposed" ? applyMoves(baseZones, moves) : baseZones),
    [baseZones, mode, moves],
  )
  const zoneMap = useMemo(() => new Map(zones.map((zone) => [zone.community, zone])), [zones])
  const maxCount = Math.max(...zones.map((zone) => zone.available_scooters), 1)
  const maxGap = Math.max(...zones.map((zone) => Math.abs(zone.share_gap_pct_points)), 1)
  const streets = useMemo(() => [
    { x1: 0, y1: 20, x2: 100, y2: 16 }, { x1: 0, y1: 45, x2: 100, y2: 48 },
    { x1: 0, y1: 68, x2: 100, y2: 64 }, { x1: 20, y1: 0, x2: 26, y2: 100 },
    { x1: 46, y1: 0, x2: 50, y2: 100 }, { x1: 68, y1: 0, x2: 64, y2: 100 },
  ], [])

  useLayoutEffect(() => {
    const map = mapRef.current
    if (!map) return

    const layoutLabels = () => {
      const mapBounds = map.getBoundingClientRect()
      if (!mapBounds.width || !mapBounds.height) return

      const circleBounds = new Map(zones.map((zone) => {
        const baseRadius = (3.2 + 6 * zone.available_scooters / maxCount) * zoneCircleScale * 1.6
        return [zone.id, {
          left: zone.x * mapBounds.width / 100 - baseRadius * mapBounds.width / 100,
          top: zone.y * mapBounds.height / 100 - baseRadius * mapBounds.height / 100,
          width: baseRadius * mapBounds.width * 2 / 100,
          height: baseRadius * mapBounds.height * 2 / 100,
        }]
      }))
      const badgeBounds = mode === "proposed"
        ? Array.from(badgeRefs.current.values()).map((badge) => {
            const bounds = badge.getBoundingClientRect()
            return { left: bounds.left - mapBounds.left, top: bounds.top - mapBounds.top, width: bounds.width, height: bounds.height }
          })
        : []
      const arcSegments = mode === "proposed" ? routeSegments(moves, zoneMap, mapBounds.width, mapBounds.height) : []
      const placedBounds: Rect[] = []
      const nextPositions = new Map<string, LabelPosition>()
      const orderedZones = [...zones].sort((a, b) => a.y - b.y || b.x - a.x || a.community.localeCompare(b.community))

      for (const zone of orderedZones) {
        const label = labelRefs.current.get(zone.id)
        if (!label) continue
        const labelBounds = label.getBoundingClientRect()
        const labelSize = { width: labelBounds.width, height: labelBounds.height }
        const center = { x: zone.x * mapBounds.width / 100, y: zone.y * mapBounds.height / 100 }
        const ownCircle = circleBounds.get(zone.id)
        const radius = ownCircle
          ? { x: ownCircle.width / 2, y: ownCircle.height / 2 }
          : { x: 0, y: 0 }

        const position = labelCandidateOrder(zone)
          .map((candidate) => labelCandidatePosition(zone, candidate, center, radius, labelSize))
          .find((candidate) => isInsideViewport(candidate, mapBounds.width, mapBounds.height)
            && !placedBounds.some((placed) => rectsIntersect(candidate, placed))
            && !Array.from(circleBounds.entries()).some(([id, circle]) => id !== zone.id && rectsIntersect(candidate, circle))
            && !badgeBounds.some((badge) => rectsIntersect(candidate, badge))
            && !arcSegments.some(([start, end]) => segmentIntersectsRect(start, end, candidate)))

        if (position) {
          nextPositions.set(zone.id, position)
          placedBounds.push(position)
        }
      }

      setLabelPositions((current) => positionsMatch(current, nextPositions) ? current : nextPositions)
    }

    layoutLabels()
    const observer = new ResizeObserver(layoutLabels)
    observer.observe(map)
    return () => observer.disconnect()
  }, [maxCount, mode, moves, zoneMap, zones])

  return (
    <div ref={mapRef} data-tour="movement-routes" className="relative h-full min-w-[760px] w-full overflow-hidden rounded-lg border border-white/10 bg-[#0a0c0f]">
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 h-full w-full">
        <defs>
          <radialGradient id="gap-red" cx="50%" cy="50%" r="50%"><stop offset="0%" stopColor="#ef4444" stopOpacity="0.45" /><stop offset="100%" stopColor="#ef4444" stopOpacity="0" /></radialGradient>
          <radialGradient id="gap-amber" cx="50%" cy="50%" r="50%"><stop offset="0%" stopColor="#f59e0b" stopOpacity="0.4" /><stop offset="100%" stopColor="#f59e0b" stopOpacity="0" /></radialGradient>
          <radialGradient id="gap-cyan" cx="50%" cy="50%" r="50%"><stop offset="0%" stopColor="#0ea5e9" stopOpacity="0.32" /><stop offset="100%" stopColor="#0ea5e9" stopOpacity="0" /></radialGradient>
          <marker id="arrow-cyan" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#22d3ee" /></marker>
        </defs>
        <g stroke="#ffffff" strokeOpacity="0.04" strokeWidth="0.35">
          {streets.map((street, index) => <line key={index} x1={street.x1} y1={street.y1} x2={street.x2} y2={street.y2} />)}
        </g>
        <rect x="0" y="0" width="100" height="100" fill="none" stroke="#ffffff" strokeOpacity="0.06" strokeWidth="0.6" />
        <g>
          {zones.map((zone) => {
            const tone = gapTone(zone.share_gap_pct_points, maxGap)
            const fill = tone === "under" ? "url(#gap-red)" : tone === "gap" ? "url(#gap-amber)" : tone === "over" ? "url(#gap-cyan)" : "none"
            return fill === "none" ? null : <circle key={zone.id} cx={zone.x} cy={zone.y} r={(3.2 + 6 * zone.available_scooters / maxCount) * zoneCircleScale * 1.6} fill={fill} />
          })}
        </g>
        {mode === "proposed" && <g fill="none">
          {moves.map((move, index) => {
            const from = zoneMap.get(move.source)
            const to = zoneMap.get(move.destination)
            if (!from || !to) return null
            const { d } = curvePath(from, to)
            const duration = 6 + ((index * 1.7) % 4)
            const delay = (index * 1.1) % 3
            return <path key={move.id} d={d} stroke="#22d3ee" strokeWidth="0.55" strokeOpacity="0.85" markerEnd="url(#arrow-cyan)" strokeDasharray="2.2 1.6" className="fleet-dash" style={{ animation: `dash ${duration}s ease-in-out infinite`, animationDelay: `${delay}s` }} />
          })}
        </g>}
        <g>
          {zones.map((zone) => {
            const color = gapColor(zone.share_gap_pct_points, maxGap)
            return <g key={zone.id}><circle cx={zone.x} cy={zone.y} r={(3.2 + 6 * zone.available_scooters / maxCount) * zoneCircleScale} fill="#111318" stroke={color} strokeWidth="0.5" /><circle cx={zone.x} cy={zone.y} r={0.6 * zoneCircleScale} fill={color} /></g>
          })}
        </g>
      </svg>
      <div
        className="absolute inset-0"
        onClick={(event) => {
          if (event.target === event.currentTarget) setSelectedZoneId(null)
        }}
      >
        {zones.map((zone) => {
          const radius = 3.2 + 6 * zone.available_scooters / maxCount
          const tone = gapTone(zone.share_gap_pct_points, maxGap)
          const toneClass = tone === "under" ? "border-red-500/40 bg-red-500/10 text-red-300" : tone === "gap" ? "border-amber-500/40 bg-amber-500/10 text-amber-300" : tone === "over" ? "border-sky-500/40 bg-sky-500/10 text-sky-300" : "border-white/15 bg-white/5 text-zinc-300"
          const gapTextClass = tone === "under" ? "text-red-300" : tone === "gap" ? "text-amber-300" : tone === "over" ? "text-sky-300" : "text-zinc-300"
          const labelPosition = labelPositions.get(zone.id)
          const alignmentClass = labelPosition?.alignment === "right" ? "items-end text-right" : labelPosition?.alignment === "left" ? "items-start text-left" : "items-center text-center"
          const labelStyle: CSSProperties = labelPosition
            ? { left: `${labelPosition.left}px`, top: `${labelPosition.top}px` }
            : { left: "50%", top: "50%", visibility: "hidden" }
          return <button
            key={zone.id}
            type="button"
            aria-label={`Inspect ${zone.community}`}
            ref={(node) => {
              if (node) labelRefs.current.set(zone.id, node)
              else labelRefs.current.delete(zone.id)
            }}
            className={cn("absolute z-10 flex flex-col gap-1.5 outline-none focus-visible:ring-1 focus-visible:ring-cyan-300/80", alignmentClass)}
            style={labelStyle}
            onMouseEnter={() => setHoveredZoneId(zone.id)}
            onMouseLeave={() => setHoveredZoneId(null)}
            onFocus={() => setHoveredZoneId(zone.id)}
            onBlur={() => setHoveredZoneId(null)}
            onClick={(event) => {
              event.stopPropagation()
              setSelectedZoneId(zone.id)
            }}
          >
            <span className="flex items-center gap-1.5 whitespace-nowrap">
              <span className={cn("rounded-full border px-1.5 py-0.5 text-[10px] font-medium leading-none tabular-nums", toneClass)}>{zone.available_scooters} scooters</span>
              <span className={cn("text-[10px] font-medium leading-none tabular-nums", gapTextClass)}>Gap {formatSignedGap(zone.share_gap_pct_points)} pp</span>
            </span>
            <span className="whitespace-nowrap text-[9px] font-semibold uppercase tracking-wider text-zinc-400">{zone.community}</span>
          </button>
        })}
        {(() => {
          const activeZone = zones.find((zone) => zone.id === (hoveredZoneId ?? selectedZoneId))
          if (!activeZone) return null

          const radius = 3.2 + 6 * activeZone.available_scooters / maxCount
          const status = activeZone.share_gap_pct_points > 0 ? "Under-supplied" : activeZone.share_gap_pct_points < 0 ? "Over-supplied" : "Balanced"

          return <div
            role="status"
            className="pointer-events-none absolute z-30 min-w-40 rounded-md border border-white/10 bg-[#111318]/95 px-3 py-2 shadow-lg shadow-black/40 backdrop-blur-sm"
            style={detailPlacement(activeZone, radius)}
          >
            <div className="text-[10px] font-semibold uppercase tracking-wider text-zinc-200">{activeZone.community}</div>
            <div className="mt-0.5 text-[10px] tabular-nums text-zinc-400">{activeZone.available_scooters} scooters</div>
            <div className="mt-2 space-y-0.5 text-[10px] leading-4 text-zinc-400">
              <div>Demand share: <span className="tabular-nums text-zinc-200">{activeZone.predicted_demand_share_pct.toFixed(1)}%</span></div>
              <div>Supply share: <span className="tabular-nums text-zinc-200">{activeZone.supply_share_pct.toFixed(1)}%</span></div>
              <div>Gap: <span className="tabular-nums text-zinc-200">{formatSignedGap(activeZone.share_gap_pct_points)} pp</span></div>
              <div>Status: <span className="text-zinc-200">{status}</span></div>
            </div>
          </div>
        })()}
        {mode === "proposed" && moves.map((move) => {
          const from = zoneMap.get(move.source)
          const to = zoneMap.get(move.destination)
          if (!from || !to) return null
          const { cx, cy } = curvePath(from, to)
          return <div
            key={move.id}
            ref={(node) => {
              if (node) badgeRefs.current.set(move.id, node)
              else badgeRefs.current.delete(move.id)
            }}
            className="absolute z-20 -translate-x-1/2 -translate-y-1/2 rounded-sm border border-cyan-400/40 bg-[#0a0c0f]/90 px-1 py-0.5 text-[9px] font-medium text-cyan-300 tabular-nums"
            style={{ left: `${cx}%`, top: `${cy}%` }}
          >+{move.scooters}</div>
        })}
      </div>
    </div>
  )
}
