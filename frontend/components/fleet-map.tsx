"use client"

import { useMemo } from "react"
import { type RebalanceMove, type Zone } from "@/lib/fleet-data"
import { cn } from "@/lib/utils"

interface FleetMapProps {
  mode: "before" | "proposed"
  zones: Zone[]
  moves: RebalanceMove[]
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

export function FleetMap({ mode, zones: baseZones, moves }: FleetMapProps) {
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

  return (
    <div data-tour="movement-routes" className="relative h-full w-full overflow-hidden rounded-lg border border-white/10 bg-[#0a0c0f]">
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
            return fill === "none" ? null : <circle key={zone.id} cx={zone.x} cy={zone.y} r={(3.2 + 6 * zone.available_scooters / maxCount) * 1.6} fill={fill} />
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
            return <g key={zone.id}><circle cx={zone.x} cy={zone.y} r={3.2 + 6 * zone.available_scooters / maxCount} fill="#111318" stroke={color} strokeWidth="0.5" /><circle cx={zone.x} cy={zone.y} r="0.6" fill={color} /></g>
          })}
        </g>
      </svg>
      <div className="absolute inset-0">
        {zones.map((zone) => {
          const radius = 3.2 + 6 * zone.available_scooters / maxCount
          const tone = gapTone(zone.share_gap_pct_points, maxGap)
          const toneClass = tone === "under" ? "border-red-500/40 bg-red-500/10 text-red-300" : tone === "gap" ? "border-amber-500/40 bg-amber-500/10 text-amber-300" : tone === "over" ? "border-sky-500/40 bg-sky-500/10 text-sky-300" : "border-white/15 bg-white/5 text-zinc-300"
          return <div key={zone.id} className="absolute flex -translate-x-1/2 flex-col items-center gap-1 text-center" style={{ left: `${zone.x}%`, top: `calc(${zone.y}% + ${radius * 1.05}%)` }}>
            <div className={cn("whitespace-nowrap rounded-full border px-1.5 py-0.5 text-[10px] font-medium leading-none tabular-nums", toneClass)}>{zone.available_scooters} scooters</div>
            <div className="whitespace-nowrap text-[9px] font-medium tabular-nums text-zinc-400">Demand {zone.predicted_demand_share_pct.toFixed(1)}% · Supply {zone.supply_share_pct.toFixed(1)}% · Gap {zone.share_gap_pct_points >= 0 ? "+" : ""}{zone.share_gap_pct_points.toFixed(1)} pp</div>
            <div className="text-[9px] font-medium uppercase tracking-wider text-zinc-500">{zone.community}</div>
          </div>
        })}
        {mode === "proposed" && moves.map((move) => {
          const from = zoneMap.get(move.source)
          const to = zoneMap.get(move.destination)
          if (!from || !to) return null
          const { cx, cy } = curvePath(from, to)
          return <div key={move.id} className="absolute -translate-x-1/2 -translate-y-1/2 rounded-sm border border-cyan-400/40 bg-[#0a0c0f]/90 px-1 py-0.5 text-[9px] font-medium text-cyan-300 tabular-nums" style={{ left: `${cx}%`, top: `${cy}%` }}>+{move.scooters}</div>
        })}
      </div>
    </div>
  )
}
