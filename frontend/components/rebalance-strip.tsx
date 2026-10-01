"use client"

import { Gauge, MoveRight, Route } from "lucide-react"
import { type AnalysisResult } from "@/lib/fleet-data"
import { Button } from "@/components/ui/button"

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
  return (
    <div data-tour="impact-metrics" className="grid h-full grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-6 overflow-x-auto border-t border-white/10 bg-[#0b0d10] px-4">
      <div className="col-start-2 flex shrink-0 items-center gap-6">
        <Metric icon={MoveRight} label="Scooters Moved" value={analysis ? String(analysis.summary.total_scooters_moved) : "—"} />
        <Metric icon={Route} label="Centroid Scooter-KM" value={analysis ? analysis.summary.total_centroid_scooter_km.toFixed(1) : "—"} />
        <Metric
          icon={Gauge}
          label="Mean Share Gap"
          value={analysis
            ? `${analysis.summary.mean_absolute_share_gap_before_pp.toFixed(2)} pp → ${analysis.summary.mean_absolute_share_gap_after_pp.toFixed(2)} pp`
            : "—"}
        />
        <Metric
          icon={Gauge}
          label="Spatial Imbalance Improvement"
          value={analysis ? analysis.summary.spatial_imbalance_improvement_pct.toFixed(2) : "—"}
          suffix="%"
        />
      </div>

      <Button size="sm" disabled={isRefreshing} onClick={onRefresh} className="col-start-3 shrink-0 justify-self-end bg-cyan-500 text-black hover:bg-cyan-400">
        {isRefreshing ? "Refreshing…" : "Refresh Plan"}
      </Button>
    </div>
  )
}
