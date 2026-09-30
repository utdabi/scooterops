"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { ArrowRight, Gauge, MoveRight, Route } from "lucide-react"
import { type AnalysisResult } from "@/lib/fleet-data"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"

function Metric({
  icon: Icon,
  label,
  value,
  suffix,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string
  suffix?: string
}) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex size-9 shrink-0 items-center justify-center rounded-md border border-white/10 bg-white/[0.03]">
        <Icon className="size-4 text-cyan-400" />
      </div>
      <div>
        <p className="text-[10px] uppercase tracking-wider text-zinc-500">{label}</p>
        <p className="text-sm font-semibold tabular-nums text-zinc-100">
          {value}
          {suffix && <span className="ml-1 text-xs font-normal text-zinc-500">{suffix}</span>}
        </p>
      </div>
    </div>
  )
}

interface RebalanceStripProps {
  analysis: AnalysisResult | null
  isRefreshing: boolean
  onRefresh: () => void
}

export function RebalanceStrip({ analysis, isRefreshing, onRefresh }: RebalanceStripProps) {
  const routeRailRef = useRef<HTMLDivElement>(null)
  const [canScrollLeft, setCanScrollLeft] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(false)

  const updateScrollControls = useCallback(() => {
    const routeRail = routeRailRef.current
    if (!routeRail) return

    const maxScrollLeft = routeRail.scrollWidth - routeRail.clientWidth
    setCanScrollLeft(routeRail.scrollLeft > 1)
    setCanScrollRight(routeRail.scrollLeft < maxScrollLeft - 1)
  }, [])

  useEffect(() => {
    const routeRail = routeRailRef.current
    if (!routeRail) return

    updateScrollControls()
    routeRail.addEventListener("scroll", updateScrollControls, { passive: true })
    const resizeObserver = new ResizeObserver(updateScrollControls)
    resizeObserver.observe(routeRail)

    return () => {
      routeRail.removeEventListener("scroll", updateScrollControls)
      resizeObserver.disconnect()
    }
  }, [analysis?.moves, updateScrollControls])

  const scrollRoutes = (left: number) => {
    routeRailRef.current?.scrollBy({ left, behavior: "smooth" })
  }

  return (
    <div data-tour="impact-metrics" className="flex h-full items-center gap-6 overflow-x-auto border-t border-white/10 bg-[#0b0d10] px-4">
      <div className="flex shrink-0 items-center gap-6">
        <Metric icon={MoveRight} label="Scooters Moved" value={analysis ? String(analysis.summary.total_scooters_moved) : "—"} />
        <Metric icon={Route} label="Centroid Scooter-KM" value={analysis ? analysis.summary.total_centroid_scooter_km.toFixed(1) : "—"} />
        <Metric
          icon={Gauge}
          label="Mean Share Gap Before"
          value={analysis ? analysis.summary.mean_absolute_share_gap_before_pp.toFixed(2) : "—"}
          suffix="pp"
        />
        <Metric
          icon={Gauge}
          label="Mean Share Gap After"
          value={analysis ? analysis.summary.mean_absolute_share_gap_after_pp.toFixed(2) : "—"}
          suffix="pp"
        />
        <Metric
          icon={Gauge}
          label="Spatial Imbalance Improvement"
          value={analysis ? analysis.summary.spatial_imbalance_improvement_pct.toFixed(2) : "—"}
          suffix="%"
        />
      </div>

      <Separator orientation="vertical" className="h-8 shrink-0 bg-white/10" />

      <button
        type="button"
        aria-label="Scroll routes left"
        disabled={!canScrollLeft}
        onClick={() => scrollRoutes(-300)}
        className="flex size-5 shrink-0 items-center justify-center rounded-sm border border-white/10 bg-white/[0.02] text-sm leading-none text-zinc-500 transition-colors hover:border-cyan-400/30 hover:text-cyan-300 disabled:cursor-default disabled:opacity-30"
      >
        ‹
      </button>

      <div ref={routeRailRef} className="no-scrollbar flex min-w-0 flex-1 items-center gap-2 overflow-x-auto">
        {analysis?.moves.map((move) => {
          return (
            <div
              key={move.id}
              className="flex shrink-0 items-center gap-1.5 rounded-md border border-white/10 bg-white/[0.02] px-2.5 py-1.5 text-xs"
            >
              <span className="font-medium text-zinc-300">{move.source}</span>
              <ArrowRight className="size-3 text-cyan-400" />
              <span className="font-medium text-zinc-300">{move.destination}</span>
              <span className="ml-1 rounded-full bg-cyan-500/10 px-1.5 py-0.5 font-mono text-[10px] text-cyan-300">
                {move.scooters}
              </span>
            </div>
          )
        })}
      </div>

      <button
        type="button"
        aria-label="Scroll routes right"
        disabled={!canScrollRight}
        onClick={() => scrollRoutes(300)}
        className="flex size-5 shrink-0 items-center justify-center rounded-sm border border-white/10 bg-white/[0.02] text-sm leading-none text-zinc-500 transition-colors hover:border-cyan-400/30 hover:text-cyan-300 disabled:cursor-default disabled:opacity-30"
      >
        ›
      </button>

      <Button size="sm" disabled={isRefreshing} onClick={onRefresh} className="shrink-0 bg-cyan-500 text-black hover:bg-cyan-400">
        {isRefreshing ? "Refreshing…" : "Refresh Plan"}
      </Button>
    </div>
  )
}
